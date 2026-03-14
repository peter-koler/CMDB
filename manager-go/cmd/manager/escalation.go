package main

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"strconv"
	"strings"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/store"
)

const (
	escalationQueueKey    = "alert:escalation:queue"
	escalationStagePrefix = "alert:escalation:stage:"
)

var popDueEscalationLua = strings.Join([]string{
	"local key=KEYS[1]",
	"local now=tonumber(ARGV[1])",
	"local limit=tonumber(ARGV[2])",
	"local items=redis.call('ZRANGEBYSCORE', key, '-inf', now, 'LIMIT', 0, limit)",
	"for _,item in ipairs(items) do",
	"  redis.call('ZREM', key, item)",
	"end",
	"return items",
}, "\n")

type escalationLevel struct {
	Level           int
	DelaySeconds    int
	NoticeRuleIDs   []int64
	TitleTemplate   string
	ContentTemplate string
}

type escalationPolicy struct {
	Enabled bool
	Levels  []escalationLevel
}

type redisEscalationQueue struct {
	addr    string
	timeout time.Duration
}

func newRedisEscalationQueue(addr string, timeout time.Duration) *redisEscalationQueue {
	if strings.TrimSpace(addr) == "" {
		addr = "127.0.0.1:6379"
	}
	if timeout <= 0 {
		timeout = time.Second
	}
	return &redisEscalationQueue{addr: addr, timeout: timeout}
}

func (q *redisEscalationQueue) zAdd(ctx context.Context, key, member string, score int64) error {
	_, err := q.exec(ctx, "ZADD", key, strconv.FormatInt(score, 10), member)
	return err
}

func (q *redisEscalationQueue) zRem(ctx context.Context, key, member string) error {
	_, err := q.exec(ctx, "ZREM", key, member)
	return err
}

func (q *redisEscalationQueue) del(ctx context.Context, keys ...string) error {
	if len(keys) == 0 {
		return nil
	}
	args := append([]string{"DEL"}, keys...)
	_, err := q.exec(ctx, args...)
	return err
}

func (q *redisEscalationQueue) hSet(ctx context.Context, key string, fields map[string]string) error {
	if len(fields) == 0 {
		return nil
	}
	args := []string{"HSET", key}
	for k, v := range fields {
		args = append(args, k, v)
	}
	_, err := q.exec(ctx, args...)
	return err
}

func (q *redisEscalationQueue) hGetAll(ctx context.Context, key string) (map[string]string, error) {
	resp, err := q.exec(ctx, "HGETALL", key)
	if err != nil {
		return nil, err
	}
	arr, ok := resp.([]any)
	if !ok {
		return map[string]string{}, nil
	}
	out := make(map[string]string, len(arr)/2)
	for i := 0; i+1 < len(arr); i += 2 {
		k := strings.TrimSpace(asRESPString(arr[i]))
		if k == "" {
			continue
		}
		out[k] = strings.TrimSpace(asRESPString(arr[i+1]))
	}
	return out, nil
}

func (q *redisEscalationQueue) claimDue(ctx context.Context, nowUnix int64, limit int) ([]string, error) {
	if limit <= 0 {
		limit = 100
	}
	resp, err := q.exec(
		ctx,
		"EVAL",
		popDueEscalationLua,
		"1",
		escalationQueueKey,
		strconv.FormatInt(nowUnix, 10),
		strconv.Itoa(limit),
	)
	if err != nil {
		return nil, err
	}
	arr, ok := resp.([]any)
	if !ok {
		return nil, nil
	}
	out := make([]string, 0, len(arr))
	for _, item := range arr {
		member := strings.TrimSpace(asRESPString(item))
		if member != "" {
			out = append(out, member)
		}
	}
	return out, nil
}

func (q *redisEscalationQueue) exec(ctx context.Context, args ...string) (any, error) {
	if len(args) == 0 {
		return nil, nil
	}
	d := net.Dialer{Timeout: q.timeout}
	conn, err := d.DialContext(ctx, "tcp", q.addr)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(q.timeout))
	if _, err := conn.Write(encodeRESP(args...)); err != nil {
		return nil, err
	}
	reader := bufio.NewReader(conn)
	return readRESP(reader)
}

func encodeRESP(parts ...string) []byte {
	b := strings.Builder{}
	b.WriteString("*")
	b.WriteString(strconv.Itoa(len(parts)))
	b.WriteString("\r\n")
	for _, p := range parts {
		b.WriteString("$")
		b.WriteString(strconv.Itoa(len(p)))
		b.WriteString("\r\n")
		b.WriteString(p)
		b.WriteString("\r\n")
	}
	return []byte(b.String())
}

func readRESP(r *bufio.Reader) (any, error) {
	prefix, err := r.ReadByte()
	if err != nil {
		return nil, err
	}
	switch prefix {
	case '+':
		line, err := readRESPLine(r)
		if err != nil {
			return nil, err
		}
		return line, nil
	case '-':
		line, err := readRESPLine(r)
		if err != nil {
			return nil, err
		}
		return nil, errors.New(line)
	case ':':
		line, err := readRESPLine(r)
		if err != nil {
			return nil, err
		}
		n, parseErr := strconv.ParseInt(line, 10, 64)
		if parseErr != nil {
			return nil, parseErr
		}
		return n, nil
	case '$':
		line, err := readRESPLine(r)
		if err != nil {
			return nil, err
		}
		n, parseErr := strconv.Atoi(line)
		if parseErr != nil {
			return nil, parseErr
		}
		if n < 0 {
			return nil, nil
		}
		buf := make([]byte, n+2)
		if _, err := r.Read(buf); err != nil {
			return nil, err
		}
		return string(buf[:n]), nil
	case '*':
		line, err := readRESPLine(r)
		if err != nil {
			return nil, err
		}
		n, parseErr := strconv.Atoi(line)
		if parseErr != nil {
			return nil, parseErr
		}
		if n < 0 {
			return nil, nil
		}
		out := make([]any, 0, n)
		for i := 0; i < n; i++ {
			item, err := readRESP(r)
			if err != nil {
				return nil, err
			}
			out = append(out, item)
		}
		return out, nil
	default:
		return nil, fmt.Errorf("unsupported resp type: %q", string(prefix))
	}
}

func readRESPLine(r *bufio.Reader) (string, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return "", err
	}
	line = strings.TrimSuffix(line, "\n")
	line = strings.TrimSuffix(line, "\r")
	return line, nil
}

func asRESPString(v any) string {
	switch t := v.(type) {
	case nil:
		return ""
	case string:
		return t
	case int64:
		return strconv.FormatInt(t, 10)
	case int:
		return strconv.Itoa(t)
	default:
		return fmt.Sprintf("%v", v)
	}
}

func buildEscalationGroupKey(ruleID int64, monitorID int64) string {
	return fmt.Sprintf("manager:%d:%d", ruleID, monitorID)
}

func parseEscalationGroupKey(groupKey string) (int64, int64, bool) {
	parts := strings.Split(strings.TrimSpace(groupKey), ":")
	if len(parts) != 3 {
		return 0, 0, false
	}
	ruleID, err1 := strconv.ParseInt(parts[1], 10, 64)
	monitorID, err2 := strconv.ParseInt(parts[2], 10, 64)
	if err1 != nil || err2 != nil || ruleID <= 0 || monitorID <= 0 {
		return 0, 0, false
	}
	return ruleID, monitorID, true
}

func parseEscalationPolicy(raw string, fallbackNotice []int64) escalationPolicy {
	policy := escalationPolicy{}
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return policy
	}
	var parsed any
	if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
		return policy
	}
	enabled := true
	levelsRaw := parsed
	if obj, ok := parsed.(map[string]any); ok {
		if val, exists := obj["enabled"]; exists {
			enabled = toBool(val, true)
		}
		if val, exists := obj["levels"]; exists {
			levelsRaw = val
		} else {
			levelsRaw = []any{}
		}
	}
	items, ok := levelsRaw.([]any)
	if !ok {
		return escalationPolicy{Enabled: enabled}
	}
	levels := make([]escalationLevel, 0, len(items))
	for idx, rawLevel := range items {
		obj, ok := rawLevel.(map[string]any)
		if !ok {
			continue
		}
		delay := toInt(obj["delay_seconds"], 0)
		if delay <= 0 {
			delay = toInt(obj["wait_seconds"], 0)
		}
		if delay <= 0 {
			continue
		}
		level := escalationLevel{
			Level:           maxInt(toInt(obj["level"], idx+1), 1),
			DelaySeconds:    delay,
			TitleTemplate:   strings.TrimSpace(toString(obj["title_template"])),
			ContentTemplate: strings.TrimSpace(toString(obj["content_template"])),
		}
		if level.ContentTemplate == "" {
			level.ContentTemplate = strings.TrimSpace(toString(obj["template"]))
		}
		noticeIDs := parseNoticeIDsAny(obj["notice_rule_ids"])
		if len(noticeIDs) == 0 {
			if one := toInt64(obj["notice_rule_id"], 0); one > 0 {
				noticeIDs = []int64{one}
			}
		}
		if len(noticeIDs) == 0 {
			noticeIDs = append(noticeIDs, fallbackNotice...)
		}
		level.NoticeRuleIDs = uniqueNoticeIDs(noticeIDs)
		levels = append(levels, level)
	}
	if !enabled || len(levels) == 0 {
		return escalationPolicy{Enabled: enabled, Levels: []escalationLevel{}}
	}
	return escalationPolicy{Enabled: true, Levels: levels}
}

func parseNoticeIDsAny(raw any) []int64 {
	arr, ok := raw.([]any)
	if !ok {
		return nil
	}
	out := make([]int64, 0, len(arr))
	for _, item := range arr {
		if v := toInt64(item, 0); v > 0 {
			out = append(out, v)
		}
	}
	return uniqueNoticeIDs(out)
}

func uniqueNoticeIDs(ids []int64) []int64 {
	seen := map[int64]struct{}{}
	out := make([]int64, 0, len(ids))
	for _, id := range ids {
		if id <= 0 {
			continue
		}
		if _, ok := seen[id]; ok {
			continue
		}
		seen[id] = struct{}{}
		out = append(out, id)
	}
	return out
}

func scheduleEscalationForCycle(ctx context.Context, queue *redisEscalationQueue, def store.RuntimeAlertRule, ruleID int64, monitorID int64) error {
	if queue == nil || ruleID <= 0 || monitorID <= 0 {
		return nil
	}
	groupKey := buildEscalationGroupKey(ruleID, monitorID)
	stageKey := escalationStagePrefix + groupKey
	policy := parseEscalationPolicy(def.Escalation, def.NoticeRules)
	if !policy.Enabled || len(policy.Levels) == 0 {
		_ = queue.zRem(ctx, escalationQueueKey, groupKey)
		_ = queue.del(ctx, stageKey)
		return nil
	}
	now := time.Now().Unix()
	first := policy.Levels[0]
	if err := queue.hSet(ctx, stageKey, map[string]string{
		"current_level": "0",
		"rule_id":       strconv.FormatInt(ruleID, 10),
		"monitor_id":    strconv.FormatInt(monitorID, 10),
		"updated_at":    strconv.FormatInt(now, 10),
	}); err != nil {
		return err
	}
	return queue.zAdd(ctx, escalationQueueKey, groupKey, now+int64(first.DelaySeconds))
}

func clearEscalation(ctx context.Context, queue *redisEscalationQueue, ruleID int64, monitorID int64) {
	if queue == nil || ruleID <= 0 || monitorID <= 0 {
		return
	}
	groupKey := buildEscalationGroupKey(ruleID, monitorID)
	stageKey := escalationStagePrefix + groupKey
	_ = queue.zRem(ctx, escalationQueueKey, groupKey)
	_ = queue.del(ctx, stageKey)
}

func runEscalationWorker(
	ctx context.Context,
	interval time.Duration,
	queue *redisEscalationQueue,
	runtimeStore *store.AlertRuntimeStore,
	getRuleDef func(ruleID int64) (store.RuntimeAlertRule, bool),
	enqueueNotice func(ev alert.Event, noticeRuleIDs []int64),
) {
	if queue == nil || runtimeStore == nil || getRuleDef == nil || enqueueNotice == nil {
		return
	}
	if interval <= 0 {
		interval = 10 * time.Second
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			runEscalationTick(ctx, queue, runtimeStore, getRuleDef, enqueueNotice)
		}
	}
}

func runEscalationTick(
	ctx context.Context,
	queue *redisEscalationQueue,
	runtimeStore *store.AlertRuntimeStore,
	getRuleDef func(ruleID int64) (store.RuntimeAlertRule, bool),
	enqueueNotice func(ev alert.Event, noticeRuleIDs []int64),
) {
	nowUnix := time.Now().Unix()
	groupKeys, err := queue.claimDue(ctx, nowUnix, 200)
	if err != nil {
		log.Printf("[Escalation] claim due failed err=%v", err)
		return
	}
	for _, groupKey := range groupKeys {
		ruleID, monitorID, ok := parseEscalationGroupKey(groupKey)
		if !ok {
			_ = queue.del(ctx, escalationStagePrefix+groupKey)
			continue
		}
		snap, exists, err := runtimeStore.LoadSingleAlertSnapshot(ruleID, monitorID)
		if err != nil {
			log.Printf("[Escalation] load snapshot failed rule=%d monitor=%d err=%v", ruleID, monitorID, err)
			_ = queue.zAdd(ctx, escalationQueueKey, groupKey, nowUnix+15)
			continue
		}
		if !exists || snap.Status != "firing" || isAlertAcknowledged(snap) {
			clearEscalation(ctx, queue, ruleID, monitorID)
			continue
		}
		def, exists := getRuleDef(ruleID)
		if !exists {
			clearEscalation(ctx, queue, ruleID, monitorID)
			continue
		}
		policy := parseEscalationPolicy(def.Escalation, def.NoticeRules)
		if !policy.Enabled || len(policy.Levels) == 0 {
			clearEscalation(ctx, queue, ruleID, monitorID)
			continue
		}
		stageKey := escalationStagePrefix + groupKey
		stage, err := queue.hGetAll(ctx, stageKey)
		if err != nil {
			log.Printf("[Escalation] load stage failed rule=%d monitor=%d err=%v", ruleID, monitorID, err)
			_ = queue.zAdd(ctx, escalationQueueKey, groupKey, nowUnix+15)
			continue
		}
		currentLevel := toInt(stage["current_level"], 0)
		if currentLevel < 0 {
			currentLevel = 0
		}
		if currentLevel >= len(policy.Levels) {
			clearEscalation(ctx, queue, ruleID, monitorID)
			continue
		}
		level := policy.Levels[currentLevel]
		if len(level.NoticeRuleIDs) == 0 {
			log.Printf("[Escalation] skip level no notice rule rule=%d monitor=%d level=%d", ruleID, monitorID, level.Level)
		} else {
			ev := buildEscalationEvent(def, snap, ruleID, monitorID, level)
			enqueueNotice(ev, level.NoticeRuleIDs)
			note := fmt.Sprintf("告警升级到 Level %d", level.Level)
			if strings.TrimSpace(ev.Content) != "" {
				note = strings.TrimSpace(ev.Content)
			}
			_ = runtimeStore.AddEscalationHistory(snap.ID, level.Level, note, time.Now())
			log.Printf("[Escalation] notified rule=%d monitor=%d level=%d notice_rules=%v", ruleID, monitorID, level.Level, level.NoticeRuleIDs)
		}
		nextIdx := currentLevel + 1
		if nextIdx >= len(policy.Levels) {
			clearEscalation(ctx, queue, ruleID, monitorID)
			continue
		}
		nextDelay := policy.Levels[nextIdx].DelaySeconds
		if nextDelay <= 0 {
			nextDelay = 60
		}
		if err := queue.hSet(ctx, stageKey, map[string]string{
			"current_level": strconv.Itoa(nextIdx),
			"rule_id":       strconv.FormatInt(ruleID, 10),
			"monitor_id":    strconv.FormatInt(monitorID, 10),
			"updated_at":    strconv.FormatInt(nowUnix, 10),
		}); err != nil {
			log.Printf("[Escalation] save stage failed rule=%d monitor=%d next_level=%d err=%v", ruleID, monitorID, nextIdx, err)
			_ = queue.zAdd(ctx, escalationQueueKey, groupKey, nowUnix+15)
			continue
		}
		if err := queue.zAdd(ctx, escalationQueueKey, groupKey, nowUnix+int64(nextDelay)); err != nil {
			log.Printf("[Escalation] reschedule failed rule=%d monitor=%d next_level=%d err=%v", ruleID, monitorID, nextIdx, err)
		}
	}
}

func isAlertAcknowledged(snap store.RuntimeSingleAlertSnapshot) bool {
	if snap.Status != "firing" {
		return true
	}
	for _, key := range []string{"assignee", "acknowledged_by", "claimed_by", "owner", "handler"} {
		if strings.TrimSpace(snap.Labels[key]) != "" {
			return true
		}
	}
	for _, key := range []string{"ack", "acknowledged", "is_acknowledged"} {
		if toBool(snap.Labels[key], false) {
			return true
		}
	}
	return false
}

func buildEscalationEvent(def store.RuntimeAlertRule, snap store.RuntimeSingleAlertSnapshot, ruleID int64, monitorID int64, level escalationLevel) alert.Event {
	labels := map[string]string{}
	for k, v := range snap.Labels {
		key := strings.TrimSpace(k)
		if key == "" {
			continue
		}
		labels[key] = strings.TrimSpace(v)
	}
	labels["escalation"] = "true"
	labels["escalation_level"] = strconv.Itoa(level.Level)
	app := strings.TrimSpace(labels["app"])
	instance := strings.TrimSpace(labels["instance"])
	if app == "" {
		app = strings.TrimSpace(getRuleLabelString(def.Labels, "app"))
	}
	if instance == "" {
		instance = strings.TrimSpace(getRuleLabelString(def.Labels, "instance"))
	}
	baseContent := strings.TrimSpace(snap.Content)
	if baseContent == "" {
		baseContent = strings.TrimSpace(def.Name)
	}
	content := renderEscalationTemplate(level.ContentTemplate, def.Name, monitorID, app, instance, level.Level, store.BuildRuleSeverity(def), baseContent)
	if content == "" {
		content = fmt.Sprintf("%s（升级 Level %d）", baseContent, level.Level)
	}
	title := renderEscalationTemplate(level.TitleTemplate, def.Name, monitorID, app, instance, level.Level, store.BuildRuleSeverity(def), baseContent)
	if title == "" {
		title = fmt.Sprintf("[Level %d] %s", level.Level, strings.TrimSpace(def.Name))
	}
	triggeredAt := time.Now()
	if snap.StartAtMs > 0 {
		triggeredAt = time.UnixMilli(snap.StartAtMs)
	}
	return alert.Event{
		RuleID:      ruleID,
		RuleName:    strings.TrimSpace(def.Name),
		MonitorID:   monitorID,
		App:         app,
		Instance:    instance,
		Severity:    store.BuildRuleSeverity(def),
		Labels:      labels,
		State:       alert.StateFiring,
		Expression:  store.BuildRuleExpression(def),
		Title:       title,
		Content:     content,
		TriggeredAt: triggeredAt,
	}
}

func renderEscalationTemplate(tpl, ruleName string, monitorID int64, app, instance string, level int, severity, content string) string {
	tpl = strings.TrimSpace(tpl)
	if tpl == "" {
		return ""
	}
	repl := map[string]string{
		"{{rule_name}}":  ruleName,
		"{{monitor_id}}": strconv.FormatInt(monitorID, 10),
		"{{app}}":        app,
		"{{instance}}":   instance,
		"{{level}}":      strconv.Itoa(level),
		"{{severity}}":   severity,
		"{{content}}":    content,
	}
	out := tpl
	for token, val := range repl {
		out = strings.ReplaceAll(out, token, val)
	}
	return strings.TrimSpace(out)
}

func toBool(raw any, fallback bool) bool {
	s := strings.TrimSpace(strings.ToLower(toString(raw)))
	if s == "" {
		return fallback
	}
	switch s {
	case "1", "true", "yes", "y", "on":
		return true
	case "0", "false", "no", "n", "off":
		return false
	default:
		return fallback
	}
}

func toInt(raw any, fallback int) int {
	s := strings.TrimSpace(toString(raw))
	if s == "" {
		return fallback
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		return fallback
	}
	return v
}

func toInt64(raw any, fallback int64) int64 {
	s := strings.TrimSpace(toString(raw))
	if s == "" {
		return fallback
	}
	v, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return fallback
	}
	return v
}

func toString(raw any) string {
	switch t := raw.(type) {
	case nil:
		return ""
	case string:
		return t
	case int:
		return strconv.Itoa(t)
	case int64:
		return strconv.FormatInt(t, 10)
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	case bool:
		if t {
			return "true"
		}
		return "false"
	default:
		return fmt.Sprintf("%v", t)
	}
}

func getRuleLabelString(labels map[string]any, key string) string {
	if len(labels) == 0 {
		return ""
	}
	raw, ok := labels[key]
	if !ok || raw == nil {
		return ""
	}
	return strings.TrimSpace(toString(raw))
}

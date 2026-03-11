package store

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type RuntimeAlertRule struct {
	ID          int64
	Name        string
	Type        string
	Expr        string
	Template    string
	Period      int
	Times       int
	Enabled     bool
	Labels      map[string]any
	Annotations map[string]any
	NoticeRule  int64
}

type RuntimeAlertGroup struct {
	ID             int64
	GroupKey       string
	MatchType      int
	GroupLabels    []string
	GroupWaitSec   int
	GroupInterval  int
	RepeatInterval int
}

type RuntimeAlertInhibit struct {
	ID           int64
	SourceLabels map[string]string
	TargetLabels map[string]string
	EqualLabels  []string
}

type RuntimeAlertSilence struct {
	ID        int64
	Type      int
	MatchType int
	Labels    map[string]string
	Days      []int
	StartAtMs int64
	EndAtMs   int64
}

type NoticeDispatch struct {
	NoticeRuleID int64
	RuleName     string
	Channel      string
	Config       json.RawMessage
	Template     string
	NotifyTimes  int
	NotifyScale  string
	FilterAll    bool
	Labels       map[string]string
	Days         []int
	PeriodStart  string
	PeriodEnd    string
}

type RuntimeAlertEvent struct {
	RuleID      int64
	RuleName    string
	MonitorID   int64
	Severity    string
	Expression  string
	Metric      string
	Value       float64
	Threshold   string
	MonitorName string
	App         string
	Instance    string
	Content     string
	TriggeredAt time.Time
	ElapsedMs   int64
}

type AlertRuntimeStore struct {
	db *sql.DB
}

func NewAlertRuntimeStoreWithPath(dbPath string) (*AlertRuntimeStore, error) {
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create alert runtime dir failed: %w", err)
	}
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite db failed: %w", err)
	}
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)
	return &AlertRuntimeStore{db: db}, nil
}

func (s *AlertRuntimeStore) LoadEnabledRealtimeMetricRules() ([]RuntimeAlertRule, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`
SELECT id, name, type, expr, template, period, times, enabled, labels_json, annotations_json, notice_rule_id
FROM alert_defines
WHERE enabled = 1 AND type = 'realtime_metric'
ORDER BY updated_at DESC, id DESC
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]RuntimeAlertRule, 0, 64)
	for rows.Next() {
		var (
			r               RuntimeAlertRule
			template        sql.NullString
			period          sql.NullInt64
			times           sql.NullInt64
			enabled         bool
			labelsJSON      string
			annotationsJSON string
			noticeRuleID    sql.NullInt64
		)
		if err := rows.Scan(&r.ID, &r.Name, &r.Type, &r.Expr, &template, &period, &times, &enabled, &labelsJSON, &annotationsJSON, &noticeRuleID); err != nil {
			return nil, err
		}
		if template.Valid {
			r.Template = strings.TrimSpace(template.String)
		}
		r.Enabled = enabled
		if period.Valid {
			r.Period = int(period.Int64)
		}
		if times.Valid {
			r.Times = int(times.Int64)
		}
		if noticeRuleID.Valid {
			r.NoticeRule = noticeRuleID.Int64
		}
		_ = json.Unmarshal([]byte(defaultJSON(labelsJSON)), &r.Labels)
		_ = json.Unmarshal([]byte(defaultJSON(annotationsJSON)), &r.Annotations)
		out = append(out, r)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *AlertRuntimeStore) LoadEnabledPeriodicMetricRules() ([]RuntimeAlertRule, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`
SELECT id, name, type, expr, template, period, times, enabled, labels_json, annotations_json, notice_rule_id
FROM alert_defines
WHERE enabled = 1 AND type = 'periodic_metric'
ORDER BY updated_at DESC, id DESC
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]RuntimeAlertRule, 0, 64)
	for rows.Next() {
		var (
			r               RuntimeAlertRule
			template        sql.NullString
			period          sql.NullInt64
			times           sql.NullInt64
			enabled         bool
			labelsJSON      string
			annotationsJSON string
			noticeRuleID    sql.NullInt64
		)
		if err := rows.Scan(&r.ID, &r.Name, &r.Type, &r.Expr, &template, &period, &times, &enabled, &labelsJSON, &annotationsJSON, &noticeRuleID); err != nil {
			return nil, err
		}
		if template.Valid {
			r.Template = strings.TrimSpace(template.String)
		}
		r.Enabled = enabled
		if period.Valid {
			r.Period = int(period.Int64)
		}
		if times.Valid {
			r.Times = int(times.Int64)
		}
		if noticeRuleID.Valid {
			r.NoticeRule = noticeRuleID.Int64
		}
		_ = json.Unmarshal([]byte(defaultJSON(labelsJSON)), &r.Labels)
		_ = json.Unmarshal([]byte(defaultJSON(annotationsJSON)), &r.Annotations)
		out = append(out, r)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *AlertRuntimeStore) LoadEnabledAlertGroups() ([]RuntimeAlertGroup, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`
SELECT id, group_key, match_type, labels_json, group_wait, group_interval, repeat_interval
FROM alert_groups
WHERE enabled = 1
ORDER BY updated_at DESC, id DESC
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]RuntimeAlertGroup, 0, 32)
	for rows.Next() {
		var (
			g              RuntimeAlertGroup
			labelsJSON     string
			groupWaitSec   sql.NullInt64
			groupInterval  sql.NullInt64
			repeatInterval sql.NullInt64
		)
		if err := rows.Scan(&g.ID, &g.GroupKey, &g.MatchType, &labelsJSON, &groupWaitSec, &groupInterval, &repeatInterval); err != nil {
			return nil, err
		}
		if groupWaitSec.Valid {
			g.GroupWaitSec = int(groupWaitSec.Int64)
		}
		if groupInterval.Valid {
			g.GroupInterval = int(groupInterval.Int64)
		}
		if repeatInterval.Valid {
			g.RepeatInterval = int(repeatInterval.Int64)
		}
		_ = json.Unmarshal([]byte(defaultJSON(labelsJSON)), &g.GroupLabels)
		out = append(out, g)
	}
	return out, rows.Err()
}

func (s *AlertRuntimeStore) LoadEnabledAlertInhibits() ([]RuntimeAlertInhibit, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`
SELECT id, source_labels_json, target_labels_json, equal_labels_json
FROM alert_inhibits
WHERE enabled = 1
ORDER BY updated_at DESC, id DESC
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]RuntimeAlertInhibit, 0, 32)
	for rows.Next() {
		var (
			it         RuntimeAlertInhibit
			sourceJSON string
			targetJSON string
			equalJSON  string
		)
		if err := rows.Scan(&it.ID, &sourceJSON, &targetJSON, &equalJSON); err != nil {
			return nil, err
		}
		_ = json.Unmarshal([]byte(defaultJSON(sourceJSON)), &it.SourceLabels)
		_ = json.Unmarshal([]byte(defaultJSON(targetJSON)), &it.TargetLabels)
		_ = json.Unmarshal([]byte(defaultJSON(equalJSON)), &it.EqualLabels)
		if it.SourceLabels == nil {
			it.SourceLabels = map[string]string{}
		}
		if it.TargetLabels == nil {
			it.TargetLabels = map[string]string{}
		}
		out = append(out, it)
	}
	return out, rows.Err()
}

func (s *AlertRuntimeStore) LoadEnabledAlertSilences() ([]RuntimeAlertSilence, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`
SELECT id, type, match_type, labels_json, days_json, start_time, end_time
FROM alert_silences
WHERE enabled = 1
ORDER BY updated_at DESC, id DESC
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]RuntimeAlertSilence, 0, 32)
	for rows.Next() {
		var (
			it        RuntimeAlertSilence
			labelsRaw string
			daysRaw   string
			startAt   sql.NullInt64
			endAt     sql.NullInt64
		)
		if err := rows.Scan(&it.ID, &it.Type, &it.MatchType, &labelsRaw, &daysRaw, &startAt, &endAt); err != nil {
			return nil, err
		}
		_ = json.Unmarshal([]byte(defaultJSON(labelsRaw)), &it.Labels)
		_ = json.Unmarshal([]byte(defaultJSON(daysRaw)), &it.Days)
		if it.Labels == nil {
			it.Labels = map[string]string{}
		}
		if startAt.Valid {
			it.StartAtMs = startAt.Int64
		}
		if endAt.Valid {
			it.EndAtMs = endAt.Int64
		}
		out = append(out, it)
	}
	return out, rows.Err()
}

func (s *AlertRuntimeStore) UpsertFiringAlert(ev RuntimeAlertEvent) error {
	if s == nil || s.db == nil {
		return nil
	}
	if ev.TriggeredAt.IsZero() {
		ev.TriggeredAt = time.Now()
	}
	now := ev.TriggeredAt.UTC()
	nowMS := now.UnixMilli()
	fingerprint := alertFingerprint(ev.RuleID, ev.MonitorID)

	labels := map[string]any{
		"alertname":    ev.RuleName,
		"severity":     strings.TrimSpace(ev.Severity),
		"monitor_id":   ev.MonitorID,
		"monitor_name": ev.MonitorName,
		"app":          ev.App,
		"instance":     ev.Instance,
		"metric":       ev.Metric,
		"value":        strconv.FormatFloat(ev.Value, 'f', -1, 64),
		"threshold":    ev.Threshold,
		"rule_id":      ev.RuleID,
	}
	content := strings.TrimSpace(ev.Content)
	if content == "" {
		content = ev.RuleName
	}
	annotations := map[string]any{
		"summary":    content,
		"expression": ev.Expression,
		"severity":   strings.TrimSpace(ev.Severity),
	}
	labelsJSON, _ := json.Marshal(labels)
	annotationsJSON, _ := json.Marshal(annotations)

	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	var (
		id           int64
		triggerTimes int
		exists       bool
	)
	row := tx.QueryRow(`SELECT id, trigger_times FROM single_alerts WHERE fingerprint = ?`, fingerprint)
	if err := row.Scan(&id, &triggerTimes); err == nil {
		exists = true
	}
	if exists {
		_, err = tx.Exec(`
UPDATE single_alerts
SET labels_json = ?, annotations_json = ?, content = ?, status = 'firing',
    trigger_times = ?, active_at = ?, end_at = NULL, modifier = 'manager-go', updated_at = ?
WHERE id = ?
`, string(labelsJSON), string(annotationsJSON), content, triggerTimes+1, nowMS, now.Format(time.RFC3339Nano), id)
	} else {
		_, err = tx.Exec(`
INSERT INTO single_alerts
  (fingerprint, labels_json, annotations_json, content, status, trigger_times, start_at, active_at, end_at, creator, modifier, created_at, updated_at)
VALUES
  (?, ?, ?, ?, 'firing', 1, ?, ?, NULL, 'manager-go', 'manager-go', ?, ?)
`, fingerprint, string(labelsJSON), string(annotationsJSON), content, nowMS, nowMS, now.Format(time.RFC3339Nano), now.Format(time.RFC3339Nano))
	}
	if err != nil {
		_ = tx.Rollback()
		return err
	}
	return tx.Commit()
}

func (s *AlertRuntimeStore) ResolveAlert(ruleID int64, monitorID int64, resolvedAt time.Time) error {
	if s == nil || s.db == nil {
		return nil
	}
	if resolvedAt.IsZero() {
		resolvedAt = time.Now()
	}
	now := resolvedAt.UTC()
	nowMS := now.UnixMilli()
	fingerprint := alertFingerprint(ruleID, monitorID)

	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	var (
		id              int64
		status          string
		triggerTimes    int
		startAt         sql.NullInt64
		labelsJSON      string
		annotationsJSON string
		content         sql.NullString
	)
	row := tx.QueryRow(`
SELECT id, status, trigger_times, start_at, labels_json, annotations_json, content
FROM single_alerts
WHERE fingerprint = ?
`, fingerprint)
	if err := row.Scan(&id, &status, &triggerTimes, &startAt, &labelsJSON, &annotationsJSON, &content); err != nil {
		_ = tx.Rollback()
		if err == sql.ErrNoRows {
			return nil
		}
		return err
	}
	if strings.TrimSpace(strings.ToLower(status)) != "firing" {
		_ = tx.Rollback()
		return nil
	}
	if _, err := tx.Exec(`
UPDATE single_alerts
SET status = 'resolved', end_at = ?, modifier = 'manager-go', updated_at = ?
WHERE id = ?
`, nowMS, now.Format(time.RFC3339Nano), id); err != nil {
		_ = tx.Rollback()
		return err
	}
	startMs := nowMS
	if startAt.Valid && startAt.Int64 > 0 {
		startMs = startAt.Int64
	}
	duration := nowMS - startMs
	if duration < 0 {
		duration = 0
	}
	if _, err := tx.Exec(`
INSERT INTO alert_history
  (alert_id, alert_type, labels_json, annotations_json, content, status, trigger_times, start_at, end_at, duration_ms, created_at)
VALUES
  (?, 'single', ?, ?, ?, 'resolved', ?, ?, ?, ?, ?)
`, id, defaultJSON(labelsJSON), defaultJSON(annotationsJSON), content.String, triggerTimes, startMs, nowMS, duration, now.Format(time.RFC3339Nano)); err != nil {
		_ = tx.Rollback()
		return err
	}
	return tx.Commit()
}

func (s *AlertRuntimeStore) LoadNoticeDispatch(noticeRuleID int64) (NoticeDispatch, error) {
	if s == nil || s.db == nil {
		return NoticeDispatch{}, fmt.Errorf("runtime store not configured")
	}
	if noticeRuleID <= 0 {
		return NoticeDispatch{}, fmt.Errorf("invalid notice_rule_id")
	}
	var (
		out             NoticeDispatch
		receiverType    int
		receiverEnabled bool
		ruleEnabled     bool
		notifyTimes     sql.NullInt64
		notifyScale     sql.NullString
		filterAll       bool
		labelsJSON      sql.NullString
		daysJSON        sql.NullString
		periodStart     sql.NullString
		periodEnd       sql.NullString
		smtpHost        sql.NullString
		smtpPort        sql.NullInt64
		smtpUsername    sql.NullString
		smtpPassword    sql.NullString
		emailFrom       sql.NullString
		emailTo         sql.NullString
		hookURL         sql.NullString
		hookMethod      sql.NullString
		hookContentType sql.NullString
		hookAuthType    sql.NullString
		hookAuthToken   sql.NullString
		wecomKey        sql.NullString
		templateContent sql.NullString
	)
	row := s.db.QueryRow(`
SELECT
  nr.id,
  nr.name,
  nr.enable,
  nr.notify_times,
  nr.notify_scale,
  nr.filter_all,
  nr.labels_json,
  nr.days_json,
  nr.period_start,
  nr.period_end,
  rc.type,
  rc.enable,
  rc.smtp_host,
  rc.smtp_port,
  rc.smtp_username,
  rc.smtp_password,
  rc.email_from,
  rc.email_to,
  rc.hook_url,
  rc.hook_method,
  rc.hook_content_type,
  rc.hook_auth_type,
  rc.hook_auth_token,
  rc.wecom_key,
  nt.content
FROM notice_rules nr
JOIN notice_receivers rc ON rc.id = nr.receiver_channel_id
LEFT JOIN notice_templates nt ON nt.id = nr.template_id
WHERE nr.id = ?
LIMIT 1
`, noticeRuleID)
	if err := row.Scan(
		&out.NoticeRuleID,
		&out.RuleName,
		&ruleEnabled,
		&notifyTimes,
		&notifyScale,
		&filterAll,
		&labelsJSON,
		&daysJSON,
		&periodStart,
		&periodEnd,
		&receiverType,
		&receiverEnabled,
		&smtpHost,
		&smtpPort,
		&smtpUsername,
		&smtpPassword,
		&emailFrom,
		&emailTo,
		&hookURL,
		&hookMethod,
		&hookContentType,
		&hookAuthType,
		&hookAuthToken,
		&wecomKey,
		&templateContent,
	); err != nil {
		return NoticeDispatch{}, err
	}
	if !ruleEnabled {
		return NoticeDispatch{}, fmt.Errorf("notice rule %d disabled", noticeRuleID)
	}
	if !receiverEnabled {
		return NoticeDispatch{}, fmt.Errorf("notice receiver for rule %d disabled", noticeRuleID)
	}
	out.NotifyTimes = int(notifyTimes.Int64)
	if out.NotifyTimes <= 0 {
		out.NotifyTimes = 1
	}
	out.NotifyScale = strings.ToLower(strings.TrimSpace(notifyScale.String))
	if out.NotifyScale == "" {
		out.NotifyScale = "single"
	}
	out.FilterAll = filterAll
	out.PeriodStart = strings.TrimSpace(periodStart.String)
	out.PeriodEnd = strings.TrimSpace(periodEnd.String)
	out.Labels = map[string]string{}
	_ = json.Unmarshal([]byte(defaultJSON(labelsJSON.String)), &out.Labels)
	if out.Labels == nil {
		out.Labels = map[string]string{}
	}
	_ = json.Unmarshal([]byte(defaultJSON(daysJSON.String)), &out.Days)
	if len(out.Days) == 0 {
		out.Days = []int{1, 2, 3, 4, 5, 6, 7}
	}
	if templateContent.Valid && strings.TrimSpace(templateContent.String) != "" {
		out.Template = templateContent.String
	}
	switch receiverType {
	case 1: // email
		cfg := map[string]any{
			"host":     strings.TrimSpace(smtpHost.String),
			"port":     int(smtpPort.Int64),
			"username": strings.TrimSpace(smtpUsername.String),
			"password": smtpPassword.String,
			"from":     strings.TrimSpace(emailFrom.String),
			"to":       strings.TrimSpace(emailTo.String),
		}
		if cfg["host"] == "" || cfg["port"].(int) <= 0 || cfg["from"] == "" || cfg["to"] == "" {
			return NoticeDispatch{}, fmt.Errorf("notice rule %d email config invalid", noticeRuleID)
		}
		raw, _ := json.Marshal(cfg)
		out.Channel = "email"
		out.Config = raw
		return out, nil
	case 2: // webhook
		headers := map[string]string{}
		contentType := strings.TrimSpace(hookContentType.String)
		if contentType != "" {
			headers["Content-Type"] = contentType
		}
		authType := strings.ToLower(strings.TrimSpace(hookAuthType.String))
		authToken := strings.TrimSpace(hookAuthToken.String)
		if authType == "bearer" && authToken != "" {
			headers["Authorization"] = "Bearer " + authToken
		}
		cfg := map[string]any{
			"url":    strings.TrimSpace(hookURL.String),
			"method": strings.TrimSpace(hookMethod.String),
			"header": headers,
		}
		if cfg["url"] == "" {
			return NoticeDispatch{}, fmt.Errorf("notice rule %d webhook url empty", noticeRuleID)
		}
		raw, _ := json.Marshal(cfg)
		out.Channel = "webhook"
		out.Config = raw
		return out, nil
	case 4: // wecom robot
		webhookURL := strings.TrimSpace(hookURL.String)
		if webhookURL == "" {
			key := strings.TrimSpace(wecomKey.String)
			if key != "" {
				webhookURL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + key
			}
		}
		if webhookURL == "" {
			return NoticeDispatch{}, fmt.Errorf("notice rule %d wecom webhook empty", noticeRuleID)
		}
		cfg := map[string]any{"webhook_url": webhookURL}
		raw, _ := json.Marshal(cfg)
		out.Channel = "wecom"
		out.Config = raw
		return out, nil
	default:
		return NoticeDispatch{}, fmt.Errorf("notice rule %d receiver type=%d not supported", noticeRuleID, receiverType)
	}
}

func (d NoticeDispatch) MatchEventLabels(labels map[string]string) bool {
	if d.FilterAll {
		return true
	}
	if len(d.Labels) == 0 {
		return true
	}
	for key, want := range d.Labels {
		k := strings.TrimSpace(key)
		if k == "" {
			continue
		}
		got := strings.TrimSpace(labels[k])
		if got != strings.TrimSpace(want) {
			return false
		}
	}
	return true
}

func (d NoticeDispatch) MatchTime(now time.Time) bool {
	if len(d.Days) > 0 {
		weekDay := int(now.Weekday())
		if weekDay == 0 {
			weekDay = 7
		}
		allowed := false
		for _, day := range d.Days {
			if day == weekDay {
				allowed = true
				break
			}
		}
		if !allowed {
			return false
		}
	}
	return inPeriodRange(now, d.PeriodStart, d.PeriodEnd)
}

func inPeriodRange(now time.Time, start, end string) bool {
	start = strings.TrimSpace(start)
	end = strings.TrimSpace(end)
	if start == "" || end == "" {
		return true
	}
	currentSec := now.Hour()*3600 + now.Minute()*60 + now.Second()
	startSec, ok := parseClockSeconds(start)
	if !ok {
		return true
	}
	endSec, ok := parseClockSeconds(end)
	if !ok {
		return true
	}
	if startSec <= endSec {
		return currentSec >= startSec && currentSec <= endSec
	}
	return currentSec >= startSec || currentSec <= endSec
}

func parseClockSeconds(raw string) (int, bool) {
	parts := strings.Split(strings.TrimSpace(raw), ":")
	if len(parts) != 3 {
		return 0, false
	}
	hour, err1 := strconv.Atoi(parts[0])
	minute, err2 := strconv.Atoi(parts[1])
	second, err3 := strconv.Atoi(parts[2])
	if err1 != nil || err2 != nil || err3 != nil {
		return 0, false
	}
	if hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59 {
		return 0, false
	}
	return hour*3600 + minute*60 + second, true
}

func BuildRuleExpression(rule RuntimeAlertRule) string {
	raw := strings.TrimSpace(rule.Expr)
	if raw != "" {
		return raw
	}
	metric := strings.TrimSpace(asStringAny(rule.Labels["metric"]))
	if metric == "" {
		metric = "value"
	}
	op := strings.TrimSpace(asStringAny(rule.Labels["operator"]))
	if op == "" {
		op = ">"
	}
	threshold := strings.TrimSpace(asStringAny(rule.Labels["threshold"]))
	if threshold == "" {
		threshold = "0"
	}
	return fmt.Sprintf("%s %s %s", metric, op, threshold)
}

func BuildRuleSeverity(rule RuntimeAlertRule) string {
	raw := strings.TrimSpace(strings.ToLower(asStringAny(rule.Labels["severity"])))
	if raw == "" {
		return "warning"
	}
	return raw
}

func BuildRuleDurationSeconds(rule RuntimeAlertRule) int {
	if rule.Times > 0 {
		return rule.Times
	}
	return 1
}

func BuildRuleThreshold(rule RuntimeAlertRule) string {
	return strings.TrimSpace(asStringAny(rule.Labels["threshold"]))
}

func BuildRuleMetric(rule RuntimeAlertRule) string {
	m := strings.TrimSpace(asStringAny(rule.Labels["metric"]))
	if m == "" {
		return "value"
	}
	return m
}

func BuildPeriodicPromQL(rule RuntimeAlertRule, monitorID int64) string {
	metric := BuildRuleMetric(rule)
	if metric == "" || metric == "value" {
		return ""
	}
	periodSec := rule.Period
	if periodSec <= 0 {
		periodSec = 60
	}
	windowMin := periodSec / 60
	if windowMin <= 0 {
		windowMin = 1
	}
	return fmt.Sprintf(`last_over_time({__monitor_id__="%d",__name__="%s"}[%dm])`, monitorID, metric, windowMin)
}

func RuleAppliesToTarget(rule RuntimeAlertRule, monitorID int64, app string, instance string) bool {
	labels := rule.Labels
	if len(labels) == 0 {
		return true
	}
	if raw, ok := labels["monitor_id"]; ok {
		want := strings.TrimSpace(asStringAny(raw))
		if want != "" && want != strconv.FormatInt(monitorID, 10) {
			return false
		}
	}
	if raw, ok := labels["app"]; ok {
		want := strings.TrimSpace(strings.ToLower(asStringAny(raw)))
		if want != "" && want != strings.TrimSpace(strings.ToLower(app)) {
			return false
		}
	}
	if raw, ok := labels["instance"]; ok {
		want := strings.TrimSpace(strings.ToLower(asStringAny(raw)))
		if want != "" && want != strings.TrimSpace(strings.ToLower(instance)) {
			return false
		}
	}
	return true
}

func asStringAny(v any) string {
	switch t := v.(type) {
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
		return fmt.Sprintf("%v", v)
	}
}

func alertFingerprint(ruleID int64, monitorID int64) string {
	return fmt.Sprintf("manager:%d:%d", ruleID, monitorID)
}

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

	"manager-go/internal/dbutil"

	_ "github.com/lib/pq"
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
	NoticeRules []int64
	Escalation  string
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
	NoticeRuleID   int64
	RuleName       string
	Channel        string
	Config         json.RawMessage
	Template       string
	NotifyTimes    int
	NotifyScale    string
	FilterAll      bool
	Labels         map[string]string
	Days           []int
	PeriodStart    string
	PeriodEnd      string
	RecipientType  string
	RecipientIDs   []int64
	IncludeSubDept bool
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

type RuntimeSingleAlertSnapshot struct {
	ID           int64
	Status       string
	Labels       map[string]string
	Annotations  map[string]string
	Content      string
	StartAtMs    int64
	TriggerTimes int
}

type AlertRuntimeStore struct {
	db     *sql.DB
	driver string
}

func NewAlertRuntimeStoreWithPath(dsn string) (*AlertRuntimeStore, error) {
	driver, resolved := dbutil.ResolveDriverAndDSN(dsn, "../backend/instance/it_ops.db")
	if driver == "sqlite3" {
		dir := filepath.Dir(resolved)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return nil, fmt.Errorf("create alert runtime dir failed: %w", err)
		}
	}
	db, err := sql.Open(driver, resolved)
	if err != nil {
		return nil, fmt.Errorf("open %s db failed: %w", driver, err)
	}
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)
	return &AlertRuntimeStore{db: db, driver: driver}, nil
}

func (s *AlertRuntimeStore) LoadEnabledRealtimeMetricRules() ([]RuntimeAlertRule, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	hasEscalation := s.hasTableColumn("alert_defines", "escalation_config")
	query := `
SELECT id, name, type, expr, template, period, times, enabled, labels_json, annotations_json, notice_rule_id, notice_rule_ids_json`
	if hasEscalation {
		query += `, escalation_config`
	}
	query += `
FROM alert_defines
WHERE enabled = 1 AND type = 'realtime_metric'
ORDER BY updated_at DESC, id DESC
`
	rows, err := s.query(query)
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
			noticeRuleIDs   sql.NullString
			escalation      sql.NullString
		)
		if hasEscalation {
			err = rows.Scan(&r.ID, &r.Name, &r.Type, &r.Expr, &template, &period, &times, &enabled, &labelsJSON, &annotationsJSON, &noticeRuleID, &noticeRuleIDs, &escalation)
		} else {
			err = rows.Scan(&r.ID, &r.Name, &r.Type, &r.Expr, &template, &period, &times, &enabled, &labelsJSON, &annotationsJSON, &noticeRuleID, &noticeRuleIDs)
		}
		if err != nil {
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
		if noticeRuleIDs.Valid {
			r.NoticeRules = parseNoticeRuleIDs(noticeRuleIDs.String)
		}
		if len(r.NoticeRules) == 0 && r.NoticeRule > 0 {
			r.NoticeRules = []int64{r.NoticeRule}
		}
		if escalation.Valid {
			r.Escalation = strings.TrimSpace(escalation.String)
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
	hasEscalation := s.hasTableColumn("alert_defines", "escalation_config")
	query := `
SELECT id, name, type, expr, template, period, times, enabled, labels_json, annotations_json, notice_rule_id, notice_rule_ids_json`
	if hasEscalation {
		query += `, escalation_config`
	}
	query += `
FROM alert_defines
WHERE enabled = 1 AND type = 'periodic_metric'
ORDER BY updated_at DESC, id DESC
`
	rows, err := s.query(query)
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
			noticeRuleIDs   sql.NullString
			escalation      sql.NullString
		)
		if hasEscalation {
			err = rows.Scan(&r.ID, &r.Name, &r.Type, &r.Expr, &template, &period, &times, &enabled, &labelsJSON, &annotationsJSON, &noticeRuleID, &noticeRuleIDs, &escalation)
		} else {
			err = rows.Scan(&r.ID, &r.Name, &r.Type, &r.Expr, &template, &period, &times, &enabled, &labelsJSON, &annotationsJSON, &noticeRuleID, &noticeRuleIDs)
		}
		if err != nil {
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
		if noticeRuleIDs.Valid {
			r.NoticeRules = parseNoticeRuleIDs(noticeRuleIDs.String)
		}
		if len(r.NoticeRules) == 0 && r.NoticeRule > 0 {
			r.NoticeRules = []int64{r.NoticeRule}
		}
		if escalation.Valid {
			r.Escalation = strings.TrimSpace(escalation.String)
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
	rows, err := s.query(`
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
	rows, err := s.query(`
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
	rows, err := s.query(`
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

func (s *AlertRuntimeStore) UpsertFiringAlert(ev RuntimeAlertEvent) (bool, error) {
	if s == nil || s.db == nil {
		return false, nil
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
		return false, err
	}
	var (
		id           int64
		status       string
		triggerTimes int
		exists       bool
	)
	row := s.txQueryRow(tx, `SELECT id, status, trigger_times FROM single_alerts WHERE fingerprint = ?`, fingerprint)
	if err := row.Scan(&id, &status, &triggerTimes); err == nil {
		exists = true
	}
	newCycle := !exists || strings.TrimSpace(strings.ToLower(status)) != "firing"
	if exists {
		_, err = s.txExec(tx, `
UPDATE single_alerts
SET labels_json = ?, annotations_json = ?, content = ?, status = 'firing',
    trigger_times = ?, active_at = ?, end_at = NULL, modifier = 'manager-go', updated_at = ?
WHERE id = ?
`, string(labelsJSON), string(annotationsJSON), content, triggerTimes+1, nowMS, now.Format(time.RFC3339Nano), id)
	} else {
		_, err = s.txExec(tx, `
INSERT INTO single_alerts
  (fingerprint, labels_json, annotations_json, content, status, trigger_times, start_at, active_at, end_at, creator, modifier, created_at, updated_at)
VALUES
  (?, ?, ?, ?, 'firing', 1, ?, ?, NULL, 'manager-go', 'manager-go', ?, ?)
`, fingerprint, string(labelsJSON), string(annotationsJSON), content, nowMS, nowMS, now.Format(time.RFC3339Nano), now.Format(time.RFC3339Nano))
	}
	if err != nil {
		_ = tx.Rollback()
		return false, err
	}
	if err := tx.Commit(); err != nil {
		return false, err
	}
	return newCycle, nil
}

func (s *AlertRuntimeStore) ResolveAlert(ruleID int64, monitorID int64, resolvedAt time.Time) (bool, error) {
	if s == nil || s.db == nil {
		return false, nil
	}
	if resolvedAt.IsZero() {
		resolvedAt = time.Now()
	}
	now := resolvedAt.UTC()
	nowMS := now.UnixMilli()
	fingerprint := alertFingerprint(ruleID, monitorID)

	tx, err := s.db.Begin()
	if err != nil {
		return false, err
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
	row := s.txQueryRow(tx, `
SELECT id, status, trigger_times, start_at, labels_json, annotations_json, content
FROM single_alerts
WHERE fingerprint = ?
`, fingerprint)
	if err := row.Scan(&id, &status, &triggerTimes, &startAt, &labelsJSON, &annotationsJSON, &content); err != nil {
		_ = tx.Rollback()
		if err == sql.ErrNoRows {
			return false, nil
		}
		return false, err
	}
	if strings.TrimSpace(strings.ToLower(status)) != "firing" {
		_ = tx.Rollback()
		return false, nil
	}
	if _, err := s.txExec(tx, `
UPDATE single_alerts
SET status = 'resolved', end_at = ?, modifier = 'manager-go', updated_at = ?
WHERE id = ?
`, nowMS, now.Format(time.RFC3339Nano), id); err != nil {
		_ = tx.Rollback()
		return false, err
	}
	startMs := nowMS
	if startAt.Valid && startAt.Int64 > 0 {
		startMs = startAt.Int64
	}
	duration := nowMS - startMs
	if duration < 0 {
		duration = 0
	}
	if _, err := s.txExec(tx, `
INSERT INTO alert_history
  (alert_id, alert_type, labels_json, annotations_json, content, status, trigger_times, start_at, end_at, duration_ms, created_at)
VALUES
  (?, 'single', ?, ?, ?, 'resolved', ?, ?, ?, ?, ?)
`, id, defaultJSON(labelsJSON), defaultJSON(annotationsJSON), content.String, triggerTimes, startMs, nowMS, duration, now.Format(time.RFC3339Nano)); err != nil {
		_ = tx.Rollback()
		return false, err
	}
	if err := tx.Commit(); err != nil {
		return false, err
	}
	return true, nil
}

func (s *AlertRuntimeStore) FindCurrentAlertID(ruleID int64, monitorID int64) (int64, error) {
	if s == nil || s.db == nil {
		return 0, nil
	}
	fingerprint := alertFingerprint(ruleID, monitorID)
	var id int64
	row := s.queryRow(`
SELECT id
FROM single_alerts
WHERE fingerprint = ?
LIMIT 1
`, fingerprint)
	if err := row.Scan(&id); err != nil {
		if err == sql.ErrNoRows {
			return 0, nil
		}
		return 0, err
	}
	return id, nil
}

func (s *AlertRuntimeStore) LoadSingleAlertSnapshot(ruleID int64, monitorID int64) (RuntimeSingleAlertSnapshot, bool, error) {
	if s == nil || s.db == nil {
		return RuntimeSingleAlertSnapshot{}, false, nil
	}
	fingerprint := alertFingerprint(ruleID, monitorID)
	var (
		snap            RuntimeSingleAlertSnapshot
		labelsJSON      string
		annotationsJSON string
		content         sql.NullString
		startAt         sql.NullInt64
	)
	row := s.queryRow(`
SELECT id, status, labels_json, annotations_json, content, start_at, trigger_times
FROM single_alerts
WHERE fingerprint = ?
LIMIT 1
`, fingerprint)
	if err := row.Scan(&snap.ID, &snap.Status, &labelsJSON, &annotationsJSON, &content, &startAt, &snap.TriggerTimes); err != nil {
		if err == sql.ErrNoRows {
			return RuntimeSingleAlertSnapshot{}, false, nil
		}
		return RuntimeSingleAlertSnapshot{}, false, err
	}
	snap.Status = strings.TrimSpace(strings.ToLower(snap.Status))
	snap.Labels = parseStringMapJSON(labelsJSON)
	snap.Annotations = parseStringMapJSON(annotationsJSON)
	snap.Content = strings.TrimSpace(content.String)
	if startAt.Valid {
		snap.StartAtMs = startAt.Int64
	}
	if snap.TriggerTimes <= 0 {
		snap.TriggerTimes = 1
	}
	return snap, true, nil
}

func (s *AlertRuntimeStore) AddEscalationHistory(alertID int64, level int, content string, createdAt time.Time) error {
	if s == nil || s.db == nil || alertID <= 0 {
		return nil
	}
	if createdAt.IsZero() {
		createdAt = time.Now()
	}
	var (
		labelsJSON      string
		annotationsJSON string
		triggerTimes    int
		startAt         sql.NullInt64
	)
	row := s.queryRow(`
SELECT labels_json, annotations_json, trigger_times, start_at
FROM single_alerts
WHERE id = ?
LIMIT 1
`, alertID)
	if err := row.Scan(&labelsJSON, &annotationsJSON, &triggerTimes, &startAt); err != nil {
		if err == sql.ErrNoRows {
			return nil
		}
		return err
	}
	if triggerTimes <= 0 {
		triggerTimes = 1
	}
	startMs := createdAt.UnixMilli()
	if startMs <= 0 && startAt.Valid && startAt.Int64 > 0 {
		startMs = startAt.Int64
	}

	// Attach explicit escalation action markers for stable timeline filtering.
	annotations := map[string]any{}
	_ = json.Unmarshal([]byte(defaultJSON(annotationsJSON)), &annotations)
	if annotations == nil {
		annotations = map[string]any{}
	}
	annotations["action"] = "escalated"
	annotations["escalation_level"] = level
	annotations["escalated_at"] = createdAt.UTC().Format(time.RFC3339Nano)
	annotationsJSONBytes, _ := json.Marshal(annotations)

	if _, err := s.exec(`
INSERT INTO alert_history
  (alert_id, alert_type, labels_json, annotations_json, content, status, trigger_times, start_at, end_at, duration_ms, created_at)
VALUES
  (?, 'single', ?, ?, ?, 'firing', ?, ?, NULL, NULL, ?)
`, alertID, defaultJSON(labelsJSON), defaultJSON(string(annotationsJSONBytes)), strings.TrimSpace(content), triggerTimes, startMs, createdAt.UTC().Format(time.RFC3339Nano)); err != nil {
		return err
	}
	return nil
}

func (s *AlertRuntimeStore) SaveAlertNotification(
	alertID int64,
	ruleID int64,
	notifyType string,
	status int,
	content string,
	errorMsg string,
	retryTimes int,
) error {
	if s == nil || s.db == nil {
		return nil
	}
	if alertID <= 0 {
		return nil
	}
	notifyType = strings.TrimSpace(strings.ToLower(notifyType))
	switch notifyType {
	case "email", "sms", "webhook", "wecom", "dingtalk", "feishu":
	default:
		return nil
	}
	now := time.Now().UTC()
	nowMS := now.UnixMilli()
	_, err := s.exec(`
INSERT INTO alert_notifications
  (alert_id, rule_id, receiver_type, receiver_id, notify_type, status, content, error_msg, retry_times, sent_at, created_at, updated_at)
VALUES
  (?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
`,
		alertID,
		ruleID,
		notifyType,
		status,
		strings.TrimSpace(content),
		strings.TrimSpace(errorMsg),
		retryTimes,
		nowMS,
		now.Format(time.RFC3339Nano),
		now.Format(time.RFC3339Nano),
	)
	return err
}

func (s *AlertRuntimeStore) LoadNoticeDispatch(noticeRuleID int64) (NoticeDispatch, error) {
	if s == nil || s.db == nil {
		return NoticeDispatch{}, fmt.Errorf("runtime store not configured")
	}
	if noticeRuleID <= 0 {
		return NoticeDispatch{}, fmt.Errorf("invalid notice_rule_id")
	}
	var (
		out              NoticeDispatch
		receiverType     int
		receiverEnabled  bool
		ruleEnabled      bool
		notifyTimes      sql.NullInt64
		notifyScale      sql.NullString
		filterAll        bool
		labelsJSON       sql.NullString
		daysJSON         sql.NullString
		periodStart      sql.NullString
		periodEnd        sql.NullString
		recipientType    sql.NullString
		recipientIDsJSON sql.NullString
		includeSubDept   sql.NullBool
		smtpHost         sql.NullString
		smtpPort         sql.NullInt64
		smtpUsername     sql.NullString
		smtpPassword     sql.NullString
		emailFrom        sql.NullString
		emailTo          sql.NullString
		hookURL          sql.NullString
		hookMethod       sql.NullString
		hookContentType  sql.NullString
		hookAuthType     sql.NullString
		hookAuthToken    sql.NullString
		wecomKey         sql.NullString
		templateContent  sql.NullString
	)
	row := s.queryRow(`
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
  nr.recipient_type,
  nr.recipient_ids_json,
  nr.include_sub_departments,
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
		&recipientType,
		&recipientIDsJSON,
		&includeSubDept,
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
	out.RecipientType = strings.ToLower(strings.TrimSpace(recipientType.String))
	if out.RecipientType == "" {
		out.RecipientType = "user"
	}
	out.RecipientIDs = parseInt64Slice(recipientIDsJSON.String)
	out.IncludeSubDept = includeSubDept.Bool
	if recipientType.Valid && !includeSubDept.Valid {
		out.IncludeSubDept = true
	}
	switch receiverType {
	case 1: // email
		if len(out.RecipientIDs) > 0 {
			emails, err := s.resolveRecipientEmails(out.RecipientType, out.RecipientIDs, out.IncludeSubDept)
			if err != nil {
				return NoticeDispatch{}, err
			}
			if len(emails) == 0 {
				return NoticeDispatch{}, fmt.Errorf("notice rule %d email recipients empty", noticeRuleID)
			}
			emailTo = sql.NullString{String: strings.Join(emails, ","), Valid: true}
		}
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
	case 15: // system notification
		out.Channel = "system"
		if len(out.RecipientIDs) == 0 {
			return NoticeDispatch{}, fmt.Errorf("notice rule %d system recipients empty", noticeRuleID)
		}
		out.Config = json.RawMessage(`{}`)
		return out, nil
	default:
		return NoticeDispatch{}, fmt.Errorf("notice rule %d receiver type=%d not supported", noticeRuleID, receiverType)
	}
}

func parseInt64Slice(raw string) []int64 {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	var items []any
	if err := json.Unmarshal([]byte(raw), &items); err != nil {
		return nil
	}
	out := make([]int64, 0, len(items))
	for _, v := range items {
		switch t := v.(type) {
		case float64:
			out = append(out, int64(t))
		case int64:
			out = append(out, t)
		case string:
			if n, err := strconv.ParseInt(strings.TrimSpace(t), 10, 64); err == nil {
				out = append(out, n)
			}
		}
	}
	return out
}

func parseNoticeRuleIDs(raw string) []int64 {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	var out []int64
	if err := json.Unmarshal([]byte(defaultJSON(raw)), &out); err == nil {
		filtered := make([]int64, 0, len(out))
		seen := map[int64]struct{}{}
		for _, val := range out {
			if val <= 0 {
				continue
			}
			if _, ok := seen[val]; ok {
				continue
			}
			seen[val] = struct{}{}
			filtered = append(filtered, val)
		}
		return filtered
	}
	return nil
}

type recipientUser struct {
	ID    int64
	Email string
	Phone string
}

func (s *AlertRuntimeStore) resolveRecipientEmails(recipientType string, recipientIDs []int64, includeSub bool) ([]string, error) {
	users, err := s.resolveRecipientUsers(recipientType, recipientIDs, includeSub)
	if err != nil {
		return nil, err
	}
	seen := map[string]bool{}
	out := make([]string, 0, len(users))
	for _, u := range users {
		email := strings.TrimSpace(u.Email)
		if email == "" || seen[email] {
			continue
		}
		seen[email] = true
		out = append(out, email)
	}
	return out, nil
}

func (s *AlertRuntimeStore) resolveRecipientUsers(recipientType string, recipientIDs []int64, includeSub bool) ([]recipientUser, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("runtime store not configured")
	}
	if len(recipientIDs) == 0 {
		return nil, nil
	}
	switch strings.ToLower(strings.TrimSpace(recipientType)) {
	case "department":
		deptIDs, err := s.expandDepartmentIDs(recipientIDs, includeSub)
		if err != nil {
			return nil, err
		}
		return s.queryUsersByDepartments(deptIDs)
	default:
		return s.queryUsersByIDs(recipientIDs)
	}
}

func (s *AlertRuntimeStore) expandDepartmentIDs(ids []int64, includeSub bool) ([]int64, error) {
	if !includeSub {
		return ids, nil
	}
	placeholders, args := buildInClause(ids)
	if placeholders == "" {
		return ids, nil
	}
	query := fmt.Sprintf(`
WITH RECURSIVE dept_tree(id) AS (
  SELECT id FROM departments WHERE id IN (%s)
  UNION ALL
  SELECT d.id FROM departments d JOIN dept_tree dt ON d.parent_id = dt.id
)
SELECT id FROM dept_tree
`, placeholders)
	rows, err := s.query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []int64
	for rows.Next() {
		var id int64
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		out = append(out, id)
	}
	return out, nil
}

func (s *AlertRuntimeStore) queryUsersByIDs(ids []int64) ([]recipientUser, error) {
	placeholders, args := buildInClause(ids)
	if placeholders == "" {
		return nil, nil
	}
	query := fmt.Sprintf(`
SELECT id, email, phone
FROM users
WHERE deleted_at IS NULL AND status = 'active' AND id IN (%s)
`, placeholders)
	return s.scanRecipientUsers(query, args...)
}

func (s *AlertRuntimeStore) queryUsersByDepartments(deptIDs []int64) ([]recipientUser, error) {
	placeholders, args := buildInClause(deptIDs)
	if placeholders == "" {
		return nil, nil
	}
	users := map[int64]recipientUser{}

	query := fmt.Sprintf(`
SELECT id, email, phone
FROM users
WHERE deleted_at IS NULL AND status = 'active' AND department_id IN (%s)
`, placeholders)
	rows, err := s.scanRecipientUsers(query, args...)
	if err != nil {
		return nil, err
	}
	for _, u := range rows {
		users[u.ID] = u
	}

	query = fmt.Sprintf(`
SELECT u.id, u.email, u.phone
FROM users u
JOIN department_users du ON du.user_id = u.id
WHERE u.deleted_at IS NULL AND u.status = 'active' AND du.department_id IN (%s)
`, placeholders)
	rows, err = s.scanRecipientUsers(query, args...)
	if err != nil {
		return nil, err
	}
	for _, u := range rows {
		users[u.ID] = u
	}

	out := make([]recipientUser, 0, len(users))
	for _, u := range users {
		out = append(out, u)
	}
	return out, nil
}

func (s *AlertRuntimeStore) scanRecipientUsers(query string, args ...any) ([]recipientUser, error) {
	rows, err := s.query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []recipientUser
	for rows.Next() {
		var (
			u     recipientUser
			email sql.NullString
			phone sql.NullString
		)
		if err := rows.Scan(&u.ID, &email, &phone); err != nil {
			return nil, err
		}
		if email.Valid {
			u.Email = strings.TrimSpace(email.String)
		}
		if phone.Valid {
			u.Phone = strings.TrimSpace(phone.String)
		}
		out = append(out, u)
	}
	return out, nil
}

func buildInClause(ids []int64) (string, []any) {
	if len(ids) == 0 {
		return "", nil
	}
	parts := make([]string, 0, len(ids))
	args := make([]any, 0, len(ids))
	for _, id := range ids {
		parts = append(parts, "?")
		args = append(args, id)
	}
	return strings.Join(parts, ","), args
}

func (s *AlertRuntimeStore) SendSystemNotification(title, content string, recipientType string, recipientIDs []int64, includeSub bool) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("runtime store not configured")
	}
	if len(recipientIDs) == 0 {
		return fmt.Errorf("system notification recipients empty")
	}
	users, err := s.resolveRecipientUsers(recipientType, recipientIDs, includeSub)
	if err != nil {
		return err
	}
	if len(users) == 0 {
		return fmt.Errorf("system notification recipients empty")
	}
	userIDs := make([]int64, 0, len(users))
	for _, u := range users {
		userIDs = append(userIDs, u.ID)
	}

	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer func() {
		if err != nil {
			_ = tx.Rollback()
		}
	}()

	var typeID int64
	if err = s.txQueryRow(tx, `SELECT id FROM notification_types WHERE name = 'system' LIMIT 1`).Scan(&typeID); err != nil {
		return fmt.Errorf("notification type system not found")
	}
	var senderID int64
	if err = s.txQueryRow(tx, `SELECT id FROM users WHERE deleted_at IS NULL AND status = 'active' AND role = 'admin' ORDER BY id LIMIT 1`).Scan(&senderID); err != nil {
		if err = s.txQueryRow(tx, `SELECT id FROM users WHERE deleted_at IS NULL AND status = 'active' ORDER BY id LIMIT 1`).Scan(&senderID); err != nil {
			return fmt.Errorf("no active sender user found")
		}
	}

	insertNotificationSQL := `
INSERT INTO notifications (title, content, content_html, type_id, sender_id, created_at, expires_at, is_archived)
VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now', '+90 days'), 0)
`
	if s.driver == "postgres" {
		insertNotificationSQL = `
INSERT INTO notifications (title, content, content_html, type_id, sender_id, created_at, expires_at, is_archived)
VALUES (?, ?, ?, ?, ?, NOW(), NOW() + INTERVAL '90 days', false)
`
	}
	res, err := s.txExec(tx, insertNotificationSQL, title, content, content, typeID, senderID)
	if err != nil {
		return err
	}
	var notificationID int64
	if s.driver == "postgres" {
		if err = s.txQueryRow(tx, `SELECT id FROM notifications WHERE sender_id = ? ORDER BY id DESC LIMIT 1`, senderID).Scan(&notificationID); err != nil {
			return err
		}
	} else {
		notificationID, err = res.LastInsertId()
		if err != nil {
			return err
		}
	}

	insertRecipientSQL := `
INSERT OR IGNORE INTO notification_recipients (notification_id, user_id, is_read, delivery_status, created_at)
VALUES (?, ?, 0, 'pending', datetime('now'))
`
	if s.driver == "postgres" {
		insertRecipientSQL = `
INSERT INTO notification_recipients (notification_id, user_id, is_read, delivery_status, created_at)
VALUES (?, ?, false, 'pending', NOW())
ON CONFLICT (notification_id, user_id) DO NOTHING
`
	}
	stmt, err := s.txPrepare(tx, insertRecipientSQL)
	if err != nil {
		return err
	}
	defer stmt.Close()
	for _, uid := range userIDs {
		if _, err = stmt.Exec(notificationID, uid); err != nil {
			return err
		}
	}
	return tx.Commit()
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

func (s *AlertRuntimeStore) hasTableColumn(table, column string) bool {
	if s == nil || s.db == nil {
		return false
	}
	if s.driver == "postgres" {
		var count int
		err := s.queryRow(`
SELECT COUNT(1)
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
`, strings.ToLower(strings.TrimSpace(table)), strings.ToLower(strings.TrimSpace(column))).Scan(&count)
		return err == nil && count > 0
	}
	rows, err := s.query(fmt.Sprintf("PRAGMA table_info(%s)", table))
	if err != nil {
		return false
	}
	defer rows.Close()
	for rows.Next() {
		var (
			cid       int
			name      string
			typ       string
			notnull   int
			dfltValue sql.NullString
			pk        int
		)
		if err := rows.Scan(&cid, &name, &typ, &notnull, &dfltValue, &pk); err != nil {
			return false
		}
		if strings.EqualFold(strings.TrimSpace(name), strings.TrimSpace(column)) {
			return true
		}
	}
	return false
}

func (s *AlertRuntimeStore) rebind(query string) string {
	if s.driver != "postgres" {
		return query
	}
	var b strings.Builder
	b.Grow(len(query) + 16)
	arg := 1
	for _, ch := range query {
		if ch == '?' {
			b.WriteByte('$')
			b.WriteString(strconv.Itoa(arg))
			arg++
			continue
		}
		b.WriteRune(ch)
	}
	return b.String()
}

func (s *AlertRuntimeStore) exec(query string, args ...any) (sql.Result, error) {
	return s.db.Exec(s.rebind(query), args...)
}

func (s *AlertRuntimeStore) query(query string, args ...any) (*sql.Rows, error) {
	return s.db.Query(s.rebind(query), args...)
}

func (s *AlertRuntimeStore) queryRow(query string, args ...any) *sql.Row {
	return s.db.QueryRow(s.rebind(query), args...)
}

func (s *AlertRuntimeStore) txExec(tx *sql.Tx, query string, args ...any) (sql.Result, error) {
	return tx.Exec(s.rebind(query), args...)
}

func (s *AlertRuntimeStore) txQueryRow(tx *sql.Tx, query string, args ...any) *sql.Row {
	return tx.QueryRow(s.rebind(query), args...)
}

func (s *AlertRuntimeStore) txPrepare(tx *sql.Tx, query string) (*sql.Stmt, error) {
	return tx.Prepare(s.rebind(query))
}

func parseStringMapJSON(raw string) map[string]string {
	out := map[string]string{}
	parsed := map[string]any{}
	if err := json.Unmarshal([]byte(defaultJSON(raw)), &parsed); err != nil {
		return out
	}
	for k, v := range parsed {
		key := strings.TrimSpace(k)
		if key == "" {
			continue
		}
		out[key] = strings.TrimSpace(asStringAny(v))
	}
	return out
}

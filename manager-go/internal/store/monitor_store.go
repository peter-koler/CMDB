package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"manager-go/internal/model"

	_ "github.com/mattn/go-sqlite3"
)

var (
	ErrNotFound        = errors.New("monitor not found")
	ErrVersionConflict = errors.New("monitor version conflict")
	ErrInvalidInput    = errors.New("invalid monitor input")
)

type MonitorStore struct {
	mu           sync.RWMutex
	nextID       int64
	records      map[int64]model.Monitor
	metricsViews map[int64]MonitorMetricsViewPref
	db           *sql.DB
}

type MonitorCompileLog struct {
	ID        int64  `json:"id"`
	MonitorID int64  `json:"monitor_id"`
	App       string `json:"app"`
	Stage     string `json:"stage"`
	Status    string `json:"status"`
	ErrorPath string `json:"error_path,omitempty"`
	Reason    string `json:"reason,omitempty"`
	CreatedAt string `json:"created_at"`
}

type MonitorMetricsViewPref struct {
	MonitorID            int64               `json:"monitor_id"`
	VisibleFieldsByGroup map[string][]string `json:"visible_fields_by_group"`
	UpdatedAt            string              `json:"updated_at,omitempty"`
}

func NewMonitorStore() *MonitorStore {
	return &MonitorStore{
		nextID:       1,
		records:      map[int64]model.Monitor{},
		metricsViews: map[int64]MonitorMetricsViewPref{},
	}
}

func NewMonitorStoreWithPath(dbPath string) (*MonitorStore, error) {
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create monitor store directory failed: %w", err)
	}
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open monitor sqlite db failed: %w", err)
	}
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)

	s := &MonitorStore{
		nextID:       1,
		records:      map[int64]model.Monitor{},
		metricsViews: map[int64]MonitorMetricsViewPref{},
		db:           db,
	}
	if err := s.initTable(); err != nil {
		return nil, err
	}
	if err := s.migrateLegacyManagerMonitors(); err != nil {
		return nil, err
	}
	if err := s.loadFromDB(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *MonitorStore) Create(in model.MonitorCreateInput) (model.Monitor, error) {
	if err := validateCreate(in); err != nil {
		return model.Monitor{}, err
	}
	interval := normalizedInterval(in.IntervalSeconds, in.Interval)
	now := time.Now()
	s.mu.Lock()
	defer s.mu.Unlock()
	id := s.nextID
	s.nextID++
	m := model.Monitor{
		ID:              id,
		JobID:           buildJobID(id, now),
		CIID:            in.CIID,
		CIModelID:       in.CIModelID,
		CIName:          in.CIName,
		CICode:          in.CICode,
		Name:            in.Name,
		App:             in.App,
		Target:          in.Target,
		TemplateID:      in.TemplateID,
		IntervalSeconds: interval,
		Enabled:         in.Enabled,
		Status:          model.StatusUnknown,
		Labels:          cloneStringMap(in.Labels),
		Params:          cloneStringMap(in.Params),
		Version:         1,
		CreatedAt:       now,
		UpdatedAt:       now,
	}
	s.records[id] = m
	if err := s.persistUpsert(m); err != nil {
		delete(s.records, id)
		return model.Monitor{}, err
	}
	return m, nil
}

func (s *MonitorStore) Get(id int64) (model.Monitor, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	m, ok := s.records[id]
	if !ok {
		return model.Monitor{}, ErrNotFound
	}
	return m, nil
}

func (s *MonitorStore) List() []model.Monitor {
	s.mu.RLock()
	defer s.mu.RUnlock()
	items := make([]model.Monitor, 0, len(s.records))
	for _, m := range s.records {
		items = append(items, m)
	}
	sort.Slice(items, func(i, j int) bool { return items[i].ID < items[j].ID })
	return items
}

func (s *MonitorStore) Update(id int64, in model.MonitorUpdateInput) (model.Monitor, error) {
	if err := validateUpdate(in); err != nil {
		return model.Monitor{}, err
	}
	interval := normalizedInterval(in.IntervalSeconds, in.Interval)
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.records[id]
	if !ok {
		return model.Monitor{}, ErrNotFound
	}
	if cur.Version != in.Version {
		return model.Monitor{}, ErrVersionConflict
	}
	cur.CIID = in.CIID
	cur.CIModelID = in.CIModelID
	cur.CIName = in.CIName
	cur.CICode = in.CICode
	cur.Name = in.Name
	cur.App = in.App
	cur.Target = in.Target
	cur.TemplateID = in.TemplateID
	cur.IntervalSeconds = interval
	cur.Enabled = in.Enabled
	cur.Labels = cloneStringMap(in.Labels)
	cur.Params = cloneStringMap(in.Params)
	cur.Version++
	cur.UpdatedAt = time.Now()
	s.records[id] = cur
	if err := s.persistUpsert(cur); err != nil {
		return model.Monitor{}, err
	}
	return cur, nil
}

func (s *MonitorStore) SetEnabled(id int64, enabled bool, version int64) (model.Monitor, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.records[id]
	if !ok {
		return model.Monitor{}, ErrNotFound
	}
	if cur.Version != version {
		return model.Monitor{}, ErrVersionConflict
	}
	cur.Enabled = enabled
	cur.Version++
	cur.UpdatedAt = time.Now()
	s.records[id] = cur
	if err := s.persistUpsert(cur); err != nil {
		return model.Monitor{}, err
	}
	return cur, nil
}

func (s *MonitorStore) Delete(id int64, version int64) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.records[id]
	if !ok {
		return ErrNotFound
	}
	if cur.Version != version {
		return ErrVersionConflict
	}
	delete(s.records, id)
	if err := s.persistDelete(id); err != nil {
		return err
	}
	delete(s.metricsViews, id)
	if s.db != nil {
		_, _ = s.db.Exec(`DELETE FROM monitor_view_prefs WHERE monitor_id = ?`, id)
	}
	return nil
}

func (s *MonitorStore) GetMetricsViewPref(monitorID int64) (MonitorMetricsViewPref, error) {
	s.mu.RLock()
	_, ok := s.records[monitorID]
	if !ok {
		s.mu.RUnlock()
		return MonitorMetricsViewPref{}, ErrNotFound
	}
	if s.db == nil {
		item, exists := s.metricsViews[monitorID]
		s.mu.RUnlock()
		if !exists {
			return MonitorMetricsViewPref{
				MonitorID:            monitorID,
				VisibleFieldsByGroup: map[string][]string{},
			}, nil
		}
		out := item
		out.VisibleFieldsByGroup = cloneStringSliceMap(item.VisibleFieldsByGroup)
		return out, nil
	}
	s.mu.RUnlock()

	row := s.db.QueryRow(`
SELECT metrics_visible_json, updated_at
FROM monitor_view_prefs
WHERE monitor_id = ?
`, monitorID)
	var rawJSON string
	var updatedAt string
	switch err := row.Scan(&rawJSON, &updatedAt); {
	case err == nil:
		parsed := parseMetricsVisibleJSON(rawJSON)
		return MonitorMetricsViewPref{
			MonitorID:            monitorID,
			VisibleFieldsByGroup: parsed,
			UpdatedAt:            updatedAt,
		}, nil
	case errors.Is(err, sql.ErrNoRows):
		return MonitorMetricsViewPref{
			MonitorID:            monitorID,
			VisibleFieldsByGroup: map[string][]string{},
		}, nil
	default:
		return MonitorMetricsViewPref{}, err
	}
}

func (s *MonitorStore) UpsertMetricsViewPref(monitorID int64, visibleFieldsByGroup map[string][]string) (MonitorMetricsViewPref, error) {
	s.mu.Lock()
	_, ok := s.records[monitorID]
	if !ok {
		s.mu.Unlock()
		return MonitorMetricsViewPref{}, ErrNotFound
	}
	sanitized := sanitizeMetricsVisibleMap(visibleFieldsByGroup)
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if s.db == nil {
		item := MonitorMetricsViewPref{
			MonitorID:            monitorID,
			VisibleFieldsByGroup: cloneStringSliceMap(sanitized),
			UpdatedAt:            now,
		}
		s.metricsViews[monitorID] = item
		s.mu.Unlock()
		return item, nil
	}
	s.mu.Unlock()

	raw, err := json.Marshal(sanitized)
	if err != nil {
		return MonitorMetricsViewPref{}, err
	}
	_, err = s.db.Exec(`
INSERT INTO monitor_view_prefs (monitor_id, metrics_visible_json, updated_at)
VALUES (?, ?, ?)
ON CONFLICT(monitor_id) DO UPDATE SET
	metrics_visible_json = excluded.metrics_visible_json,
	updated_at = excluded.updated_at
`, monitorID, string(raw), now)
	if err != nil {
		return MonitorMetricsViewPref{}, err
	}
	return MonitorMetricsViewPref{
		MonitorID:            monitorID,
		VisibleFieldsByGroup: sanitized,
		UpdatedAt:            now,
	}, nil
}

func validateCreate(in model.MonitorCreateInput) error {
	interval := normalizedInterval(in.IntervalSeconds, in.Interval)
	if in.Name == "" || in.App == "" || in.Target == "" || in.TemplateID <= 0 || interval < 10 {
		return ErrInvalidInput
	}
	return nil
}

func validateUpdate(in model.MonitorUpdateInput) error {
	if in.Version <= 0 {
		return ErrInvalidInput
	}
	return validateCreate(model.MonitorCreateInput{
		Name:            in.Name,
		App:             in.App,
		Target:          in.Target,
		TemplateID:      in.TemplateID,
		IntervalSeconds: in.IntervalSeconds,
		Interval:        in.Interval,
		Enabled:         in.Enabled,
	})
}

func normalizedInterval(primary int, fallback int) int {
	if primary > 0 {
		return primary
	}
	return fallback
}

func cloneStringMap(src map[string]string) map[string]string {
	if len(src) == 0 {
		return nil
	}
	out := make(map[string]string, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

func cloneStringSliceMap(src map[string][]string) map[string][]string {
	if len(src) == 0 {
		return map[string][]string{}
	}
	out := make(map[string][]string, len(src))
	for key, values := range src {
		copied := make([]string, 0, len(values))
		for _, value := range values {
			trimmed := strings.TrimSpace(value)
			if trimmed == "" {
				continue
			}
			copied = append(copied, trimmed)
		}
		out[strings.TrimSpace(key)] = copied
	}
	return out
}

func sanitizeMetricsVisibleMap(src map[string][]string) map[string][]string {
	if len(src) == 0 {
		return map[string][]string{}
	}
	out := make(map[string][]string, len(src))
	for rawGroup, rawFields := range src {
		group := strings.TrimSpace(rawGroup)
		if group == "" {
			continue
		}
		seen := make(map[string]struct{}, len(rawFields))
		fields := make([]string, 0, len(rawFields))
		for _, rawField := range rawFields {
			field := strings.TrimSpace(rawField)
			if field == "" {
				continue
			}
			if _, ok := seen[field]; ok {
				continue
			}
			seen[field] = struct{}{}
			fields = append(fields, field)
		}
		out[group] = fields
	}
	return out
}

func parseMetricsVisibleJSON(raw string) map[string][]string {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return map[string][]string{}
	}
	var parsed map[string][]string
	if err := json.Unmarshal([]byte(trimmed), &parsed); err == nil {
		return sanitizeMetricsVisibleMap(parsed)
	}
	var generic map[string]any
	if err := json.Unmarshal([]byte(trimmed), &generic); err != nil {
		return map[string][]string{}
	}
	converted := make(map[string][]string, len(generic))
	for rawGroup, raw := range generic {
		group := strings.TrimSpace(rawGroup)
		if group == "" {
			continue
		}
		list, ok := raw.([]any)
		if !ok {
			continue
		}
		fields := make([]string, 0, len(list))
		for _, one := range list {
			field := strings.TrimSpace(fmt.Sprintf("%v", one))
			if field == "" {
				continue
			}
			fields = append(fields, field)
		}
		converted[group] = fields
	}
	return sanitizeMetricsVisibleMap(converted)
}

func buildJobID(id int64, now time.Time) string {
	return fmt.Sprintf("job-%d-%d", id, now.UnixMilli())
}

// Shared schema with Python Web: monitors + monitor_params.
func (s *MonitorStore) initTable() error {
	if s == nil || s.db == nil {
		return nil
	}
	_, err := s.db.Exec(`
CREATE TABLE IF NOT EXISTS monitors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id BIGINT,
  name TEXT NOT NULL,
  app TEXT NOT NULL,
  scrape TEXT,
  instance TEXT NOT NULL,
  intervals INTEGER NOT NULL DEFAULT 60,
  schedule_type TEXT NOT NULL DEFAULT 'interval',
  cron_expression TEXT,
  status INTEGER NOT NULL DEFAULT 0,
  type INTEGER NOT NULL DEFAULT 0,
  labels_json TEXT NOT NULL DEFAULT '{}',
  annotations_json TEXT NOT NULL DEFAULT '{}',
  description TEXT,
  creator TEXT,
  modifier TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_monitors_app ON monitors(app);
CREATE INDEX IF NOT EXISTS idx_monitors_instance ON monitors(instance);
CREATE INDEX IF NOT EXISTS idx_monitors_status ON monitors(status);

CREATE TABLE IF NOT EXISTS monitor_params (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monitor_id INTEGER NOT NULL,
  field TEXT NOT NULL,
  param_value TEXT,
  type INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(monitor_id, field)
);
CREATE INDEX IF NOT EXISTS idx_monitor_params_monitor_id ON monitor_params(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_params_field ON monitor_params(field);

CREATE TABLE IF NOT EXISTS monitor_view_prefs (
  monitor_id INTEGER PRIMARY KEY,
  metrics_visible_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_compile_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monitor_id INTEGER NOT NULL,
  app TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  error_path TEXT,
  reason TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_monitor_compile_logs_monitor_id ON monitor_compile_logs(monitor_id);
CREATE INDEX IF NOT EXISTS idx_monitor_compile_logs_created_at ON monitor_compile_logs(created_at);
`)
	return err
}

func (s *MonitorStore) AddCompileLog(monitorID int64, app string, stage string, status string, errorPath string, reason string) error {
	if s == nil || s.db == nil {
		return nil
	}
	if strings.TrimSpace(stage) == "" {
		stage = "unknown"
	}
	if strings.TrimSpace(status) == "" {
		status = "unknown"
	}
	_, err := s.db.Exec(`
INSERT INTO monitor_compile_logs (monitor_id, app, stage, status, error_path, reason, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
`, monitorID, strings.TrimSpace(app), strings.TrimSpace(stage), strings.TrimSpace(status), strings.TrimSpace(errorPath), strings.TrimSpace(reason), time.Now().Format(time.RFC3339Nano))
	return err
}

func (s *MonitorStore) ListCompileLogs(monitorID int64, limit int) ([]MonitorCompileLog, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	if limit <= 0 {
		limit = 20
	}
	if limit > 200 {
		limit = 200
	}
	rows, err := s.db.Query(`
SELECT id, monitor_id, app, stage, status, error_path, reason, created_at
FROM monitor_compile_logs
WHERE monitor_id = ?
ORDER BY id DESC
LIMIT ?
`, monitorID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]MonitorCompileLog, 0, limit)
	for rows.Next() {
		var item MonitorCompileLog
		if err := rows.Scan(&item.ID, &item.MonitorID, &item.App, &item.Stage, &item.Status, &item.ErrorPath, &item.Reason, &item.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *MonitorStore) loadFromDB() error {
	if s == nil || s.db == nil {
		return nil
	}
	rows, err := s.db.Query(`
SELECT id, job_id, name, app, instance, intervals, status, labels_json, annotations_json, created_at, updated_at
FROM monitors
ORDER BY id ASC
`)
	if err != nil {
		return err
	}
	defer rows.Close()

	maxID := int64(0)
	for rows.Next() {
		var m model.Monitor
		var jobID sql.NullInt64
		var statusInt int
		var labelsJSON string
		var annotationsJSON string
		var createdAt string
		var updatedAt string
		if err := rows.Scan(
			&m.ID, &jobID, &m.Name, &m.App, &m.Target, &m.IntervalSeconds, &statusInt, &labelsJSON, &annotationsJSON, &createdAt, &updatedAt,
		); err != nil {
			return err
		}
		if jobID.Valid {
			m.JobID = strconv.FormatInt(jobID.Int64, 10)
		}
		m.Enabled = statusInt != 0
		switch statusInt {
		case 0:
			m.Status = model.MonitorStatus("paused")
		case 1:
			m.Status = model.MonitorStatus("up")
		default:
			m.Status = model.MonitorStatus("down")
		}
		_ = json.Unmarshal([]byte(defaultJSON(labelsJSON)), &m.Labels)
		meta := map[string]any{}
		_ = json.Unmarshal([]byte(defaultJSON(annotationsJSON)), &meta)
		m.TemplateID = readMetaInt64(meta, "template_id", 1)
		m.Version = readMetaInt64(meta, "manager_version", 1)
		m.CIID = readMetaInt64(meta, "ci_id", 0)
		m.CIModelID = readMetaInt64(meta, "ci_model_id", 0)
		m.CIName = readMetaString(meta, "ci_name")
		m.CICode = readMetaString(meta, "ci_code")
		m.CreatedAt = parseDBTime(createdAt, time.Now())
		m.UpdatedAt = parseDBTime(updatedAt, m.CreatedAt)
		m.Params, err = s.loadParamsByMonitorID(m.ID)
		if err != nil {
			return err
		}
		s.records[m.ID] = m
		if m.ID > maxID {
			maxID = m.ID
		}
	}
	if err := rows.Err(); err != nil {
		return err
	}
	s.nextID = maxID + 1
	return nil
}

func (s *MonitorStore) persistUpsert(m model.Monitor) error {
	if s == nil || s.db == nil {
		return nil
	}
	labelsJSON, _ := json.Marshal(defaultMap(m.Labels))
	meta := map[string]any{
		"template_id":     m.TemplateID,
		"manager_version": m.Version,
		"ci_id":           m.CIID,
		"ci_model_id":     m.CIModelID,
		"ci_name":         m.CIName,
		"ci_code":         m.CICode,
	}
	annotationsJSON, _ := json.Marshal(meta)
	status := 0
	if m.Enabled {
		status = 1
	}
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	_, err = tx.Exec(`
INSERT INTO monitors
  (id, job_id, name, app, instance, intervals, schedule_type, status, type, labels_json, annotations_json, description, created_at, updated_at)
VALUES
  (?, ?, ?, ?, ?, ?, 'interval', ?, 0, ?, ?, '', ?, ?)
ON CONFLICT(id) DO UPDATE SET
  job_id=excluded.job_id,
  name=excluded.name,
  app=excluded.app,
  instance=excluded.instance,
  intervals=excluded.intervals,
  schedule_type=excluded.schedule_type,
  status=excluded.status,
  type=excluded.type,
  labels_json=excluded.labels_json,
  annotations_json=excluded.annotations_json,
  description=excluded.description,
  created_at=excluded.created_at,
  updated_at=excluded.updated_at
`,
		m.ID, m.ID, m.Name, m.App, m.Target, m.IntervalSeconds, status,
		string(labelsJSON), string(annotationsJSON), m.CreatedAt.Format(time.RFC3339Nano), m.UpdatedAt.Format(time.RFC3339Nano),
	)
	if err != nil {
		_ = tx.Rollback()
		return err
	}
	if _, err := tx.Exec(`DELETE FROM monitor_params WHERE monitor_id = ?`, m.ID); err != nil {
		_ = tx.Rollback()
		return err
	}
	for k, v := range m.Params {
		field := strings.TrimSpace(k)
		if field == "" {
			continue
		}
		if _, err := tx.Exec(`
INSERT INTO monitor_params (monitor_id, field, param_value, type, created_at, updated_at)
VALUES (?, ?, ?, 1, ?, ?)
`,
			m.ID, field, v, m.CreatedAt.Format(time.RFC3339Nano), m.UpdatedAt.Format(time.RFC3339Nano)); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func (s *MonitorStore) persistDelete(id int64) error {
	if s == nil || s.db == nil {
		return nil
	}
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	if _, err := tx.Exec(`DELETE FROM monitor_params WHERE monitor_id = ?`, id); err != nil {
		_ = tx.Rollback()
		return err
	}
	if _, err := tx.Exec(`DELETE FROM monitors WHERE id = ?`, id); err != nil {
		_ = tx.Rollback()
		return err
	}
	return tx.Commit()
}

func (s *MonitorStore) loadParamsByMonitorID(id int64) (map[string]string, error) {
	if s == nil || s.db == nil {
		return nil, nil
	}
	rows, err := s.db.Query(`SELECT field, param_value FROM monitor_params WHERE monitor_id = ?`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	params := map[string]string{}
	for rows.Next() {
		var field string
		var value string
		if err := rows.Scan(&field, &value); err != nil {
			return nil, err
		}
		params[field] = value
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if len(params) == 0 {
		return nil, nil
	}
	return params, nil
}

func boolToInt(v bool) int {
	if v {
		return 1
	}
	return 0
}

func defaultMap(src map[string]string) map[string]string {
	if src == nil {
		return map[string]string{}
	}
	return src
}

func defaultJSON(s string) string {
	if strings.TrimSpace(s) == "" {
		return "{}"
	}
	return s
}

func readMetaInt64(meta map[string]any, key string, def int64) int64 {
	v, ok := meta[key]
	if !ok || v == nil {
		return def
	}
	switch n := v.(type) {
	case int:
		return int64(n)
	case int64:
		return n
	case float64:
		return int64(n)
	case string:
		if x, err := strconv.ParseInt(strings.TrimSpace(n), 10, 64); err == nil {
			return x
		}
	}
	return def
}

func readMetaString(meta map[string]any, key string) string {
	v, ok := meta[key]
	if !ok || v == nil {
		return ""
	}
	return fmt.Sprintf("%v", v)
}

func parseDBTime(raw string, def time.Time) time.Time {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return def
	}
	layouts := []string{
		time.RFC3339Nano,
		time.RFC3339,
		"2006-01-02 15:04:05.999999",
		"2006-01-02 15:04:05",
	}
	for _, layout := range layouts {
		if tm, err := time.Parse(layout, raw); err == nil {
			return tm
		}
	}
	return def
}

func (s *MonitorStore) migrateLegacyManagerMonitors() error {
	if s == nil || s.db == nil {
		return nil
	}
	var legacyExists int
	if err := s.db.QueryRow(`SELECT COUNT(1) FROM sqlite_master WHERE type='table' AND name='manager_monitors'`).Scan(&legacyExists); err != nil {
		return err
	}
	if legacyExists == 0 {
		return nil
	}
	var targetCount int
	if err := s.db.QueryRow(`SELECT COUNT(1) FROM monitors`).Scan(&targetCount); err != nil {
		return err
	}
	if targetCount > 0 {
		return nil
	}

	rows, err := s.db.Query(`
SELECT id, ci_id, ci_model_id, ci_name, ci_code, name, app, target, template_id,
       interval_seconds, enabled, labels_json, params_json, version, created_at, updated_at
FROM manager_monitors
ORDER BY id ASC
`)
	if err != nil {
		return nil
	}
	defer rows.Close()

	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	for rows.Next() {
		var (
			id         int64
			ciID       int64
			ciModelID  int64
			ciName     string
			ciCode     string
			name       string
			app        string
			target     string
			templateID int64
			intervals  int
			enabled    int
			labelsJSON string
			paramsJSON string
			version    int64
			createdAt  string
			updatedAt  string
		)
		if err := rows.Scan(&id, &ciID, &ciModelID, &ciName, &ciCode, &name, &app, &target, &templateID,
			&intervals, &enabled, &labelsJSON, &paramsJSON, &version, &createdAt, &updatedAt); err != nil {
			_ = tx.Rollback()
			return err
		}
		status := 0
		if enabled != 0 {
			status = 1
		}
		meta := map[string]any{
			"template_id":     templateID,
			"manager_version": version,
			"ci_id":           ciID,
			"ci_model_id":     ciModelID,
			"ci_name":         ciName,
			"ci_code":         ciCode,
		}
		annotationsJSON, _ := json.Marshal(meta)
		if _, err := tx.Exec(`
INSERT INTO monitors
  (id, job_id, name, app, instance, intervals, schedule_type, status, type, labels_json, annotations_json, description, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, 'interval', ?, 0, ?, ?, '', ?, ?)
ON CONFLICT(id) DO NOTHING
`, id, id, name, app, target, intervals, status, defaultJSON(labelsJSON), string(annotationsJSON), createdAt, updatedAt); err != nil {
			_ = tx.Rollback()
			return err
		}
		params := map[string]string{}
		_ = json.Unmarshal([]byte(defaultJSON(paramsJSON)), &params)
		for k, v := range params {
			if strings.TrimSpace(k) == "" {
				continue
			}
			if _, err := tx.Exec(`
INSERT INTO monitor_params (monitor_id, field, param_value, type, created_at, updated_at)
VALUES (?, ?, ?, 1, ?, ?)
ON CONFLICT(monitor_id, field) DO UPDATE SET param_value=excluded.param_value, updated_at=excluded.updated_at
`, id, k, v, createdAt, updatedAt); err != nil {
				_ = tx.Rollback()
				return err
			}
		}
	}
	if err := rows.Err(); err != nil {
		_ = tx.Rollback()
		return err
	}
	return tx.Commit()
}

package store

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"manager-go/internal/dbutil"

	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3"
)

type TopologyTemplateLayer struct {
	ID        string   `json:"id"`
	Name      string   `json:"name"`
	ModelKeys []string `json:"modelKeys"`
}

type TopologyTemplate struct {
	ID                   string                  `json:"id"`
	Name                 string                  `json:"name"`
	Description          string                  `json:"description"`
	SeedModels           []string                `json:"seedModels"`
	TraverseDirection    string                  `json:"traverseDirection"`
	AllowedRelationTypes []string                `json:"allowedRelationTypes"`
	VisibleModelKeys     []string                `json:"visibleModelKeys"`
	Layers               []TopologyTemplateLayer `json:"layers"`
	LayoutDirection      string                  `json:"layoutDirection"`
	GroupBy              string                  `json:"groupBy"`
	AggregateEnabled     bool                    `json:"aggregateEnabled"`
	AggregateThreshold   int                     `json:"aggregateThreshold"`
	CreatedAt            string                  `json:"createdAt,omitempty"`
	UpdatedAt            string                  `json:"updatedAt,omitempty"`
	CreatedBy            string                  `json:"createdBy,omitempty"`
	UpdatedBy            string                  `json:"updatedBy,omitempty"`
}

type TopologyTemplateStore struct {
	db     *sql.DB
	driver string
}

func NewTopologyTemplateStoreWithPath(dsn string) (*TopologyTemplateStore, error) {
	driver, resolved := dbutil.ResolveDriverAndDSN(dsn, "../backend/instance/it_ops.db")
	if driver == "sqlite3" {
		dir := filepath.Dir(resolved)
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return nil, fmt.Errorf("create topology template store directory failed: %w", err)
		}
	}
	db, err := sql.Open(driver, resolved)
	if err != nil {
		return nil, fmt.Errorf("open %s db failed: %w", driver, err)
	}
	db.SetMaxOpenConns(5)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(time.Hour)

	s := &TopologyTemplateStore{db: db, driver: driver}
	if err := s.initTable(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *TopologyTemplateStore) Close() error {
	if s == nil || s.db == nil {
		return nil
	}
	return s.db.Close()
}

func (s *TopologyTemplateStore) rebind(query string) string {
	if s.driver != "postgres" {
		return query
	}
	var b strings.Builder
	b.Grow(len(query) + 16)
	arg := 1
	for _, ch := range query {
		if ch == '?' {
			b.WriteByte('$')
			b.WriteString(fmt.Sprintf("%d", arg))
			arg++
			continue
		}
		b.WriteRune(ch)
	}
	return b.String()
}

func (s *TopologyTemplateStore) exec(query string, args ...any) (sql.Result, error) {
	return s.db.Exec(s.rebind(query), args...)
}

func (s *TopologyTemplateStore) query(query string, args ...any) (*sql.Rows, error) {
	return s.db.Query(s.rebind(query), args...)
}

func (s *TopologyTemplateStore) queryRow(query string, args ...any) *sql.Row {
	return s.db.QueryRow(s.rebind(query), args...)
}

func (s *TopologyTemplateStore) initTable() error {
	if s == nil || s.db == nil {
		return nil
	}
	sqlStmt := `
CREATE TABLE IF NOT EXISTS cmdb_topology_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  seed_models TEXT NOT NULL DEFAULT '[]',
  traverse_direction TEXT NOT NULL DEFAULT 'both',
  allowed_relation_types TEXT NOT NULL DEFAULT '[]',
  visible_model_keys TEXT NOT NULL DEFAULT '[]',
  layers TEXT NOT NULL DEFAULT '[]',
  layout_direction TEXT NOT NULL DEFAULT 'horizontal',
  group_by_key TEXT NOT NULL DEFAULT 'idc',
  aggregate_enabled INTEGER NOT NULL DEFAULT 1,
  aggregate_threshold INTEGER NOT NULL DEFAULT 4,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by TEXT,
  updated_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_cmdb_topology_templates_updated_at ON cmdb_topology_templates(updated_at);
`
	if s.driver == "postgres" {
		sqlStmt = `
CREATE TABLE IF NOT EXISTS cmdb_topology_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  seed_models TEXT NOT NULL DEFAULT '[]',
  traverse_direction TEXT NOT NULL DEFAULT 'both',
  allowed_relation_types TEXT NOT NULL DEFAULT '[]',
  visible_model_keys TEXT NOT NULL DEFAULT '[]',
  layers TEXT NOT NULL DEFAULT '[]',
  layout_direction TEXT NOT NULL DEFAULT 'horizontal',
  group_by_key TEXT NOT NULL DEFAULT 'idc',
  aggregate_enabled BOOLEAN NOT NULL DEFAULT true,
  aggregate_threshold INTEGER NOT NULL DEFAULT 4,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by TEXT,
  updated_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_cmdb_topology_templates_updated_at ON cmdb_topology_templates(updated_at);
`
	}
	_, err := s.exec(sqlStmt)
	return err
}

func (s *TopologyTemplateStore) List(keyword string, page, pageSize int) ([]TopologyTemplate, int, error) {
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}
	if pageSize > 200 {
		pageSize = 200
	}
	kw := strings.TrimSpace(keyword)
	where := ""
	args := []any{}
	if kw != "" {
		where = "WHERE name ILIKE ? OR description ILIKE ?"
		args = append(args, "%"+kw+"%", "%"+kw+"%")
		if s.driver != "postgres" {
			where = "WHERE LOWER(name) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?)"
		}
	}

	countQuery := fmt.Sprintf("SELECT COUNT(1) FROM cmdb_topology_templates %s", where)
	var total int
	if err := s.queryRow(countQuery, args...).Scan(&total); err != nil {
		return nil, 0, err
	}

	listArgs := append([]any{}, args...)
	listArgs = append(listArgs, pageSize, (page-1)*pageSize)
	rows, err := s.query(fmt.Sprintf(`
SELECT id,name,description,seed_models,traverse_direction,allowed_relation_types,visible_model_keys,layers,layout_direction,group_by_key,aggregate_enabled,aggregate_threshold,created_at,updated_at,created_by,updated_by
FROM cmdb_topology_templates
%s
ORDER BY updated_at DESC, id DESC
LIMIT ? OFFSET ?
`, where), listArgs...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	items := make([]TopologyTemplate, 0)
	for rows.Next() {
		item, err := scanTopologyTemplate(rows)
		if err != nil {
			return nil, 0, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, 0, err
	}
	return items, total, nil
}

func (s *TopologyTemplateStore) Get(id string) (TopologyTemplate, error) {
	rows, err := s.query(`
SELECT id,name,description,seed_models,traverse_direction,allowed_relation_types,visible_model_keys,layers,layout_direction,group_by_key,aggregate_enabled,aggregate_threshold,created_at,updated_at,created_by,updated_by
FROM cmdb_topology_templates WHERE id = ?
`, strings.TrimSpace(id))
	if err != nil {
		return TopologyTemplate{}, err
	}
	defer rows.Close()
	if !rows.Next() {
		return TopologyTemplate{}, ErrNotFound
	}
	item, err := scanTopologyTemplate(rows)
	if err != nil {
		return TopologyTemplate{}, err
	}
	return item, nil
}

func (s *TopologyTemplateStore) Create(in TopologyTemplate) (TopologyTemplate, error) {
	in = normalizeTopologyTemplate(in)
	now := time.Now().UTC().Format(time.RFC3339)
	if strings.TrimSpace(in.CreatedAt) == "" {
		in.CreatedAt = now
	}
	in.UpdatedAt = now
	_, err := s.exec(`
INSERT INTO cmdb_topology_templates(
  id,name,description,seed_models,traverse_direction,allowed_relation_types,visible_model_keys,layers,
  layout_direction,group_by_key,aggregate_enabled,aggregate_threshold,created_at,updated_at,created_by,updated_by
) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
`,
		in.ID,
		in.Name,
		in.Description,
		mustJSON(in.SeedModels),
		in.TraverseDirection,
		mustJSON(in.AllowedRelationTypes),
		mustJSON(in.VisibleModelKeys),
		mustJSON(in.Layers),
		in.LayoutDirection,
		in.GroupBy,
		in.AggregateEnabled,
		in.AggregateThreshold,
		in.CreatedAt,
		in.UpdatedAt,
		nullIfEmpty(in.CreatedBy),
		nullIfEmpty(in.UpdatedBy),
	)
	if err != nil {
		return TopologyTemplate{}, err
	}
	return in, nil
}

func (s *TopologyTemplateStore) Update(id string, in TopologyTemplate) (TopologyTemplate, error) {
	cur, err := s.Get(id)
	if err != nil {
		return TopologyTemplate{}, err
	}
	next := normalizeTopologyTemplate(in)
	next.ID = cur.ID
	next.CreatedAt = cur.CreatedAt
	next.CreatedBy = cur.CreatedBy
	next.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	if strings.TrimSpace(next.UpdatedBy) == "" {
		next.UpdatedBy = cur.UpdatedBy
	}
	_, err = s.exec(`
UPDATE cmdb_topology_templates
SET name = ?,
    description = ?,
    seed_models = ?,
    traverse_direction = ?,
    allowed_relation_types = ?,
    visible_model_keys = ?,
    layers = ?,
    layout_direction = ?,
    group_by_key = ?,
    aggregate_enabled = ?,
    aggregate_threshold = ?,
    updated_at = ?,
    updated_by = ?
WHERE id = ?
`,
		next.Name,
		next.Description,
		mustJSON(next.SeedModels),
		next.TraverseDirection,
		mustJSON(next.AllowedRelationTypes),
		mustJSON(next.VisibleModelKeys),
		mustJSON(next.Layers),
		next.LayoutDirection,
		next.GroupBy,
		next.AggregateEnabled,
		next.AggregateThreshold,
		next.UpdatedAt,
		nullIfEmpty(next.UpdatedBy),
		next.ID,
	)
	if err != nil {
		return TopologyTemplate{}, err
	}
	return next, nil
}

func (s *TopologyTemplateStore) Delete(id string) error {
	res, err := s.exec(`DELETE FROM cmdb_topology_templates WHERE id = ?`, strings.TrimSpace(id))
	if err != nil {
		return err
	}
	affected, _ := res.RowsAffected()
	if affected <= 0 {
		return ErrNotFound
	}
	return nil
}

func (s *TopologyTemplateStore) Clone(id string, operator string) (TopologyTemplate, error) {
	cur, err := s.Get(id)
	if err != nil {
		return TopologyTemplate{}, err
	}
	next := cur
	next.ID = buildTopologyTemplateID()
	next.Name = cur.Name + "-副本"
	now := time.Now().UTC().Format(time.RFC3339)
	next.CreatedAt = now
	next.UpdatedAt = now
	if strings.TrimSpace(operator) != "" {
		next.CreatedBy = operator
		next.UpdatedBy = operator
	}
	return s.Create(next)
}

func scanTopologyTemplate(rows *sql.Rows) (TopologyTemplate, error) {
	var (
		item                                        TopologyTemplate
		seedModelsRaw, relationTypesRaw, visibleRaw string
		layersRaw                                   string
		aggregateEnabledRaw                         any
		createdByRaw, updatedByRaw                  sql.NullString
	)
	if err := rows.Scan(
		&item.ID,
		&item.Name,
		&item.Description,
		&seedModelsRaw,
		&item.TraverseDirection,
		&relationTypesRaw,
		&visibleRaw,
		&layersRaw,
		&item.LayoutDirection,
		&item.GroupBy,
		&aggregateEnabledRaw,
		&item.AggregateThreshold,
		&item.CreatedAt,
		&item.UpdatedAt,
		&createdByRaw,
		&updatedByRaw,
	); err != nil {
		return TopologyTemplate{}, err
	}
	item.SeedModels = parseStringList(seedModelsRaw)
	item.AllowedRelationTypes = parseStringList(relationTypesRaw)
	item.VisibleModelKeys = parseStringList(visibleRaw)
	item.Layers = parseLayerList(layersRaw)
	item.AggregateEnabled = parseBoolAny(aggregateEnabledRaw)
	if createdByRaw.Valid {
		item.CreatedBy = createdByRaw.String
	}
	if updatedByRaw.Valid {
		item.UpdatedBy = updatedByRaw.String
	}
	return item, nil
}

func parseStringList(raw string) []string {
	if strings.TrimSpace(raw) == "" {
		return []string{}
	}
	var out []string
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return []string{}
	}
	return out
}

func parseLayerList(raw string) []TopologyTemplateLayer {
	if strings.TrimSpace(raw) == "" {
		return []TopologyTemplateLayer{}
	}
	var out []TopologyTemplateLayer
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return []TopologyTemplateLayer{}
	}
	return out
}

func parseBoolAny(v any) bool {
	switch x := v.(type) {
	case bool:
		return x
	case int64:
		return x != 0
	case int:
		return x != 0
	case float64:
		return x != 0
	case []byte:
		return string(x) == "t" || string(x) == "true" || string(x) == "1"
	case string:
		text := strings.ToLower(strings.TrimSpace(x))
		return text == "t" || text == "true" || text == "1"
	default:
		return false
	}
}

func mustJSON(v any) string {
	raw, err := json.Marshal(v)
	if err != nil {
		return "[]"
	}
	return string(raw)
}

func normalizeTopologyTemplate(in TopologyTemplate) TopologyTemplate {
	out := in
	if strings.TrimSpace(out.ID) == "" {
		out.ID = buildTopologyTemplateID()
	}
	out.Name = strings.TrimSpace(out.Name)
	out.Description = strings.TrimSpace(out.Description)
	if out.TraverseDirection == "" {
		out.TraverseDirection = "both"
	}
	if out.LayoutDirection == "" {
		out.LayoutDirection = "horizontal"
	}
	if out.GroupBy == "" {
		out.GroupBy = "idc"
	}
	if out.AggregateThreshold < 2 {
		out.AggregateThreshold = 2
	}
	if out.SeedModels == nil {
		out.SeedModels = []string{}
	}
	if out.AllowedRelationTypes == nil {
		out.AllowedRelationTypes = []string{}
	}
	if out.VisibleModelKeys == nil {
		out.VisibleModelKeys = []string{}
	}
	if out.Layers == nil {
		out.Layers = []TopologyTemplateLayer{}
	}
	return out
}

func buildTopologyTemplateID() string {
	return fmt.Sprintf("tpl-%d", time.Now().UnixNano())
}

func nullIfEmpty(v string) any {
	text := strings.TrimSpace(v)
	if text == "" {
		return nil
	}
	return text
}

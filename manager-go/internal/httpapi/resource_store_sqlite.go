package httpapi

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type sqliteResourceStore struct {
	dbPath string
	name   string
}

func newSQLiteResourceStore(dbPath, name string) *sqliteResourceStore {
	return &sqliteResourceStore{dbPath: dbPath, name: name}
}

func (s *sqliteResourceStore) create(payload map[string]any) (map[string]any, error) {
	now := time.Now().UTC().Format(time.RFC3339)
	item := cloneMap(payload)
	if _, ok := item["enabled"]; !ok {
		item["enabled"] = true
	}
	if _, ok := item["version"]; !ok {
		item["version"] = int64(1)
	}
	item["created_at"] = now
	item["updated_at"] = now

	raw, err := json.Marshal(item)
	if err != nil {
		return nil, err
	}
	sql := fmt.Sprintf(`
INSERT INTO resources(resource_type,data_json,enabled,version,created_at,updated_at)
VALUES('%s','%s',%d,%d,'%s','%s') RETURNING id;
`,
		quoteSQL(s.name), quoteSQL(string(raw)), toBoolInt(item["enabled"]), toInt64(item["version"]), quoteSQL(now), quoteSQL(now),
	)
	rows, err := s.queryJSON(sql)
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return nil, fmt.Errorf("create resource failed: empty returning")
	}
	id := toInt64(rows[0]["id"])
	item["id"] = id
	if err := s.syncData(id, item); err != nil {
		return nil, err
	}
	return item, nil
}

func (s *sqliteResourceStore) list(page, pageSize int) ([]map[string]any, int, error) {
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}
	countRows, err := s.queryJSON(fmt.Sprintf(`SELECT COUNT(1) AS total FROM resources WHERE resource_type='%s';`, quoteSQL(s.name)))
	if err != nil {
		return nil, 0, err
	}
	total := 0
	if len(countRows) > 0 {
		total = int(toInt64(countRows[0]["total"]))
	}
	rows, err := s.queryJSON(fmt.Sprintf(`
SELECT id,data_json,enabled,version,created_at,updated_at
FROM resources
WHERE resource_type='%s'
ORDER BY id DESC
LIMIT %d OFFSET %d;
`, quoteSQL(s.name), pageSize, (page-1)*pageSize))
	if err != nil {
		return nil, 0, err
	}
	out := make([]map[string]any, 0, len(rows))
	for _, row := range rows {
		item, err := rowToItem(row)
		if err != nil {
			return nil, 0, err
		}
		out = append(out, item)
	}
	return out, total, nil
}

func (s *sqliteResourceStore) get(id string) (map[string]any, bool, error) {
	n, err := strconv.ParseInt(id, 10, 64)
	if err != nil {
		return nil, false, nil
	}
	rows, err := s.queryJSON(fmt.Sprintf(`
SELECT id,data_json,enabled,version,created_at,updated_at
FROM resources WHERE resource_type='%s' AND id=%d;
`, quoteSQL(s.name), n))
	if err != nil {
		return nil, false, err
	}
	if len(rows) == 0 {
		return nil, false, nil
	}
	item, err := rowToItem(rows[0])
	if err != nil {
		return nil, false, err
	}
	return item, true, nil
}

func (s *sqliteResourceStore) update(id string, payload map[string]any) (map[string]any, bool, error) {
	item, ok, err := s.get(id)
	if err != nil || !ok {
		return nil, ok, err
	}
	for k, v := range payload {
		if k == "id" || k == "created_at" {
			continue
		}
		item[k] = v
	}
	item["updated_at"] = time.Now().UTC().Format(time.RFC3339)
	item["version"] = toInt64(item["version"]) + 1
	n, _ := strconv.ParseInt(id, 10, 64)
	if err := s.syncData(n, item); err != nil {
		return nil, false, err
	}
	return item, true, nil
}

func (s *sqliteResourceStore) delete(id string) (bool, error) {
	n, err := strconv.ParseInt(id, 10, 64)
	if err != nil {
		return false, nil
	}
	beforeRows, err := s.queryJSON(fmt.Sprintf(`SELECT COUNT(1) AS total FROM resources WHERE resource_type='%s' AND id=%d;`, quoteSQL(s.name), n))
	if err != nil {
		return false, err
	}
	if len(beforeRows) == 0 || toInt64(beforeRows[0]["total"]) == 0 {
		return false, nil
	}
	if _, err := s.execSQL(fmt.Sprintf(`DELETE FROM resources WHERE resource_type='%s' AND id=%d;`, quoteSQL(s.name), n)); err != nil {
		return false, err
	}
	return true, nil
}

func (s *sqliteResourceStore) setEnabled(id string, enabled bool) (map[string]any, bool, error) {
	item, ok, err := s.get(id)
	if err != nil || !ok {
		return nil, ok, err
	}
	item["enabled"] = enabled
	item["updated_at"] = time.Now().UTC().Format(time.RFC3339)
	item["version"] = toInt64(item["version"]) + 1
	n, _ := strconv.ParseInt(id, 10, 64)
	if err := s.syncData(n, item); err != nil {
		return nil, false, err
	}
	return item, true, nil
}

func (s *sqliteResourceStore) syncData(id int64, item map[string]any) error {
	raw, err := json.Marshal(item)
	if err != nil {
		return err
	}
	_, err = s.execSQL(fmt.Sprintf(`
UPDATE resources
SET data_json='%s', enabled=%d, version=%d, updated_at='%s'
WHERE resource_type='%s' AND id=%d;
`, quoteSQL(string(raw)), toBoolInt(item["enabled"]), toInt64(item["version"]), quoteSQL(fmt.Sprint(item["updated_at"])), quoteSQL(s.name), id))
	return err
}

func NewSQLiteResourceHub(path string) (*resourceHub, error) {
	if strings.TrimSpace(path) == "" {
		path = "data/resources.db"
	}
	if _, err := execSQL(path, `
CREATE TABLE IF NOT EXISTS resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_type TEXT NOT NULL,
  data_json TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resources_type_id ON resources(resource_type, id DESC);
`); err != nil {
		return nil, err
	}
	hub := newResourceHubWithFactory(func(name string) resourceRepo {
		return newSQLiteResourceStore(path, name)
	})
	return hub, nil
}

func (s *sqliteResourceStore) queryJSON(sql string) ([]map[string]any, error) {
	out, err := queryJSON(s.dbPath, sql)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (s *sqliteResourceStore) execSQL(sql string) (string, error) {
	return execSQL(s.dbPath, sql)
}

func queryJSON(path, sql string) ([]map[string]any, error) {
	out, err := exec.Command("sqlite3", "-json", path, sql).CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("sqlite3 query failed: %w: %s", err, string(out))
	}
	raw := strings.TrimSpace(string(out))
	if raw == "" {
		return []map[string]any{}, nil
	}
	var rows []map[string]any
	if err := json.Unmarshal([]byte(raw), &rows); err != nil {
		return nil, fmt.Errorf("decode sqlite json output failed: %w output=%s", err, raw)
	}
	return rows, nil
}

func execSQL(path, sql string) (string, error) {
	out, err := exec.Command("sqlite3", path, sql).CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("sqlite3 exec failed: %w: %s", err, string(out))
	}
	return strings.TrimSpace(string(out)), nil
}

func rowToItem(row map[string]any) (map[string]any, error) {
	item := map[string]any{}
	raw, _ := row["data_json"].(string)
	if raw != "" {
		if err := json.Unmarshal([]byte(raw), &item); err != nil {
			return nil, err
		}
	}
	item["id"] = toInt64(row["id"])
	item["enabled"] = toInt64(row["enabled"]) == 1
	item["version"] = toInt64(row["version"])
	item["created_at"] = fmt.Sprint(row["created_at"])
	item["updated_at"] = fmt.Sprint(row["updated_at"])
	return item, nil
}

func quoteSQL(v string) string {
	return strings.ReplaceAll(v, "'", "''")
}

func toBoolInt(v any) int {
	switch x := v.(type) {
	case bool:
		if x {
			return 1
		}
		return 0
	case int:
		if x != 0 {
			return 1
		}
		return 0
	case int64:
		if x != 0 {
			return 1
		}
	case float64:
		if x != 0 {
			return 1
		}
	}
	return 0
}

func toInt64(v any) int64 {
	switch x := v.(type) {
	case int64:
		return x
	case int:
		return int64(x)
	case float64:
		return int64(x)
	case json.Number:
		n, _ := x.Int64()
		return n
	case string:
		n, _ := strconv.ParseInt(x, 10, 64)
		return n
	}
	return 0
}

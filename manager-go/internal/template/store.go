package template

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"manager-go/internal/dbutil"

	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3"
)

type Store struct {
	db     *sql.DB
	driver string
}

func NewStoreWithPath(dsn string) (*Store, error) {
	driver, resolved := dbutil.ResolveDriverAndDSN(dsn, "../backend/instance/it_ops.db")
	if driver == "sqlite3" {
		dir := filepath.Dir(resolved)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return nil, fmt.Errorf("create directory failed: %w", err)
		}
	}
	db, err := sql.Open(driver, resolved)
	if err != nil {
		return nil, fmt.Errorf("open %s db failed: %w", driver, err)
	}
	db.SetMaxOpenConns(5)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(time.Hour)
	return &Store{db: db, driver: driver}, nil
}

func (s *Store) Close() error {
	if s == nil || s.db == nil {
		return nil
	}
	return s.db.Close()
}

type TemplateRow struct {
	ID        int64
	App       string
	Name      string
	Category  string
	Content   string
	Version   int64
	IsHidden  bool
	CreatedAt string
	UpdatedAt string
}

func (s *Store) ListVisibleTemplates() ([]TemplateRow, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("template store db is nil")
	}
	hiddenExpr := "CAST(COALESCE(is_hidden, 0) AS INTEGER)"
	if s.driver == "postgres" {
		hiddenExpr = "CASE WHEN COALESCE(is_hidden, false) THEN 1 ELSE 0 END"
	}
	query := fmt.Sprintf(`
SELECT
  id,
  app,
  name,
  category,
  content,
  version,
  %s AS is_hidden_norm,
  CAST(created_at AS TEXT) AS created_at,
  CAST(updated_at AS TEXT) AS updated_at
FROM monitor_templates
WHERE %s = 0
ORDER BY app ASC, version ASC, id ASC
`, hiddenExpr, hiddenExpr)
	rows, err := s.db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]TemplateRow, 0, 64)
	for rows.Next() {
		var r TemplateRow
		var isHiddenInt int
		if err := rows.Scan(&r.ID, &r.App, &r.Name, &r.Category, &r.Content, &r.Version, &isHiddenInt, &r.CreatedAt, &r.UpdatedAt); err != nil {
			return nil, err
		}
		r.IsHidden = isHiddenInt != 0
		out = append(out, r)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

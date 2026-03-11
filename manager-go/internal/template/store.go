package template

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Store struct {
	db *sql.DB
}

func NewStoreWithPath(dbPath string) (*Store, error) {
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create directory failed: %w", err)
	}
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite db failed: %w", err)
	}
	db.SetMaxOpenConns(5)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(time.Hour)
	return &Store{db: db}, nil
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
	rows, err := s.db.Query(`
SELECT
  id,
  app,
  name,
  category,
  content,
  version,
  CAST(COALESCE(is_hidden, 0) AS INTEGER) AS is_hidden_norm,
  created_at,
  updated_at
FROM monitor_templates
WHERE CAST(COALESCE(is_hidden, 0) AS INTEGER) = 0
ORDER BY app ASC, version ASC, id ASC
`)
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

package store

import (
	"database/sql"
	"path/filepath"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func TestInitTableAddsPinnedColumnForLegacyBindTable(t *testing.T) {
	t.Parallel()

	dbPath := filepath.Join(t.TempDir(), "collector_legacy.db")
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		t.Fatalf("open sqlite failed: %v", err)
	}

	legacySchema := `
CREATE TABLE IF NOT EXISTS collectors (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL UNIQUE,
	ip TEXT NOT NULL,
	version TEXT,
	status INTEGER NOT NULL DEFAULT 1,
	mode TEXT NOT NULL DEFAULT 'public',
	creator TEXT,
	modifier TEXT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS collector_monitor_binds (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	collector TEXT NOT NULL,
	monitor_id INTEGER NOT NULL,
	creator TEXT,
	modifier TEXT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	UNIQUE(collector, monitor_id)
);
`
	if _, err := db.Exec(legacySchema); err != nil {
		t.Fatalf("create legacy schema failed: %v", err)
	}
	_ = db.Close()

	store, err := NewCollectorStoreWithPath(dbPath)
	if err != nil {
		t.Fatalf("new collector store failed: %v", err)
	}
	defer store.db.Close()

	if err := store.InitTable(); err != nil {
		t.Fatalf("init table failed: %v", err)
	}

	bind, err := store.CreateBind("collector-1", 1001, 1)
	if err != nil {
		t.Fatalf("create bind failed: %v", err)
	}
	if bind.Pinned != 1 {
		t.Fatalf("unexpected pinned value: got=%d want=1", bind.Pinned)
	}
}

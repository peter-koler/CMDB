package tpl

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadFromDir(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, "define", "app-mysql.yml")
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte("app: mysql\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	store, err := LoadFromDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	tpl, ok := store.Get("mysql")
	if !ok {
		t.Fatal("expected mysql template")
	}
	if tpl.FilePath != filepath.Clean(p) {
		t.Fatalf("unexpected path: %s", tpl.FilePath)
	}
}

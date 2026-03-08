package httpapi

import (
	"net/http"
	"path/filepath"
	"testing"

	"manager-go/internal/store"
)

func TestSQLiteResourceHubReload(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "resources.db")
	hub1, err := NewSQLiteResourceHub(dbPath)
	if err != nil {
		t.Fatalf("create sqlite hub1 failed: %v", err)
	}
	srv1 := NewServer(store.NewMonitorStore(), WithResourceHub(hub1))
	h1 := srv1.Handler()
	_ = doJSON(t, h1, http.MethodPost, "/api/v1/status-pages", map[string]any{
		"name": "public-page",
		"slug": "status",
	}, http.StatusCreated)

	hub2, err := NewSQLiteResourceHub(dbPath)
	if err != nil {
		t.Fatalf("create sqlite hub2 failed: %v", err)
	}
	srv2 := NewServer(store.NewMonitorStore(), WithResourceHub(hub2))
	h2 := srv2.Handler()
	list := doJSON(t, h2, http.MethodGet, "/api/v1/status-pages?page=1&page_size=20", nil, http.StatusOK)
	if int(list["total"].(float64)) != 1 {
		t.Fatalf("expected persisted sqlite item, got=%v", list)
	}
}

package httpapi

import (
	"net/http"
	"testing"

	"manager-go/internal/store"
)

func TestPersistentResourceHubReload(t *testing.T) {
	dir := t.TempDir()
	hub1, err := NewPersistentResourceHub(dir)
	if err != nil {
		t.Fatalf("create hub1 failed: %v", err)
	}
	srv1 := NewServer(store.NewMonitorStore(), WithResourceHub(hub1))
	h1 := srv1.Handler()
	created := doJSON(t, h1, http.MethodPost, "/api/v1/labels", map[string]any{
		"name":  "env",
		"value": "prod",
	}, http.StatusCreated)
	if created["name"] != "env" {
		t.Fatalf("unexpected created payload: %v", created)
	}

	hub2, err := NewPersistentResourceHub(dir)
	if err != nil {
		t.Fatalf("create hub2 failed: %v", err)
	}
	srv2 := NewServer(store.NewMonitorStore(), WithResourceHub(hub2))
	h2 := srv2.Handler()
	list := doJSON(t, h2, http.MethodGet, "/api/v1/labels?page=1&page_size=20", nil, http.StatusOK)
	if int(list["total"].(float64)) != 1 {
		t.Fatalf("expected persisted item, got=%v", list)
	}
	items := list["items"].([]any)
	item := items[0].(map[string]any)
	if item["name"] != "env" || item["value"] != "prod" {
		t.Fatalf("unexpected persisted item: %v", item)
	}
}

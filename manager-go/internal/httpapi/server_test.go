package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"manager-go/internal/store"
)

func TestMonitorCRUDFlow(t *testing.T) {
	srv := NewServer(store.NewMonitorStore())
	h := srv.Handler()

	body := map[string]any{
		"name":             "demo",
		"app":              "linux",
		"target":           "127.0.0.1",
		"template_id":      1,
		"interval_seconds": 10,
		"enabled":          true,
	}
	created := doJSON(t, h, http.MethodPost, "/api/v1/monitors", body, http.StatusCreated)
	id := int(created["id"].(float64))
	version := int(created["version"].(float64))

	_ = doJSON(t, h, http.MethodGet, "/api/v1/monitors", nil, http.StatusOK)
	_ = doJSON(t, h, http.MethodGet, "/api/v1/monitors/1", nil, http.StatusOK)

	update := map[string]any{
		"name":             "demo2",
		"app":              "linux",
		"target":           "127.0.0.2",
		"template_id":      1,
		"interval_seconds": 15,
		"enabled":          true,
		"version":          version,
	}
	updated := doJSON(t, h, http.MethodPut, "/api/v1/monitors/1", update, http.StatusOK)
	version = int(updated["version"].(float64))

	disable := map[string]any{"version": version}
	disabled := doJSON(t, h, http.MethodPatch, "/api/v1/monitors/1/disable", disable, http.StatusOK)
	version = int(disabled["version"].(float64))

	req := httptest.NewRequest(http.MethodDelete, "/api/v1/monitors/"+strconv.Itoa(id)+"?version="+strconv.Itoa(version), nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete failed status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestNotifyTestAPIValidation(t *testing.T) {
	srv := NewServer(store.NewMonitorStore())
	h := srv.Handler()
	body := map[string]any{
		"channel":  "unsupported",
		"title":    "t",
		"template": "hello {{.Name}}",
		"data": map[string]any{
			"Name": "ops",
		},
		"config": map[string]any{},
	}
	resp := doJSON(t, h, http.MethodPost, "/api/v1/notify/test", body, http.StatusBadRequest)
	if _, ok := resp["error"]; !ok {
		t.Fatalf("expected error response, got=%v", resp)
	}
}

func doJSON(t *testing.T, h http.Handler, method, path string, body any, want int) map[string]any {
	t.Helper()
	var reader *bytes.Reader
	if body == nil {
		reader = bytes.NewReader(nil)
	} else {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		reader = bytes.NewReader(b)
	}
	req := httptest.NewRequest(method, path, reader)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != want {
		t.Fatalf("%s %s got=%d want=%d body=%s", method, path, rec.Code, want, rec.Body.String())
	}
	if rec.Body.Len() == 0 {
		return map[string]any{}
	}
	var out map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	return out
}

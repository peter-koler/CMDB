package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/collector"
	"manager-go/internal/model"
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

func TestCollectorRegisterAndTasks(t *testing.T) {
	st := store.NewMonitorStore()
	created, err := st.Create(model.MonitorCreateInput{
		Name:            "demo",
		App:             "linux",
		Target:          "127.0.0.1",
		TemplateID:      1,
		IntervalSeconds: 10,
		Enabled:         true,
	})
	if err != nil {
		t.Fatalf("create monitor: %v", err)
	}
	reg := collector.NewRegistry()
	srv := NewServer(st, WithCollectorRegistry(reg, 30))
	h := srv.Handler()

	_ = doJSON(t, h, http.MethodPost, "/api/v1/collectors/register", map[string]any{
		"id":   "c1",
		"addr": "127.0.0.1:50051",
	}, http.StatusOK)
	_ = doJSON(t, h, http.MethodPost, "/api/v1/collectors/register", map[string]any{
		"id":   "c2",
		"addr": "127.0.0.1:50052",
	}, http.StatusOK)

	tasks := doJSON(t, h, http.MethodGet, "/api/v1/collectors/c1/tasks", nil, http.StatusOK)
	if _, ok := tasks["items"]; !ok {
		t.Fatalf("tasks response invalid: %v", tasks)
	}

	assign := doJSON(t, h, http.MethodGet, "/api/v1/collectors/assignments", nil, http.StatusOK)
	if int(assign["total"].(float64)) <= 0 {
		t.Fatalf("assignments should not be empty, monitor=%d", created.ID)
	}
}

func TestMetricsIngest(t *testing.T) {
	st := store.NewMonitorStore()
	called := 0
	srv := NewServer(st, WithMetricIngest(func(point model.MetricPoint) error {
		called++
		if point.MonitorID != 1 {
			t.Fatalf("unexpected monitor id=%d", point.MonitorID)
		}
		return nil
	}))
	h := srv.Handler()
	resp := doJSON(t, h, http.MethodPost, "/api/v1/metrics", map[string]any{
		"items": []map[string]any{
			{
				"monitor_id": 1,
				"app":        "linux",
				"metrics":    "cpu",
				"field":      "usage",
				"value":      88.1,
				"unix_ms":    1,
				"instance":   "127.0.0.1",
			},
		},
	}, http.StatusOK)
	if int(resp["accepted"].(float64)) != 1 || called != 1 {
		t.Fatalf("ingest failed resp=%v called=%d", resp, called)
	}
}

func TestAlertAndDeadLetterAPIs(t *testing.T) {
	st := store.NewMonitorStore()
	alertStore := alert.NewAlertStore()
	deadStore := alert.NewDeadLetterStore()

	fired := alertStore.Fire(alert.Event{
		RuleID:      1,
		RuleName:    "cpu_high",
		MonitorID:   100,
		Severity:    "warning",
		State:       alert.StateFiring,
		Expression:  "value > 80",
		ElapsedMs:   6000,
		TriggeredAt: time.Now(),
	})
	dead := deadStore.Save(alert.NotifyTask{
		ID:      10,
		Channel: "webhook",
		Event: alert.Event{
			RuleID:      1,
			RuleName:    "cpu_high",
			MonitorID:   100,
			Severity:    "warning",
			State:       alert.StateFiring,
			TriggeredAt: time.Now(),
		},
	}, "max retry reached")

	retried := false
	srv := NewServer(st,
		WithAlertStore(alertStore),
		WithDeadLetterStore(deadStore, func(id int64) error {
			retried = true
			if id != dead.ID {
				t.Fatalf("unexpected dead letter id=%d", id)
			}
			return nil
		}),
	)
	h := srv.Handler()

	_ = doJSON(t, h, http.MethodGet, "/api/v1/alerts?scope=current", nil, http.StatusOK)
	_ = doJSON(t, h, http.MethodPost, "/api/v1/alerts/"+strconv.FormatInt(fired.ID, 10)+"/acknowledge", map[string]any{}, http.StatusOK)
	_ = doJSON(t, h, http.MethodPost, "/api/v1/alerts/"+strconv.FormatInt(fired.ID, 10)+"/close", map[string]any{}, http.StatusOK)
	_ = doJSON(t, h, http.MethodGet, "/api/v1/alerts/history", nil, http.StatusOK)
	_ = doJSON(t, h, http.MethodGet, "/api/v1/dead-letters", nil, http.StatusOK)
	_ = doJSON(t, h, http.MethodPost, "/api/v1/dead-letters/"+strconv.FormatInt(dead.ID, 10)+"/retry", map[string]any{}, http.StatusOK)
	if !retried {
		t.Fatal("dead letter retry callback not called")
	}
}

func TestExtendedResourceAPIs(t *testing.T) {
	srv := NewServer(store.NewMonitorStore())
	h := srv.Handler()

	resources := []struct {
		name      string
		path      string
		hasToggle bool
		hasTest   bool
	}{
		{name: "alert-rules", path: "/api/v1/alert-rules", hasToggle: true},
		{name: "alert-integrations", path: "/api/v1/alert-integrations", hasTest: true},
		{name: "alert-groups", path: "/api/v1/alert-groups"},
		{name: "alert-inhibits", path: "/api/v1/alert-inhibits"},
		{name: "alert-silences", path: "/api/v1/alert-silences"},
		{name: "alert-notices", path: "/api/v1/alert-notices", hasTest: true},
		{name: "labels", path: "/api/v1/labels"},
		{name: "status-pages", path: "/api/v1/status-pages"},
	}

	for _, tc := range resources {
		t.Run(tc.name, func(t *testing.T) {
			created := doJSON(t, h, http.MethodPost, tc.path, map[string]any{
				"name": tc.name + "-demo",
				"type": tc.name,
			}, http.StatusCreated)
			id := int(created["id"].(float64))

			list := doJSON(t, h, http.MethodGet, tc.path+"?page=1&page_size=20", nil, http.StatusOK)
			if int(list["total"].(float64)) <= 0 {
				t.Fatalf("%s should have at least one item", tc.name)
			}

			updated := doJSON(t, h, http.MethodPut, tc.path+"/"+strconv.Itoa(id), map[string]any{
				"name": tc.name + "-updated",
			}, http.StatusOK)
			if updated["name"].(string) != tc.name+"-updated" {
				t.Fatalf("%s update failed: %v", tc.name, updated)
			}

			if tc.hasToggle {
				enabled := doJSON(t, h, http.MethodPatch, tc.path+"/"+strconv.Itoa(id)+"/disable", map[string]any{}, http.StatusOK)
				if enabled["enabled"] != false {
					t.Fatalf("%s disable failed: %v", tc.name, enabled)
				}
				enabled = doJSON(t, h, http.MethodPatch, tc.path+"/"+strconv.Itoa(id)+"/enable", map[string]any{}, http.StatusOK)
				if enabled["enabled"] != true {
					t.Fatalf("%s enable failed: %v", tc.name, enabled)
				}
			}

			if tc.hasTest {
				testResp := doJSON(t, h, http.MethodPost, tc.path+"/"+strconv.Itoa(id)+"/test", map[string]any{}, http.StatusOK)
				if testResp["status"].(string) != "ok" {
					t.Fatalf("%s test endpoint failed: %v", tc.name, testResp)
				}
			}

			req := httptest.NewRequest(http.MethodDelete, tc.path+"/"+strconv.Itoa(id), nil)
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)
			if rec.Code != http.StatusNoContent {
				t.Fatalf("%s delete failed status=%d body=%s", tc.name, rec.Code, rec.Body.String())
			}
		})
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

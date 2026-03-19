package httpcollector

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"collector-go/internal/model"
)

func TestCollectMissingURL(t *testing.T) {
	c := &Collector{}
	_, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "m1",
		Protocol: "http",
		Params:   map[string]string{},
	})
	if err == nil {
		t.Fatal("expected missing url error")
	}
}

func TestCollectDefaultJSON(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"UP","version":"1.0.0"}`))
	}))
	defer srv.Close()
	c := &Collector{}
	fields, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "health",
		Protocol: "http",
		Params: map[string]string{
			"url":       srv.URL,
			"parseType": "default",
		},
		FieldSpecs: []model.FieldSpec{{Field: "status"}, {Field: "version"}},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if fields["status"] != "UP" {
		t.Fatalf("status want=UP got=%s", fields["status"])
	}
	if fields["version"] != "1.0.0" {
		t.Fatalf("version want=1.0.0 got=%s", fields["version"])
	}
}

func TestCollectJSONPathArray(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[{"name":"rabbit@a","running":"true"},{"name":"rabbit@b","running":"false"}]`))
	}))
	defer srv.Close()
	c := &Collector{}
	fields, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "nodes",
		Protocol: "http",
		Params: map[string]string{
			"url":         srv.URL,
			"parseType":   "jsonPath",
			"parseScript": "$",
		},
		FieldSpecs: []model.FieldSpec{{Field: "name"}, {Field: "running"}},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if fields["name"] != "rabbit@a" || fields["row2_name"] != "rabbit@b" {
		t.Fatalf("unexpected names: %+v", fields)
	}
}

func TestCollectPrometheus(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		_, _ = w.Write([]byte(strings.Join([]string{
			`# HELP process_open_fds open fds`,
			`process_open_fds 12`,
			"",
		}, "\n")))
	}))
	defer srv.Close()
	c := &Collector{}
	fields, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "process_open_fds",
		Protocol: "http",
		Params: map[string]string{
			"url":       srv.URL,
			"parseType": "prometheus",
		},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if fields["value"] != "12" {
		t.Fatalf("value want=12 got=%s", fields["value"])
	}
}

func TestCollectDigestAuth(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.Header.Get("Authorization"), "Digest ") {
			w.Header().Set("WWW-Authenticate", `Digest realm="cam", nonce="abc123", qop="auth"`)
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		_, _ = w.Write([]byte(`{"ok":"true"}`))
	}))
	defer srv.Close()

	c := &Collector{}
	fields, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "hikvision",
		Protocol: "http",
		Params: map[string]string{
			"url":                              srv.URL,
			"method":                           "GET",
			"parseType":                        "default",
			"authorization.digestAuthUsername": "admin",
			"authorization.digestAuthPassword": "secret",
		},
		FieldSpecs: []model.FieldSpec{{Field: "ok"}},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if fields["ok"] != "true" {
		t.Fatalf("ok want=true got=%s", fields["ok"])
	}
}

func TestCollectXMLPathAndConfig(t *testing.T) {
	xmlSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`<DeviceStatus><CPUList><CPU><cpuUtilization>68</cpuUtilization></CPU></CPUList></DeviceStatus>`))
	}))
	defer xmlSrv.Close()

	c := &Collector{}
	xmlFields, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "status",
		Protocol: "http",
		Params: map[string]string{
			"url":         xmlSrv.URL,
			"parseType":   "xmlPath",
			"parseScript": "//DeviceStatus",
		},
		CalculateSpecs: []model.CalculateSpec{
			{Field: "CPU_utilization", Expression: "CPUList/CPU/cpuUtilization"},
		},
		FieldSpecs: []model.FieldSpec{{Field: "CPU_utilization"}},
	})
	if err != nil {
		t.Fatalf("xml collect failed: %v", err)
	}
	if xmlFields["CPU_utilization"] != "68" {
		t.Fatalf("CPU_utilization want=68 got=%s", xmlFields["CPU_utilization"])
	}

	cfgSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("users[0].ClientAddress=10.0.0.10\nusers[0].Name=admin\nusers[1].Name=viewer\n"))
	}))
	defer cfgSrv.Close()
	cfgFields, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "users",
		Protocol: "http",
		Params: map[string]string{
			"url":         cfgSrv.URL,
			"parseType":   "config",
			"parseScript": "users",
		},
		FieldSpecs: []model.FieldSpec{{Field: "ClientAddress"}, {Field: "Name"}},
	})
	if err != nil {
		t.Fatalf("config collect failed: %v", err)
	}
	if cfgFields["ClientAddress"] != "10.0.0.10" || cfgFields["row2_Name"] != "viewer" {
		t.Fatalf("unexpected config fields: %+v", cfgFields)
	}
}

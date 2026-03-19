package jdbccollector

import (
	"strings"
	"testing"
)

func TestBuildClickHouseDSN(t *testing.T) {
	dsn, err := buildClickHouseDSN(map[string]string{
		"host":     "10.0.0.8",
		"port":     "8123",
		"database": "default",
		"username": "default",
		"password": "secret",
		"timeout":  "5000",
	})
	if err != nil {
		t.Fatalf("build clickhouse dsn failed: %v", err)
	}
	if !strings.HasPrefix(dsn, "clickhouse://10.0.0.8:8123/default?") {
		t.Fatalf("unexpected dsn: %s", dsn)
	}
	if !strings.Contains(dsn, "username=default") {
		t.Fatalf("dsn missing username: %s", dsn)
	}
}

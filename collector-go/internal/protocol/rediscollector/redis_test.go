package rediscollector

import "testing"

func TestParseInfoBasic(t *testing.T) {
	raw := "# Server\r\nredis_version:7.2.4\r\nuptime_in_seconds:100\r\n"
	out := parseInfo(raw)
	if out["redis_version"] != "7.2.4" {
		t.Fatalf("redis_version want=7.2.4 got=%s", out["redis_version"])
	}
	if out["uptime_in_seconds"] != "100" {
		t.Fatalf("uptime_in_seconds want=100 got=%s", out["uptime_in_seconds"])
	}
}

func TestParseInfoCommandStatsExpanded(t *testing.T) {
	raw := "cmdstat_get:calls=20,usec=200,usec_per_call=10.00\r\n"
	out := parseInfo(raw)
	if out["cmdstat_get_calls"] != "20" {
		t.Fatalf("cmdstat_get_calls want=20 got=%s", out["cmdstat_get_calls"])
	}
	if out["cmdstat_get_usec"] != "200" {
		t.Fatalf("cmdstat_get_usec want=200 got=%s", out["cmdstat_get_usec"])
	}
	if out["cmdstat_get_usec_per_call"] != "10.00" {
		t.Fatalf("cmdstat_get_usec_per_call want=10.00 got=%s", out["cmdstat_get_usec_per_call"])
	}
}

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
	if out["cmdstat_get"] != "calls=20,usec=200,usec_per_call=10.00" {
		t.Fatalf("cmdstat_get raw value mismatch: %s", out["cmdstat_get"])
	}
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

func TestParseInfoKeyspaceExpandedAndRaw(t *testing.T) {
	raw := "db0:keys=2,expires=1,avg_ttl=0\r\n"
	out := parseInfo(raw)
	if out["db0"] != "keys=2,expires=1,avg_ttl=0" {
		t.Fatalf("db0 raw value mismatch: %s", out["db0"])
	}
	if out["db0_keys"] != "2" || out["db0_expires"] != "1" || out["db0_avg_ttl"] != "0" {
		t.Fatalf("db0 expanded mismatch: keys=%s expires=%s avg_ttl=%s", out["db0_keys"], out["db0_expires"], out["db0_avg_ttl"])
	}
}

func TestParseInfoErrorStatsSinglePairExpanded(t *testing.T) {
	raw := "errorstat_ERR:count=3\r\n"
	out := parseInfo(raw)
	if out["errorstat_ERR"] != "count=3" {
		t.Fatalf("errorstat_ERR raw value mismatch: %s", out["errorstat_ERR"])
	}
	if out["errorstat_ERR_count"] != "3" {
		t.Fatalf("errorstat_ERR_count want=3 got=%s", out["errorstat_ERR_count"])
	}
}

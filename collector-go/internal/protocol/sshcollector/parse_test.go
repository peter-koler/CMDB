package sshcollector

import (
	"testing"

	"collector-go/internal/model"
)

func TestParseOneRow(t *testing.T) {
	raw := "hostname kernel_release uptime_s cpu_cores\nnode-a 6.8.0 7200 8\n"
	got := parseOutput(raw, "oneRow", nil)
	if got["hostname"] != "node-a" || got["kernel_release"] != "6.8.0" {
		t.Fatalf("unexpected parse result: %+v", got)
	}
}

func TestParseOneRowWithSpecsFallback(t *testing.T) {
	raw := "node-b 6.8.1 3600 16\n"
	got := parseOutput(raw, "oneRow", []model.FieldSpec{
		{Field: "hostname"},
		{Field: "kernel_release"},
		{Field: "uptime_s"},
		{Field: "cpu_cores"},
	})
	if got["hostname"] != "node-b" || got["cpu_cores"] != "16" {
		t.Fatalf("unexpected parse result: %+v", got)
	}
}

func TestParseMultiRow(t *testing.T) {
	raw := "fs used avail\n/ 1024 2048\n/data 2048 4096\n"
	got := parseOutput(raw, "multiRow", nil)
	if got["fs"] != "/" || got["row2_fs"] != "/data" {
		t.Fatalf("unexpected parse result: %+v", got)
	}
	if got["row2_avail"] != "4096" {
		t.Fatalf("unexpected row2 value: %+v", got)
	}
}

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

func TestParseOneRowWithBannerNoise(t *testing.T) {
	raw := "Authorized users only\nLast login: Tue Mar 24\nhostname kernel_release uptime_s cpu_cores\nnode-c 6.8.2 1800 4\n"
	got := parseOutput(raw, "oneRow", []model.FieldSpec{
		{Field: "hostname"},
		{Field: "kernel_release"},
		{Field: "uptime_s"},
		{Field: "cpu_cores"},
	})
	if got["hostname"] != "node-c" || got["cpu_cores"] != "4" {
		t.Fatalf("unexpected parse result with noise: %+v", got)
	}
}

func TestParseOneRowWithInterleavedNoiseLine(t *testing.T) {
	raw := "hostname cpu_usage mem_usage command\nbash: warning: setlocale: LC_ALL: cannot change locale\n123 0.4 0.5 /usr/bin/gnome-shell\n"
	got := parseOutput(raw, "oneRow", []model.FieldSpec{
		{Field: "hostname", Type: "string"},
		{Field: "cpu_usage", Type: "number"},
		{Field: "mem_usage", Type: "number"},
		{Field: "command", Type: "string"},
	})
	if got["hostname"] != "123" || got["cpu_usage"] != "0.4" || got["mem_usage"] != "0.5" {
		t.Fatalf("unexpected parse result with interleaved noise: %+v", got)
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

func TestParseMultiRowWithBannerNoise(t *testing.T) {
	raw := "Welcome to host\nfs used avail\n/ 1024 2048\n/data 2048 4096\n"
	got := parseOutput(raw, "multiRow", []model.FieldSpec{
		{Field: "fs"},
		{Field: "used"},
		{Field: "avail"},
	})
	if got["fs"] != "/" || got["row2_fs"] != "/data" {
		t.Fatalf("unexpected parse result with noise: %+v", got)
	}
	if got["row2_avail"] != "4096" {
		t.Fatalf("unexpected row2 value with noise: %+v", got)
	}
}

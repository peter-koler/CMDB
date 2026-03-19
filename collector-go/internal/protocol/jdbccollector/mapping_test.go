package jdbccollector

import "testing"

func TestParseAliasFields(t *testing.T) {
	got := parseAliasFields(" Qcache_hits, Qcache_inserts ,Qcache_hits,, ")
	if len(got) != 2 {
		t.Fatalf("unexpected alias fields: %+v", got)
	}
	if got[0] != "Qcache_hits" || got[1] != "Qcache_inserts" {
		t.Fatalf("unexpected alias order: %+v", got)
	}
}

func TestProjectRow_CaseInsensitive(t *testing.T) {
	row := map[string]string{
		"Variable_name": "Qcache_hits",
		"Value":         "100",
		"Qcache_hits":   "100",
	}
	cols := []string{"Variable_name", "Value"}
	got := projectRow(row, cols, []string{"qcache_hits"})
	if got["qcache_hits"] != "100" {
		t.Fatalf("expected case-insensitive projection, got: %+v", got)
	}
}

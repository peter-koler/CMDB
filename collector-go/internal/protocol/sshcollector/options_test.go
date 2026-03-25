package sshcollector

import (
	"testing"
	"time"

	"collector-go/internal/model"
)

func TestParseOptionsBasic(t *testing.T) {
	opts, err := parseOptions(model.MetricsTask{
		Timeout: 5 * time.Second,
		Params: map[string]string{
			"host":      "10.0.0.1",
			"port":      "22",
			"username":  "root",
			"password":  "pwd",
			"script":    "echo ok",
			"parseType": "oneRow",
		},
	})
	if err != nil {
		t.Fatalf("parseOptions failed: %v", err)
	}
	if opts.Host != "10.0.0.1" || opts.Username != "root" || opts.ParseType != "onerow" {
		t.Fatalf("unexpected options: %+v", opts)
	}
}

func TestParseOptionsMissingScript(t *testing.T) {
	_, err := parseOptions(model.MetricsTask{
		Params: map[string]string{
			"host":     "10.0.0.1",
			"username": "root",
		},
	})
	if err == nil {
		t.Fatalf("expected error when script and bundleScript are both missing")
	}
}

func TestParseOptionsBundleWithoutScript(t *testing.T) {
	opts, err := parseOptions(model.MetricsTask{
		Params: map[string]string{
			"host":          "10.0.0.1",
			"username":      "root",
			"bundleScript":  "echo __ARCO_SECTION_BEGIN__cpu; echo ok; echo __ARCO_SECTION_END__cpu",
			"bundleSection": "cpu",
		},
	})
	if err != nil {
		t.Fatalf("expected bundle-only options to pass, got: %v", err)
	}
	if opts.BundleSection != "cpu" || opts.Script != "" {
		t.Fatalf("unexpected bundle-only options: %+v", opts)
	}
}

func TestNormalizeBoolDefaults(t *testing.T) {
	if parseBool("", true) != true {
		t.Fatalf("expected default true")
	}
	if parseBool("off", true) != false {
		t.Fatalf("expected false")
	}
}

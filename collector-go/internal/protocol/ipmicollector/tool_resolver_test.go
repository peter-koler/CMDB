package ipmicollector

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestResolveIPMIToolPathFromEnv(t *testing.T) {
	dir := t.TempDir()
	name := "ipmitool"
	if runtime.GOOS == "windows" {
		name = "ipmitool.exe"
	}
	bin := filepath.Join(dir, name)
	if err := os.WriteFile(bin, []byte("stub"), 0o755); err != nil {
		t.Fatalf("write file: %v", err)
	}
	t.Setenv(envIPMIToolBin, bin)
	path, err := resolveIPMIToolPath()
	if err != nil {
		t.Fatalf("resolve failed: %v", err)
	}
	if path != bin {
		t.Fatalf("want %s got %s", bin, path)
	}
}

func TestResolveIPMIToolPathMissing(t *testing.T) {
	t.Setenv(envIPMIToolBin, "")
	t.Setenv(envAllowSystemIPMITool, "false")
	_, err := resolveIPMIToolPath()
	if err == nil {
		t.Fatal("expected missing error")
	}
}

package ipmicollector

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

const envIPMIToolBin = "COLLECTOR_IPMITOOL_BIN"
const envAllowSystemIPMITool = "COLLECTOR_ALLOW_SYSTEM_IPMITOOL"

func resolveIPMIToolPath() (string, error) {
	if custom := strings.TrimSpace(os.Getenv(envIPMIToolBin)); custom != "" {
		if isExecutableFile(custom) {
			return custom, nil
		}
		return "", fmt.Errorf("%s is set but file is not executable: %s", envIPMIToolBin, custom)
	}

	candidates := bundledCandidates()
	for _, candidate := range candidates {
		if isExecutableFile(candidate) {
			return candidate, nil
		}
	}

	if isTruthy(os.Getenv(envAllowSystemIPMITool)) {
		if path, err := exec.LookPath("ipmitool"); err == nil {
			return path, nil
		}
	}
	return "", fmt.Errorf("ipmitool binary not found in collector bundle; set %s or place binary under tools/ipmitool/bin", envIPMIToolBin)
}

func bundledCandidates() []string {
	exe, _ := os.Executable()
	exeDir := filepath.Dir(exe)
	name := "ipmitool"
	if runtime.GOOS == "windows" {
		name = "ipmitool.exe"
	}
	tagged := fmt.Sprintf("ipmitool-%s-%s", runtime.GOOS, runtime.GOARCH)
	if runtime.GOOS == "windows" {
		tagged += ".exe"
	}
	return []string{
		filepath.Join(exeDir, "tools", "ipmitool", "bin", tagged),
		filepath.Join(exeDir, "tools", "ipmitool", "bin", name),
		filepath.Join(exeDir, "..", "tools", "ipmitool", "bin", tagged),
		filepath.Join(exeDir, "..", "tools", "ipmitool", "bin", name),
		filepath.Join("tools", "ipmitool", "bin", tagged),
		filepath.Join("tools", "ipmitool", "bin", name),
	}
}

func isExecutableFile(path string) bool {
	info, err := os.Stat(path)
	if err != nil || info.IsDir() {
		return false
	}
	if runtime.GOOS == "windows" {
		return strings.HasSuffix(strings.ToLower(path), ".exe")
	}
	return info.Mode()&0o111 != 0
}

func isTruthy(raw string) bool {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}

package ipmicollector

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

func collectByTool(ctx context.Context, host, port, user, pass, typ string, timeout time.Duration) (map[string]string, error) {
	baseArgs := []string{"-I", "lanplus", "-H", host, "-p", port, "-U", user, "-P", pass}
	ipmiBin, err := resolveIPMIToolPathCached()
	if err != nil {
		return nil, err
	}

	var args []string
	switch strings.ToLower(strings.TrimSpace(typ)) {
	case "sensor":
		args = append(baseArgs, "sdr", "elist")
	default:
		args = append(baseArgs, "chassis", "status")
	}

	out, err := runCommand(ctx, timeout, ipmiBin, args...)
	if err != nil {
		return nil, err
	}

	switch strings.ToLower(strings.TrimSpace(typ)) {
	case "sensor":
		return parseSensorOutput(out), nil
	default:
		return parseChassisOutput(out), nil
	}
}

func runCommand(ctx context.Context, timeout time.Duration, name string, args ...string) (string, error) {
	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx2, name, args...)
	raw, err := cmd.CombinedOutput()
	out := strings.TrimSpace(string(raw))
	if err != nil {
		if out == "" {
			return "", err
		}
		return "", fmt.Errorf("%w: %s", err, out)
	}
	return out, nil
}

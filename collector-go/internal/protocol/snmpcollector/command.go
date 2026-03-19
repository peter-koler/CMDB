package snmpcollector

import (
	"context"
	"os/exec"
	"strconv"
	"strings"
)

var runSNMPCmd = func(ctx context.Context, bin string, args ...string) (string, error) {
	out, err := exec.CommandContext(ctx, bin, args...).CombinedOutput()
	return strings.TrimSpace(string(out)), err
}

func buildArgs(opts options, oid string) []string {
	return []string{
		"-v" + opts.Version,
		"-c", opts.Community,
		"-t", strconv.Itoa(opts.TimeoutS),
		"-r", "0",
		opts.Address,
		oid,
	}
}

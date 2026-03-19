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
	args := []string{
		"-v" + opts.Version,
		"-t", strconv.Itoa(opts.TimeoutS),
		"-r", "0",
	}
	if opts.Version == "3" {
		if strings.TrimSpace(opts.SecurityLevel) != "" {
			args = append(args, "-l", opts.SecurityLevel)
		}
		if strings.TrimSpace(opts.Username) != "" {
			args = append(args, "-u", opts.Username)
		}
		if strings.TrimSpace(opts.AuthPassphrase) != "" {
			args = append(args, "-a", opts.AuthPasswordEncryption, "-A", opts.AuthPassphrase)
		}
		if strings.TrimSpace(opts.PrivPassphrase) != "" {
			args = append(args, "-x", opts.PrivPasswordEncryption, "-X", opts.PrivPassphrase)
		}
		if strings.TrimSpace(opts.ContextName) != "" {
			args = append(args, "-n", opts.ContextName)
		}
	} else {
		args = append(args, "-c", opts.Community)
	}
	args = append(args, opts.Address, oid)
	return args
}

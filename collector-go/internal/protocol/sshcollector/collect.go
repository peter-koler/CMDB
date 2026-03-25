package sshcollector

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"log"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
	"golang.org/x/crypto/ssh"
)

type Collector struct{}

var executeScript = func(ctx context.Context, client *ssh.Client, script string, timeout time.Duration) (string, error) {
	if strings.TrimSpace(script) == "" {
		return "", fmt.Errorf("ssh script is empty")
	}

	// Strategy 1 (preferred): feed script via stdin to "sh -s" (same as manual ssh test).
	out, err := executeByStdin(ctx, client, script, timeout)
	log.Printf("[DEBUG] [ssh-exec] strategy=stdin_sh_s out_len=%d err=%v", len(out), err)
	if strings.TrimSpace(out) != "" {
		return out, err
	}

	// Strategy 2: execute through remote shell with heredoc on sh.
	wrapped := wrapScriptAsHeredoc(script)
	out2, err2 := executeByCommand(ctx, client, "sh -lc "+quoteForSingleShellArg(wrapped), timeout)
	log.Printf("[DEBUG] [ssh-exec] strategy=sh_lc_heredoc out_len=%d err=%v", len(out2), err2)
	if strings.TrimSpace(out2) != "" {
		return out2, err2
	}

	// Strategy 3: execute through bash if available.
	out3, err3 := executeByCommand(ctx, client, "bash -lc "+quoteForSingleShellArg(wrapped), timeout)
	log.Printf("[DEBUG] [ssh-exec] strategy=bash_lc_heredoc out_len=%d err=%v", len(out3), err3)
	if strings.TrimSpace(out3) != "" {
		return out3, err3
	}

	// All strategies returned empty output.
	if err != nil {
		return out, err
	}
	if err2 != nil {
		return out2, err2
	}
	if err3 != nil {
		return out3, err3
	}
	return "", nil
}

func wrapScriptAsHeredoc(script string) string {
	marker := "__ARCO_SSH_BUNDLE_EOF__"
	for strings.Contains(script, marker) {
		marker += "_X"
	}
	var sb strings.Builder
	sb.WriteString("sh -s <<'")
	sb.WriteString(marker)
	sb.WriteString("'\n")
	sb.WriteString(script)
	if !strings.HasSuffix(script, "\n") {
		sb.WriteString("\n")
	}
	sb.WriteString(marker)
	sb.WriteString("\n")
	return sb.String()
}

func quoteForSingleShellArg(raw string) string {
	escaped := strings.ReplaceAll(raw, `'`, `'"'"'`)
	return "'" + escaped + "'"
}

func executeByStdin(ctx context.Context, client *ssh.Client, script string, timeout time.Duration) (string, error) {
	session, err := client.NewSession()
	if err != nil {
		return "", err
	}
	defer session.Close()

	var output bytes.Buffer
	session.Stdout = &output
	session.Stderr = &output

	stdin, err := session.StdinPipe()
	if err != nil {
		return "", err
	}
	done := make(chan error, 1)
	go func() {
		if startErr := session.Start("sh -s"); startErr != nil {
			done <- startErr
			return
		}
		_, writeErr := io.WriteString(stdin, script)
		if writeErr == nil && !strings.HasSuffix(script, "\n") {
			_, writeErr = io.WriteString(stdin, "\n")
		}
		closeErr := stdin.Close()
		waitErr := session.Wait()
		if writeErr != nil {
			done <- writeErr
			return
		}
		if closeErr != nil {
			done <- closeErr
			return
		}
		done <- waitErr
	}()
	select {
	case runErr := <-done:
		return output.String(), runErr
	case <-ctx.Done():
		_ = session.Close()
		return output.String(), ctx.Err()
	case <-time.After(timeout):
		_ = session.Close()
		return output.String(), fmt.Errorf("ssh script timeout")
	}
}

func executeByCommand(ctx context.Context, client *ssh.Client, command string, timeout time.Duration) (string, error) {
	session, err := client.NewSession()
	if err != nil {
		return "", err
	}
	defer session.Close()
	var output bytes.Buffer
	session.Stdout = &output
	session.Stderr = &output
	done := make(chan error, 1)
	go func() {
		done <- session.Run(command)
	}()
	select {
	case runErr := <-done:
		return output.String(), runErr
	case <-ctx.Done():
		_ = session.Close()
		return output.String(), ctx.Err()
	case <-time.After(timeout):
		_ = session.Close()
		return output.String(), fmt.Errorf("ssh script timeout")
	}
}

func init() {
	protocol.Register("ssh", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	opts, err := parseOptions(task)
	if err != nil {
		return nil, "", err
	}
	client, err := getClient(ctx, opts)
	if err != nil {
		return nil, "", err
	}
	if !opts.ReuseConnection {
		defer client.Close()
	}
	out, err := executeScript(ctx, client, opts.Script, opts.Timeout)
	fields := parseOutput(out, opts.ParseType, task.FieldSpecs)
	if err != nil {
		if len(fields) == 0 {
			fields = map[string]string{}
		}
		fields["output"] = out
		return fields, "ssh script failed", err
	}
	return fields, "ok", nil
}

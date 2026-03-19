package sshcollector

import (
	"bytes"
	"context"
	"fmt"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
	"golang.org/x/crypto/ssh"
)

type Collector struct{}

var executeScript = func(ctx context.Context, client *ssh.Client, script string, timeout time.Duration) (string, error) {
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
		done <- session.Run(script)
	}()
	select {
	case runErr := <-done:
		return output.String(), runErr
	case <-ctx.Done():
		return output.String(), ctx.Err()
	case <-time.After(timeout):
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

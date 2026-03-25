package sshcollector

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"golang.org/x/crypto/ssh"
)

type BundleTaskResult struct {
	Task      model.MetricsTask
	Fields    map[string]string
	Message   string
	Err       error
	RawOutput string
}

type BundleOutcome struct {
	Script     string
	RawOutput  string
	RawLatency time.Duration
	Results    []BundleTaskResult
}

func CollectBundle(ctx context.Context, tasks []model.MetricsTask) (BundleOutcome, error) {
	if len(tasks) == 0 {
		return BundleOutcome{}, fmt.Errorf("ssh bundle requires at least one task")
	}
	opts := make([]options, 0, len(tasks))
	for idx, task := range tasks {
		if strings.TrimSpace(strings.ToLower(task.Protocol)) != "ssh" {
			return BundleOutcome{}, fmt.Errorf("metrics %q is not ssh protocol", task.Name)
		}
		opt, err := parseOptions(task)
		if err != nil {
			return BundleOutcome{}, fmt.Errorf("metrics %q parse options failed: %w", task.Name, err)
		}
		if idx > 0 && !sameBundleConnection(opts[0], opt) {
			return BundleOutcome{}, fmt.Errorf("metrics %q ssh connection params mismatch in bundle", task.Name)
		}
		opts = append(opts, opt)
	}
	client, err := getClient(ctx, opts[0])
	if err != nil {
		return BundleOutcome{}, err
	}
	if !opts[0].ReuseConnection {
		defer client.Close()
	}

	snapshotScript, snapshotModeErr := sharedBundleScript(opts)
	if snapshotModeErr != nil {
		return BundleOutcome{}, snapshotModeErr
	}
	if strings.TrimSpace(snapshotScript) != "" {
		return collectBySnapshotScript(ctx, client, snapshotScript, opts, tasks)
	}
	return collectByPerTaskScripts(ctx, client, opts, tasks)
}

func sameBundleConnection(a, b options) bool {
	return a.Host == b.Host &&
		a.Port == b.Port &&
		a.Username == b.Username &&
		a.Password == b.Password &&
		a.PrivateKey == b.PrivateKey &&
		a.PrivateKeyPath == b.PrivateKeyPath &&
		a.PrivateKeyPassphrase == b.PrivateKeyPassphrase &&
		a.KnownHostsPath == b.KnownHostsPath &&
		a.StrictHostKeyChecking == b.StrictHostKeyChecking &&
		a.HostKeyFingerprint == b.HostKeyFingerprint &&
		a.UseProxy == b.UseProxy &&
		a.ProxyHost == b.ProxyHost &&
		a.ProxyPort == b.ProxyPort &&
		a.ProxyUsername == b.ProxyUsername &&
		a.ProxyPassword == b.ProxyPassword &&
		a.ProxyPrivateKey == b.ProxyPrivateKey &&
		a.ProxyPrivateKeyPath == b.ProxyPrivateKeyPath &&
		a.ProxyPrivateKeyPassphrase == b.ProxyPrivateKeyPassphrase
}

func bundleTimeout(opts []options) time.Duration {
	total := 0 * time.Second
	for _, opt := range opts {
		t := opt.Timeout
		if t <= 0 {
			t = 6 * time.Second
		}
		total += t
	}
	if total <= 0 {
		total = 30 * time.Second
	}
	total += 5 * time.Second
	if total > 10*time.Minute {
		return 10 * time.Minute
	}
	return total
}

func collectBySnapshotScript(ctx context.Context, client *ssh.Client, script string, opts []options, tasks []model.MetricsTask) (BundleOutcome, error) {
	timeout := bundleTimeout(opts)
	start := time.Now()
	raw, runErr := executeScript(ctx, client, script, timeout)
	latency := time.Since(start)
	if runErr == nil && strings.TrimSpace(raw) == "" {
		runErr = fmt.Errorf("ssh bundle produced empty output")
	}

	results := make([]BundleTaskResult, 0, len(tasks))
	for idx := range tasks {
		section := strings.TrimSpace(opts[idx].BundleSection)
		if section == "" {
			section = strings.TrimSpace(tasks[idx].Name)
		}
		sectionOut, sectionErr := extractSnapshotSection(raw, section)
		fields := parseOutput(sectionOut, opts[idx].ParseType, tasks[idx].FieldSpecs)
		msg := "ok"
		var err error
		recoveredByFallback := false
		if sectionErr != nil {
			// Fallback path: when bundled snapshot cannot be section-parsed,
			// try execute current section script independently.
			fallbackScript := strings.TrimSpace(opts[idx].Script)
			if fallbackScript == "" {
				if parsedSectionScript, parseErr := extractSnapshotSection(script, section); parseErr == nil {
					fallbackScript = strings.TrimSpace(parsedSectionScript)
				}
			}
			if fallbackScript != "" {
				fallbackOut, fallbackErr := executeScript(ctx, client, fallbackScript, opts[idx].Timeout)
				fallbackFields := parseOutput(fallbackOut, opts[idx].ParseType, tasks[idx].FieldSpecs)
				if fallbackErr == nil && len(fallbackFields) > 0 {
					fields = fallbackFields
					sectionOut = fallbackOut
					sectionErr = nil
					recoveredByFallback = true
				}
			}
		}
		if sectionErr != nil {
			err = sectionErr
			if len(fields) == 0 {
				fields = map[string]string{}
			}
			fields["output"] = sectionOut
			msg = "ssh script failed"
		}
		if runErr != nil && !recoveredByFallback {
			if err != nil {
				err = fmt.Errorf("%w; %v", runErr, err)
			} else {
				err = runErr
			}
			msg = "ssh bundle failed"
			if len(fields) == 0 {
				fields = map[string]string{}
			}
			if _, exists := fields["output"]; !exists {
				fields["output"] = sectionOut
			}
		}
		results = append(results, BundleTaskResult{
			Task:      tasks[idx],
			Fields:    fields,
			Message:   msg,
			Err:       err,
			RawOutput: sectionOut,
		})
	}

	return BundleOutcome{
		Script:     script,
		RawOutput:  raw,
		RawLatency: latency,
		Results:    results,
	}, nil
}

func collectByPerTaskScripts(ctx context.Context, client *ssh.Client, opts []options, tasks []model.MetricsTask) (BundleOutcome, error) {
	bundleID := strconv.FormatInt(time.Now().UnixNano(), 10)
	script := buildBundleScript(bundleID, opts, tasks)
	timeout := bundleTimeout(opts)

	start := time.Now()
	raw, runErr := executeScript(ctx, client, script, timeout)
	latency := time.Since(start)

	chunks := splitBundleOutput(bundleID, raw, len(tasks))
	results := make([]BundleTaskResult, 0, len(tasks))
	for idx := range tasks {
		chunk := chunks[idx]
		fields := parseOutput(chunk.output, opts[idx].ParseType, tasks[idx].FieldSpecs)
		if chunk.err != nil {
			if len(fields) == 0 {
				fields = map[string]string{}
			}
			fields["output"] = chunk.output
			results = append(results, BundleTaskResult{
				Task:      tasks[idx],
				Fields:    fields,
				Message:   "ssh script failed",
				Err:       chunk.err,
				RawOutput: chunk.output,
			})
			continue
		}
		results = append(results, BundleTaskResult{
			Task:      tasks[idx],
			Fields:    fields,
			Message:   "ok",
			RawOutput: chunk.output,
		})
	}

	// Keep partial parse results even when transport-layer execution failed.
	if runErr != nil {
		if len(results) == 0 {
			for _, task := range tasks {
				results = append(results, BundleTaskResult{
					Task:    task,
					Fields:  map[string]string{"output": raw},
					Message: "ssh bundle failed",
					Err:     runErr,
				})
			}
		}
		for idx := range results {
			if results[idx].Err == nil {
				results[idx].Err = runErr
				if results[idx].Message == "" || results[idx].Message == "ok" {
					results[idx].Message = "ssh bundle failed"
				}
				if len(results[idx].Fields) == 0 {
					results[idx].Fields = map[string]string{}
				}
				if _, exists := results[idx].Fields["output"]; !exists {
					results[idx].Fields["output"] = results[idx].RawOutput
				}
			}
		}
	}

	return BundleOutcome{
		Script:     script,
		RawOutput:  raw,
		RawLatency: latency,
		Results:    results,
	}, nil
}

func sharedBundleScript(opts []options) (string, error) {
	shared := ""
	for _, opt := range opts {
		s := strings.TrimSpace(opt.BundleScript)
		if s == "" {
			continue
		}
		if shared == "" {
			shared = s
			continue
		}
		if shared != s {
			return "", fmt.Errorf("ssh bundleScript mismatch between metrics tasks")
		}
	}
	return shared, nil
}

func extractSnapshotSection(raw string, section string) (string, error) {
	if strings.TrimSpace(section) == "" {
		return "", fmt.Errorf("bundle section is empty")
	}
	begin := "__ARCO_SECTION_BEGIN__" + section
	end := "__ARCO_SECTION_END__" + section
	lines := strings.Split(strings.ReplaceAll(raw, "\r", ""), "\n")
	inSection := false
	var out []string
	seenBegin := false
	seenEnd := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == begin {
			inSection = true
			seenBegin = true
			continue
		}
		if trimmed == end {
			if inSection {
				seenEnd = true
				inSection = false
			}
			continue
		}
		if inSection {
			out = append(out, line)
		}
	}
	if !seenBegin || !seenEnd {
		return strings.TrimSpace(strings.Join(out, "\n")), fmt.Errorf("bundle section %q not found", section)
	}
	return strings.TrimSpace(strings.Join(out, "\n")), nil
}

func buildBundleScript(bundleID string, opts []options, tasks []model.MetricsTask) string {
	var sb strings.Builder
	sb.WriteString("set +e\n")
	for idx, opt := range opts {
		taskName := sanitizeMarkerToken(tasks[idx].Name)
		sb.WriteString("echo \"__ARCO_BUNDLE_BEGIN__")
		sb.WriteString(bundleID)
		sb.WriteString("__")
		sb.WriteString(strconv.Itoa(idx))
		sb.WriteString("__")
		sb.WriteString(taskName)
		sb.WriteString("\"\n")
		sb.WriteString("(\n")
		sb.WriteString(opt.Script)
		sb.WriteString("\n)\n")
		sb.WriteString("rc=$?\n")
		sb.WriteString("echo \"__ARCO_BUNDLE_END__")
		sb.WriteString(bundleID)
		sb.WriteString("__")
		sb.WriteString(strconv.Itoa(idx))
		sb.WriteString("__RC=$rc\"\n")
	}
	return sb.String()
}

func sanitizeMarkerToken(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "task"
	}
	raw = strings.ReplaceAll(raw, " ", "_")
	raw = strings.ReplaceAll(raw, "\"", "")
	return raw
}

type bundleChunk struct {
	output string
	err    error
}

func splitBundleOutput(bundleID string, raw string, taskCount int) []bundleChunk {
	out := make([]bundleChunk, taskCount)
	beginPrefix := "__ARCO_BUNDLE_BEGIN__" + bundleID + "__"
	endPrefix := "__ARCO_BUNDLE_END__" + bundleID + "__"
	current := -1
	buffers := make([][]string, taskCount)
	lines := strings.Split(strings.ReplaceAll(raw, "\r", ""), "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, beginPrefix) {
			idx := parseBundleIndex(trimmed[len(beginPrefix):])
			if idx >= 0 && idx < taskCount {
				current = idx
			} else {
				current = -1
			}
			continue
		}
		if strings.HasPrefix(trimmed, endPrefix) {
			payload := trimmed[len(endPrefix):]
			parts := strings.SplitN(payload, "__RC=", 2)
			idx := parseBundleIndex(payload)
			if idx >= 0 && idx < taskCount {
				rc := 0
				if len(parts) == 2 {
					if parsed, err := strconv.Atoi(strings.TrimSpace(parts[1])); err == nil {
						rc = parsed
					} else {
						out[idx].err = fmt.Errorf("ssh script exit code parse failed: %v", err)
					}
				}
				if rc != 0 && out[idx].err == nil {
					out[idx].err = fmt.Errorf("ssh script exited with code %d", rc)
				}
			}
			current = -1
			continue
		}
		if current >= 0 && current < taskCount {
			buffers[current] = append(buffers[current], line)
		}
	}
	for i := 0; i < taskCount; i++ {
		out[i].output = strings.TrimSpace(strings.Join(buffers[i], "\n"))
	}
	return out
}

func parseBundleIndex(raw string) int {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return -1
	}
	parts := strings.SplitN(raw, "__", 2)
	idx, err := strconv.Atoi(strings.TrimSpace(parts[0]))
	if err != nil {
		return -1
	}
	return idx
}

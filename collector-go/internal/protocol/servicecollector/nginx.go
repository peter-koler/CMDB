package servicecollector

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
)

type NginxCollector struct{}

func (c *NginxCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "nginx.host")
	if host == "" {
		return nil, "missing host", fmt.Errorf("missing host")
	}
	port := parsePort(params, "80", "port", "nginx.port")
	ssl := boolFrom(params, false, "ssl", "nginx.ssl")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "nginx.timeout")
	path := firstNonEmpty(params, "url", "nginx.url")
	if path == "" {
		path = "/nginx-status"
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	scheme := "http"
	if ssl {
		scheme = "https"
	}
	url := scheme + "://" + host + ":" + port + path

	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, "build request failed", err
	}
	start := time.Now()
	resp, err := client.Do(req)
	if err != nil {
		return nil, "request failed", err
	}
	defer resp.Body.Close()
	latency := time.Since(start)
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, "nginx status bad status", fmt.Errorf("status code %d", resp.StatusCode)
	}

	fields := map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds())}
	bodyText := strings.TrimSpace(string(body))
	if strings.Contains(path, "req-status") {
		parseReqStatus(bodyText, fields)
	} else {
		parseStubStatus(bodyText, fields)
	}
	return fields, "ok", nil
}

func parseStubStatus(body string, out map[string]string) {
	// Active connections: 291
	// server accepts handled requests
	// 16630948 16630948 31070465
	// Reading: 6 Writing: 179 Waiting: 106
	s := bufio.NewScanner(strings.NewReader(body))
	lines := []string{}
	for s.Scan() {
		line := strings.TrimSpace(s.Text())
		if line != "" {
			lines = append(lines, line)
		}
	}
	if len(lines) == 0 {
		return
	}
	if strings.HasPrefix(strings.ToLower(lines[0]), "active") {
		parts := strings.Fields(lines[0])
		if len(parts) > 0 {
			out["active"] = parts[len(parts)-1]
		}
	}
	for _, line := range lines {
		if strings.HasPrefix(line, "Reading:") {
			parts := strings.Fields(strings.ReplaceAll(strings.ReplaceAll(line, ":", " "), "  ", " "))
			for i := 0; i+1 < len(parts); i += 2 {
				out[strings.ToLower(parts[i])] = parts[i+1]
			}
		}
	}
	for i, line := range lines {
		if strings.Contains(line, "accepts") && strings.Contains(line, "handled") {
			if i+1 < len(lines) {
				parts := strings.Fields(lines[i+1])
				if len(parts) >= 3 {
					out["accepts"] = parts[0]
					out["handled"] = parts[1]
					out["requests"] = parts[2]
					if a, err1 := strconv.ParseInt(parts[0], 10, 64); err1 == nil {
						if h, err2 := strconv.ParseInt(parts[1], 10, 64); err2 == nil {
							out["dropped"] = fmt.Sprintf("%d", a-h)
						}
					}
				}
			}
			break
		}
	}
}

func parseReqStatus(body string, out map[string]string) {
	// Best effort parsing. We read first data line to provide fields required by template.
	lines := strings.Split(body, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(strings.ToLower(line), "zone") {
			continue
		}
		parts := strings.Fields(line)
		if len(parts) == 0 {
			continue
		}
		out["zone_name"] = parts[0]
		if len(parts) > 1 {
			out["key"] = parts[1]
		}
		if len(parts) > 2 {
			out["max_active"] = parts[2]
		}
		if len(parts) > 3 {
			out["max_bw"] = parts[3]
		}
		if len(parts) > 4 {
			out["traffic"] = parts[4]
		}
		if len(parts) > 5 {
			out["requests"] = parts[5]
		}
		if len(parts) > 6 {
			out["active"] = parts[6]
		}
		if len(parts) > 7 {
			out["bandwidth"] = parts[7]
		}
		break
	}
}

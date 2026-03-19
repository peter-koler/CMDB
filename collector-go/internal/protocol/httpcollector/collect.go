package httpcollector

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"collector-go/internal/model"
)

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	reqSpec, err := buildRequestSpec(task)
	if err != nil {
		return nil, "", err
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequestWithContext(ctx, reqSpec.Method, reqSpec.URL, strings.NewReader(reqSpec.Body))
	if err != nil {
		return nil, "", err
	}
	for key, value := range reqSpec.Headers {
		req.Header.Set(key, value)
	}
	if reqSpec.BasicAuthUser != "" {
		req.SetBasicAuth(reqSpec.BasicAuthUser, reqSpec.BasicAuthPass)
	}
	start := time.Now()
	resp, err := executeRequest(client, req, reqSpec)
	if err != nil {
		return nil, "", err
	}
	defer resp.Body.Close()
	latency := time.Since(start)
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, "", err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		return nil, "", fmt.Errorf("unexpected status code %d", resp.StatusCode)
	}
	parser := newParser(task, latency, body)
	parser.statusCode = resp.StatusCode
	parser.headers = resp.Header
	fields, err := parser.parse()
	if err != nil {
		return nil, "", err
	}
	if fields == nil {
		fields = map[string]string{}
	}
	fields["status_code"] = fmt.Sprintf("%d", resp.StatusCode)
	fields["responseTime"] = fmt.Sprintf("%d", latency.Milliseconds())
	fields["latency_ms"] = fmt.Sprintf("%d", latency.Milliseconds())
	return fields, "ok", nil
}

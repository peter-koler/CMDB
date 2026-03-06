package httpcollector

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("http", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	url := task.Params["url"]
	if url == "" {
		return nil, "", fmt.Errorf("missing url")
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, "", err
	}
	start := time.Now()
	resp, err := client.Do(req)
	if err != nil {
		return nil, "", err
	}
	defer resp.Body.Close()
	latency := time.Since(start)
	fields := map[string]string{
		"status_code": fmt.Sprintf("%d", resp.StatusCode),
		"latency_ms":  fmt.Sprintf("%d", latency.Milliseconds()),
	}
	return fields, "ok", nil
}

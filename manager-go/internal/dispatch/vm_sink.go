package dispatch

import (
	"bytes"
	"context"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"time"

	"manager-go/internal/model"
)

type VMSink struct {
	URL    string
	Client *http.Client
}

func NewVMSink(url string, timeout time.Duration) *VMSink {
	if url == "" {
		url = "http://127.0.0.1:8428"
	}
	if timeout <= 0 {
		timeout = 500 * time.Millisecond
	}
	return &VMSink{
		URL: strings.TrimRight(url, "/"),
		Client: &http.Client{
			Timeout: timeout,
		},
	}
}

func (s *VMSink) Name() string { return "victoria_metrics" }

func (s *VMSink) Write(ctx context.Context, key string, point model.MetricPoint) error {
	line := toPromLine(key, point)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.URL+"/api/v1/import/prometheus", bytes.NewBufferString(line))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "text/plain")
	resp, err := s.Client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("vm status: %d", resp.StatusCode)
	}
	return nil
}

func toPromLine(idemKey string, point model.MetricPoint) string {
	labels := map[string]string{
		"job":            point.App,
		"instance":       point.Instance,
		"__monitor_id__": fmt.Sprintf("%d", point.MonitorID),
		"__metrics__":    point.Metrics,
		"__metric__":     point.Field,
		"idem_key":       idemKey,
	}
	for k, v := range point.Labels {
		labels[k] = v
	}
	metricName := point.Metrics + "_" + point.Field
	return metricName + "{" + renderLabels(labels) + "} " + fmt.Sprintf("%f %d", point.Value, point.UnixMs) + "\n"
}

func renderLabels(labels map[string]string) string {
	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	items := make([]string, 0, len(keys))
	for _, k := range keys {
		v := strings.ReplaceAll(labels[k], `"`, `\"`)
		items = append(items, k+`="`+v+`"`)
	}
	return strings.Join(items, ",")
}

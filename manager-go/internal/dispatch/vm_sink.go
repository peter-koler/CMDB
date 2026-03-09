package dispatch

import (
	"bytes"
	"context"
	"fmt"
	"net/http"
	"regexp"
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
	_ = idemKey
	metricsName := normalizeMetricToken(point.Metrics)
	fieldName := normalizeMetricToken(point.Field)
	job := strings.TrimSpace(point.App)
	if strings.HasPrefix(job, "_prometheus_") {
		job = strings.TrimPrefix(job, "_prometheus_")
	}
	if job == "" {
		job = "unknown"
	}
	instance := strings.TrimSpace(point.Instance)
	if instance == "" {
		instance = "unknown"
	}
	labels := map[string]string{
		"job":            job,
		"instance":       instance,
		"__monitor_id__": fmt.Sprintf("%d", point.MonitorID),
		"__metrics__":    metricsName,
		"__metric__":     fieldName,
	}
	for k, v := range point.Labels {
		key := normalizeLabelKey(k)
		if key == "" || isForbiddenLabel(key) {
			continue
		}
		labels[key] = v
	}
	metricName := normalizeMetricToken(metricsName + "_" + fieldName)
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

var invalidMetricToken = regexp.MustCompile(`[^a-zA-Z0-9_]`)

func normalizeMetricToken(raw string) string {
	s := strings.TrimSpace(raw)
	if s == "" {
		return "unknown"
	}
	s = invalidMetricToken.ReplaceAllString(s, "_")
	s = strings.Trim(s, "_")
	if s == "" {
		return "unknown"
	}
	if s[0] >= '0' && s[0] <= '9' {
		s = "m_" + s
	}
	return s
}

func normalizeLabelKey(raw string) string {
	s := normalizeMetricToken(raw)
	if s == "unknown" {
		return ""
	}
	return s
}

func isForbiddenLabel(key string) bool {
	switch key {
	case "timestamp", "time", "rand", "random", "uuid", "trace_id", "span_id", "request_id", "session_id", "pod_uid":
		return true
	default:
		return false
	}
}

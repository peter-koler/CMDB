package metrics

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type RangePoint struct {
	Timestamp int64   `json:"timestamp"`
	Value     float64 `json:"value"`
}

type RangeSeries struct {
	Name   string            `json:"name"`
	Labels map[string]string `json:"labels,omitempty"`
	Points []RangePoint      `json:"points"`
}

type VMClient struct {
	BaseURL string
	Client  *http.Client
}

func NewVMClient(baseURL string, timeout time.Duration) *VMClient {
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8428"
	}
	if timeout <= 0 {
		timeout = 1500 * time.Millisecond
	}
	return &VMClient{
		BaseURL: strings.TrimRight(baseURL, "/"),
		Client:  &http.Client{Timeout: timeout},
	}
}

func (c *VMClient) ListSeries(ctx context.Context, matchers []string, start, end time.Time) ([]map[string]string, error) {
	u, err := url.Parse(c.BaseURL + "/api/v1/series")
	if err != nil {
		return nil, err
	}
	q := u.Query()
	for _, matcher := range matchers {
		m := strings.TrimSpace(matcher)
		if m == "" {
			continue
		}
		q.Add("match[]", m)
	}
	q.Set("start", strconv.FormatFloat(float64(start.UnixMilli())/1000, 'f', 3, 64))
	q.Set("end", strconv.FormatFloat(float64(end.UnixMilli())/1000, 'f', 3, 64))
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.Client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("vm series status=%d", resp.StatusCode)
	}

	var payload struct {
		Status string              `json:"status"`
		Data   []map[string]string `json:"data"`
		Error  string              `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, err
	}
	if payload.Status != "success" {
		return nil, fmt.Errorf("vm series failed: %s", payload.Error)
	}
	return payload.Data, nil
}

func (c *VMClient) QueryRange(ctx context.Context, promQL string, start, end time.Time, step time.Duration) ([]RangeSeries, error) {
	if step <= 0 {
		step = time.Minute
	}
	u, err := url.Parse(c.BaseURL + "/api/v1/query_range")
	if err != nil {
		return nil, err
	}
	q := u.Query()
	q.Set("query", promQL)
	q.Set("start", strconv.FormatFloat(float64(start.UnixMilli())/1000, 'f', 3, 64))
	q.Set("end", strconv.FormatFloat(float64(end.UnixMilli())/1000, 'f', 3, 64))
	q.Set("step", strconv.FormatInt(int64(step.Seconds()), 10))
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.Client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("vm query_range status=%d", resp.StatusCode)
	}

	var payload struct {
		Status string `json:"status"`
		Data   struct {
			ResultType string `json:"resultType"`
			Result     []struct {
				Metric map[string]string `json:"metric"`
				Values [][]any           `json:"values"`
			} `json:"result"`
		} `json:"data"`
		Error string `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, err
	}
	if payload.Status != "success" {
		return nil, fmt.Errorf("vm query_range failed: %s", payload.Error)
	}

	series := make([]RangeSeries, 0, len(payload.Data.Result))
	for _, item := range payload.Data.Result {
		name := item.Metric["__name__"]
		points := make([]RangePoint, 0, len(item.Values))
		for _, pair := range item.Values {
			if len(pair) < 2 {
				continue
			}
			ts, err := toUnixMs(pair[0])
			if err != nil {
				continue
			}
			val, err := toFloat(pair[1])
			if err != nil {
				continue
			}
			points = append(points, RangePoint{Timestamp: ts, Value: val})
		}
		series = append(series, RangeSeries{
			Name:   name,
			Labels: item.Metric,
			Points: points,
		})
	}
	return series, nil
}

func toUnixMs(raw any) (int64, error) {
	switch v := raw.(type) {
	case float64:
		return int64(v * 1000), nil
	case int64:
		return v * 1000, nil
	case string:
		f, err := strconv.ParseFloat(strings.TrimSpace(v), 64)
		if err != nil {
			return 0, err
		}
		return int64(f * 1000), nil
	default:
		return 0, fmt.Errorf("unsupported timestamp type %T", raw)
	}
}

func toFloat(raw any) (float64, error) {
	switch v := raw.(type) {
	case float64:
		return v, nil
	case int64:
		return float64(v), nil
	case string:
		return strconv.ParseFloat(strings.TrimSpace(v), 64)
	default:
		return 0, fmt.Errorf("unsupported value type %T", raw)
	}
}

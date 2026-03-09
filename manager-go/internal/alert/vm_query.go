package alert

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

var ErrVMQueryEmptyResult = errors.New("vm query empty result")

type VMQuerier interface {
	QueryValue(ctx context.Context, promQL string, ts time.Time) (float64, error)
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
		timeout = time.Second
	}
	return &VMClient{
		BaseURL: strings.TrimRight(baseURL, "/"),
		Client:  &http.Client{Timeout: timeout},
	}
}

func (c *VMClient) QueryValue(ctx context.Context, promQL string, ts time.Time) (float64, error) {
	u, err := url.Parse(c.BaseURL + "/api/v1/query")
	if err != nil {
		return 0, err
	}
	q := u.Query()
	q.Set("query", promQL)
	q.Set("time", strconv.FormatInt(ts.Unix(), 10))
	u.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if err != nil {
		return 0, err
	}
	resp, err := c.Client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return 0, fmt.Errorf("vm query status=%d", resp.StatusCode)
	}

	var payload struct {
		Status string `json:"status"`
		Data   struct {
			ResultType string `json:"resultType"`
			Result     []struct {
				Value []any `json:"value"`
			} `json:"result"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return 0, err
	}
	if payload.Status != "success" {
		return 0, fmt.Errorf("vm query failed status=%s", payload.Status)
	}
	if len(payload.Data.Result) == 0 || len(payload.Data.Result[0].Value) < 2 {
		return 0, ErrVMQueryEmptyResult
	}
	raw := fmt.Sprintf("%v", payload.Data.Result[0].Value[1])
	v, err := strconv.ParseFloat(raw, 64)
	if err != nil {
		return 0, err
	}
	return v, nil
}

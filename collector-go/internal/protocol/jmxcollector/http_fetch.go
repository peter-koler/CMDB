package jmxcollector

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

func fetchJMXPayload(ctx context.Context, cfg taskConfig) (map[string]any, error) {
	ctx2, cancel := context.WithTimeout(ctx, cfg.Timeout)
	defer cancel()

	reqURL, err := withQueryObjectName(cfg.Endpoint, cfg.ObjectName)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx2, http.MethodGet, reqURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/json")
	if cfg.Username != "" || cfg.Password != "" {
		req.SetBasicAuth(cfg.Username, cfg.Password)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		return nil, fmt.Errorf("jmx endpoint status=%d body=%s", resp.StatusCode, strings.TrimSpace(string(body)))
	}
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	var out map[string]any
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func withQueryObjectName(endpoint, objectName string) (string, error) {
	u, err := url.Parse(endpoint)
	if err != nil {
		return "", err
	}
	query := u.Query()
	if strings.TrimSpace(query.Get("qry")) == "" {
		query.Set("qry", objectName)
	}
	u.RawQuery = query.Encode()
	return u.String(), nil
}

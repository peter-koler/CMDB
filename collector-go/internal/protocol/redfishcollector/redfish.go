package redfishcollector

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("redfish", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host := strings.TrimSpace(task.Params["host"])
	port := strings.TrimSpace(task.Params["port"])
	if host == "" {
		return nil, "", fmt.Errorf("missing host")
	}
	if port == "" {
		port = "443"
	}
	timeout := resolveTimeout(task)
	client := &http.Client{Timeout: timeout}
	scheme := "https"
	if strings.EqualFold(strings.TrimSpace(task.Params["ssl"]), "false") {
		scheme = "http"
	}
	baseURL := fmt.Sprintf("%s://%s:%s", scheme, host, port)
	username := strings.TrimSpace(task.Params["username"])
	password := strings.TrimSpace(task.Params["password"])

	schema := strings.TrimSpace(task.Params["schema"])
	if schema == "" {
		schema = defaultSchema(task.Name)
	}
	if schema == "" {
		return nil, "", fmt.Errorf("redfish schema not found for metric %s", task.Name)
	}
	paths := splitCSV(task.Params["jsonPath"])
	if len(paths) == 0 {
		return nil, "", fmt.Errorf("missing redfish jsonPath")
	}

	resourceURIs, err := expandResourceURIs(ctx, client, baseURL, username, password, schema)
	if err != nil {
		return nil, "", err
	}
	if len(resourceURIs) == 0 {
		return nil, "", fmt.Errorf("no redfish resources found")
	}

	rows := make([]map[string]string, 0, len(resourceURIs))
	for _, uri := range resourceURIs {
		payload, err := getJSON(ctx, client, baseURL+uri, username, password)
		if err != nil {
			continue
		}
		row := map[string]string{}
		for idx, field := range task.FieldSpecs {
			if idx >= len(paths) {
				break
			}
			value := evalSimpleJSONPath(payload, paths[idx])
			row[strings.TrimSpace(field.Field)] = value
		}
		if len(row) > 0 {
			rows = append(rows, row)
		}
	}
	if len(rows) == 0 {
		return nil, "", fmt.Errorf("redfish collect got empty rows")
	}
	out := map[string]string{}
	for i, row := range rows {
		rowNo := i + 1
		for key, value := range row {
			if rowNo == 1 {
				out[key] = value
			}
			out[fmt.Sprintf("row%d_%s", rowNo, key)] = value
		}
	}
	out["responseTime"] = strconv.FormatInt(timeout.Milliseconds(), 10)
	return out, "ok", nil
}

func resolveTimeout(task model.MetricsTask) time.Duration {
	if task.Timeout > 0 {
		return task.Timeout
	}
	if raw := strings.TrimSpace(task.Params["timeout"]); raw != "" {
		if ms, err := strconv.Atoi(raw); err == nil && ms > 0 {
			return time.Duration(ms) * time.Millisecond
		}
	}
	return 6 * time.Second
}

func getJSON(ctx context.Context, client *http.Client, url string, username string, password string) (map[string]any, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if username != "" {
		req.SetBasicAuth(username, password)
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		return nil, fmt.Errorf("status=%d", resp.StatusCode)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var out map[string]any
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, err
	}
	return out, nil
}

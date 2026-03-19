package httpcollector

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"collector-go/internal/model"
)

type parser struct {
	task       model.MetricsTask
	latency    time.Duration
	body       []byte
	headers    http.Header
	statusCode int
}

func newParser(task model.MetricsTask, latency time.Duration, body []byte) parser {
	return parser{task: task, latency: latency, body: body}
}

func (p parser) parse() (map[string]string, error) {
	parseType := strings.ToLower(strings.TrimSpace(firstNonEmpty(
		p.task.Params["parseType"],
		p.task.Params["http.parseType"],
	)))
	switch parseType {
	case "", "default":
		return p.parseDefault()
	case "jsonpath":
		return p.parseJSONPath()
	case "prometheus":
		return p.parsePrometheus()
	case "website":
		return p.parseWebsite()
	case "header":
		return p.parseHeader()
	case "xmlpath":
		return p.parseXMLPath()
	case "config":
		return p.parseConfig()
	default:
		return nil, fmt.Errorf("unsupported http parseType: %s", parseType)
	}
}

func (p parser) parseDefault() (map[string]string, error) {
	var payload any
	if len(strings.TrimSpace(string(p.body))) > 0 {
		if err := json.Unmarshal(p.body, &payload); err == nil {
			switch typed := payload.(type) {
			case map[string]any:
				return flattenObject(typed, requestedFieldNames(p.task), p.latency), nil
			case []any:
				rows := rowsFromJSONArray(typed, requestedFieldNames(p.task))
				return flattenRows(rows, p.latency), nil
			}
		}
	}
	out := map[string]string{
		"responseTime": fmt.Sprintf("%d", p.latency.Milliseconds()),
	}
	for _, spec := range p.task.FieldSpecs {
		field := strings.TrimSpace(spec.Field)
		if field == "" || field == "responseTime" {
			continue
		}
		if field == "body" {
			out[field] = strings.TrimSpace(string(p.body))
		}
	}
	return out, nil
}

package httpcollector

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
)

func (p parser) parseJSONPath() (map[string]string, error) {
	var payload any
	if err := json.Unmarshal(p.body, &payload); err != nil {
		return nil, err
	}
	script := strings.TrimSpace(firstNonEmpty(p.task.Params["parseScript"], p.task.Params["http.parseScript"]))
	selected, err := applySimpleJSONPath(payload, script)
	if err != nil {
		return nil, err
	}
	calculated := deriveCalculatedJSONFields(payload, p.task)
	switch typed := selected.(type) {
	case map[string]any:
		out := flattenObject(typed, requestedFieldNames(p.task), p.latency)
		mergeStringMaps(out, calculated)
		return out, nil
	case []any:
		rows := rowsFromJSONArray(typed, requestedFieldNames(p.task))
		out := flattenRows(rows, p.latency)
		mergeStringMaps(out, calculated)
		return out, nil
	case nil:
		out := map[string]string{"responseTime": fmt.Sprintf("%d", p.latency.Milliseconds())}
		mergeStringMaps(out, calculated)
		return out, nil
	default:
		out := map[string]string{
			"value":        stringifyJSONValue(typed),
			"metric_value": stringifyJSONValue(typed),
			"responseTime": fmt.Sprintf("%d", p.latency.Milliseconds()),
		}
		mergeStringMaps(out, calculated)
		return out, nil
	}
}

func applySimpleJSONPath(value any, script string) (any, error) {
	script = strings.TrimSpace(script)
	if script == "" || script == "$" {
		return value, nil
	}
	if script == "$.*" {
		obj, ok := value.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("jsonPath $.* requires object")
		}
		out := make([]any, 0, len(obj))
		for _, item := range obj {
			out = append(out, item)
		}
		return out, nil
	}
	return evalJSONExpression(value, script)
}

func flattenObject(obj map[string]any, requested map[string]struct{}, latency time.Duration) map[string]string {
	out := map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
	}
	for key, value := range obj {
		if len(requested) > 0 {
			if _, ok := requested[key]; !ok && key != "responseTime" {
				continue
			}
		}
		out[key] = stringifyJSONValue(value)
	}
	return out
}

func deriveCalculatedJSONFields(payload any, task model.MetricsTask) map[string]string {
	out := map[string]string{}
	for _, calc := range task.CalculateSpecs {
		field := strings.TrimSpace(calc.Field)
		expr := strings.TrimSpace(calc.Expression)
		if field == "" || expr == "" {
			continue
		}
		if literal, ok := parseQuotedLiteral(expr); ok {
			out[field] = literal
			continue
		}
		if !strings.HasPrefix(expr, "$") {
			continue
		}
		value, err := evalJSONExpression(payload, expr)
		if err != nil {
			continue
		}
		out[field] = firstJSONString(value)
	}
	return out
}

func parseQuotedLiteral(raw string) (string, bool) {
	if len(raw) < 2 {
		return "", false
	}
	if (strings.HasPrefix(raw, "'") && strings.HasSuffix(raw, "'")) || (strings.HasPrefix(raw, "\"") && strings.HasSuffix(raw, "\"")) {
		return raw[1 : len(raw)-1], true
	}
	return "", false
}

func firstJSONString(value any) string {
	switch typed := value.(type) {
	case []any:
		if len(typed) == 0 {
			return ""
		}
		return stringifyJSONValue(typed[0])
	default:
		return stringifyJSONValue(typed)
	}
}

func mergeStringMaps(dst map[string]string, src map[string]string) {
	for key, value := range src {
		if key == "" {
			continue
		}
		dst[key] = value
	}
}

func rowsFromJSONArray(items []any, requested map[string]struct{}) []map[string]string {
	rows := make([]map[string]string, 0, len(items))
	for _, item := range items {
		switch typed := item.(type) {
		case map[string]any:
			row := map[string]string{}
			for key, value := range typed {
				if len(requested) > 0 {
					if _, ok := requested[key]; !ok {
						continue
					}
				}
				row[key] = stringifyJSONValue(value)
			}
			if len(row) > 0 {
				rows = append(rows, row)
			}
		default:
			rows = append(rows, map[string]string{"value": stringifyJSONValue(typed)})
		}
	}
	return rows
}

func flattenRows(rows []map[string]string, latency time.Duration) map[string]string {
	out := map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
	}
	for idx, row := range rows {
		rowNo := idx + 1
		for key, value := range row {
			if rowNo == 1 {
				out[key] = value
			}
			out[fmt.Sprintf("row%d_%s", rowNo, key)] = value
		}
	}
	return out
}

func stringifyJSONValue(value any) string {
	switch typed := value.(type) {
	case nil:
		return ""
	case string:
		return typed
	case bool:
		if typed {
			return "true"
		}
		return "false"
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	case int:
		return strconv.Itoa(typed)
	case int64:
		return strconv.FormatInt(typed, 10)
	default:
		raw, err := json.Marshal(typed)
		if err != nil {
			return fmt.Sprintf("%v", typed)
		}
		return string(raw)
	}
}

func requestedFieldNames(task model.MetricsTask) map[string]struct{} {
	if len(task.FieldSpecs) == 0 {
		return nil
	}
	out := make(map[string]struct{}, len(task.FieldSpecs))
	for _, spec := range task.FieldSpecs {
		field := strings.TrimSpace(spec.Field)
		if field != "" {
			out[field] = struct{}{}
		}
	}
	return out
}

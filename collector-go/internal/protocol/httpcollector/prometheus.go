package httpcollector

import (
	"bufio"
	"bytes"
	"fmt"
	"strconv"
	"strings"
)

func (p parser) parsePrometheus() (map[string]string, error) {
	rows, err := parsePrometheusRows(p.task.Name, p.body)
	if err != nil {
		return nil, err
	}
	return flattenRows(rows, p.latency), nil
}

func parsePrometheusRows(metricName string, body []byte) ([]map[string]string, error) {
	scanner := bufio.NewScanner(bytes.NewReader(body))
	rows := make([]map[string]string, 0, 4)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if !strings.HasPrefix(line, metricName) {
			continue
		}
		row, err := parsePrometheusLine(metricName, line)
		if err != nil {
			return nil, err
		}
		rows = append(rows, row)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return []map[string]string{}, nil
	}
	return rows, nil
}

func parsePrometheusLine(metricName, line string) (map[string]string, error) {
	out := map[string]string{}
	rest := strings.TrimPrefix(line, metricName)
	valuePart := strings.TrimSpace(rest)
	if strings.HasPrefix(rest, "{") {
		end := strings.Index(rest, "}")
		if end < 0 {
			return nil, fmt.Errorf("invalid prometheus labels line: %s", line)
		}
		labels := strings.TrimPrefix(rest[:end+1], "{")
		labels = strings.TrimSuffix(labels, "}")
		parsePrometheusLabels(labels, out)
		valuePart = strings.TrimSpace(rest[end+1:])
	}
	fields := strings.Fields(valuePart)
	if len(fields) == 0 {
		return nil, fmt.Errorf("prometheus sample missing value: %s", line)
	}
	out["value"] = normalizePrometheusNumber(fields[0])
	out["metric_value"] = out["value"]
	return out, nil
}

func parsePrometheusLabels(labels string, out map[string]string) {
	for _, item := range splitRespectingQuotes(labels, ',') {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		parts := strings.SplitN(item, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		value := strings.Trim(strings.TrimSpace(parts[1]), `"`)
		out[key] = value
	}
}

func splitRespectingQuotes(s string, sep rune) []string {
	out := []string{}
	var current strings.Builder
	inQuote := false
	for _, r := range s {
		switch r {
		case '"':
			inQuote = !inQuote
			current.WriteRune(r)
		case sep:
			if inQuote {
				current.WriteRune(r)
			} else {
				out = append(out, current.String())
				current.Reset()
			}
		default:
			current.WriteRune(r)
		}
	}
	out = append(out, current.String())
	return out
}

func normalizePrometheusNumber(raw string) string {
	raw = strings.TrimSpace(raw)
	if f, err := strconv.ParseFloat(raw, 64); err == nil {
		return strconv.FormatFloat(f, 'f', -1, 64)
	}
	return raw
}

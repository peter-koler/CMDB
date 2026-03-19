package httpcollector

import (
	"fmt"
	"strconv"
	"strings"
)

func (p parser) parseWebsite() (map[string]string, error) {
	body := string(p.body)
	keyword := strings.TrimSpace(firstNonEmpty(p.task.Params["keyword"], p.task.Params["http.keyword"]))
	matched := true
	if keyword != "" {
		for _, one := range splitKeywords(keyword) {
			if !strings.Contains(body, one) {
				matched = false
				break
			}
		}
	}
	out := map[string]string{
		"responseTime": fmt.Sprintf("%d", p.latency.Milliseconds()),
		"statusCode":   strconv.Itoa(p.statusCode),
		"keyword":      strconv.FormatBool(matched),
	}
	if contentType := strings.TrimSpace(p.headers.Get("Content-Type")); contentType != "" {
		out["Content-Type"] = contentType
		out["content_type"] = contentType
	}
	if contentLength := strings.TrimSpace(p.headers.Get("Content-Length")); contentLength != "" {
		out["Content-Length"] = contentLength
		out["content_length"] = contentLength
	}
	return out, nil
}

func (p parser) parseHeader() (map[string]string, error) {
	out := map[string]string{
		"responseTime": fmt.Sprintf("%d", p.latency.Milliseconds()),
		"statusCode":   strconv.Itoa(p.statusCode),
	}
	for _, spec := range p.task.FieldSpecs {
		field := strings.TrimSpace(spec.Field)
		if field == "" {
			continue
		}
		switch field {
		case "content_type":
			out[field] = strings.TrimSpace(p.headers.Get("Content-Type"))
		case "content_length":
			out[field] = strings.TrimSpace(p.headers.Get("Content-Length"))
		case "statusCode":
			out[field] = strconv.Itoa(p.statusCode)
		default:
			out[field] = strings.TrimSpace(p.headers.Get(field))
		}
	}
	return out, nil
}

func splitKeywords(raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	items := strings.Split(raw, ",")
	out := make([]string, 0, len(items))
	for _, item := range items {
		v := strings.TrimSpace(item)
		if v != "" {
			out = append(out, v)
		}
	}
	if len(out) == 0 {
		return []string{raw}
	}
	return out
}

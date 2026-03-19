package httpcollector

import (
	"strconv"
	"strings"

	"collector-go/internal/model"
)

func applyPathCalculates(out map[string]string, source map[string]string, task model.MetricsTask) {
	for _, calc := range task.CalculateSpecs {
		field := strings.TrimSpace(calc.Field)
		expr := strings.TrimSpace(calc.Expression)
		if field == "" || expr == "" {
			continue
		}
		if value, ok := source[expr]; ok {
			out[field] = value
			continue
		}
		if value, ok := source[strings.TrimPrefix(expr, "$.")]; ok {
			out[field] = value
			continue
		}
	}
}

func parseIndexedSegment(seg string) (base string, index int, ok bool) {
	start := strings.Index(seg, "[")
	end := strings.LastIndex(seg, "]")
	if start < 0 || end <= start {
		return "", 0, false
	}
	base = strings.TrimSpace(seg[:start])
	raw := strings.TrimSpace(seg[start+1 : end])
	num, err := strconv.Atoi(raw)
	if err != nil {
		return "", 0, false
	}
	return base, num, true
}

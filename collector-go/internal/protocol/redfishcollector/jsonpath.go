package redfishcollector

import (
	"encoding/json"
	"strconv"
	"strings"
)

func evalSimpleJSONPath(payload map[string]any, expr string) string {
	expr = strings.TrimSpace(expr)
	if expr == "" || expr == "$" {
		return ""
	}
	expr = strings.TrimPrefix(expr, "$.")
	expr = strings.ReplaceAll(expr, "['", ".")
	expr = strings.ReplaceAll(expr, "']", "")
	expr = strings.TrimPrefix(expr, ".")
	if expr == "" {
		return ""
	}
	segments := strings.Split(expr, ".")
	var cur any = payload
	for _, seg := range segments {
		seg = strings.TrimSpace(seg)
		if seg == "" {
			continue
		}
		switch typed := cur.(type) {
		case map[string]any:
			cur = typed[seg]
		case []any:
			idx, err := strconv.Atoi(seg)
			if err != nil || idx < 0 || idx >= len(typed) {
				return ""
			}
			cur = typed[idx]
		default:
			return ""
		}
	}
	return toString(cur)
}

func toString(v any) string {
	switch val := v.(type) {
	case nil:
		return ""
	case string:
		return val
	case bool:
		if val {
			return "true"
		}
		return "false"
	case float64:
		return strconv.FormatFloat(val, 'f', -1, 64)
	case int:
		return strconv.Itoa(val)
	default:
		raw, _ := json.Marshal(val)
		return string(raw)
	}
}

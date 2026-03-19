package snmpcollector

import "strings"

func parseSNMPValue(raw string) string {
	text := strings.TrimSpace(raw)
	if text == "" {
		return ""
	}
	parts := strings.SplitN(text, "=", 2)
	if len(parts) != 2 {
		return text
	}
	right := strings.TrimSpace(parts[1])
	if colon := strings.Index(right, ":"); colon >= 0 {
		right = strings.TrimSpace(right[colon+1:])
	}
	right = strings.Trim(right, "\"")
	if strings.Contains(right, "(") && strings.Contains(right, ")") {
		start := strings.Index(right, "(")
		end := strings.Index(right[start+1:], ")")
		if start >= 0 && end >= 0 {
			mid := strings.TrimSpace(right[start+1 : start+1+end])
			if mid != "" {
				return mid
			}
		}
	}
	return strings.TrimSpace(right)
}

func parseWalkValues(raw string) []string {
	lines := strings.Split(raw, "\n")
	out := make([]string, 0, len(lines))
	for _, line := range lines {
		val := parseSNMPValue(line)
		if strings.TrimSpace(val) == "" {
			continue
		}
		out = append(out, val)
	}
	return out
}

package linuxcollector

import (
	"strings"
)

func merge(dst map[string]string, src map[string]string) {
	for k, v := range src {
		if strings.TrimSpace(k) == "" || strings.TrimSpace(v) == "" {
			continue
		}
		dst[k] = v
	}
}

func splitLines(s string) []string {
	raw := strings.Split(s, "\n")
	out := make([]string, 0, len(raw))
	for _, line := range raw {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		out = append(out, line)
	}
	return out
}

func splitKV(line string) (string, string, bool) {
	line = strings.TrimSpace(line)
	if line == "" {
		return "", "", false
	}
	parts := strings.Fields(line)
	if len(parts) < 2 {
		return "", "", false
	}
	key := strings.TrimSuffix(strings.ToLower(strings.TrimSpace(parts[0])), ":")
	val := strings.TrimSpace(parts[1])
	if key == "" || val == "" {
		return "", "", false
	}
	return key, val, true
}

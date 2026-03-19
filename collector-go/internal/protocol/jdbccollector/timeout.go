package jdbccollector

import (
	"strconv"
	"strings"
	"time"
)

func parseTimeoutDuration(raw string, def time.Duration) time.Duration {
	text := strings.TrimSpace(raw)
	if text == "" {
		return def
	}
	if strings.HasSuffix(text, "ms") || strings.HasSuffix(text, "s") {
		if d, err := time.ParseDuration(text); err == nil && d > 0 {
			return d
		}
	}
	if ms, err := strconv.Atoi(text); err == nil && ms > 0 {
		return time.Duration(ms) * time.Millisecond
	}
	return def
}

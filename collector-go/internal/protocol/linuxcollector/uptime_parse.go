package linuxcollector

import "strings"

func parseUptimeLoads(raw string) (string, string, string) {
	text := strings.TrimSpace(raw)
	if text == "" {
		return "", "", ""
	}
	idx := strings.Index(strings.ToLower(text), "load average:")
	if idx == -1 {
		idx = strings.Index(strings.ToLower(text), "load averages:")
	}
	if idx == -1 {
		return "", "", ""
	}
	loadPart := strings.TrimSpace(text[idx:])
	pieces := strings.Split(loadPart, ":")
	if len(pieces) < 2 {
		return "", "", ""
	}
	items := strings.Split(strings.TrimSpace(pieces[len(pieces)-1]), ",")
	if len(items) < 3 {
		return "", "", ""
	}
	return strings.TrimSpace(items[0]), strings.TrimSpace(items[1]), strings.TrimSpace(items[2])
}

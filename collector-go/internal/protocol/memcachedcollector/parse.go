package memcachedcollector

import "strings"

func parseKVLine(fields map[string]string, line string) {
	parts := strings.Fields(strings.TrimSpace(line))
	if len(parts) != 3 || parts[0] != "STAT" {
		return
	}
	key := strings.TrimSpace(parts[1])
	if key == "" {
		return
	}
	fields[key] = strings.TrimSpace(parts[2])
}

func parseSizesLine(fields map[string]string, line string) {
	parts := strings.Fields(strings.TrimSpace(line))
	if len(parts) < 3 || parts[0] != "STAT" {
		return
	}
	fields["item_size"] = strings.TrimSpace(parts[1])
	fields["item_count"] = strings.TrimSpace(parts[2])
}

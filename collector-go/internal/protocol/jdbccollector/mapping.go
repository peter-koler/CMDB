package jdbccollector

import "strings"

func parseAliasFields(raw string) []string {
	text := strings.TrimSpace(raw)
	if text == "" {
		return nil
	}
	parts := strings.Split(text, ",")
	out := make([]string, 0, len(parts))
	seen := make(map[string]struct{}, len(parts))
	for _, part := range parts {
		name := strings.TrimSpace(part)
		if name == "" {
			continue
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, name)
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func projectRow(row map[string]string, cols []string, selected []string) map[string]string {
	if len(row) == 0 {
		return map[string]string{}
	}
	out := make(map[string]string)
	lookup := make(map[string]string, len(row))
	for k, v := range row {
		lookup[strings.ToLower(strings.TrimSpace(k))] = v
	}
	if len(selected) == 0 {
		for _, col := range cols {
			key := strings.TrimSpace(col)
			if key == "" {
				continue
			}
			out[key] = lookup[strings.ToLower(key)]
		}
		return out
	}
	for _, name := range selected {
		key := strings.TrimSpace(name)
		if key == "" {
			continue
		}
		out[key] = lookup[strings.ToLower(key)]
	}
	return out
}

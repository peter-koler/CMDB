package httpcollector

import (
	"strconv"
	"strings"
)

func (p parser) parseConfig() (map[string]string, error) {
	script := strings.TrimSpace(firstNonEmpty(p.task.Params["parseScript"], p.task.Params["http.parseScript"]))
	requested := requestedFieldNames(p.task)
	parsed := parseConfigKV(string(p.body), script)

	out := map[string]string{
		"responseTime": strconv.FormatInt(p.latency.Milliseconds(), 10),
	}
	for key, value := range parsed {
		if key == "" {
			continue
		}
		out[key] = value
		leaf := key
		if idx := strings.LastIndex(leaf, "."); idx >= 0 {
			leaf = leaf[idx+1:]
		}
		if _, ok := requested[leaf]; ok && out[leaf] == "" {
			out[leaf] = value
		}
	}

	for key, value := range parsed {
		segments := strings.Split(key, ".")
		for i, seg := range segments {
			base, idx, ok := parseIndexedSegment(seg)
			if !ok {
				continue
			}
			if i == len(segments)-1 {
				continue
			}
			field := segments[len(segments)-1]
			rowKey := "row" + strconv.Itoa(idx+1) + "_" + field
			out[rowKey] = value
			if idx == 0 && out[field] == "" {
				out[field] = value
			}
			if base != "" {
				_ = base
			}
			break
		}
	}

	applyPathCalculates(out, parsed, p.task)
	if len(requested) > 0 {
		for key := range out {
			if key == "responseTime" {
				continue
			}
			if _, ok := requested[key]; ok {
				continue
			}
			if strings.HasPrefix(key, "row") {
				continue
			}
			delete(out, key)
		}
	}
	return out, nil
}

func parseConfigKV(raw string, script string) map[string]string {
	out := map[string]string{}
	lines := strings.Split(raw, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(strings.TrimSuffix(line, "\r"))
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])
		if key == "" {
			continue
		}
		normKey := key
		if script != "" {
			if key == script {
				normKey = ""
			} else if strings.HasPrefix(key, script+".") {
				normKey = strings.TrimPrefix(key, script+".")
			} else if strings.HasPrefix(key, script+"[") {
				normKey = strings.TrimPrefix(key, script)
				normKey = strings.TrimPrefix(normKey, ".")
			} else {
				continue
			}
		}
		normKey = strings.TrimPrefix(normKey, ".")
		out[key] = value
		if normKey != "" {
			out[normKey] = value
		}
	}
	return out
}

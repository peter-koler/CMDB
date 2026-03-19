package jmxcollector

import (
	"fmt"
	"strconv"
	"strings"

	"collector-go/internal/model"
)

func extractBeans(payload map[string]any) []map[string]any {
	if len(payload) == 0 {
		return nil
	}
	if beans, ok := payload["beans"].([]any); ok {
		out := make([]map[string]any, 0, len(beans))
		for _, item := range beans {
			if m, ok := item.(map[string]any); ok {
				out = append(out, m)
			}
		}
		return out
	}
	return []map[string]any{payload}
}

func collectFromBeans(beans []map[string]any, task model.MetricsTask) map[string]string {
	fields := map[string]string{}
	if len(beans) == 0 {
		return fields
	}
	aliases := parseAliasMappings(task.Params["alias_fields"])
	specNames := collectFieldSpecNames(task.FieldSpecs)

	for idx, bean := range beans {
		flat := flattenBean(bean)
		row := buildBeanRow(flat, aliases, specNames)
		if len(row) == 0 {
			continue
		}
		rowNum := idx + 1
		for k, v := range row {
			if rowNum == 1 {
				fields[k] = v
			}
			fields["row"+strconv.Itoa(rowNum)+"_"+k] = v
		}
	}
	return fields
}

type aliasMapping struct {
	source string
	target string
}

func parseAliasMappings(raw string) []aliasMapping {
	text := strings.TrimSpace(raw)
	if text == "" {
		return nil
	}
	items := strings.Split(text, ",")
	out := make([]aliasMapping, 0, len(items))
	seen := map[string]struct{}{}
	for _, item := range items {
		cur := strings.TrimSpace(item)
		if cur == "" {
			continue
		}
		parts := strings.Split(cur, "->")
		source := strings.TrimSpace(cur)
		target := source
		if len(parts) >= 2 {
			target = strings.TrimSpace(parts[len(parts)-1])
		}
		if source == "" || target == "" {
			continue
		}
		key := strings.ToLower(source + "->" + target)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, aliasMapping{source: source, target: target})
	}
	return out
}

func collectFieldSpecNames(specs []model.FieldSpec) []string {
	if len(specs) == 0 {
		return nil
	}
	out := make([]string, 0, len(specs))
	seen := map[string]struct{}{}
	for _, spec := range specs {
		name := strings.TrimSpace(spec.Field)
		if name == "" {
			continue
		}
		key := strings.ToLower(name)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, name)
	}
	return out
}

func flattenBean(bean map[string]any) map[string]string {
	out := map[string]string{}
	for k, v := range bean {
		flattenValue(out, strings.TrimSpace(k), v)
	}
	return out
}

func flattenValue(dst map[string]string, prefix string, value any) {
	if prefix == "" || value == nil {
		return
	}
	switch typed := value.(type) {
	case map[string]any:
		for k, v := range typed {
			next := strings.TrimSpace(k)
			if next == "" {
				continue
			}
			flattenValue(dst, prefix+"->"+next, v)
		}
	case []any:
		dst[prefix] = fmt.Sprintf("%v", typed)
	default:
		dst[prefix] = strings.TrimSpace(fmt.Sprintf("%v", typed))
	}
}

func buildBeanRow(flat map[string]string, aliases []aliasMapping, specNames []string) map[string]string {
	out := map[string]string{}
	lower := map[string]string{}
	for k, v := range flat {
		lower[strings.ToLower(strings.TrimSpace(k))] = v
	}

	for _, alias := range aliases {
		if value := lookupValue(lower, alias.source); value != "" {
			out[alias.target] = value
		}
	}
	for _, name := range specNames {
		if _, exists := out[name]; exists {
			continue
		}
		if value := lookupValue(lower, name); value != "" {
			out[name] = value
		}
	}

	if len(out) > 0 {
		return out
	}
	for k, v := range flat {
		if k == "" || strings.TrimSpace(v) == "" {
			continue
		}
		out[k] = v
	}
	return out
}

func lookupValue(lower map[string]string, key string) string {
	k := strings.ToLower(strings.TrimSpace(key))
	if k == "" {
		return ""
	}
	if v, ok := lower[k]; ok {
		return v
	}
	if strings.Contains(k, ".") {
		if v, ok := lower[strings.ReplaceAll(k, ".", "->")]; ok {
			return v
		}
	}
	if strings.Contains(k, "_") {
		if v, ok := lower[strings.ReplaceAll(k, "_", ".")]; ok {
			return v
		}
	}
	return ""
}

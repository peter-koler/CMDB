package sshcollector

import (
	"fmt"
	"strings"

	"collector-go/internal/model"
)

func parseOutput(raw string, parseType string, fieldSpecs []model.FieldSpec) map[string]string {
	lines := compactLines(raw)
	switch strings.TrimSpace(strings.ToLower(parseType)) {
	case "onerow":
		return parseOneRow(lines, fieldSpecs)
	case "multirow":
		return parseMultiRow(lines, fieldSpecs)
	default:
		return parseMultiRow(lines, fieldSpecs)
	}
}

func parseOneRow(lines []string, specs []model.FieldSpec) map[string]string {
	out := map[string]string{}
	if len(lines) == 0 {
		return out
	}
	if len(lines) >= 2 {
		headers := tokenize(lines[0], 0)
		values := tokenize(lines[1], len(headers))
		for i, h := range headers {
			if i < len(values) {
				out[h] = values[i]
			}
		}
		return out
	}
	values := tokenize(lines[0], len(specs))
	for i, spec := range specs {
		if i >= len(values) {
			break
		}
		out[spec.Field] = values[i]
	}
	return out
}

func parseMultiRow(lines []string, specs []model.FieldSpec) map[string]string {
	out := map[string]string{}
	if len(lines) == 0 {
		return out
	}
	if len(lines) == 1 {
		out["output"] = lines[0]
		return out
	}
	headers := tokenize(lines[0], 0)
	if len(headers) == 0 {
		out["output"] = strings.Join(lines, "\n")
		return out
	}
	for idx, rowLine := range lines[1:] {
		values := tokenize(rowLine, len(headers))
		for i, h := range headers {
			if i >= len(values) {
				continue
			}
			val := values[i]
			if idx == 0 {
				out[h] = val
			}
			out[fmt.Sprintf("row%d_%s", idx+1, h)] = val
		}
	}
	return out
}

func compactLines(raw string) []string {
	items := strings.Split(strings.ReplaceAll(raw, "\r", ""), "\n")
	out := make([]string, 0, len(items))
	for _, item := range items {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		out = append(out, item)
	}
	return out
}

func tokenize(line string, expect int) []string {
	parts := strings.Fields(strings.TrimSpace(line))
	if expect > 0 && len(parts) > expect {
		head := append([]string(nil), parts[:expect-1]...)
		tail := strings.Join(parts[expect-1:], " ")
		return append(head, tail)
	}
	return parts
}

package sshcollector

import (
	"fmt"
	"strconv"
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
		headerIdx := len(lines) - 2
		if idx := findHeaderLine(lines, specs, true); idx >= 0 && idx+1 < len(lines) {
			headerIdx = idx
		}
		headers := tokenize(lines[headerIdx], 0)
		if len(headers) > 0 {
			valueIdx := pickOneRowValueLine(lines, headerIdx, headers, specs)
			if valueIdx >= 0 && valueIdx < len(lines) {
				values := tokenize(lines[valueIdx], len(headers))
				for i, h := range headers {
					if i < len(values) {
						out[h] = values[i]
					}
				}
			}
		}
		if len(out) > 0 {
			return out
		}
	}
	values := tokenize(lines[len(lines)-1], len(specs))
	for i, spec := range specs {
		if i >= len(values) {
			break
		}
		out[spec.Field] = values[i]
	}
	return out
}

func pickOneRowValueLine(lines []string, headerIdx int, headers []string, specs []model.FieldSpec) int {
	if headerIdx+1 >= len(lines) {
		return -1
	}
	bestIdx := -1
	bestScore := -1
	for idx := headerIdx + 1; idx < len(lines); idx++ {
		values := tokenize(lines[idx], len(headers))
		score := scoreOneRowCandidate(headers, values, specs)
		if score > bestScore {
			bestScore = score
			bestIdx = idx
		}
	}
	if bestIdx >= 0 {
		return bestIdx
	}
	return headerIdx + 1
}

func scoreOneRowCandidate(headers []string, values []string, specs []model.FieldSpec) int {
	if len(headers) == 0 || len(values) == 0 {
		return -1
	}
	if looksLikeHeader(headers, values) {
		return -1
	}
	specByField := make(map[string]model.FieldSpec, len(specs))
	for _, spec := range specs {
		key := strings.TrimSpace(spec.Field)
		if key == "" {
			continue
		}
		specByField[key] = spec
	}
	score := 0
	for i, h := range headers {
		if i >= len(values) {
			continue
		}
		value := strings.TrimSpace(values[i])
		if value == "" {
			continue
		}
		score++
		spec, ok := specByField[strings.TrimSpace(h)]
		if !ok {
			continue
		}
		fieldType := strings.ToLower(strings.TrimSpace(spec.Type))
		if fieldType == "string" || fieldType == "time" {
			continue
		}
		normalized := strings.TrimSpace(strings.TrimSuffix(value, "%"))
		if _, err := strconv.ParseFloat(normalized, 64); err == nil {
			score += 2
		}
	}
	return score
}

func looksLikeHeader(headers []string, values []string) bool {
	if len(headers) == 0 || len(values) == 0 {
		return false
	}
	limit := minInt(len(headers), len(values))
	matched := 0
	for i := 0; i < limit; i++ {
		if strings.EqualFold(strings.TrimSpace(headers[i]), strings.TrimSpace(values[i])) {
			matched++
		}
	}
	return matched == limit
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
	headerIdx := 0
	if idx := findHeaderLine(lines, specs, false); idx >= 0 && idx < len(lines)-1 {
		headerIdx = idx
	}
	headers := tokenize(lines[headerIdx], 0)
	if len(headers) == 0 {
		out["output"] = strings.Join(lines, "\n")
		return out
	}
	for idx, rowLine := range lines[headerIdx+1:] {
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

func findHeaderLine(lines []string, specs []model.FieldSpec, oneRow bool) int {
	expected := make(map[string]struct{}, len(specs))
	for _, spec := range specs {
		field := strings.TrimSpace(spec.Field)
		if field == "" {
			continue
		}
		expected[field] = struct{}{}
	}
	if len(expected) == 0 {
		return -1
	}

	maxIdx := len(lines) - 1
	if oneRow {
		maxIdx = len(lines) - 2
	}
	if maxIdx < 0 {
		return -1
	}

	bestIdx := -1
	bestScore := 0
	for idx := 0; idx <= maxIdx; idx++ {
		tokens := tokenize(lines[idx], 0)
		if len(tokens) == 0 {
			continue
		}
		score := 0
		seen := map[string]struct{}{}
		for _, token := range tokens {
			if _, ok := expected[token]; !ok {
				continue
			}
			if _, duplicated := seen[token]; duplicated {
				continue
			}
			seen[token] = struct{}{}
			score++
		}
		if score == len(expected) {
			return idx
		}
		if score > bestScore {
			bestScore = score
			bestIdx = idx
		}
	}
	if bestScore >= minInt(2, len(expected)) {
		return bestIdx
	}
	return -1
}

func minInt(a int, b int) int {
	if a < b {
		return a
	}
	return b
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

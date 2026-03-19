package httpcollector

import (
	"fmt"
	"strconv"
	"strings"
)

type jsonSelectorKind string

const (
	selectorField    jsonSelectorKind = "field"
	selectorIndex    jsonSelectorKind = "index"
	selectorWildcard jsonSelectorKind = "wildcard"
	selectorFilter   jsonSelectorKind = "filter"
)

type jsonSelector struct {
	kind        jsonSelectorKind
	field       string
	index       int
	filterField string
	filterValue string
}

func evalJSONExpression(root any, expr string) (any, error) {
	selectors, err := parseJSONExpression(expr)
	if err != nil {
		return nil, err
	}
	current := []any{root}
	for _, selector := range selectors {
		next := make([]any, 0, len(current))
		for _, item := range current {
			values, err := applySelector(item, selector)
			if err != nil {
				return nil, err
			}
			next = append(next, values...)
		}
		current = next
	}
	if len(current) == 0 {
		return nil, nil
	}
	if len(current) == 1 {
		return current[0], nil
	}
	return current, nil
}

func parseJSONExpression(expr string) ([]jsonSelector, error) {
	expr = strings.TrimSpace(expr)
	if expr == "" || expr == "$" {
		return nil, nil
	}
	if !strings.HasPrefix(expr, "$") {
		return nil, fmt.Errorf("jsonPath must start with $")
	}
	var selectors []jsonSelector
	for i := 1; i < len(expr); {
		switch expr[i] {
		case '.':
			i++
			if i < len(expr) && expr[i] == '*' {
				selectors = append(selectors, jsonSelector{kind: selectorWildcard})
				i++
				continue
			}
			field, next := readFieldToken(expr, i)
			if field == "" {
				return nil, fmt.Errorf("invalid field token in %s", expr)
			}
			selectors = append(selectors, jsonSelector{kind: selectorField, field: field})
			i = next
		case '[':
			selector, next, err := readBracketSelector(expr, i)
			if err != nil {
				return nil, err
			}
			selectors = append(selectors, selector)
			i = next
		default:
			return nil, fmt.Errorf("unsupported token %q in %s", string(expr[i]), expr)
		}
	}
	return selectors, nil
}

func readFieldToken(expr string, start int) (string, int) {
	i := start
	for i < len(expr) && expr[i] != '.' && expr[i] != '[' {
		i++
	}
	return strings.TrimSpace(expr[start:i]), i
}

func readBracketSelector(expr string, start int) (jsonSelector, int, error) {
	end := findMatchingBracket(expr, start)
	if end < 0 {
		return jsonSelector{}, 0, fmt.Errorf("unclosed bracket in %s", expr)
	}
	body := strings.TrimSpace(expr[start+1 : end])
	switch {
	case body == "*":
		return jsonSelector{kind: selectorWildcard}, end + 1, nil
	case strings.HasPrefix(body, "'") || strings.HasPrefix(body, "\""):
		field := body
		if strings.HasPrefix(body, "'") && strings.HasSuffix(body, "'") {
			field = body[1 : len(body)-1]
		} else {
			unquoted, err := strconv.Unquote(body)
			if err != nil {
				return jsonSelector{}, 0, err
			}
			field = unquoted
		}
		return jsonSelector{kind: selectorField, field: field}, end + 1, nil
	case strings.HasPrefix(body, "?(") && strings.HasSuffix(body, ")"):
		filterField, filterValue, err := parseFilter(body)
		if err != nil {
			return jsonSelector{}, 0, err
		}
		return jsonSelector{kind: selectorFilter, filterField: filterField, filterValue: filterValue}, end + 1, nil
	default:
		index, err := strconv.Atoi(body)
		if err != nil {
			return jsonSelector{}, 0, fmt.Errorf("unsupported bracket token [%s]", body)
		}
		return jsonSelector{kind: selectorIndex, index: index}, end + 1, nil
	}
}

func parseFilter(body string) (string, string, error) {
	inner := strings.TrimSuffix(strings.TrimPrefix(body, "?("), ")")
	inner = strings.TrimSpace(inner)
	const prefix = "@."
	if !strings.HasPrefix(inner, prefix) {
		return "", "", fmt.Errorf("unsupported filter %s", body)
	}
	parts := strings.SplitN(strings.TrimPrefix(inner, prefix), "==", 2)
	if len(parts) != 2 {
		return "", "", fmt.Errorf("unsupported filter %s", body)
	}
	field := strings.TrimSpace(parts[0])
	value := strings.TrimSpace(parts[1])
	value = strings.Trim(value, `"'`)
	if field == "" {
		return "", "", fmt.Errorf("invalid filter %s", body)
	}
	return field, value, nil
}

func findMatchingBracket(expr string, start int) int {
	depth := 0
	inQuote := byte(0)
	for i := start; i < len(expr); i++ {
		ch := expr[i]
		if inQuote != 0 {
			if ch == inQuote && expr[i-1] != '\\' {
				inQuote = 0
			}
			continue
		}
		if ch == '\'' || ch == '"' {
			inQuote = ch
			continue
		}
		if ch == '[' {
			depth++
			continue
		}
		if ch == ']' {
			depth--
			if depth == 0 {
				return i
			}
		}
	}
	return -1
}

func applySelector(current any, selector jsonSelector) ([]any, error) {
	switch selector.kind {
	case selectorField:
		switch typed := current.(type) {
		case map[string]any:
			if value, ok := typed[selector.field]; ok {
				return []any{value}, nil
			}
			return nil, nil
		case []any:
			out := make([]any, 0, len(typed))
			for _, item := range typed {
				values, err := applySelector(item, selector)
				if err != nil {
					return nil, err
				}
				out = append(out, values...)
			}
			return out, nil
		default:
			return nil, nil
		}
	case selectorIndex:
		items, ok := current.([]any)
		if !ok {
			return nil, nil
		}
		if selector.index < 0 || selector.index >= len(items) {
			return nil, nil
		}
		return []any{items[selector.index]}, nil
	case selectorWildcard:
		switch typed := current.(type) {
		case []any:
			return typed, nil
		case map[string]any:
			out := make([]any, 0, len(typed))
			for _, value := range typed {
				out = append(out, value)
			}
			return out, nil
		default:
			return nil, nil
		}
	case selectorFilter:
		items, ok := current.([]any)
		if !ok {
			return nil, nil
		}
		out := make([]any, 0, len(items))
		for _, item := range items {
			obj, ok := item.(map[string]any)
			if !ok {
				continue
			}
			if stringifyJSONValue(obj[selector.filterField]) == selector.filterValue {
				out = append(out, item)
			}
		}
		return out, nil
	default:
		return nil, fmt.Errorf("unsupported selector kind %s", selector.kind)
	}
}

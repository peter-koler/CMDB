package dispatcher

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"

	"collector-go/internal/model"
)

var dynamicPlaceholderPattern = regexp.MustCompile(`\^o\^([A-Za-z0-9_]+)\^o\^`)
var rowFieldRegex = regexp.MustCompile(`^row\d+_(.+)$`)

type cycleValueStore struct {
	mu      sync.RWMutex
	ordered map[string][]string
}

func newCycleValueStore() *cycleValueStore {
	return &cycleValueStore{ordered: map[string][]string{}}
}

func (s *cycleValueStore) Save(fields map[string]string) {
	if s == nil || len(fields) == 0 {
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for key, value := range fields {
		value = strings.TrimSpace(value)
		if value == "" {
			continue
		}
		base := key
		if matches := rowFieldRegex.FindStringSubmatch(key); len(matches) == 2 {
			base = strings.TrimSpace(matches[1])
		}
		if base == "" {
			continue
		}
		if containsString(s.ordered[base], value) {
			continue
		}
		s.ordered[base] = append(s.ordered[base], value)
	}
}

func (s *cycleValueStore) Resolve(task model.MetricsTask) []model.MetricsTask {
	if s == nil || !taskHasDynamicPlaceholders(task) {
		return []model.MetricsTask{task}
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	keys := dynamicPlaceholderKeys(task)
	if len(keys) == 0 {
		return []model.MetricsTask{task}
	}
	valueSets := make([][]string, 0, len(keys))
	for _, key := range keys {
		values := append([]string(nil), s.ordered[key]...)
		if len(values) == 0 {
			return []model.MetricsTask{}
		}
		valueSets = append(valueSets, values)
	}
	var out []model.MetricsTask
	buildTaskVariants(task, keys, valueSets, 0, map[string]string{}, &out)
	return out
}

func buildTaskVariants(base model.MetricsTask, keys []string, valueSets [][]string, idx int, bound map[string]string, out *[]model.MetricsTask) {
	if idx >= len(keys) {
		*out = append(*out, bindDynamicValues(base, bound))
		return
	}
	key := keys[idx]
	for _, value := range valueSets[idx] {
		bound[key] = value
		buildTaskVariants(base, keys, valueSets, idx+1, bound, out)
	}
	delete(bound, key)
}

func bindDynamicValues(task model.MetricsTask, bound map[string]string) model.MetricsTask {
	dup := cloneMetricsTask(task)
	for key, value := range dup.Params {
		dup.Params[key] = replaceDynamicPlaceholders(value, bound)
	}
	for idx, calc := range dup.CalculateSpecs {
		dup.CalculateSpecs[idx].Expression = replaceDynamicPlaceholders(calc.Expression, bound)
	}
	return dup
}

func replaceDynamicPlaceholders(raw string, bound map[string]string) string {
	if raw == "" || len(bound) == 0 {
		return raw
	}
	return dynamicPlaceholderPattern.ReplaceAllStringFunc(raw, func(part string) string {
		match := dynamicPlaceholderPattern.FindStringSubmatch(part)
		if len(match) != 2 {
			return part
		}
		value := strings.TrimSpace(bound[match[1]])
		if value == "" {
			return part
		}
		return value
	})
}

func taskHasDynamicPlaceholders(task model.MetricsTask) bool {
	if dynamicPlaceholderPattern.MatchString(task.Name) {
		return true
	}
	for _, value := range task.Params {
		if dynamicPlaceholderPattern.MatchString(value) {
			return true
		}
	}
	for _, calc := range task.CalculateSpecs {
		if dynamicPlaceholderPattern.MatchString(calc.Expression) {
			return true
		}
	}
	return false
}

func dynamicPlaceholderKeys(task model.MetricsTask) []string {
	seen := map[string]struct{}{}
	collect := func(raw string) {
		matches := dynamicPlaceholderPattern.FindAllStringSubmatch(raw, -1)
		for _, item := range matches {
			if len(item) != 2 {
				continue
			}
			key := strings.TrimSpace(item[1])
			if key == "" {
				continue
			}
			seen[key] = struct{}{}
		}
	}
	collect(task.Name)
	for _, value := range task.Params {
		collect(value)
	}
	for _, calc := range task.CalculateSpecs {
		collect(calc.Expression)
	}
	out := make([]string, 0, len(seen))
	for key := range seen {
		out = append(out, key)
	}
	sort.Strings(out)
	return out
}

func containsString(items []string, target string) bool {
	for _, item := range items {
		if item == target {
			return true
		}
	}
	return false
}

func mergeCollectedFields(parts []map[string]string) map[string]string {
	if len(parts) == 0 {
		return nil
	}
	out := map[string]string{}
	row := 0
	for _, part := range parts {
		if len(part) == 0 {
			continue
		}
		row++
		for key, value := range part {
			if row == 1 && !strings.HasPrefix(key, "row") {
				out[key] = value
			}
			outKey := key
			if !strings.HasPrefix(key, "row") {
				outKey = "row" + strconv.Itoa(row) + "_" + key
			}
			out[outKey] = value
		}
	}
	return out
}

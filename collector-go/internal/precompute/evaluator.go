package precompute

import (
	"fmt"
	"strconv"
	"strings"

	"collector-go/internal/model"
)

type Rule struct {
	Metrics   string
	Protocol  string
	Field     string
	Op        string
	Threshold float64
	Summary   string
}

type Evaluator struct {
	enabled bool
	rules   []Rule
}

func New(enabled bool, rules []Rule) *Evaluator {
	return &Evaluator{enabled: enabled, rules: rules}
}

func (e *Evaluator) Enabled() bool { return e != nil && e.enabled }

func (e *Evaluator) Evaluate(task model.MetricsTask, fields map[string]string) (bool, string) {
	if !e.Enabled() || len(fields) == 0 {
		return false, ""
	}
	summaries := make([]string, 0)
	for _, r := range e.rules {
		if r.Metrics != "" && r.Metrics != task.Name {
			continue
		}
		if r.Protocol != "" && r.Protocol != task.Protocol {
			continue
		}
		raw, ok := fields[r.Field]
		if !ok {
			continue
		}
		v, err := strconv.ParseFloat(strings.TrimSpace(raw), 64)
		if err != nil {
			continue
		}
		if hit(v, r.Op, r.Threshold) {
			if r.Summary != "" {
				summaries = append(summaries, r.Summary)
			} else {
				summaries = append(summaries, fmt.Sprintf("%s %s %.2f", r.Field, r.Op, r.Threshold))
			}
		}
	}
	if len(summaries) == 0 {
		return false, ""
	}
	return true, strings.Join(summaries, "; ")
}

func hit(v float64, op string, threshold float64) bool {
	switch op {
	case ">":
		return v > threshold
	case ">=":
		return v >= threshold
	case "<":
		return v < threshold
	case "<=":
		return v <= threshold
	case "==":
		return v == threshold
	case "!=":
		return v != threshold
	default:
		return false
	}
}

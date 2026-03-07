package alert

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

type Rule struct {
	ID              int64
	Name            string
	Expression      string
	DurationSeconds int
	Severity        string
	Enabled         bool
}

type State string

const (
	StateNormal  State = "normal"
	StatePending State = "pending"
	StateFiring  State = "firing"
)

type Event struct {
	RuleID      int64
	RuleName    string
	MonitorID   int64
	Severity    string
	State       State
	Expression  string
	ElapsedMs   int64
	TriggeredAt time.Time
}

type condState struct {
	firstTrueAt time.Time
	firing      bool
}

type Engine struct {
	mu     sync.Mutex
	states map[string]condState
}

func NewEngine() *Engine {
	return &Engine{states: map[string]condState{}}
}

func (e *Engine) Evaluate(rule Rule, monitorID int64, vars map[string]float64, now time.Time) (Event, bool, error) {
	if !rule.Enabled {
		return Event{}, false, nil
	}
	ok, err := evalExpression(rule.Expression, vars)
	if err != nil {
		return Event{}, false, err
	}
	key := fmt.Sprintf("%d:%d", rule.ID, monitorID)

	e.mu.Lock()
	defer e.mu.Unlock()
	st := e.states[key]
	if !ok {
		delete(e.states, key)
		return Event{
			RuleID:      rule.ID,
			RuleName:    rule.Name,
			MonitorID:   monitorID,
			Severity:    rule.Severity,
			State:       StateNormal,
			Expression:  rule.Expression,
			ElapsedMs:   0,
			TriggeredAt: now,
		}, true, nil
	}
	if st.firstTrueAt.IsZero() {
		st.firstTrueAt = now
	}
	elapsed := now.Sub(st.firstTrueAt)
	required := time.Duration(rule.DurationSeconds) * time.Second
	if required <= 0 {
		required = time.Second
	}
	if elapsed >= required {
		st.firing = true
		e.states[key] = st
		return Event{
			RuleID:      rule.ID,
			RuleName:    rule.Name,
			MonitorID:   monitorID,
			Severity:    rule.Severity,
			State:       StateFiring,
			Expression:  rule.Expression,
			ElapsedMs:   elapsed.Milliseconds(),
			TriggeredAt: now,
		}, true, nil
	}
	e.states[key] = st
	return Event{
		RuleID:      rule.ID,
		RuleName:    rule.Name,
		MonitorID:   monitorID,
		Severity:    rule.Severity,
		State:       StatePending,
		Expression:  rule.Expression,
		ElapsedMs:   elapsed.Milliseconds(),
		TriggeredAt: now,
	}, true, nil
}

func evalExpression(expr string, vars map[string]float64) (bool, error) {
	orParts := splitBy(expr, "||")
	if len(orParts) == 0 {
		return false, fmt.Errorf("empty expression")
	}
	for _, orPart := range orParts {
		andParts := splitBy(orPart, "&&")
		allTrue := true
		for _, cond := range andParts {
			ok, err := evalCondition(cond, vars)
			if err != nil {
				return false, err
			}
			if !ok {
				allTrue = false
				break
			}
		}
		if allTrue {
			return true, nil
		}
	}
	return false, nil
}

func splitBy(expr, op string) []string {
	parts := strings.Split(expr, op)
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		out = append(out, p)
	}
	return out
}

func evalCondition(cond string, vars map[string]float64) (bool, error) {
	ops := []string{">=", "<=", "==", "!=", ">", "<"}
	for _, op := range ops {
		if idx := strings.Index(cond, op); idx > 0 {
			left := strings.TrimSpace(cond[:idx])
			right := strings.TrimSpace(cond[idx+len(op):])
			return compare(left, op, right, vars)
		}
	}
	return false, fmt.Errorf("unsupported condition: %s", cond)
}

func compare(left, op, right string, vars map[string]float64) (bool, error) {
	lv, ok := vars[left]
	if !ok {
		return false, fmt.Errorf("unknown variable: %s", left)
	}
	rv, err := parseNumberOrVar(right, vars)
	if err != nil {
		return false, err
	}
	switch op {
	case ">":
		return lv > rv, nil
	case ">=":
		return lv >= rv, nil
	case "<":
		return lv < rv, nil
	case "<=":
		return lv <= rv, nil
	case "==":
		return lv == rv, nil
	case "!=":
		return lv != rv, nil
	default:
		return false, fmt.Errorf("unsupported operator: %s", op)
	}
}

func parseNumberOrVar(raw string, vars map[string]float64) (float64, error) {
	if v, ok := vars[raw]; ok {
		return v, nil
	}
	var sign float64 = 1
	s := strings.TrimSpace(raw)
	if strings.HasPrefix(s, "-") {
		sign = -1
		s = strings.TrimPrefix(s, "-")
	}
	var n float64
	if _, err := fmt.Sscanf(s, "%f", &n); err == nil {
		return sign * n, nil
	}
	return 0, fmt.Errorf("invalid number or variable: %s", raw)
}

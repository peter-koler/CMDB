package alert

import (
	"context"
	"fmt"
	"log"
	"time"
)

type PeriodicRule struct {
	ID              int64
	Name            string
	PromQL          string
	Expression      string
	DurationSeconds int
	Severity        string
	Interval        time.Duration
	Enabled         bool
}

type PeriodicResult struct {
	Rule  PeriodicRule
	Value float64
	Event Event
}

type PeriodicEvaluator struct {
	engine  *Engine
	querier VMQuerier
	rules   []PeriodicRule
	nextRun map[string]time.Time
}

func NewPeriodicEvaluator(engine *Engine, querier VMQuerier, rules []PeriodicRule) *PeriodicEvaluator {
	return &PeriodicEvaluator{
		engine:  engine,
		querier: querier,
		rules:   rules,
		nextRun: map[string]time.Time{},
	}
}

func (p *PeriodicEvaluator) RunDue(ctx context.Context, monitorID int64, now time.Time) []PeriodicResult {
	out := make([]PeriodicResult, 0)
	for _, r := range p.rules {
		if !r.Enabled {
			continue
		}
		interval := r.Interval
		if interval <= 0 {
			interval = 30 * time.Second
		}
		key := scheduleKey(monitorID, r.ID)
		nr, ok := p.nextRun[key]
		if ok && now.Before(nr) {
			continue
		}
		p.nextRun[key] = now.Add(interval)

		value, err := p.querier.QueryValue(ctx, r.PromQL, now)
		if err != nil {
			log.Printf("periodic rule query error rule=%s err=%v", r.Name, err)
			continue
		}
		ev, matched, err := p.engine.Evaluate(Rule{
			ID:              r.ID,
			Name:            r.Name,
			Expression:      r.Expression,
			DurationSeconds: r.DurationSeconds,
			Severity:        r.Severity,
			Enabled:         r.Enabled,
		}, monitorID, map[string]float64{"value": value}, now)
		if err != nil {
			log.Printf("periodic rule eval error rule=%s err=%v", r.Name, err)
			continue
		}
		if matched {
			out = append(out, PeriodicResult{Rule: r, Value: value, Event: ev})
		}
	}
	return out
}

func scheduleKey(monitorID, ruleID int64) string {
	return fmt.Sprintf("%d:%d", monitorID, ruleID)
}

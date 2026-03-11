package alert

import (
	"strings"
	"sync"
	"time"
)

type SilenceRule struct {
	ID        int64
	MatchType int
	Labels    map[string]string
	Type      int // 0 one-time, 1 cyclic
	Days      map[int]struct{}
	StartAtMs int64
	EndAtMs   int64
	// compatibility fallback
	MonitorID int64
	RuleID    int64
	StartHour int
	EndHour   int
}

type InhibitRule struct {
	ID           int64
	SourceLabels map[string]string
	TargetLabels map[string]string
	EqualLabels  []string
}

type GroupRule struct {
	ID              int64
	GroupKey        string
	MatchType       int
	GroupLabels     []string
	GroupInterval   time.Duration
	RepeatInterval  time.Duration
	DefaultGroupKey bool
}

type ReduceDecision struct {
	Emit         bool
	SuppressedBy string
	GroupedCount int
}

type Reducer struct {
	mu            sync.Mutex
	groupWindow   time.Duration
	inhibitWindow time.Duration
	silences      []SilenceRule
	inhibits      []InhibitRule
	groups        []GroupRule

	lastEmitAt      map[string]time.Time
	lastRepeatAt    map[string]time.Time
	groupedCounts   map[string]int
	activeEvents    map[string]Event
	activeUpdatedAt map[string]time.Time
}

func NewReducer(groupWindow, inhibitWindow time.Duration, silences []SilenceRule) *Reducer {
	if groupWindow <= 0 {
		groupWindow = 60 * time.Second
	}
	if inhibitWindow <= 0 {
		inhibitWindow = 5 * time.Minute
	}
	return &Reducer{
		groupWindow:     groupWindow,
		inhibitWindow:   inhibitWindow,
		silences:        silences,
		lastEmitAt:      map[string]time.Time{},
		lastRepeatAt:    map[string]time.Time{},
		groupedCounts:   map[string]int{},
		activeEvents:    map[string]Event{},
		activeUpdatedAt: map[string]time.Time{},
	}
}

func (r *Reducer) UpdateRules(groups []GroupRule, inhibits []InhibitRule, silences []SilenceRule) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.groups = groups
	r.inhibits = inhibits
	r.silences = silences
}

func (r *Reducer) Process(ev Event, now time.Time) ReduceDecision {
	r.mu.Lock()
	defer r.mu.Unlock()

	if ev.State != StateFiring {
		r.clearActive(ev)
		return ReduceDecision{Emit: false, SuppressedBy: "non_firing"}
	}
	r.markActive(ev, now)
	if r.inSilence(ev, now) {
		return ReduceDecision{Emit: false, SuppressedBy: "silence"}
	}
	if r.isInhibited(ev, now) {
		return ReduceDecision{Emit: false, SuppressedBy: "inhibit"}
	}

	key, window, repeat := r.groupReduceKey(ev)
	if at, ok := r.lastEmitAt[key]; ok && now.Sub(at) < window {
		r.groupedCounts[key]++
		return ReduceDecision{
			Emit:         false,
			SuppressedBy: "group",
			GroupedCount: r.groupedCounts[key],
		}
	}
	grouped := r.groupedCounts[key]
	r.groupedCounts[key] = 0
	if at, ok := r.lastRepeatAt[key]; ok && repeat > 0 && now.Sub(at) < repeat {
		return ReduceDecision{Emit: false, SuppressedBy: "repeat", GroupedCount: grouped}
	}
	r.lastEmitAt[key] = now
	r.lastRepeatAt[key] = now
	return ReduceDecision{Emit: true, GroupedCount: grouped}
}

func (r *Reducer) markActive(ev Event, now time.Time) {
	key := activeEventKey(ev)
	r.activeEvents[key] = ev
	r.activeUpdatedAt[key] = now
}

func (r *Reducer) clearActive(ev Event) {
	key := activeEventKey(ev)
	delete(r.activeEvents, key)
	delete(r.activeUpdatedAt, key)
}

func (r *Reducer) isInhibited(ev Event, now time.Time) bool {
	if len(r.inhibits) == 0 {
		sev := strings.ToLower(strings.TrimSpace(ev.Severity))
		if sev == "warning" || sev == "info" {
			for k, active := range r.activeEvents {
				if active.MonitorID != ev.MonitorID {
					continue
				}
				if strings.ToLower(strings.TrimSpace(active.Severity)) != "critical" {
					continue
				}
				if ts, ok := r.activeUpdatedAt[k]; ok && now.Sub(ts) <= r.inhibitWindow {
					return true
				}
			}
		}
		return false
	}
	target := eventLabels(ev)
	for key, sourceEvent := range r.activeEvents {
		ts, ok := r.activeUpdatedAt[key]
		if !ok || now.Sub(ts) > r.inhibitWindow {
			continue
		}
		source := eventLabels(sourceEvent)
		for _, rule := range r.inhibits {
			if !matchLabels(rule.TargetLabels, target) {
				continue
			}
			if !matchLabels(rule.SourceLabels, source) {
				continue
			}
			if !matchEqualLabels(rule.EqualLabels, source, target) {
				continue
			}
			return true
		}
	}
	return false
}

func (r *Reducer) inSilence(ev Event, now time.Time) bool {
	hour := now.Hour()
	event := eventLabels(ev)
	for _, s := range r.silences {
		if s.MatchType == 1 && !matchLabels(s.Labels, event) {
			continue
		}
		if s.MonitorID != 0 && s.MonitorID != ev.MonitorID {
			continue
		}
		if s.RuleID != 0 && s.RuleID != ev.RuleID {
			continue
		}
		if s.Type == 0 && s.StartAtMs > 0 && s.EndAtMs > 0 {
			nowMs := now.UnixMilli()
			if nowMs >= s.StartAtMs && nowMs <= s.EndAtMs {
				return true
			}
			continue
		}
		if s.Type == 1 && len(s.Days) > 0 {
			weekday := int(now.Weekday())
			if weekday == 0 {
				weekday = 7
			}
			if _, ok := s.Days[weekday]; !ok {
				continue
			}
			startHour, endHour := extractHourFromMs(s.StartAtMs), extractHourFromMs(s.EndAtMs)
			if inHourRange(hour, startHour, endHour) {
				return true
			}
			continue
		}
		if inHourRange(hour, s.StartHour, s.EndHour) {
			return true
		}
	}
	return false
}

func (r *Reducer) groupReduceKey(ev Event) (string, time.Duration, time.Duration) {
	labels := eventLabels(ev)
	for _, g := range r.groups {
		if g.MatchType == 1 && len(g.GroupLabels) > 0 {
			matched := true
			for _, key := range g.GroupLabels {
				if strings.TrimSpace(labels[key]) == "" {
					matched = false
					break
				}
			}
			if !matched {
				continue
			}
		}
		base := strings.TrimSpace(g.GroupKey)
		if base == "" {
			base = reduceKey(ev)
		}
		key := base
		for _, lk := range g.GroupLabels {
			key += "|" + lk + "=" + labels[lk]
		}
		window := g.GroupInterval
		if window <= 0 {
			window = r.groupWindow
		}
		return key, window, g.RepeatInterval
	}
	return reduceKey(ev), r.groupWindow, 0
}

func reduceKey(ev Event) string {
	return itoa(ev.RuleID) + ":" + itoa(ev.MonitorID) + ":" + ev.Severity
}

func activeEventKey(ev Event) string {
	return itoa(ev.RuleID) + ":" + itoa(ev.MonitorID)
}

func eventLabels(ev Event) map[string]string {
	out := map[string]string{
		"rule_id":    itoa(ev.RuleID),
		"monitor_id": itoa(ev.MonitorID),
		"severity":   strings.TrimSpace(ev.Severity),
		"rule_name":  strings.TrimSpace(ev.RuleName),
		"app":        strings.TrimSpace(ev.App),
		"instance":   strings.TrimSpace(ev.Instance),
	}
	for k, v := range ev.Labels {
		key := strings.TrimSpace(k)
		if key == "" {
			continue
		}
		out[key] = strings.TrimSpace(v)
	}
	return out
}

func matchLabels(expected map[string]string, actual map[string]string) bool {
	if len(expected) == 0 {
		return true
	}
	for key, val := range expected {
		k := strings.TrimSpace(key)
		if k == "" {
			continue
		}
		if strings.TrimSpace(actual[k]) != strings.TrimSpace(val) {
			return false
		}
	}
	return true
}

func matchEqualLabels(keys []string, source map[string]string, target map[string]string) bool {
	for _, key := range keys {
		k := strings.TrimSpace(key)
		if k == "" {
			continue
		}
		if source[k] == "" || target[k] == "" {
			return false
		}
		if source[k] != target[k] {
			return false
		}
	}
	return true
}

func extractHourFromMs(ms int64) int {
	if ms <= 0 {
		return 0
	}
	t := time.UnixMilli(ms)
	return t.Hour()
}

func inHourRange(hour, startHour, endHour int) bool {
	if startHour == 0 && endHour == 0 {
		return false
	}
	if startHour <= endHour {
		return hour >= startHour && hour < endHour
	}
	return hour >= startHour || hour < endHour
}

func itoa(v int64) string {
	if v == 0 {
		return "0"
	}
	sign := ""
	if v < 0 {
		sign = "-"
		v = -v
	}
	buf := [20]byte{}
	i := len(buf)
	for v > 0 {
		i--
		buf[i] = byte('0' + (v % 10))
		v /= 10
	}
	return sign + string(buf[i:])
}

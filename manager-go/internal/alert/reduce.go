package alert

import "time"

type SilenceRule struct {
	MonitorID int64
	RuleID    int64
	StartHour int
	EndHour   int
}

type ReduceDecision struct {
	Emit         bool
	SuppressedBy string
	GroupedCount int
}

type Reducer struct {
	groupWindow   time.Duration
	inhibitWindow time.Duration
	silences      []SilenceRule

	lastEmitAt      map[string]time.Time
	groupedCounts   map[string]int
	activeCriticals map[int64]time.Time
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
		groupedCounts:   map[string]int{},
		activeCriticals: map[int64]time.Time{},
	}
}

func (r *Reducer) Process(ev Event, now time.Time) ReduceDecision {
	if ev.State != StateFiring {
		return ReduceDecision{Emit: false, SuppressedBy: "non_firing"}
	}
	if r.inSilence(ev, now) {
		return ReduceDecision{Emit: false, SuppressedBy: "silence"}
	}

	if ev.Severity == "critical" {
		r.activeCriticals[ev.MonitorID] = now
	}
	if (ev.Severity == "warning" || ev.Severity == "info") && r.hasActiveCritical(ev.MonitorID, now) {
		return ReduceDecision{Emit: false, SuppressedBy: "inhibit"}
	}

	key := reduceKey(ev)
	if at, ok := r.lastEmitAt[key]; ok && now.Sub(at) < r.groupWindow {
		r.groupedCounts[key]++
		return ReduceDecision{
			Emit:         false,
			SuppressedBy: "group",
			GroupedCount: r.groupedCounts[key],
		}
	}
	grouped := r.groupedCounts[key]
	r.groupedCounts[key] = 0
	r.lastEmitAt[key] = now
	return ReduceDecision{Emit: true, GroupedCount: grouped}
}

func (r *Reducer) hasActiveCritical(monitorID int64, now time.Time) bool {
	at, ok := r.activeCriticals[monitorID]
	if !ok {
		return false
	}
	return now.Sub(at) <= r.inhibitWindow
}

func (r *Reducer) inSilence(ev Event, now time.Time) bool {
	hour := now.Hour()
	for _, s := range r.silences {
		if s.MonitorID != 0 && s.MonitorID != ev.MonitorID {
			continue
		}
		if s.RuleID != 0 && s.RuleID != ev.RuleID {
			continue
		}
		if s.StartHour <= s.EndHour {
			if hour >= s.StartHour && hour < s.EndHour {
				return true
			}
		} else {
			// cross-day silence, e.g. 23 -> 6
			if hour >= s.StartHour || hour < s.EndHour {
				return true
			}
		}
	}
	return false
}

func reduceKey(ev Event) string {
	return itoa(ev.RuleID) + ":" + itoa(ev.MonitorID) + ":" + ev.Severity
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

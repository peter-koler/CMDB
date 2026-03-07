package scheduler

import (
	"context"
	"sync"
	"sync/atomic"
	"time"
)

type TaskFunc func(context.Context)

type entry struct {
	id        int64
	interval  time.Duration
	rounds    int64
	nextDue   time.Time
	cancelled atomic.Bool
	f         TaskFunc
}

type Stats struct {
	TotalRuns      int64
	ActiveTasks    int64
	MaxDriftMs     int64
	AvgDriftMs     int64
	LastDriftMs    int64
	DroppedDueRuns int64
}

type Wheel struct {
	tick   time.Duration
	slots  []map[int64]*entry
	cursor int

	mu     sync.Mutex
	tasks  map[int64]*entry
	nextID int64
	stopCh chan struct{}
	doneCh chan struct{}

	totalRuns   atomic.Int64
	sumDriftNs  atomic.Int64
	maxDriftNs  atomic.Int64
	lastDriftNs atomic.Int64
	lateRuns    atomic.Int64
}

func NewWheel(tick time.Duration, size int) *Wheel {
	if tick <= 0 {
		tick = time.Second
	}
	if size < 64 {
		size = 64
	}
	slots := make([]map[int64]*entry, size)
	for i := range slots {
		slots[i] = make(map[int64]*entry)
	}
	return &Wheel{
		tick:   tick,
		slots:  slots,
		tasks:  make(map[int64]*entry),
		stopCh: make(chan struct{}),
		doneCh: make(chan struct{}),
	}
}

func (w *Wheel) Start(ctx context.Context) {
	ticker := time.NewTicker(w.tick)
	defer func() {
		ticker.Stop()
		close(w.doneCh)
	}()
	for {
		select {
		case <-ctx.Done():
			return
		case <-w.stopCh:
			return
		case <-ticker.C:
			w.onTick(ctx)
		}
	}
}

func (w *Wheel) Stop() {
	close(w.stopCh)
	<-w.doneCh
}

func (w *Wheel) ScheduleEvery(interval time.Duration, f TaskFunc) int64 {
	if interval < w.tick {
		interval = w.tick
	}
	id := atomic.AddInt64(&w.nextID, 1)
	now := time.Now()
	e := &entry{id: id, interval: interval, nextDue: now.Add(interval), f: f}

	w.mu.Lock()
	defer w.mu.Unlock()
	w.tasks[id] = e
	w.placeLocked(e)
	return id
}

func (w *Wheel) Cancel(id int64) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if e, ok := w.tasks[id]; ok {
		e.cancelled.Store(true)
		delete(w.tasks, id)
	}
}

func (w *Wheel) placeLocked(e *entry) {
	ticks := int64(e.interval / w.tick)
	if ticks < 1 {
		ticks = 1
	}
	slot := (w.cursor + int(ticks)%len(w.slots)) % len(w.slots)
	rounds := ticks / int64(len(w.slots))
	if int64(slot) <= int64(w.cursor) && rounds > 0 {
		rounds--
	}
	e.rounds = rounds
	w.slots[slot][e.id] = e
}

func (w *Wheel) onTick(ctx context.Context) {
	now := time.Now()
	w.mu.Lock()
	bucket := w.slots[w.cursor]
	w.slots[w.cursor] = make(map[int64]*entry)
	w.cursor = (w.cursor + 1) % len(w.slots)
	w.mu.Unlock()

	for _, e := range bucket {
		if e.cancelled.Load() {
			continue
		}
		if e.rounds > 0 {
			e.rounds--
			w.mu.Lock()
			w.slots[(w.cursor-1+len(w.slots))%len(w.slots)][e.id] = e
			w.mu.Unlock()
			continue
		}

		e.f(ctx)
		w.recordDrift(now.Sub(e.nextDue))
		nextDue := e.nextDue.Add(e.interval)
		if nextDue.Before(now) {
			w.lateRuns.Add(1)
			nextDue = now.Add(e.interval)
		}
		e.nextDue = nextDue

		w.mu.Lock()
		if !e.cancelled.Load() {
			w.placeLocked(e)
		}
		w.mu.Unlock()
	}
}

func (w *Wheel) recordDrift(d time.Duration) {
	if d < 0 {
		d = 0
	}
	ns := d.Nanoseconds()
	w.totalRuns.Add(1)
	w.sumDriftNs.Add(ns)
	w.lastDriftNs.Store(ns)
	for {
		old := w.maxDriftNs.Load()
		if ns <= old {
			break
		}
		if w.maxDriftNs.CompareAndSwap(old, ns) {
			break
		}
	}
}

func (w *Wheel) Stats() Stats {
	total := w.totalRuns.Load()
	sumNs := w.sumDriftNs.Load()
	maxNs := w.maxDriftNs.Load()
	lastNs := w.lastDriftNs.Load()
	w.mu.Lock()
	active := int64(len(w.tasks))
	w.mu.Unlock()
	avgMs := int64(0)
	if total > 0 {
		avgMs = (sumNs / total) / int64(time.Millisecond)
	}
	return Stats{
		TotalRuns:      total,
		ActiveTasks:    active,
		MaxDriftMs:     maxNs / int64(time.Millisecond),
		AvgDriftMs:     avgMs,
		LastDriftMs:    lastNs / int64(time.Millisecond),
		DroppedDueRuns: w.lateRuns.Load(),
	}
}

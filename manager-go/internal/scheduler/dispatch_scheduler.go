package scheduler

import (
	"context"
	"time"

	"manager-go/internal/store"
)

type DispatchScheduler struct {
	store   *store.MonitorStore
	tick    time.Duration
	nextRun map[int64]time.Time
	out     chan int64
}

func NewDispatchScheduler(st *store.MonitorStore, tick time.Duration, out chan int64) *DispatchScheduler {
	if tick <= 0 {
		tick = time.Second
	}
	return &DispatchScheduler{
		store:   st,
		tick:    tick,
		nextRun: map[int64]time.Time{},
		out:     out,
	}
}

func (s *DispatchScheduler) Start(ctx context.Context) {
	ticker := time.NewTicker(s.tick)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case now := <-ticker.C:
			s.onTick(now)
		}
	}
}

func (s *DispatchScheduler) onTick(now time.Time) {
	items := s.store.List()
	active := make(map[int64]struct{}, len(items))
	for _, m := range items {
		if !m.Enabled {
			delete(s.nextRun, m.ID)
			continue
		}
		active[m.ID] = struct{}{}
		nr, ok := s.nextRun[m.ID]
		if !ok {
			nr = now
		}
		if !now.Before(nr) {
			select {
			case s.out <- m.ID:
			default:
			}
			s.nextRun[m.ID] = now.Add(time.Duration(m.IntervalSeconds) * time.Second)
		} else {
			s.nextRun[m.ID] = nr
		}
	}
	for id := range s.nextRun {
		if _, ok := active[id]; !ok {
			delete(s.nextRun, id)
		}
	}
}

package dispatch

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"sync"
	"time"

	"manager-go/internal/model"
)

type RetryPolicy struct {
	MaxAttempts int
	Backoff     []time.Duration
}

type Result struct {
	Key    string            `json:"key"`
	Status map[string]string `json:"status"`
	Errors map[string]string `json:"errors,omitempty"`
}

type Dispatcher struct {
	sinks  []Sink
	retry  RetryPolicy
	idem   *idemCache
	mu     sync.Mutex
	totals map[string]int64
	failed map[string]int64
}

func NewDispatcher(sinks []Sink, retry RetryPolicy, idemLimit int) *Dispatcher {
	if retry.MaxAttempts <= 0 {
		retry.MaxAttempts = 3
	}
	return &Dispatcher{
		sinks:  sinks,
		retry:  retry,
		idem:   newIdemCache(idemLimit),
		totals: map[string]int64{},
		failed: map[string]int64{},
	}
}

func (d *Dispatcher) Dispatch(ctx context.Context, point model.MetricPoint) Result {
	key := idempotencyKey(point)
	res := Result{
		Key:    key,
		Status: map[string]string{},
		Errors: map[string]string{},
	}
	var wg sync.WaitGroup
	var mu sync.Mutex

	for _, sink := range d.sinks {
		s := sink
		wg.Add(1)
		go func() {
			defer wg.Done()
			name := s.Name()
			d.mu.Lock()
			d.totals[name]++
			d.mu.Unlock()

			if d.idem.Seen(name, key) {
				mu.Lock()
				res.Status[name] = "deduplicated"
				mu.Unlock()
				return
			}

			err := d.writeWithRetry(ctx, s, key, point)
			mu.Lock()
			defer mu.Unlock()
			if err != nil {
				res.Status[name] = "failed"
				res.Errors[name] = err.Error()
				d.mu.Lock()
				d.failed[name]++
				d.mu.Unlock()
				return
			}
			d.idem.Mark(name, key)
			res.Status[name] = "ok"
		}()
	}
	wg.Wait()
	if len(res.Errors) == 0 {
		res.Errors = nil
	}
	return res
}

func (d *Dispatcher) writeWithRetry(ctx context.Context, sink Sink, key string, point model.MetricPoint) error {
	var last error
	for attempt := 1; attempt <= d.retry.MaxAttempts; attempt++ {
		if attempt > 1 {
			backoff := d.backoffFor(attempt - 2)
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
			}
		}
		if err := sink.Write(ctx, key, point); err != nil {
			last = err
			continue
		}
		return nil
	}
	return last
}

func (d *Dispatcher) backoffFor(i int) time.Duration {
	if len(d.retry.Backoff) == 0 {
		return 20 * time.Millisecond
	}
	if i >= len(d.retry.Backoff) {
		return d.retry.Backoff[len(d.retry.Backoff)-1]
	}
	return d.retry.Backoff[i]
}

func (d *Dispatcher) SuccessRate(name string) float64 {
	d.mu.Lock()
	defer d.mu.Unlock()
	total := d.totals[name]
	if total == 0 {
		return 1.0
	}
	fail := d.failed[name]
	ok := total - fail
	return float64(ok) / float64(total)
}

func idempotencyKey(point model.MetricPoint) string {
	payload, _ := json.Marshal(point)
	sum := sha1.Sum(payload)
	return hex.EncodeToString(sum[:])
}

type idemCache struct {
	mu    sync.Mutex
	limit int
	order map[string][]string
	seen  map[string]map[string]struct{}
}

func newIdemCache(limit int) *idemCache {
	if limit <= 0 {
		limit = 5000
	}
	return &idemCache{
		limit: limit,
		order: map[string][]string{},
		seen:  map[string]map[string]struct{}{},
	}
}

func (c *idemCache) Seen(sink, key string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	ks := c.seen[sink]
	if ks == nil {
		return false
	}
	_, ok := ks[key]
	return ok
}

func (c *idemCache) Mark(sink, key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.seen[sink] == nil {
		c.seen[sink] = map[string]struct{}{}
	}
	if _, ok := c.seen[sink][key]; ok {
		return
	}
	c.seen[sink][key] = struct{}{}
	c.order[sink] = append(c.order[sink], key)
	if len(c.order[sink]) > c.limit {
		old := c.order[sink][0]
		c.order[sink] = c.order[sink][1:]
		delete(c.seen[sink], old)
	}
}

package protocol

import (
	"context"
	"errors"
	"sync"

	"collector-go/internal/model"
)

var ErrProtocolNotFound = errors.New("protocol not found")

type Collector interface {
	Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error)
}

var (
	mu       sync.RWMutex
	registry = map[string]Collector{}
)

func Register(name string, collector Collector) {
	mu.Lock()
	defer mu.Unlock()
	registry[name] = collector
}

func Get(name string) (Collector, error) {
	mu.RLock()
	defer mu.RUnlock()
	c, ok := registry[name]
	if !ok {
		return nil, ErrProtocolNotFound
	}
	return c, nil
}

func Snapshot() map[string]Collector {
	mu.RLock()
	defer mu.RUnlock()
	out := make(map[string]Collector, len(registry))
	for k, v := range registry {
		out[k] = v
	}
	return out
}

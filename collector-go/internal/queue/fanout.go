package queue

import (
	"context"

	"collector-go/internal/model"
)

// FanoutQueue keeps an in-memory primary queue for local consumers
// and forwards copies to extra sinks (e.g. Kafka).
type FanoutQueue struct {
	primary *MemoryQueue
	sinks   []ResultQueue
}

func NewFanoutQueue(primary *MemoryQueue, sinks ...ResultQueue) *FanoutQueue {
	return &FanoutQueue{primary: primary, sinks: sinks}
}

func (q *FanoutQueue) Push(ctx context.Context, result model.Result) error {
	if err := q.primary.Push(ctx, result); err != nil {
		return err
	}
	for _, sink := range q.sinks {
		_ = sink.Push(ctx, result)
	}
	return nil
}

func (q *FanoutQueue) Pop(ctx context.Context) (model.Result, error) {
	return q.primary.Pop(ctx)
}

func (q *FanoutQueue) Len() int {
	return q.primary.Len()
}

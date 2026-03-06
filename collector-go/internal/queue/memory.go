package queue

import (
	"context"

	"collector-go/internal/model"
)

type MemoryQueue struct {
	ch chan model.Result
}

func NewMemoryQueue(size int) *MemoryQueue {
	if size <= 0 {
		size = 1024
	}
	return &MemoryQueue{ch: make(chan model.Result, size)}
}

func (q *MemoryQueue) Push(ctx context.Context, result model.Result) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	case q.ch <- result:
		return nil
	default:
		return ErrQueueFull
	}
}

func (q *MemoryQueue) Pop(ctx context.Context) (model.Result, error) {
	select {
	case <-ctx.Done():
		return model.Result{}, ctx.Err()
	case item := <-q.ch:
		return item, nil
	}
}

func (q *MemoryQueue) Len() int {
	return len(q.ch)
}

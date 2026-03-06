package queue

import (
	"context"
	"errors"

	"collector-go/internal/model"
)

var ErrQueueFull = errors.New("queue is full")

type ResultQueue interface {
	Push(ctx context.Context, result model.Result) error
	Pop(ctx context.Context) (model.Result, error)
	Len() int
}

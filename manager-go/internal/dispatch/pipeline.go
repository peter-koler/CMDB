package dispatch

import (
	"context"

	"manager-go/internal/model"
)

type Pipeline struct {
	dispatcher *Dispatcher
	queue      chan model.MetricPoint
	workers    int
}

func NewPipeline(dispatcher *Dispatcher, queueSize int, workers int) *Pipeline {
	if queueSize <= 0 {
		queueSize = 1024
	}
	if workers <= 0 {
		workers = 4
	}
	return &Pipeline{
		dispatcher: dispatcher,
		queue:      make(chan model.MetricPoint, queueSize),
		workers:    workers,
	}
}

func (p *Pipeline) Start(ctx context.Context) {
	for i := 0; i < p.workers; i++ {
		go func() {
			for {
				select {
				case <-ctx.Done():
					return
				case point := <-p.queue:
					_ = p.dispatcher.Dispatch(ctx, point)
				}
			}
		}()
	}
}

func (p *Pipeline) Submit(point model.MetricPoint) bool {
	select {
	case p.queue <- point:
		return true
	default:
		return false
	}
}

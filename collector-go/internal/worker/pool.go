package worker

import (
	"context"
	"errors"
	"sync"
)

var ErrBusy = errors.New("worker pool queue is full")

type Task func(context.Context)

type Pool struct {
	workers int
	queue   chan Task
	wg      sync.WaitGroup
}

func New(workers, queueSize int) *Pool {
	if workers < 1 {
		workers = 1
	}
	if queueSize < workers {
		queueSize = workers * 2
	}
	return &Pool{workers: workers, queue: make(chan Task, queueSize)}
}

func (p *Pool) Start(ctx context.Context) {
	for i := 0; i < p.workers; i++ {
		p.wg.Add(1)
		go func() {
			defer p.wg.Done()
			for {
				select {
				case <-ctx.Done():
					return
				case task, ok := <-p.queue:
					if !ok {
						return
					}
					task(ctx)
				}
			}
		}()
	}
}

func (p *Pool) Submit(task Task) error {
	select {
	case p.queue <- task:
		return nil
	default:
		return ErrBusy
	}
}

func (p *Pool) Stop() {
	close(p.queue)
	p.wg.Wait()
}

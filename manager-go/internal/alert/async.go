package alert

import (
	"context"
	"log"
	"sync/atomic"
	"time"
)

type NotifyTask struct {
	ID        int64
	Event     Event
	Channel   string
	Attempt   int
	CreatedAt time.Time
}

type Sender interface {
	Send(ctx context.Context, task NotifyTask) error
}

type Queues struct {
	alertQueue  chan Event
	notifyQueue chan NotifyTask
	retryQueue  chan NotifyTask

	retryDelays []time.Duration
	maxRetry    int
	nextID      atomic.Int64
}

func NewQueues(size int, retryDelays []time.Duration, maxRetry int) *Queues {
	if size <= 0 {
		size = 1024
	}
	if len(retryDelays) == 0 {
		retryDelays = []time.Duration{time.Minute, 5 * time.Minute, 15 * time.Minute, time.Hour}
	}
	if maxRetry <= 0 {
		maxRetry = 5
	}
	return &Queues{
		alertQueue:  make(chan Event, size),
		notifyQueue: make(chan NotifyTask, size),
		retryQueue:  make(chan NotifyTask, size),
		retryDelays: retryDelays,
		maxRetry:    maxRetry,
	}
}

func (q *Queues) EnqueueAlert(ev Event) bool {
	select {
	case q.alertQueue <- ev:
		return true
	default:
		return false
	}
}

func (q *Queues) Start(ctx context.Context, sender Sender, alertWorkers, notifyWorkers int) {
	if alertWorkers <= 0 {
		alertWorkers = 2
	}
	if notifyWorkers <= 0 {
		notifyWorkers = 2
	}
	for i := 0; i < alertWorkers; i++ {
		go q.alertWorker(ctx)
	}
	for i := 0; i < notifyWorkers; i++ {
		go q.notifyWorker(ctx, sender)
	}
	go q.retryWorker(ctx)
}

func (q *Queues) alertWorker(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case ev := <-q.alertQueue:
			task := NotifyTask{
				ID:        q.nextID.Add(1),
				Event:     ev,
				Channel:   "webhook",
				Attempt:   0,
				CreatedAt: time.Now(),
			}
			select {
			case q.notifyQueue <- task:
			default:
				log.Printf("notify queue full drop event rule=%s monitor=%d", ev.RuleName, ev.MonitorID)
			}
		}
	}
}

func (q *Queues) notifyWorker(ctx context.Context, sender Sender) {
	for {
		select {
		case <-ctx.Done():
			return
		case task := <-q.notifyQueue:
			if err := sender.Send(ctx, task); err != nil {
				task.Attempt++
				if task.Attempt >= q.maxRetry {
					log.Printf("notify max retry reached task=%d rule=%s monitor=%d -> manual handling",
						task.ID, task.Event.RuleName, task.Event.MonitorID)
					continue
				}
				select {
				case q.retryQueue <- task:
				default:
					log.Printf("retry queue full drop task=%d", task.ID)
				}
			}
		}
	}
}

func (q *Queues) retryWorker(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case task := <-q.retryQueue:
			delay := q.retryDelay(task.Attempt - 1)
			timer := time.NewTimer(delay)
			select {
			case <-ctx.Done():
				timer.Stop()
				return
			case <-timer.C:
			}
			select {
			case q.notifyQueue <- task:
			default:
				log.Printf("notify queue full after retry task=%d", task.ID)
			}
		}
	}
}

func (q *Queues) retryDelay(attemptIndex int) time.Duration {
	if attemptIndex < 0 {
		attemptIndex = 0
	}
	if attemptIndex >= len(q.retryDelays) {
		return q.retryDelays[len(q.retryDelays)-1]
	}
	return q.retryDelays[attemptIndex]
}

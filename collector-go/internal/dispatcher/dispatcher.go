package dispatcher

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/pipeline"
	"collector-go/internal/protocol"
	"collector-go/internal/queue"
	"collector-go/internal/scheduler"
	"collector-go/internal/worker"
)

type PrecomputeEvaluator interface {
	Enabled() bool
	Evaluate(task model.MetricsTask, fields map[string]string) (bool, string)
}

type Dispatcher struct {
	wheel *scheduler.Wheel
	pool  *worker.Pool
	queue queue.ResultQueue

	mu          sync.Mutex
	jobTimers   map[int64]int64
	jobs        map[int64]model.Job
	defaultWait time.Duration
	dropped     atomic.Int64
	precompute  PrecomputeEvaluator
}

func New(wheel *scheduler.Wheel, pool *worker.Pool, q queue.ResultQueue) *Dispatcher {
	return &Dispatcher{
		wheel:       wheel,
		pool:        pool,
		queue:       q,
		jobTimers:   map[int64]int64{},
		jobs:        map[int64]model.Job{},
		defaultWait: 5 * time.Second,
	}
}

func (d *Dispatcher) SetPrecomputeEvaluator(ev PrecomputeEvaluator) {
	d.precompute = ev
}

func (d *Dispatcher) RegisterJob(job model.Job) {
	d.RemoveJob(job.ID)
	tasks := append([]model.MetricsTask(nil), job.Tasks...)
	// HertzBeat-like semantics: smaller priority means higher priority.
	sort.Slice(tasks, func(i, j int) bool { return tasks[i].Priority < tasks[j].Priority })
	job.Tasks = tasks
	id := d.wheel.ScheduleEvery(job.Interval, func(ctx context.Context) {
		d.submitWithRetry(ctx, func(ctx context.Context) {
			d.executeJobCycle(ctx, job)
		}, job, model.MetricsTask{Name: "job-cycle", Protocol: "dispatcher"})
	})

	d.mu.Lock()
	d.jobTimers[job.ID] = id
	d.jobs[job.ID] = job
	d.mu.Unlock()
}

func (d *Dispatcher) RemoveJob(jobID int64) {
	d.mu.Lock()
	id, ok := d.jobTimers[jobID]
	delete(d.jobTimers, jobID)
	delete(d.jobs, jobID)
	d.mu.Unlock()
	if ok {
		d.wheel.Cancel(id)
	}
}

func (d *Dispatcher) DroppedResults() int64 {
	return d.dropped.Load()
}

func (d *Dispatcher) executeJobCycle(ctx context.Context, job model.Job) {
	if len(job.Tasks) == 0 {
		return
	}
	for i := 0; i < len(job.Tasks); {
		p := job.Tasks[i].Priority
		j := i + 1
		for j < len(job.Tasks) && job.Tasks[j].Priority == p {
			j++
		}
		var wg sync.WaitGroup
		for _, t := range job.Tasks[i:j] {
			task := t
			wg.Add(1)
			go func() {
				defer wg.Done()
				d.executeTask(ctx, job, task)
			}()
		}
		wg.Wait()
		i = j
	}
}

func (d *Dispatcher) submitWithRetry(ctx context.Context, task worker.Task, job model.Job, meta model.MetricsTask) {
	backoffs := []time.Duration{0, 20 * time.Millisecond, 50 * time.Millisecond}
	for i, b := range backoffs {
		if b > 0 {
			select {
			case <-ctx.Done():
				return
			case <-time.After(b):
			}
		}
		if err := d.pool.Submit(task); err == nil {
			return
		} else if !errors.Is(err, worker.ErrBusy) {
			break
		}
		if i == len(backoffs)-1 {
			d.pushResult(ctx, model.Result{
				JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: meta.Name,
				Protocol: meta.Protocol, Time: time.Now(), Success: false, Code: model.CodeWorkerBusy,
				Message: "worker pool queue is full",
			})
		}
	}
}

func (d *Dispatcher) executeTask(ctx context.Context, job model.Job, task model.MetricsTask) {
	collector, err := protocol.Get(task.Protocol)
	if err != nil {
		d.pushResult(ctx, model.Result{
			JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: task.Name,
			Protocol: task.Protocol, Time: time.Now(), Success: false, Code: model.CodeProtocolMissing, Message: err.Error(),
		})
		return
	}
	ctx2 := ctx
	if task.Timeout > 0 {
		cancelCtx, cancel := context.WithTimeout(ctx, task.Timeout)
		defer cancel()
		ctx2 = cancelCtx
	}
	start := time.Now()
	fields, msg, err := collector.Collect(ctx2, task)
	latency := time.Since(start)
	if err == nil {
		fields, err = pipeline.Apply(fields, task.Transform)
	}
	res := model.Result{
		JobID: job.ID, MonitorID: job.Monitor, App: job.App, Metrics: task.Name,
		Protocol: task.Protocol, Time: time.Now(), Success: err == nil, Code: model.CodeSuccess, Message: msg,
		Fields: fields, RawLatency: latency,
	}
	if err != nil {
		res.Code = model.CodeCollectFailed
		if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
			res.Code = model.CodeTimeout
		}
		res.Message = fmt.Sprintf("%s: %v", msg, err)
	}
	if err == nil && d.precompute != nil && d.precompute.Enabled() {
		triggered, summary := d.precompute.Evaluate(task, fields)
		if triggered {
			if res.Fields == nil {
				res.Fields = map[string]string{}
			}
			res.Fields["__precompute_triggered__"] = "true"
			res.Fields["__precompute_summary__"] = summary
		}
	}
	d.pushResult(ctx, res)
}

func (d *Dispatcher) pushResult(ctx context.Context, result model.Result) {
	pushCtx, cancel := context.WithTimeout(ctx, d.defaultWait)
	defer cancel()
	if err := d.queue.Push(pushCtx, result); err != nil {
		d.dropped.Add(1)
		log.Printf("push result failed code=%s job=%d metrics=%s err=%v", model.CodeQueueFailed, result.JobID, result.Metrics, err)
	}
}

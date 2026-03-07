package main

import (
	"context"
	"log"
	"math"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/dispatch"
	"manager-go/internal/httpapi"
	"manager-go/internal/model"
	"manager-go/internal/scheduler"
	"manager-go/internal/store"
)

func main() {
	st := store.NewMonitorStore()
	api := httpapi.NewServer(st)

	dispatchCh := make(chan int64, 1024)
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	sched := scheduler.NewDispatchScheduler(st, 500*time.Millisecond, dispatchCh)
	go sched.Start(ctx)

	redisAddr := getenv("REDIS_ADDR", "127.0.0.1:6379")
	vmURL := getenv("VICTORIA_METRICS_URL", "http://127.0.0.1:8428")
	dispatcher := dispatch.NewDispatcher(
		[]dispatch.Sink{
			dispatch.NewRedisSink(redisAddr, "monitor:metrics", 800*time.Millisecond),
			dispatch.NewVMSink(vmURL, 800*time.Millisecond),
		},
		dispatch.RetryPolicy{
			MaxAttempts: 3,
			Backoff:     []time.Duration{20 * time.Millisecond, 50 * time.Millisecond},
		},
		10000,
	)
	pipeline := dispatch.NewPipeline(dispatcher, 2048, 4)
	pipeline.Start(ctx)
	alertEngine := alert.NewEngine()
	alertRules := []alert.Rule{
		{
			ID:              1,
			Name:            "manager_dispatch_tick_high",
			Expression:      "manager_dispatch_tick > 900",
			DurationSeconds: 5,
			Severity:        "warning",
			Enabled:         true,
		},
	}
	periodicEvaluator := alert.NewPeriodicEvaluator(
		alertEngine,
		alert.NewVMClient(vmURL, 1200*time.Millisecond),
		[]alert.PeriodicRule{
			{
				ID:              1001,
				Name:            "manager_dispatch_tick_avg_5m_high",
				PromQL:          `avg_over_time(manager_dispatch_tick[5m])`,
				Expression:      "value > 800",
				DurationSeconds: 300,
				Severity:        "warning",
				Interval:        30 * time.Second,
				Enabled:         true,
			},
		},
	)
	reducer := alert.NewReducer(
		60*time.Second,
		5*time.Minute,
		[]alert.SilenceRule{
			// Example: silence monitor 0/rule 0 not configured by default.
		},
	)
	queues := alert.NewQueues(
		2048,
		[]time.Duration{time.Minute, 5 * time.Minute, 15 * time.Minute, time.Hour},
		5,
	)
	queues.Start(ctx, logSender{}, 2, 2)

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case id := <-dispatchCh:
				m, err := st.Get(id)
				if err != nil {
					log.Printf("dispatch skip monitor id=%d err=%v", id, err)
					continue
				}
				point := makePoint(m)
				vars := pointVars(point)
				for _, rule := range alertRules {
					ev, matched, err := alertEngine.Evaluate(rule, m.ID, vars, time.Now())
					if err != nil {
						log.Printf("alert eval error rule=%s monitor=%d err=%v", rule.Name, m.ID, err)
						continue
					}
					if matched && ev.State == alert.StateFiring {
						d := reducer.Process(ev, time.Now())
						if d.Emit {
							log.Printf("alert firing rule=%s monitor=%d severity=%s elapsed_ms=%d expr=%s grouped=%d",
								ev.RuleName, ev.MonitorID, ev.Severity, ev.ElapsedMs, ev.Expression, d.GroupedCount)
							if !queues.EnqueueAlert(ev) {
								log.Printf("alert queue full rule=%s monitor=%d", ev.RuleName, ev.MonitorID)
							}
						} else {
							log.Printf("alert reduced rule=%s monitor=%d by=%s", ev.RuleName, ev.MonitorID, d.SuppressedBy)
						}
					}
				}
				if !pipeline.Submit(point) {
					log.Printf("dispatch queue full monitor id=%d", id)
				}
			}
		}
	}()

	go func() {
		ticker := time.NewTicker(time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case now := <-ticker.C:
				monitors := st.List()
				for _, m := range monitors {
					if !m.Enabled {
						continue
					}
					results := periodicEvaluator.RunDue(ctx, m.ID, now)
					for _, r := range results {
						if r.Event.State == alert.StateFiring {
							d := reducer.Process(r.Event, now)
							if d.Emit {
								log.Printf("periodic alert firing rule=%s monitor=%d value=%.4f elapsed_ms=%d query=%s grouped=%d",
									r.Rule.Name, m.ID, r.Value, r.Event.ElapsedMs, r.Rule.PromQL, d.GroupedCount)
								if !queues.EnqueueAlert(r.Event) {
									log.Printf("alert queue full periodic rule=%s monitor=%d", r.Rule.Name, m.ID)
								}
							} else {
								log.Printf("periodic alert reduced rule=%s monitor=%d by=%s", r.Rule.Name, m.ID, d.SuppressedBy)
							}
						}
					}
				}
			}
		}
	}()

	addr := ":8080"
	if v := os.Getenv("MANAGER_ADDR"); v != "" {
		addr = v
	}
	server := &http.Server{
		Addr:         addr,
		Handler:      api.Handler(),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}
	log.Printf("manager-go start on %s", addr)
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen error: %v", err)
		}
	}()

	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = server.Shutdown(shutdownCtx)
}

func makePoint(m model.Monitor) model.MetricPoint {
	now := time.Now()
	return model.MetricPoint{
		MonitorID: m.ID,
		App:       m.App,
		Metrics:   "manager_dispatch",
		Field:     "tick",
		Value:     math.Mod(float64(now.UnixNano()), 1000),
		UnixMs:    now.UnixMilli(),
		Instance:  m.Target,
		Labels: map[string]string{
			"env": "dev",
		},
	}
}

func pointVars(p model.MetricPoint) map[string]float64 {
	out := map[string]float64{
		"value": p.Value,
	}
	out[p.Metrics+"_"+p.Field] = p.Value
	return out
}

func getenv(key, def string) string {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	return v
}

type logSender struct{}

func (logSender) Send(_ context.Context, task alert.NotifyTask) error {
	log.Printf("notify send task=%d rule=%s monitor=%d severity=%s attempt=%d channel=%s",
		task.ID, task.Event.RuleName, task.Event.MonitorID, task.Event.Severity, task.Attempt, task.Channel)
	return nil
}

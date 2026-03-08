package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/collector"
	"manager-go/internal/dispatch"
	"manager-go/internal/httpapi"
	"manager-go/internal/model"
	"manager-go/internal/notify"
	"manager-go/internal/scheduler"
	"manager-go/internal/store"
)

func main() {
	st := store.NewMonitorStore()
	registry := collector.NewRegistry()
	alertStore := alert.NewAlertStore()
	deadLetters := alert.NewDeadLetterStore()

	dispatchCh := make(chan int64, 1024)
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	sched := scheduler.NewDispatchScheduler(st, 500*time.Millisecond, dispatchCh)
	go sched.Start(ctx)

	collectorTimeout := envDurationSeconds("COLLECTOR_HEARTBEAT_TIMEOUT_SECONDS", 30)
	go reapCollectors(ctx, registry, collectorTimeout)

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
		[]alert.SilenceRule{},
	)
	queues := alert.NewQueues(
		2048,
		[]time.Duration{time.Minute, 5 * time.Minute, 15 * time.Minute, time.Hour},
		5,
	)
	queues.SetDeadLetterSink(deadLetters)
	sender := newNotifySender()
	queues.Start(ctx, sender, 2, 2)

	handleFiring := func(ev alert.Event, grouped int) {
		alertStore.Fire(ev)
		if !queues.EnqueueAlert(ev) {
			log.Printf("alert queue full rule=%s monitor=%d", ev.RuleName, ev.MonitorID)
		}
		log.Printf("alert firing rule=%s monitor=%d severity=%s elapsed_ms=%d grouped=%d",
			ev.RuleName, ev.MonitorID, ev.Severity, ev.ElapsedMs, grouped)
	}

	runRealtimeAlerts := func(monitorID int64, vars map[string]float64) {
		for _, rule := range alertRules {
			ev, matched, err := alertEngine.Evaluate(rule, monitorID, vars, time.Now())
			if err != nil {
				log.Printf("alert eval error rule=%s monitor=%d err=%v", rule.Name, monitorID, err)
				continue
			}
			if matched && ev.State == alert.StateFiring {
				d := reducer.Process(ev, time.Now())
				if d.Emit {
					handleFiring(ev, d.GroupedCount)
				} else {
					log.Printf("alert reduced rule=%s monitor=%d by=%s", ev.RuleName, ev.MonitorID, d.SuppressedBy)
				}
			}
		}
	}

	ingestPoint := func(point model.MetricPoint) error {
		if point.UnixMs <= 0 {
			point.UnixMs = time.Now().UnixMilli()
		}
		if !pipeline.Submit(point) {
			return fmt.Errorf("dispatch queue full")
		}
		vars := pointVars(point)
		runRealtimeAlerts(point.MonitorID, vars)
		return nil
	}

	retryDeadLetter := func(id int64) error {
		task, ok := deadLetters.Retry(id)
		if !ok {
			return fmt.Errorf("dead letter not found or already retried")
		}
		if !queues.EnqueueNotify(task) {
			return fmt.Errorf("notify queue full")
		}
		return nil
	}

	dataDir := getenv("MANAGER_DATA_DIR", "data")
	resourceHub, err := httpapi.NewSQLiteResourceHub(filepath.Join(dataDir, "resources.db"))
	if err != nil {
		log.Printf("init sqlite resources failed, fallback to json files: %v", err)
		resourceHub, err = httpapi.NewPersistentResourceHub(filepath.Join(dataDir, "resources"))
		if err != nil {
			log.Printf("init json resources failed, fallback to memory: %v", err)
			resourceHub = nil
		}
	}

	api := httpapi.NewServer(
		st,
		httpapi.WithResourceHub(resourceHub),
		httpapi.WithCollectorRegistry(registry, collectorTimeout),
		httpapi.WithMetricIngest(ingestPoint),
		httpapi.WithAlertStore(alertStore),
		httpapi.WithDeadLetterStore(deadLetters, retryDeadLetter),
	)

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

				if len(registry.List()) > 0 {
					node, err := registry.SelectByMonitor(m.ID)
					if err != nil {
						log.Printf("dispatch assign failed monitor=%d err=%v", m.ID, err)
						continue
					}
					log.Printf("dispatch assigned monitor=%d collector=%s addr=%s", m.ID, node.ID, node.Addr)
					continue
				}

				point := makePoint(m)
				if err := ingestPoint(point); err != nil {
					log.Printf("dispatch ingest fallback failed monitor=%d err=%v", m.ID, err)
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
								handleFiring(r.Event, d.GroupedCount)
								log.Printf("periodic alert firing rule=%s monitor=%d value=%.4f elapsed_ms=%d query=%s grouped=%d",
									r.Rule.Name, m.ID, r.Value, r.Event.ElapsedMs, r.Rule.PromQL, d.GroupedCount)
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

func reapCollectors(ctx context.Context, registry *collector.Registry, timeout time.Duration) {
	if timeout <= 0 {
		return
	}
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case now := <-ticker.C:
			expired := registry.ReapExpired(timeout, now)
			for _, id := range expired {
				log.Printf("collector expired id=%s timeout=%s", id, timeout)
			}
		}
	}
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

func envDurationSeconds(key string, def int) time.Duration {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return time.Duration(def) * time.Second
	}
	n, err := strconvAtoi(raw)
	if err != nil || n <= 0 {
		return time.Duration(def) * time.Second
	}
	return time.Duration(n) * time.Second
}

func strconvAtoi(raw string) (int, error) {
	var n int
	_, err := fmt.Sscanf(raw, "%d", &n)
	return n, err
}

type notifySender struct {
	service  *notify.Service
	template string
	title    string
	channels []notify.ChannelType
	configs  map[notify.ChannelType]json.RawMessage
}

func newNotifySender() *notifySender {
	channels := parseNotifyChannels(getenv("MANAGER_NOTIFY_CHANNELS", "webhook"))
	configs := map[notify.ChannelType]json.RawMessage{
		notify.ChannelWebhook: json.RawMessage(getenv("MANAGER_NOTIFY_WEBHOOK_CONFIG", "{}")),
		notify.ChannelEmail:   json.RawMessage(getenv("MANAGER_NOTIFY_EMAIL_CONFIG", "{}")),
		notify.ChannelWeCom:   json.RawMessage(getenv("MANAGER_NOTIFY_WECOM_CONFIG", "{}")),
	}
	return &notifySender{
		service:  notify.NewService(),
		template: getenv("MANAGER_NOTIFY_TEMPLATE", "告警 {{.rule_name}} monitor={{.monitor_id}} severity={{.severity}}"),
		title:    getenv("MANAGER_NOTIFY_TITLE", "Arco Monitoring Alert"),
		channels: channels,
		configs:  configs,
	}
}

func (s *notifySender) Send(ctx context.Context, task alert.NotifyTask) error {
	if len(s.channels) == 0 {
		return fmt.Errorf("no notify channel configured")
	}
	payload := map[string]any{
		"rule_name":    task.Event.RuleName,
		"monitor_id":   task.Event.MonitorID,
		"severity":     task.Event.Severity,
		"expression":   task.Event.Expression,
		"elapsed_ms":   task.Event.ElapsedMs,
		"triggered_at": task.Event.TriggeredAt.Format(time.RFC3339),
	}
	var errs []string
	for _, ch := range s.channels {
		req := notify.TestSendRequest{
			Channel:  ch,
			Title:    s.title,
			Template: s.template,
			Data:     payload,
			Config:   s.configs[ch],
		}
		if err := s.service.TestSend(ctx, req); err != nil {
			errs = append(errs, string(ch)+": "+err.Error())
		}
	}
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}

func parseNotifyChannels(raw string) []notify.ChannelType {
	parts := strings.Split(raw, ",")
	out := make([]notify.ChannelType, 0, len(parts))
	for _, p := range parts {
		s := strings.TrimSpace(strings.ToLower(p))
		switch s {
		case string(notify.ChannelWebhook):
			out = append(out, notify.ChannelWebhook)
		case string(notify.ChannelEmail):
			out = append(out, notify.ChannelEmail)
		case string(notify.ChannelWeCom):
			out = append(out, notify.ChannelWeCom)
		}
	}
	return out
}

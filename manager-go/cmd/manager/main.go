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
	"strconv"
	"strings"
	"syscall"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/collector"
	"manager-go/internal/dispatch"
	"manager-go/internal/httpapi"
	"manager-go/internal/metrics"
	"manager-go/internal/model"
	"manager-go/internal/notify"
	pb "manager-go/internal/pb/proto"
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

	// 初始化 Collector Store 和 Manager
	// 使用与 Python Web 相同的数据库
	pythonWebDB := getenv("PYTHON_WEB_DB", "../backend/instance/it_ops.db")
	collectorStore, err := store.NewCollectorStoreWithPath(pythonWebDB)
	if err != nil {
		log.Printf("[Manager] Failed to create collector store: %v, using memory registry only", err)
		collectorStore = nil
	} else {
		// 确保表结构存在（如果 Python Web 还没创建）
		if err := collectorStore.InitTable(); err != nil {
			log.Printf("[Manager] Failed to init collector table: %v", err)
		}
		log.Printf("[Manager] Connected to Python Web database: %s", pythonWebDB)
	}

	// 创建 Collector Manager
	var collectorManager *collector.Manager
	if collectorStore != nil {
		collectorManager = collector.NewManager(
			st,
			collectorStore,
			collector.WithManagerHeartbeatInterval(5*time.Second),
			collector.WithManagerReconnectBackoff(5*time.Second),
			collector.WithManagerMaxReconnectAttempts(10),
		)
		log.Printf("[Manager] Collector manager created with database storage")
	}

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

	if collectorManager != nil {
		collectorManager.SetReportHandler(func(collectorID string, rep *pb.CollectRep) {
			points := collectorReportToPoints(st, collectorID, rep)
			for _, point := range points {
				if err := ingestPoint(point); err != nil {
					log.Printf("collector report ingest failed collector=%s monitor=%d metric=%s_%s err=%v",
						collectorID, point.MonitorID, point.Metrics, point.Field, err)
				}
			}
		})
		collectorManager.SetAckHandler(func(collectorID string, ack *pb.CommandAck) {
			if ack == nil {
				return
			}
			log.Printf("collector ack collector=%s job=%d command=%d type=%s status=%s reason=%s",
				collectorID, ack.GetJobId(), ack.GetCommandId(), ack.GetCommandType(), ack.GetStatus().String(), ack.GetReason())
		})
	}

	vmQueryClient := metrics.NewVMClient(vmURL, 1500*time.Millisecond)

	// 资源配置由 Python Web 管理，Manager 不再维护独立的 resources.db
	// 如需访问资源配置，请调用 Python Web API

	api := httpapi.NewServer(
		st,
		httpapi.WithCollectorRegistry(registry, collectorTimeout),
		httpapi.WithMetricIngest(ingestPoint),
		httpapi.WithAlertStore(alertStore),
		httpapi.WithDeadLetterStore(deadLetters, retryDeadLetter),
		httpapi.WithCollectorManager(collectorManager),
		httpapi.WithVMQueryClient(vmQueryClient),
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
				if collectorManager != nil && len(collectorManager.GetConnectedClients()) > 0 {
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

func collectorReportToPoints(st *store.MonitorStore, collectorID string, rep *pb.CollectRep) []model.MetricPoint {
	if rep == nil {
		return nil
	}
	timestamp := rep.GetTimeUnixMs()
	if timestamp <= 0 {
		timestamp = time.Now().UnixMilli()
	}

	monitor, err := st.Get(rep.GetMonitorId())
	app := strings.TrimSpace(rep.GetApp())
	instance := strings.TrimSpace(rep.GetFields()["identity"])
	if err == nil {
		if app == "" {
			app = strings.TrimSpace(monitor.App)
		}
		if instance == "" {
			instance = strings.TrimSpace(monitor.Target)
		}
	}
	if app == "" {
		app = "unknown"
	}
	if instance == "" {
		instance = "unknown"
	}

	metricGroup := strings.TrimSpace(rep.GetMetrics())
	if metricGroup == "" {
		metricGroup = "collect"
	}

	baseLabels := map[string]string{
		"collector_id": collectorID,
		"protocol":     strings.TrimSpace(rep.GetProtocol()),
		"app":          app,
	}
	if section := strings.TrimSpace(rep.GetFields()["section"]); section != "" {
		baseLabels["section"] = section
	}

	points := []model.MetricPoint{
		{
			MonitorID: rep.GetMonitorId(),
			App:       app,
			Metrics:   metricGroup,
			Field:     "success",
			Value:     boolToFloat(rep.GetSuccess()),
			UnixMs:    timestamp,
			Instance:  instance,
			Labels:    cloneLabels(baseLabels),
		},
	}
	if rep.GetRawLatencyMs() > 0 {
		points = append(points, model.MetricPoint{
			MonitorID: rep.GetMonitorId(),
			App:       app,
			Metrics:   metricGroup,
			Field:     "raw_latency_ms",
			Value:     float64(rep.GetRawLatencyMs()),
			UnixMs:    timestamp,
			Instance:  instance,
			Labels:    cloneLabels(baseLabels),
		})
	}
	for field, raw := range rep.GetFields() {
		key := strings.TrimSpace(field)
		if key == "" || key == "identity" || key == "section" {
			continue
		}
		value, err := strconv.ParseFloat(strings.TrimSpace(raw), 64)
		if err != nil || math.IsNaN(value) || math.IsInf(value, 0) {
			continue
		}
		points = append(points, model.MetricPoint{
			MonitorID: rep.GetMonitorId(),
			App:       app,
			Metrics:   metricGroup,
			Field:     key,
			Value:     value,
			UnixMs:    timestamp,
			Instance:  instance,
			Labels:    cloneLabels(baseLabels),
		})
	}
	return points
}

func boolToFloat(ok bool) float64 {
	if ok {
		return 1
	}
	return 0
}

func cloneLabels(src map[string]string) map[string]string {
	if len(src) == 0 {
		return nil
	}
	dst := make(map[string]string, len(src))
	for k, v := range src {
		if strings.TrimSpace(v) == "" {
			continue
		}
		dst[k] = v
	}
	if len(dst) == 0 {
		return nil
	}
	return dst
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

package main

import (
	"context"
	"database/sql"
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
	"sync"
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
	templ "manager-go/internal/template"
)

func main() {
	pythonWebDB := getenv("PYTHON_WEB_DB", "../backend/instance/it_ops.db")
	st, stErr := store.NewMonitorStoreWithPath(pythonWebDB)
	if stErr != nil {
		log.Printf("[Manager] Failed to create persistent monitor store: %v, fallback to memory store", stErr)
		st = store.NewMonitorStore()
	} else {
		log.Printf("[Manager] Persistent monitor store enabled: %s", pythonWebDB)
	}
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

	// 初始化模板运行时（monitor_templates -> in-memory registry）
	var templateReg *templ.Registry
	templateStore, tplErr := templ.NewStoreWithPath(pythonWebDB)
	if tplErr != nil {
		log.Printf("[Manager] Failed to create template store: %v", tplErr)
	} else {
		templateReg = templ.NewRegistry()
		if err := templateReg.ReloadFromStore(templateStore); err != nil {
			log.Printf("[Manager] Failed to initial template reload: %v", err)
		} else {
			log.Printf("[Manager] Loaded %d templates into runtime registry", len(templateReg.List()))
		}
		go reloadTemplateRegistry(ctx, templateReg, templateStore, 60*time.Second)
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
			collector.WithManagerTemplateRegistry(templateReg),
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
	alertRuntimeStore, arsErr := store.NewAlertRuntimeStoreWithPath(pythonWebDB)
	if arsErr != nil {
		log.Printf("[Manager] Failed to create alert runtime store: %v", arsErr)
		alertRuntimeStore = nil
	}
	var (
		alertRulesMu       sync.RWMutex
		alertRules         []alert.Rule
		alertRuleDefsByID  map[int64]store.RuntimeAlertRule
		periodicRuleDefs   []store.RuntimeAlertRule
		realtimeReloadedAt time.Time
		reducerRef         *alert.Reducer
		unknownVarLogMu    sync.Mutex
		unknownVarLogAt    = map[string]time.Time{}
		recoveryMu         sync.Mutex
		recoveryCounter    = map[string]int{}
	)
	reloadRealtimeAlertRules := func() {
		if alertRuntimeStore == nil {
			return
		}
		rows, err := alertRuntimeStore.LoadEnabledRealtimeMetricRules()
		if err != nil {
			log.Printf("[Manager] reload realtime alert rules failed: %v", err)
			return
		}
		nextRules := make([]alert.Rule, 0, len(rows))
		nextDefs := make(map[int64]store.RuntimeAlertRule, len(rows))
		for _, row := range rows {
			expr := store.BuildRuleExpression(row)
			if strings.TrimSpace(expr) == "" {
				continue
			}
			nextRules = append(nextRules, alert.Rule{
				ID:              row.ID,
				Name:            row.Name,
				Expression:      expr,
				DurationSeconds: store.BuildRuleDurationSeconds(row),
				Severity:        store.BuildRuleSeverity(row),
				Enabled:         row.Enabled,
			})
			nextDefs[row.ID] = row
		}
		periodicRows, err := alertRuntimeStore.LoadEnabledPeriodicMetricRules()
		if err != nil {
			log.Printf("[Manager] reload periodic alert rules failed: %v", err)
			periodicRows = nil
		}
		for _, row := range periodicRows {
			nextDefs[row.ID] = row
		}
		groupRows, err := alertRuntimeStore.LoadEnabledAlertGroups()
		if err != nil {
			log.Printf("[Manager] reload alert groups failed: %v", err)
		}
		inhibitRows, err := alertRuntimeStore.LoadEnabledAlertInhibits()
		if err != nil {
			log.Printf("[Manager] reload alert inhibits failed: %v", err)
		}
		silenceRows, err := alertRuntimeStore.LoadEnabledAlertSilences()
		if err != nil {
			log.Printf("[Manager] reload alert silences failed: %v", err)
		}
		if reducerRef != nil {
			reducerRef.UpdateRules(
				convertGroupRules(groupRows),
				convertInhibitRules(inhibitRows),
				convertSilenceRules(silenceRows),
			)
		}

		alertRulesMu.Lock()
		alertRules = nextRules
		alertRuleDefsByID = nextDefs
		periodicRuleDefs = periodicRows
		realtimeReloadedAt = time.Now()
		alertRulesMu.Unlock()
		log.Printf("[Manager] alert rules reloaded realtime=%d periodic=%d", len(nextRules), len(periodicRows))
	}
	reloadRealtimeAlertRules()
	go func() {
		ticker := time.NewTicker(60 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				reloadRealtimeAlertRules()
			}
		}
	}()

	ciAttrDB, ciDBErr := sql.Open("sqlite3", pythonWebDB)
	if ciDBErr != nil {
		log.Printf("[Manager] open ci attr db failed: %v", ciDBErr)
		ciAttrDB = nil
	} else {
		ciAttrDB.SetMaxOpenConns(3)
		ciAttrDB.SetMaxIdleConns(2)
		ciAttrDB.SetConnMaxLifetime(30 * time.Minute)
		defer ciAttrDB.Close()
	}
	type ciAttrCacheEntry struct {
		labels   map[string]string
		expireAt time.Time
	}
	var (
		ciAttrCacheMu sync.Mutex
		ciAttrCache   = map[int64]ciAttrCacheEntry{}
	)
	resolveCIAttrLabels := func(m model.Monitor) map[string]string {
		if m.CIID <= 0 {
			return nil
		}
		base := map[string]string{
			"ci.id": strconv.FormatInt(m.CIID, 10),
		}
		if code := strings.TrimSpace(m.CICode); code != "" {
			base["ci.code"] = code
		}
		if name := strings.TrimSpace(m.CIName); name != "" {
			base["ci.name"] = name
		}
		if ciAttrDB == nil {
			return cloneLabels(base)
		}
		now := time.Now()
		ciAttrCacheMu.Lock()
		if cached, ok := ciAttrCache[m.CIID]; ok && now.Before(cached.expireAt) {
			out := cloneLabels(cached.labels)
			ciAttrCacheMu.Unlock()
			return out
		}
		ciAttrCacheMu.Unlock()

		var (
			code    sql.NullString
			name    sql.NullString
			attrRaw sql.NullString
		)
		row := ciAttrDB.QueryRow(`SELECT code, name, attribute_values FROM ci_instances WHERE id = ? LIMIT 1`, m.CIID)
		if err := row.Scan(&code, &name, &attrRaw); err != nil {
			return cloneLabels(base)
		}
		if code.Valid && strings.TrimSpace(code.String) != "" {
			base["ci.code"] = strings.TrimSpace(code.String)
		}
		if name.Valid && strings.TrimSpace(name.String) != "" {
			base["ci.name"] = strings.TrimSpace(name.String)
		}
		if attrRaw.Valid && strings.TrimSpace(attrRaw.String) != "" {
			attrs := map[string]any{}
			if err := json.Unmarshal([]byte(attrRaw.String), &attrs); err == nil {
				for k, raw := range attrs {
					key := strings.TrimSpace(k)
					if key == "" || raw == nil {
						continue
					}
					val := strings.TrimSpace(fmt.Sprintf("%v", raw))
					if val == "" {
						continue
					}
					base["ci."+key] = val
				}
			}
		}
		out := cloneLabels(base)
		ciAttrCacheMu.Lock()
		ciAttrCache[m.CIID] = ciAttrCacheEntry{
			labels:   cloneLabels(base),
			expireAt: now.Add(60 * time.Second),
		}
		ciAttrCacheMu.Unlock()
		return out
	}

	periodicVM := alert.NewVMClient(vmURL, 1200*time.Millisecond)
	reducer := alert.NewReducer(
		60*time.Second,
		5*time.Minute,
		[]alert.SilenceRule{},
	)
	reducerRef = reducer
	reloadRealtimeAlertRules()
	queues := alert.NewQueues(
		2048,
		[]time.Duration{time.Minute, 5 * time.Minute, 15 * time.Minute, time.Hour},
		5,
	)
	queues.SetDeadLetterSink(deadLetters)
	sender := newNotifySender(alertRuntimeStore)
	queues.Start(ctx, sender, 2, 2)

	recoveryKey := func(ruleID int64, monitorID int64) string {
		return fmt.Sprintf("%d:%d", ruleID, monitorID)
	}
	clearRecoveryCount := func(ruleID int64, monitorID int64) {
		key := recoveryKey(ruleID, monitorID)
		recoveryMu.Lock()
		delete(recoveryCounter, key)
		recoveryMu.Unlock()
	}
	incRecoveryCount := func(ruleID int64, monitorID int64) int {
		key := recoveryKey(ruleID, monitorID)
		recoveryMu.Lock()
		defer recoveryMu.Unlock()
		next := recoveryCounter[key] + 1
		recoveryCounter[key] = next
		return next
	}
	enqueueByNoticeRules := func(ev alert.Event, noticeRuleIDs []int64) {
		if len(noticeRuleIDs) == 0 {
			if !queues.EnqueueAlert(ev) {
				log.Printf("alert queue full rule=%s monitor=%d", ev.RuleName, ev.MonitorID)
			}
			return
		}
		for _, noticeID := range noticeRuleIDs {
			evCopy := ev
			evCopy.NoticeRuleID = noticeID
			if !queues.EnqueueAlert(evCopy) {
				log.Printf("alert queue full rule=%s monitor=%d notice_rule_id=%d", evCopy.RuleName, evCopy.MonitorID, noticeID)
			}
		}
	}

	handleFiring := func(ev alert.Event, grouped int, point model.MetricPoint) {
		alertStore.Fire(ev)
		alertRulesMu.RLock()
		def := alertRuleDefsByID[ev.RuleID]
		alertRulesMu.RUnlock()
		noticeRuleIDs := def.NoticeRules
		if len(noticeRuleIDs) == 0 && def.NoticeRule > 0 {
			noticeRuleIDs = []int64{def.NoticeRule}
		}
		if alertRuntimeStore != nil {
			ev.App = point.App
			ev.Instance = point.Instance
			metric := store.BuildRuleMetric(def)
			metricValue := point.Value
			pointVarsMap := pointVars(point)
			if v, ok := pointVarsMap[metric]; ok {
				metricValue = v
			}
			ev.Title = renderAlertTitle(def, ev, metric, metricValue)
			ev.Content = renderAlertContent(def, ev, metric, metricValue)
			newCycle, err := alertRuntimeStore.UpsertFiringAlert(store.RuntimeAlertEvent{
				RuleID:      ev.RuleID,
				RuleName:    ev.RuleName,
				MonitorID:   ev.MonitorID,
				Severity:    ev.Severity,
				Expression:  ev.Expression,
				Metric:      metric,
				Value:       metricValue,
				Threshold:   store.BuildRuleThreshold(def),
				MonitorName: readStringLabel(point.Labels, "job", point.Instance),
				App:         point.App,
				Instance:    point.Instance,
				Content:     ev.Content,
				TriggeredAt: ev.TriggeredAt,
				ElapsedMs:   ev.ElapsedMs,
			})
			if err != nil {
				log.Printf("alert runtime upsert failed rule=%d monitor=%d err=%v", ev.RuleID, ev.MonitorID, err)
			} else if newCycle {
				sender.ResetNotifyLimits(ev.RuleID, ev.MonitorID)
			}
		}
		enqueueByNoticeRules(ev, noticeRuleIDs)
		log.Printf("alert firing rule=%s monitor=%d severity=%s elapsed_ms=%d grouped=%d",
			ev.RuleName, ev.MonitorID, ev.Severity, ev.ElapsedMs, grouped)
	}
	handleRecovered := func(ev alert.Event, point model.MetricPoint) {
		ev.App = point.App
		ev.Instance = point.Instance
		alertRulesMu.RLock()
		def := alertRuleDefsByID[ev.RuleID]
		alertRulesMu.RUnlock()
		metric := store.BuildRuleMetric(def)
		metricValue := point.Value
		pointVarsMap := pointVars(point)
		if v, ok := pointVarsMap[metric]; ok {
			metricValue = v
		}
		ev.Title = renderAlertTitle(def, ev, metric, metricValue)
		ev.Content = renderAlertContent(def, ev, metric, metricValue)
		noticeRuleIDs := def.NoticeRules
		if len(noticeRuleIDs) == 0 && def.NoticeRule > 0 {
			noticeRuleIDs = []int64{def.NoticeRule}
		}
		enqueueByNoticeRules(ev, noticeRuleIDs)
		log.Printf("alert recovered rule=%s monitor=%d severity=%s", ev.RuleName, ev.MonitorID, ev.Severity)
	}

	runRealtimeAlerts := func(point model.MetricPoint, vars map[string]float64) {
		alertRulesMu.RLock()
		rulesSnapshot := make([]alert.Rule, len(alertRules))
		copy(rulesSnapshot, alertRules)
		_ = realtimeReloadedAt
		alertRulesMu.RUnlock()
		for _, rule := range rulesSnapshot {
			def := alertRuleDefsByID[rule.ID]
			if !store.RuleAppliesToTarget(def, point.MonitorID, point.App, point.Instance) {
				continue
			}
			runtimeVars := vars
			ev, matched, err := alertEngine.Evaluate(rule, point.MonitorID, runtimeVars, time.Now())
			// Runtime alias补全: 兼容 server_up/app_server_up、metrics_field 与 field 名差异。
			for retry := 0; err != nil && retry < 4; retry++ {
				unknown := parseUnknownVariable(err)
				if unknown == "" {
					break
				}
				nextVars, changed := enrichUnknownVariable(runtimeVars, unknown)
				if !changed {
					break
				}
				runtimeVars = nextVars
				ev, matched, err = alertEngine.Evaluate(rule, point.MonitorID, runtimeVars, time.Now())
			}
			if err != nil {
				if unknown := parseUnknownVariable(err); unknown != "" {
					logKey := fmt.Sprintf("%d:%d:%s", point.MonitorID, rule.ID, unknown)
					shouldLog := false
					now := time.Now()
					unknownVarLogMu.Lock()
					if last, ok := unknownVarLogAt[logKey]; !ok || now.Sub(last) >= time.Minute {
						unknownVarLogAt[logKey] = now
						shouldLog = true
					}
					unknownVarLogMu.Unlock()
					if shouldLog {
						log.Printf("alert eval skip rule=%s monitor=%d reason=unknown variable: %s", rule.Name, point.MonitorID, unknown)
					}
					continue
				}
				log.Printf("alert eval error rule=%s monitor=%d err=%v", rule.Name, point.MonitorID, err)
				continue
			}
			ev.Labels = buildEventLabels(def, point)
			if matched && ev.State == alert.StateFiring {
				clearRecoveryCount(rule.ID, point.MonitorID)
				d := reducer.Process(ev, time.Now())
				if d.Emit {
					handleFiring(ev, d.GroupedCount, point)
				} else {
					log.Printf("alert reduced rule=%s monitor=%d by=%s", ev.RuleName, ev.MonitorID, d.SuppressedBy)
				}
				continue
			}
			if matched && ev.State == alert.StateNormal && alertRuntimeStore != nil {
				if !ruleAutoRecoverEnabled(def) {
					clearRecoveryCount(rule.ID, point.MonitorID)
					continue
				}
				currentRecovery := incRecoveryCount(rule.ID, point.MonitorID)
				requiredRecovery := ruleRecoverTimes(def)
				if currentRecovery < requiredRecovery {
					continue
				}
				clearRecoveryCount(rule.ID, point.MonitorID)
				changed, err := alertRuntimeStore.ResolveAlert(rule.ID, point.MonitorID, time.Now())
				if err != nil {
					log.Printf("alert resolve failed rule=%d monitor=%d err=%v", rule.ID, point.MonitorID, err)
					continue
				}
				if changed && ruleNotifyOnRecovered(def) {
					handleRecovered(ev, point)
				}
				continue
			}
			clearRecoveryCount(rule.ID, point.MonitorID)
		}
	}

	var (
		metricSnapshotMu sync.RWMutex
		metricSnapshot   = map[int64]map[string]float64{}
		metricSnapshotAt = map[int64]time.Time{}
	)
	type latestStringMetric struct {
		Value     string
		Timestamp int64
	}
	var (
		stringSnapshotMu sync.RWMutex
		stringSnapshot   = map[int64]map[string]latestStringMetric{}
	)
	updateMetricSnapshot := func(point model.MetricPoint) map[string]float64 {
		base := pointVars(point)
		// direct aliases for expression convenience, e.g. used_memory > 0
		base[strings.TrimSpace(point.Field)] = point.Value
		base[strings.TrimSpace(point.Metrics)] = point.Value
		if strings.TrimSpace(point.Field) == "success" {
			base["server_up"] = point.Value
			if appToken := normalizeAlertToken(point.App); appToken != "" {
				base[appToken+"_server_up"] = point.Value
			}
		}

		now := time.Now()
		metricSnapshotMu.Lock()
		cur := metricSnapshot[point.MonitorID]
		if cur == nil {
			cur = map[string]float64{}
		}
		// 5m snapshot TTL for cross-field realtime expressions.
		if ts, ok := metricSnapshotAt[point.MonitorID]; ok && now.Sub(ts) > 5*time.Minute {
			cur = map[string]float64{}
		}
		for k, v := range base {
			key := strings.TrimSpace(k)
			if key == "" {
				continue
			}
			cur[key] = v
		}
		metricSnapshot[point.MonitorID] = cur
		metricSnapshotAt[point.MonitorID] = now
		merged := make(map[string]float64, len(cur))
		for k, v := range cur {
			merged[k] = v
		}
		metricSnapshotMu.Unlock()
		return merged
	}

	updateStringSnapshot := func(rep *pb.CollectRep) {
		if rep == nil || rep.GetMonitorId() <= 0 {
			return
		}
		fields := rep.GetFields()
		if len(fields) == 0 {
			return
		}
		timestamp := rep.GetTimeUnixMs()
		if timestamp <= 0 {
			timestamp = time.Now().UnixMilli()
		}
		stringSnapshotMu.Lock()
		cur := stringSnapshot[rep.GetMonitorId()]
		if cur == nil {
			cur = map[string]latestStringMetric{}
		}
		for rawKey, rawValue := range fields {
			key := strings.TrimSpace(rawKey)
			if key == "" || key == "identity" || key == "section" {
				continue
			}
			cur[key] = latestStringMetric{
				Value:     strings.TrimSpace(rawValue),
				Timestamp: timestamp,
			}
		}
		stringSnapshot[rep.GetMonitorId()] = cur
		stringSnapshotMu.Unlock()
	}

	loadStringSnapshot := func(monitorID int64, names []string) map[string]httpapi.StringLatestValue {
		out := make(map[string]httpapi.StringLatestValue, len(names))
		if monitorID <= 0 || len(names) == 0 {
			return out
		}
		stringSnapshotMu.RLock()
		cur := stringSnapshot[monitorID]
		if len(cur) == 0 {
			stringSnapshotMu.RUnlock()
			return out
		}
		for _, rawName := range names {
			name := strings.TrimSpace(rawName)
			if name == "" {
				continue
			}
			if item, ok := cur[name]; ok {
				out[name] = httpapi.StringLatestValue{
					Value:     item.Value,
					Timestamp: item.Timestamp,
				}
				continue
			}
			if strings.HasSuffix(name, "_ok") {
				base := strings.TrimSuffix(name, "_ok")
				item, ok := cur[base]
				if !ok {
					continue
				}
				if okValue, mapped := statusStringToFloat(item.Value); mapped {
					text := "FAIL"
					if okValue >= 0.5 {
						text = "OK"
					}
					out[name] = httpapi.StringLatestValue{
						Value:     text,
						Timestamp: item.Timestamp,
					}
				}
			}
		}
		stringSnapshotMu.RUnlock()
		return out
	}

	ingestPoint := func(point model.MetricPoint) error {
		if point.UnixMs <= 0 {
			point.UnixMs = time.Now().UnixMilli()
		}
		if !pipeline.Submit(point) {
			return fmt.Errorf("dispatch queue full")
		}
		vars := updateMetricSnapshot(point)
		runRealtimeAlerts(point, vars)
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
			updateStringSnapshot(rep)
			points := collectorReportToPoints(st, collectorID, rep, resolveCIAttrLabels)
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
		httpapi.WithStringLatestProvider(loadStringSnapshot),
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
		nextPeriodicRun := map[string]time.Time{}
		for {
			select {
			case <-ctx.Done():
				return
			case now := <-ticker.C:
				alertRulesMu.RLock()
				periodicSnapshot := make([]store.RuntimeAlertRule, len(periodicRuleDefs))
				copy(periodicSnapshot, periodicRuleDefs)
				alertRulesMu.RUnlock()
				if len(periodicSnapshot) == 0 {
					continue
				}
				monitors := st.List()
				for _, m := range monitors {
					if !m.Enabled {
						continue
					}
					for _, def := range periodicSnapshot {
						periodSeconds := def.Period
						if periodSeconds <= 0 {
							periodSeconds = 60
						}
						key := periodicRunKey(m.ID, def.ID)
						if nr, ok := nextPeriodicRun[key]; ok && now.Before(nr) {
							continue
						}
						nextPeriodicRun[key] = now.Add(time.Duration(periodSeconds) * time.Second)

						promql := store.BuildPeriodicPromQL(def, m.ID)
						if strings.TrimSpace(promql) == "" {
							continue
						}
						if !store.RuleAppliesToTarget(def, m.ID, m.App, m.Target) {
							continue
						}
						value, err := periodicVM.QueryValue(ctx, promql, now)
						if err != nil {
							if errors.Is(err, alert.ErrVMQueryEmptyResult) {
								continue
							}
							log.Printf("periodic alert query error rule=%s monitor=%d err=%v", def.Name, m.ID, err)
							continue
						}
						rule := alert.Rule{
							ID:              def.ID,
							Name:            def.Name,
							Expression:      store.BuildRuleExpression(def),
							DurationSeconds: maxInt(def.Times, 1),
							Severity:        store.BuildRuleSeverity(def),
							Enabled:         def.Enabled,
						}
						point := model.MetricPoint{
							MonitorID: m.ID,
							App:       m.App,
							Instance:  m.Target,
							Metrics:   "periodic",
							Field:     store.BuildRuleMetric(def),
							Value:     value,
							UnixMs:    now.UnixMilli(),
						}
						ev, matched, err := alertEngine.Evaluate(rule, m.ID, map[string]float64{"value": value, store.BuildRuleMetric(def): value}, now)
						if err != nil {
							log.Printf("periodic alert eval error rule=%s monitor=%d err=%v", def.Name, m.ID, err)
							continue
						}
						ev.Labels = buildEventLabels(def, point)
						if matched && ev.State == alert.StateFiring {
							clearRecoveryCount(def.ID, m.ID)
							d := reducer.Process(ev, now)
							if d.Emit {
								handleFiring(ev, d.GroupedCount, point)
								log.Printf("periodic alert firing rule=%s monitor=%d value=%.4f elapsed_ms=%d query=%s grouped=%d",
									def.Name, m.ID, value, ev.ElapsedMs, promql, d.GroupedCount)
							} else {
								log.Printf("periodic alert reduced rule=%s monitor=%d by=%s", def.Name, m.ID, d.SuppressedBy)
							}
							continue
						}
						if matched && ev.State == alert.StateNormal && alertRuntimeStore != nil {
							if !ruleAutoRecoverEnabled(def) {
								clearRecoveryCount(def.ID, m.ID)
								continue
							}
							currentRecovery := incRecoveryCount(def.ID, m.ID)
							requiredRecovery := ruleRecoverTimes(def)
							if currentRecovery < requiredRecovery {
								continue
							}
							clearRecoveryCount(def.ID, m.ID)
							changed, err := alertRuntimeStore.ResolveAlert(def.ID, m.ID, now)
							if err != nil {
								log.Printf("periodic alert resolve failed rule=%d monitor=%d err=%v", def.ID, m.ID, err)
								continue
							}
							if changed && ruleNotifyOnRecovered(def) {
								handleRecovered(ev, point)
							}
							continue
						}
						clearRecoveryCount(def.ID, m.ID)
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

func reloadTemplateRegistry(ctx context.Context, reg *templ.Registry, st *templ.Store, interval time.Duration) {
	if reg == nil || st == nil || interval <= 0 {
		return
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := reg.ReloadFromStore(st); err != nil {
				log.Printf("[Manager] template registry reload failed: %v", err)
				continue
			}
			log.Printf("[Manager] template registry reloaded, templates=%d", len(reg.List()))
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

func collectorReportToPoints(st *store.MonitorStore, collectorID string, rep *pb.CollectRep, resolveCIAttrLabels func(model.Monitor) map[string]string) []model.MetricPoint {
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
	if err == nil {
		for key, value := range monitor.Labels {
			k := strings.TrimSpace(key)
			v := strings.TrimSpace(value)
			if k == "" || v == "" {
				continue
			}
			baseLabels[k] = v
		}
		if monitor.CIID > 0 {
			baseLabels["ci.id"] = strconv.FormatInt(monitor.CIID, 10)
		}
		if ciCode := strings.TrimSpace(monitor.CICode); ciCode != "" {
			baseLabels["ci.code"] = ciCode
		}
		if ciName := strings.TrimSpace(monitor.CIName); ciName != "" {
			baseLabels["ci.name"] = ciName
		}
		if resolveCIAttrLabels != nil {
			for key, value := range resolveCIAttrLabels(monitor) {
				k := strings.TrimSpace(key)
				v := strings.TrimSpace(value)
				if k == "" || v == "" {
					continue
				}
				baseLabels[k] = v
			}
		}
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
		trimmed := strings.TrimSpace(raw)
		value, err := strconv.ParseFloat(trimmed, 64)
		if err != nil || math.IsNaN(value) || math.IsInf(value, 0) {
			if okValue, mapped := statusStringToFloat(trimmed); mapped {
				points = append(points, model.MetricPoint{
					MonitorID: rep.GetMonitorId(),
					App:       app,
					Metrics:   metricGroup,
					Field:     key + "_ok",
					Value:     okValue,
					UnixMs:    timestamp,
					Instance:  instance,
					Labels:    cloneLabels(baseLabels),
				})
			}
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

func statusStringToFloat(raw string) (float64, bool) {
	text := strings.ToLower(strings.TrimSpace(raw))
	switch text {
	case "ok", "true", "yes", "up", "online", "connected", "success", "master":
		return 1, true
	case "err", "error", "false", "no", "down", "offline", "disconnected", "fail", "failed":
		return 0, true
	default:
		return 0, false
	}
}

func normalizeAlertToken(raw string) string {
	v := strings.TrimSpace(strings.ToLower(raw))
	if v == "" {
		return ""
	}
	buf := make([]byte, 0, len(v))
	for i := 0; i < len(v); i++ {
		ch := v[i]
		if (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_' {
			buf = append(buf, ch)
			continue
		}
		buf = append(buf, '_')
	}
	if len(buf) > 0 && buf[0] >= '0' && buf[0] <= '9' {
		buf = append([]byte{'m', '_'}, buf...)
	}
	return strings.Trim(string(buf), "_")
}

func parseUnknownVariable(err error) string {
	if err == nil {
		return ""
	}
	const prefix = "unknown variable:"
	msg := strings.TrimSpace(err.Error())
	if !strings.HasPrefix(msg, prefix) {
		return ""
	}
	return strings.TrimSpace(msg[len(prefix):])
}

func enrichUnknownVariable(vars map[string]float64, unknown string) (map[string]float64, bool) {
	key := strings.TrimSpace(unknown)
	if key == "" {
		return vars, false
	}
	if _, ok := vars[key]; ok {
		return vars, false
	}

	clone := func() map[string]float64 {
		out := make(map[string]float64, len(vars)+2)
		for k, v := range vars {
			out[k] = v
		}
		return out
	}

	// app_server_up 缺失时，回退到通用 server_up。
	if strings.HasSuffix(key, "_server_up") {
		if v, ok := vars["server_up"]; ok {
			out := clone()
			out[key] = v
			return out, true
		}
	}

	// 尝试从 "<metric_group>_<field>" 形式反向映射到 "<field>"。
	needle := "_" + key
	var (
		hitValue float64
		hitCount int
	)
	for k, v := range vars {
		if strings.HasSuffix(k, needle) {
			hitValue = v
			hitCount++
			if hitCount > 1 {
				break
			}
		}
	}
	if hitCount == 1 {
		out := clone()
		out[key] = hitValue
		return out, true
	}
	return vars, false
}

func renderAlertTemplate(tpl string, ev alert.Event, metric string, value float64) string {
	labels := map[string]string{}
	for k, v := range ev.Labels {
		key := strings.TrimSpace(k)
		val := strings.TrimSpace(v)
		if key == "" || val == "" {
			continue
		}
		labels[key] = val
	}
	labels["monitor_id"] = strconv.FormatInt(ev.MonitorID, 10)
	labels["severity"] = strings.TrimSpace(ev.Severity)
	labels["app"] = strings.TrimSpace(ev.App)
	labels["instance"] = strings.TrimSpace(ev.Instance)
	labels["metric"] = strings.TrimSpace(metric)
	labels["status"] = eventStatusText(ev)

	ci := map[string]string{}
	for key, val := range labels {
		if !strings.HasPrefix(key, "ci.") {
			continue
		}
		ciKey := strings.TrimSpace(strings.TrimPrefix(key, "ci."))
		if ciKey == "" {
			continue
		}
		ci[ciKey] = val
	}
	repl := map[string]string{
		"$value":           strconv.FormatFloat(value, 'f', -1, 64),
		"$rule_name":       ev.RuleName,
		"$monitor_id":      strconv.FormatInt(ev.MonitorID, 10),
		"$severity":        ev.Severity,
		"$expression":      ev.Expression,
		"$status":          labels["status"],
		"$labels.instance": labels["instance"],
		"$labels.app":      labels["app"],
		"$labels.metric":   labels["metric"],
	}
	content := tpl
	for key, val := range repl {
		content = strings.ReplaceAll(content, "{{"+key+"}}", val)
		content = strings.ReplaceAll(content, "{{ "+key+" }}", val)
	}
	for key, val := range labels {
		token := "$labels." + key
		content = strings.ReplaceAll(content, "{{"+token+"}}", val)
		content = strings.ReplaceAll(content, "{{ "+token+" }}", val)
	}
	for key, val := range ci {
		token := "$ci." + key
		content = strings.ReplaceAll(content, "{{"+token+"}}", val)
		content = strings.ReplaceAll(content, "{{ "+token+" }}", val)
	}
	return strings.TrimSpace(content)
}

func annotationString(def store.RuntimeAlertRule, key string) string {
	if def.Annotations == nil {
		return ""
	}
	raw, ok := def.Annotations[key]
	if !ok {
		return ""
	}
	return strings.TrimSpace(fmt.Sprintf("%v", raw))
}

func renderAlertTitle(def store.RuntimeAlertRule, ev alert.Event, metric string, value float64) string {
	tpl := annotationString(def, "title_template")
	if tpl == "" {
		tpl = annotationString(def, "title")
	}
	if tpl == "" {
		tpl = "[{{$severity}}] {{$rule_name}} - {{$labels.app}}/{{$labels.instance}}"
	}
	title := renderAlertTemplate(tpl, ev, metric, value)
	if title == "" {
		return fmt.Sprintf("[%s] %s", strings.TrimSpace(ev.Severity), strings.TrimSpace(ev.RuleName))
	}
	return title
}

func renderAlertContent(def store.RuntimeAlertRule, ev alert.Event, metric string, value float64) string {
	tpl := strings.TrimSpace(def.Template)
	if tpl == "" {
		tpl = "[{{$severity}}] {{$rule_name}}\n应用: {{$labels.app}}\n实例: {{$labels.instance}}\n指标: {{$labels.metric}}\n当前值: {{$value}}\n触发条件: {{$expression}}"
	}
	content := renderAlertTemplate(tpl, ev, metric, value)
	if content == "" {
		return fmt.Sprintf("[%s] %s", strings.TrimSpace(ev.Severity), strings.TrimSpace(ev.RuleName))
	}
	return content
}

func buildEventLabels(def store.RuntimeAlertRule, point model.MetricPoint) map[string]string {
	out := map[string]string{
		"monitor_id": strconv.FormatInt(point.MonitorID, 10),
		"app":        strings.TrimSpace(point.App),
		"instance":   strings.TrimSpace(point.Instance),
		"metric":     strings.TrimSpace(point.Field),
		"metrics":    strings.TrimSpace(point.Metrics),
	}
	for key, val := range point.Labels {
		k := strings.TrimSpace(key)
		v := strings.TrimSpace(val)
		if k == "" || v == "" {
			continue
		}
		out[k] = v
	}
	for key, raw := range def.Labels {
		k := strings.TrimSpace(key)
		if k == "" {
			continue
		}
		out[k] = strings.TrimSpace(fmt.Sprintf("%v", raw))
	}
	return out
}

func readStringLabel(labels map[string]string, key string, def string) string {
	if len(labels) == 0 {
		return def
	}
	v := strings.TrimSpace(labels[key])
	if v == "" {
		return def
	}
	return v
}

func periodicRunKey(monitorID int64, ruleID int64) string {
	return fmt.Sprintf("%d:%d", monitorID, ruleID)
}

func convertGroupRules(rows []store.RuntimeAlertGroup) []alert.GroupRule {
	out := make([]alert.GroupRule, 0, len(rows))
	for _, row := range rows {
		interval := row.GroupInterval
		if interval <= 0 {
			interval = row.GroupWaitSec
		}
		if interval <= 0 {
			interval = 60
		}
		out = append(out, alert.GroupRule{
			ID:             row.ID,
			GroupKey:       strings.TrimSpace(row.GroupKey),
			MatchType:      row.MatchType,
			GroupLabels:    row.GroupLabels,
			GroupInterval:  time.Duration(interval) * time.Second,
			RepeatInterval: time.Duration(maxInt(row.RepeatInterval, 0)) * time.Second,
		})
	}
	return out
}

func convertInhibitRules(rows []store.RuntimeAlertInhibit) []alert.InhibitRule {
	out := make([]alert.InhibitRule, 0, len(rows))
	for _, row := range rows {
		out = append(out, alert.InhibitRule{
			ID:           row.ID,
			SourceLabels: row.SourceLabels,
			TargetLabels: row.TargetLabels,
			EqualLabels:  row.EqualLabels,
		})
	}
	return out
}

func convertSilenceRules(rows []store.RuntimeAlertSilence) []alert.SilenceRule {
	out := make([]alert.SilenceRule, 0, len(rows))
	for _, row := range rows {
		days := map[int]struct{}{}
		for _, day := range row.Days {
			if day >= 1 && day <= 7 {
				days[day] = struct{}{}
			}
		}
		out = append(out, alert.SilenceRule{
			ID:        row.ID,
			Type:      row.Type,
			MatchType: row.MatchType,
			Labels:    row.Labels,
			Days:      days,
			StartAtMs: row.StartAtMs,
			EndAtMs:   row.EndAtMs,
		})
	}
	return out
}

func ruleAutoRecoverEnabled(def store.RuntimeAlertRule) bool {
	return getLabelBool(def.Labels, true, "auto_recover", "recover_auto_close")
}

func ruleRecoverTimes(def store.RuntimeAlertRule) int {
	return maxInt(getLabelInt(def.Labels, 2, "recover_times", "auto_recover_times"), 1)
}

func ruleNotifyOnRecovered(def store.RuntimeAlertRule) bool {
	return getLabelBool(def.Labels, true, "notify_on_recovered", "recover_notify")
}

func getLabelBool(labels map[string]any, def bool, keys ...string) bool {
	if len(labels) == 0 {
		return def
	}
	for _, key := range keys {
		v, ok := labels[key]
		if !ok {
			continue
		}
		switch t := v.(type) {
		case bool:
			return t
		case string:
			normalized := strings.TrimSpace(strings.ToLower(t))
			switch normalized {
			case "1", "true", "yes", "on":
				return true
			case "0", "false", "no", "off":
				return false
			}
		case float64:
			return t != 0
		case int:
			return t != 0
		}
	}
	return def
}

func getLabelInt(labels map[string]any, def int, keys ...string) int {
	if len(labels) == 0 {
		return def
	}
	for _, key := range keys {
		v, ok := labels[key]
		if !ok {
			continue
		}
		switch t := v.(type) {
		case float64:
			return int(t)
		case int:
			return t
		case string:
			text := strings.TrimSpace(t)
			if text == "" {
				continue
			}
			parsed, err := strconv.Atoi(text)
			if err == nil {
				return parsed
			}
		}
	}
	return def
}

func eventStatusText(ev alert.Event) string {
	if ev.State == alert.StateNormal {
		return "recovered"
	}
	return "firing"
}

func formatNotifyTime(t time.Time) string {
	if t.IsZero() {
		t = time.Now()
	}
	return t.Local().Format("2006-01-02 15:04:05")
}

func maxInt(a, b int) int {
	if a >= b {
		return a
	}
	return b
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
	service       *notify.Service
	template      string
	batchTemplate string
	title         string
	channels      []notify.ChannelType
	configs       map[notify.ChannelType]json.RawMessage
	runtimeStore  *store.AlertRuntimeStore
	cacheMu       sync.Mutex
	noticeCache   map[int64]cachedNoticeDispatch
	cacheTTL      time.Duration
	limitMu       sync.Mutex
	notifyLimits  map[string]notifyLimitState
	limitTTL      time.Duration
	batchMu       sync.Mutex
	batchWindow   time.Duration
	batchBuckets  map[int64]*batchBucket
}

type cachedNoticeDispatch struct {
	dispatch store.NoticeDispatch
	expireAt time.Time
}

type notifyLimitState struct {
	count   int
	updated time.Time
}

type batchBucket struct {
	dispatch store.NoticeDispatch
	channel  notify.ChannelType
	config   json.RawMessage
	template string
	firstAt  time.Time
	lastAt   time.Time
	alerts   []map[string]any
}

func newNotifySender(runtimeStore *store.AlertRuntimeStore) *notifySender {
	channels := parseNotifyChannels(getenv("MANAGER_NOTIFY_CHANNELS", "webhook"))
	configs := map[notify.ChannelType]json.RawMessage{
		notify.ChannelWebhook: json.RawMessage(getenv("MANAGER_NOTIFY_WEBHOOK_CONFIG", "{}")),
		notify.ChannelEmail:   json.RawMessage(getenv("MANAGER_NOTIFY_EMAIL_CONFIG", "{}")),
		notify.ChannelWeCom:   json.RawMessage(getenv("MANAGER_NOTIFY_WECOM_CONFIG", "{}")),
	}
	sender := &notifySender{
		service:       notify.NewService(),
		template:      getenv("MANAGER_NOTIFY_TEMPLATE", "【{{.severity}}】{{.rule_name}}\n对象: {{.app}}/{{.instance}} (monitor={{.monitor_id}})\n内容: {{.content}}\n时间: {{.triggered_at}}"),
		batchTemplate: getenv("MANAGER_NOTIFY_BATCH_TEMPLATE", "批量告警 {{.count}} 条，最近一条：{{.last_rule_name}} monitor={{.last_monitor_id}} severity={{.last_severity}}"),
		title:         getenv("MANAGER_NOTIFY_TITLE", "Arco Monitoring Alert"),
		channels:      channels,
		configs:       configs,
		runtimeStore:  runtimeStore,
		noticeCache:   map[int64]cachedNoticeDispatch{},
		cacheTTL:      30 * time.Second,
		notifyLimits:  map[string]notifyLimitState{},
		limitTTL:      24 * time.Hour,
		batchWindow:   10 * time.Second,
		batchBuckets:  map[int64]*batchBucket{},
	}
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			_ = sender.flushDueBatches(context.Background(), false)
		}
	}()
	return sender
}

func (s *notifySender) Send(ctx context.Context, task alert.NotifyTask) error {
	var (
		channels     []notify.ChannelType
		configs      map[notify.ChannelType]json.RawMessage
		templateText = s.template
	)
	titleText := strings.TrimSpace(task.Event.Title)
	if titleText == "" {
		titleText = s.title
	}
	payloadLabels := map[string]string{
		"app":      strings.TrimSpace(task.Event.App),
		"instance": strings.TrimSpace(task.Event.Instance),
	}
	for k, v := range task.Event.Labels {
		key := strings.TrimSpace(k)
		val := strings.TrimSpace(v)
		if key == "" || val == "" {
			continue
		}
		payloadLabels[key] = val
	}
	ciVars := map[string]string{}
	for key, val := range payloadLabels {
		if !strings.HasPrefix(key, "ci.") {
			continue
		}
		ciKey := strings.TrimSpace(strings.TrimPrefix(key, "ci."))
		if ciKey == "" {
			continue
		}
		ciVars[ciKey] = val
	}
	payload := map[string]any{
		"title":            titleText,
		"rule_name":        task.Event.RuleName,
		"notice_rule_id":   task.Event.NoticeRuleID,
		"monitor_id":       task.Event.MonitorID,
		"app":              task.Event.App,
		"instance":         task.Event.Instance,
		"severity":         task.Event.Severity,
		"status":           eventStatusText(task.Event),
		"content":          task.Event.Content,
		"expression":       task.Event.Expression,
		"elapsed_ms":       task.Event.ElapsedMs,
		"triggered_at":     formatNotifyTime(task.Event.TriggeredAt),
		"triggered_at_iso": task.Event.TriggeredAt.Format(time.RFC3339),
		"labels":           payloadLabels,
		"ci":               ciVars,
	}
	if task.Event.NoticeRuleID > 0 {
		dispatch, err := s.loadNoticeDispatch(task.Event.NoticeRuleID)
		if err != nil {
			return fmt.Errorf("load notice dispatch failed notice_rule_id=%d: %w", task.Event.NoticeRuleID, err)
		}
		log.Printf("[INFO] notify dispatch resolved rule=%s monitor=%d notice_rule_id=%d channel=%s",
			task.Event.RuleName, task.Event.MonitorID, dispatch.NoticeRuleID, dispatch.Channel)
		eventLabels := map[string]string{
			"severity":   strings.TrimSpace(task.Event.Severity),
			"monitor_id": strconv.FormatInt(task.Event.MonitorID, 10),
			"app":        strings.TrimSpace(task.Event.App),
			"instance":   strings.TrimSpace(task.Event.Instance),
			"rule_name":  strings.TrimSpace(task.Event.RuleName),
		}
		for k, v := range task.Event.Labels {
			key := strings.TrimSpace(k)
			if key == "" {
				continue
			}
			eventLabels[key] = strings.TrimSpace(v)
		}
		if !dispatch.MatchTime(time.Now()) {
			log.Printf("[INFO] notify skipped by time window rule=%s monitor=%d notice_rule_id=%d",
				task.Event.RuleName, task.Event.MonitorID, dispatch.NoticeRuleID)
			return nil
		}
		if !dispatch.MatchEventLabels(eventLabels) {
			log.Printf("[INFO] notify skipped by label filter rule=%s monitor=%d notice_rule_id=%d",
				task.Event.RuleName, task.Event.MonitorID, dispatch.NoticeRuleID)
			return nil
		}
		if !s.allowNotify(task.Event, dispatch) {
			log.Printf("[INFO] notify skipped by notify_times rule=%s monitor=%d notice_rule_id=%d",
				task.Event.RuleName, task.Event.MonitorID, dispatch.NoticeRuleID)
			return nil
		}
		ch, ok := parseNotifyChannel(dispatch.Channel)
		if !ok {
			return fmt.Errorf("unsupported notice dispatch channel=%s notice_rule_id=%d", dispatch.Channel, dispatch.NoticeRuleID)
		}
		if dispatch.NotifyScale == "batch" {
			s.enqueueBatch(dispatch, ch, dispatch.Config, s.batchTemplate, task.Event)
			log.Printf("[INFO] notify enqueued batch rule=%s monitor=%d notice_rule_id=%d channel=%s",
				task.Event.RuleName, task.Event.MonitorID, dispatch.NoticeRuleID, ch)
			return s.flushDueBatches(ctx, false)
		}
		channels = []notify.ChannelType{ch}
		configs = map[notify.ChannelType]json.RawMessage{ch: dispatch.Config}
		if ch == notify.ChannelSystem {
			body, err := notify.Render(templateText, payload)
			if err != nil {
				return err
			}
			if s.runtimeStore == nil {
				return fmt.Errorf("runtime store unavailable for system notification")
			}
			if err := s.runtimeStore.SendSystemNotification(titleText, body, dispatch.RecipientType, dispatch.RecipientIDs, dispatch.IncludeSubDept); err != nil {
				return err
			}
			log.Printf("[INFO] system notification sent rule=%s monitor=%d notice_rule_id=%d recipients=%d recipient_type=%s",
				task.Event.RuleName, task.Event.MonitorID, dispatch.NoticeRuleID, len(dispatch.RecipientIDs), dispatch.RecipientType)
			return nil
		}
	} else {
		channels, configs = s.resolveDefaultChannels()
		if len(channels) == 0 {
			log.Printf("[INFO] notify skipped rule=%s monitor=%d notice_rule_id=0 reason=no valid default channel configured",
				task.Event.RuleName, task.Event.MonitorID)
			return nil
		}
	}
	if len(channels) == 0 {
		return fmt.Errorf("no notify channel configured")
	}
	alertID := int64(0)
	if s.runtimeStore != nil {
		id, err := s.runtimeStore.FindCurrentAlertID(task.Event.RuleID, task.Event.MonitorID)
		if err != nil {
			log.Printf("[WARN] resolve current alert id failed rule=%d monitor=%d err=%v", task.Event.RuleID, task.Event.MonitorID, err)
		} else {
			alertID = id
		}
	}
	var errs []string
	for _, ch := range channels {
		body, renderErr := notify.Render(templateText, payload)
		if renderErr != nil {
			errs = append(errs, string(ch)+": "+renderErr.Error())
			log.Printf("[ERROR] notify content render failed rule=%s monitor=%d notice_rule_id=%d channel=%s err=%v",
				task.Event.RuleName, task.Event.MonitorID, task.Event.NoticeRuleID, ch, renderErr)
			continue
		}
		req := notify.TestSendRequest{
			Channel:  ch,
			Title:    titleText,
			Template: templateText,
			Data:     payload,
			Config:   configs[ch],
		}
		if err := s.service.TestSend(ctx, req); err != nil {
			errs = append(errs, string(ch)+": "+err.Error())
			log.Printf("[ERROR] notify channel send failed rule=%s monitor=%d notice_rule_id=%d channel=%s err=%v",
				task.Event.RuleName, task.Event.MonitorID, task.Event.NoticeRuleID, ch, err)
			if s.runtimeStore != nil && alertID > 0 {
				_ = s.runtimeStore.SaveAlertNotification(alertID, task.Event.RuleID, string(ch), 3, body, err.Error(), task.Attempt+1)
			}
			continue
		}
		log.Printf("[INFO] notify channel sent rule=%s monitor=%d notice_rule_id=%d channel=%s",
			task.Event.RuleName, task.Event.MonitorID, task.Event.NoticeRuleID, ch)
		if s.runtimeStore != nil && alertID > 0 {
			_ = s.runtimeStore.SaveAlertNotification(alertID, task.Event.RuleID, string(ch), 2, body, "", task.Attempt)
		}
	}
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}

func (s *notifySender) allowNotify(ev alert.Event, dispatch store.NoticeDispatch) bool {
	if ev.State == alert.StateNormal {
		// 恢复通知由状态迁移触发，不受 firing 次数限流影响。
		return true
	}
	limit := dispatch.NotifyTimes
	if limit <= 0 {
		limit = 1
	}
	now := time.Now()
	key := fmt.Sprintf("%d:%d:%d", dispatch.NoticeRuleID, ev.RuleID, ev.MonitorID)
	s.limitMu.Lock()
	defer s.limitMu.Unlock()
	cur, ok := s.notifyLimits[key]
	if ok && now.Sub(cur.updated) > s.limitTTL {
		cur = notifyLimitState{}
	}
	if cur.count >= limit {
		return false
	}
	cur.count++
	cur.updated = now
	s.notifyLimits[key] = cur
	return true
}

func (s *notifySender) ResetNotifyLimits(ruleID int64, monitorID int64) {
	if ruleID <= 0 || monitorID <= 0 {
		return
	}
	suffix := fmt.Sprintf(":%d:%d", ruleID, monitorID)
	s.limitMu.Lock()
	defer s.limitMu.Unlock()
	for key := range s.notifyLimits {
		if strings.HasSuffix(key, suffix) {
			delete(s.notifyLimits, key)
		}
	}
}

func (s *notifySender) enqueueBatch(dispatch store.NoticeDispatch, channel notify.ChannelType, cfg json.RawMessage, template string, ev alert.Event) {
	now := time.Now()
	item := map[string]any{
		"rule_name":        ev.RuleName,
		"notice_rule_id":   ev.NoticeRuleID,
		"monitor_id":       ev.MonitorID,
		"app":              ev.App,
		"instance":         ev.Instance,
		"severity":         ev.Severity,
		"status":           eventStatusText(ev),
		"content":          ev.Content,
		"expression":       ev.Expression,
		"elapsed_ms":       ev.ElapsedMs,
		"triggered_at":     formatNotifyTime(ev.TriggeredAt),
		"triggered_at_iso": ev.TriggeredAt.Format(time.RFC3339),
	}
	s.batchMu.Lock()
	defer s.batchMu.Unlock()
	b := s.batchBuckets[dispatch.NoticeRuleID]
	if b == nil {
		b = &batchBucket{
			dispatch: dispatch,
			channel:  channel,
			config:   cfg,
			template: template,
			firstAt:  now,
			lastAt:   now,
			alerts:   make([]map[string]any, 0, 8),
		}
		s.batchBuckets[dispatch.NoticeRuleID] = b
	}
	b.lastAt = now
	b.alerts = append(b.alerts, item)
}

func (s *notifySender) flushDueBatches(ctx context.Context, force bool) error {
	now := time.Now()
	var pending []*batchBucket
	s.batchMu.Lock()
	for noticeID, bucket := range s.batchBuckets {
		if bucket == nil || len(bucket.alerts) == 0 {
			delete(s.batchBuckets, noticeID)
			continue
		}
		if !force && now.Sub(bucket.firstAt) < s.batchWindow && len(bucket.alerts) < 20 {
			continue
		}
		pending = append(pending, bucket)
		delete(s.batchBuckets, noticeID)
	}
	s.batchMu.Unlock()
	if len(pending) == 0 {
		return nil
	}
	var errs []string
	for _, bucket := range pending {
		last := bucket.alerts[len(bucket.alerts)-1]
		data := map[string]any{
			"count":           len(bucket.alerts),
			"alerts":          bucket.alerts,
			"last_rule_name":  last["rule_name"],
			"last_monitor_id": last["monitor_id"],
			"last_severity":   last["severity"],
			"last_content":    last["content"],
		}
		if bucket.channel == notify.ChannelSystem {
			body, err := notify.Render(bucket.template, data)
			if err != nil {
				errs = append(errs, fmt.Sprintf("notice_rule_id=%d channel=%s err=%v", bucket.dispatch.NoticeRuleID, bucket.channel, err))
				continue
			}
			if s.runtimeStore == nil {
				errs = append(errs, fmt.Sprintf("notice_rule_id=%d channel=%s err=runtime store unavailable", bucket.dispatch.NoticeRuleID, bucket.channel))
				continue
			}
			if err := s.runtimeStore.SendSystemNotification(s.title, body, bucket.dispatch.RecipientType, bucket.dispatch.RecipientIDs, bucket.dispatch.IncludeSubDept); err != nil {
				errs = append(errs, fmt.Sprintf("notice_rule_id=%d channel=%s err=%v", bucket.dispatch.NoticeRuleID, bucket.channel, err))
			}
			continue
		}
		req := notify.TestSendRequest{
			Channel:  bucket.channel,
			Title:    s.title,
			Template: bucket.template,
			Data:     data,
			Config:   bucket.config,
		}
		if err := s.service.TestSend(ctx, req); err != nil {
			errs = append(errs, fmt.Sprintf("notice_rule_id=%d channel=%s err=%v", bucket.dispatch.NoticeRuleID, bucket.channel, err))
		}
	}
	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}

func (s *notifySender) loadNoticeDispatch(noticeRuleID int64) (store.NoticeDispatch, error) {
	if s.runtimeStore == nil {
		return store.NoticeDispatch{}, fmt.Errorf("notice runtime store unavailable")
	}
	now := time.Now()
	s.cacheMu.Lock()
	if cached, ok := s.noticeCache[noticeRuleID]; ok && now.Before(cached.expireAt) {
		s.cacheMu.Unlock()
		return cached.dispatch, nil
	}
	s.cacheMu.Unlock()

	dispatch, err := s.runtimeStore.LoadNoticeDispatch(noticeRuleID)
	if err != nil {
		return store.NoticeDispatch{}, err
	}
	s.cacheMu.Lock()
	s.noticeCache[noticeRuleID] = cachedNoticeDispatch{
		dispatch: dispatch,
		expireAt: now.Add(s.cacheTTL),
	}
	s.cacheMu.Unlock()
	return dispatch, nil
}

func parseNotifyChannel(raw string) (notify.ChannelType, bool) {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case string(notify.ChannelWebhook):
		return notify.ChannelWebhook, true
	case string(notify.ChannelEmail):
		return notify.ChannelEmail, true
	case string(notify.ChannelWeCom):
		return notify.ChannelWeCom, true
	case string(notify.ChannelSystem):
		return notify.ChannelSystem, true
	default:
		return "", false
	}
}

func (s *notifySender) resolveDefaultChannels() ([]notify.ChannelType, map[notify.ChannelType]json.RawMessage) {
	outChannels := make([]notify.ChannelType, 0, len(s.channels))
	outConfigs := map[notify.ChannelType]json.RawMessage{}
	for _, ch := range s.channels {
		if ch == notify.ChannelSystem {
			// 系统消息需要 notice rule 的接收人上下文，默认通道不支持。
			continue
		}
		cfg, ok := s.configs[ch]
		if !ok || !s.isDefaultChannelConfigured(ch, cfg) {
			continue
		}
		outChannels = append(outChannels, ch)
		outConfigs[ch] = cfg
	}
	return outChannels, outConfigs
}

func (s *notifySender) isDefaultChannelConfigured(ch notify.ChannelType, raw json.RawMessage) bool {
	switch ch {
	case notify.ChannelWebhook:
		var cfg notify.WebhookConfig
		if err := json.Unmarshal(raw, &cfg); err != nil {
			return false
		}
		return strings.TrimSpace(cfg.URL) != ""
	case notify.ChannelEmail:
		var cfg notify.EmailConfig
		if err := json.Unmarshal(raw, &cfg); err != nil {
			return false
		}
		return strings.TrimSpace(cfg.Host) != "" &&
			cfg.Port > 0 &&
			strings.TrimSpace(cfg.From) != "" &&
			strings.TrimSpace(cfg.To) != ""
	case notify.ChannelWeCom:
		var cfg notify.WeComConfig
		if err := json.Unmarshal(raw, &cfg); err != nil {
			return false
		}
		return strings.TrimSpace(cfg.WebhookURL) != ""
	default:
		return false
	}
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
		case string(notify.ChannelSystem):
			out = append(out, notify.ChannelSystem)
		}
	}
	return out
}

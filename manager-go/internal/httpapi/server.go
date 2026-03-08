package httpapi

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/collector"
	"manager-go/internal/model"
	"manager-go/internal/notify"
	"manager-go/internal/store"
)

type Server struct {
	store            *store.MonitorStore
	notifier         *notify.Service
	mux              *http.ServeMux
	resources        *resourceHub
	registry         *collector.Registry
	collectorTO      time.Duration
	ingestMetric     func(model.MetricPoint) error
	alertStore       *alert.AlertStore
	deadLetterStore  *alert.DeadLetterStore
	retryDeadLetter  func(int64) error
	collectorManager *collector.Manager
}

type Option func(*Server)

func WithResourceHub(hub *resourceHub) Option {
	return func(s *Server) {
		if hub != nil {
			s.resources = hub
		}
	}
}

func WithCollectorRegistry(reg *collector.Registry, timeout time.Duration) Option {
	return func(s *Server) {
		s.registry = reg
		s.collectorTO = timeout
	}
}

func WithCollectorManager(mgr *collector.Manager) Option {
	return func(s *Server) {
		s.collectorManager = mgr
	}
}

func WithMetricIngest(fn func(model.MetricPoint) error) Option {
	return func(s *Server) {
		s.ingestMetric = fn
	}
}

func WithAlertStore(st *alert.AlertStore) Option {
	return func(s *Server) {
		s.alertStore = st
	}
}

func WithDeadLetterStore(st *alert.DeadLetterStore, retryFn func(int64) error) Option {
	return func(s *Server) {
		s.deadLetterStore = st
		s.retryDeadLetter = retryFn
	}
}

func NewServer(st *store.MonitorStore, opts ...Option) *Server {
	s := &Server{
		store:     st,
		notifier:  notify.NewService(),
		mux:       http.NewServeMux(),
		resources: newResourceHub(),
	}
	for _, opt := range opts {
		opt(s)
	}
	s.routes()
	return s
}

func (s *Server) Handler() http.Handler {
	return s.mux
}

func (s *Server) routes() {
	s.mux.HandleFunc("/api/v1/health", s.handleHealth)
	s.mux.HandleFunc("/api/v1/monitors", s.handleMonitors)
	s.mux.HandleFunc("/api/v1/monitors/", s.handleMonitorByID)
	s.mux.HandleFunc("/api/v1/notify/test", s.handleNotifyTest)
	// 注意：更具体的路由必须在通用路由之前注册
	s.mux.HandleFunc("/api/v1/collectors/register", s.handleCollectorRegister)
	s.mux.HandleFunc("/api/v1/collectors/assignments", s.handleCollectorAssignments)
	s.mux.HandleFunc("/api/v1/collectors/", s.handleCollectorByID)
	s.mux.HandleFunc("/api/v1/collectors", s.handleCollectors)
	s.mux.HandleFunc("/api/v1/metrics", s.handleMetricsIngest)
	s.mux.HandleFunc("/api/v1/alerts", s.handleAlerts)
	s.mux.HandleFunc("/api/v1/alerts/history", s.handleAlertsHistory)
	s.mux.HandleFunc("/api/v1/alerts/", s.handleAlertByID)
	s.mux.HandleFunc("/api/v1/dead-letters", s.handleDeadLetters)
	s.mux.HandleFunc("/api/v1/dead-letters/", s.handleDeadLetterByID)
	s.mux.HandleFunc("/api/v1/alert-rules", s.handleAlertRules)
	s.mux.HandleFunc("/api/v1/alert-rules/", s.handleAlertRuleByID)
	s.mux.HandleFunc("/api/v1/alert-integrations", s.handleAlertIntegrations)
	s.mux.HandleFunc("/api/v1/alert-integrations/", s.handleAlertIntegrationByID)
	s.mux.HandleFunc("/api/v1/alert-groups", s.handleAlertGroups)
	s.mux.HandleFunc("/api/v1/alert-groups/", s.handleAlertGroupByID)
	s.mux.HandleFunc("/api/v1/alert-inhibits", s.handleAlertInhibits)
	s.mux.HandleFunc("/api/v1/alert-inhibits/", s.handleAlertInhibitByID)
	s.mux.HandleFunc("/api/v1/alert-silences", s.handleAlertSilences)
	s.mux.HandleFunc("/api/v1/alert-silences/", s.handleAlertSilenceByID)
	s.mux.HandleFunc("/api/v1/alert-notices", s.handleAlertNotices)
	s.mux.HandleFunc("/api/v1/alert-notices/", s.handleAlertNoticeByID)
	s.mux.HandleFunc("/api/v1/labels", s.handleLabels)
	s.mux.HandleFunc("/api/v1/labels/", s.handleLabelByID)
	s.mux.HandleFunc("/api/v1/status-pages", s.handleStatusPages)
	s.mux.HandleFunc("/api/v1/status-pages/", s.handleStatusPageByID)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "service": "manager-go"})
}

func (s *Server) handleMonitors(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var in model.MonitorCreateInput
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		m, err := s.store.Create(in)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, m)
	case http.MethodGet:
		items := s.store.List()
		writeJSON(w, http.StatusOK, map[string]any{
			"items":     items,
			"page":      1,
			"page_size": len(items),
			"total":     len(items),
		})
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleMonitorByID(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/monitors/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		w.WriteHeader(http.StatusNotFound)
		return
	}
	id, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "invalid monitor id")
		return
	}
	if len(parts) == 1 {
		s.handleMonitorCRUD(w, r, id)
		return
	}
	if len(parts) == 2 && r.Method == http.MethodPatch && (parts[1] == "enable" || parts[1] == "disable") {
		s.handleEnableDisable(w, r, id, parts[1] == "enable")
		return
	}
	w.WriteHeader(http.StatusNotFound)
}

func (s *Server) handleNotifyTest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var req notify.TestSendRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	if err := s.notifier.TestSend(r.Context(), req); err != nil {
		writeErr(w, http.StatusBadRequest, "NOTIFY_SEND_FAILED", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (s *Server) handleCollectorRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		ID      string `json:"id"`
		Addr    string `json:"addr"`
		Version string `json:"version"`
		Mode    string `json:"mode"`
		IP      string `json:"ip"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	if req.ID == "" {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "id is required")
		return
	}
	if req.Addr == "" {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "addr is required")
		return
	}
	if req.Mode == "" {
		req.Mode = "public"
	}

	// 优先使用 collectorManager（数据库 + gRPC）
	if s.collectorManager != nil {
		if err := s.collectorManager.RegisterWithInfo(req.ID, req.Addr, req.IP, req.Version, req.Mode); err != nil {
			writeErr(w, http.StatusConflict, "COLLECTOR_EXISTS", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"id":      req.ID,
			"addr":    req.Addr,
			"version": req.Version,
			"mode":    req.Mode,
			"status":  "registered",
		})
		return
	}

	// 回退到 registry（内存）
	if s.registry == nil {
		writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector registry not configured")
		return
	}
	n := s.registry.Upsert(req.ID, req.Addr)
	writeJSON(w, http.StatusOK, n)
}

func (s *Server) handleCollectors(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	// 优先从 collectorManager 获取（数据库）
	if s.collectorManager != nil {
		collectors, err := s.collectorManager.GetCollectorList()
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "DB_ERROR", err.Error())
			return
		}

		// 转换为响应格式
		items := make([]map[string]any, 0, len(collectors))
		for _, c := range collectors {
			items = append(items, map[string]any{
				"id":         c.ID,
				"name":       c.Name,
				"ip":         c.IP,
				"version":    c.Version,
				"status":     c.Status,
				"mode":       c.Mode,
				"creator":    c.Creator,
				"modifier":   c.Modifier,
				"created_at": c.CreatedAt.Format(time.RFC3339),
				"updated_at": c.UpdatedAt.Format(time.RFC3339),
			})
		}

		writeJSON(w, http.StatusOK, map[string]any{
			"items":     items,
			"total":     len(items),
			"page":      1,
			"page_size": len(items),
		})
		return
	}

	// 回退到 registry（内存）
	if s.registry == nil {
		writeJSON(w, http.StatusOK, map[string]any{"items": []collector.Node{}, "total": 0})
		return
	}
	now := time.Now()
	if s.collectorTO > 0 {
		_ = s.registry.ReapExpired(s.collectorTO, now)
	}
	items := s.registry.List()
	writeJSON(w, http.StatusOK, map[string]any{
		"items":     items,
		"total":     len(items),
		"page":      1,
		"page_size": len(items),
	})
}

func (s *Server) handleCollectorAssignments(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.registry == nil {
		writeJSON(w, http.StatusOK, map[string]any{"items": []any{}, "total": 0})
		return
	}
	monitors := s.store.List()
	rows := make([]map[string]any, 0, len(monitors))
	for _, m := range monitors {
		if !m.Enabled {
			continue
		}
		n, err := s.registry.SelectByMonitor(m.ID)
		if err != nil {
			continue
		}
		rows = append(rows, map[string]any{
			"monitor_id":     m.ID,
			"monitor_name":   m.Name,
			"collector_id":   n.ID,
			"collector_addr": n.Addr,
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"items": rows, "total": len(rows), "page": 1, "page_size": len(rows)})
}

func (s *Server) handleCollectorByID(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/collectors/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		w.WriteHeader(http.StatusNotFound)
		return
	}
	collectorID := parts[0]
	if len(parts) == 1 {
		if r.Method != http.MethodDelete {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}

		// 优先使用 collectorManager
		if s.collectorManager != nil {
			s.collectorManager.Unregister(collectorID)
			w.WriteHeader(http.StatusNoContent)
			return
		}

		// 回退到 registry
		if s.registry == nil {
			writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector registry not configured")
			return
		}
		if !s.registry.Remove(collectorID) {
			writeErr(w, http.StatusNotFound, "COLLECTOR_NOT_FOUND", "collector not found")
			return
		}
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if len(parts) == 2 && parts[1] == "heartbeat" {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		if s.registry == nil {
			writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector registry not configured")
			return
		}
		if !s.registry.Touch(collectorID) {
			writeErr(w, http.StatusNotFound, "COLLECTOR_NOT_FOUND", "collector not found")
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
		return
	}
	if len(parts) == 2 && parts[1] == "tasks" {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		s.handleCollectorTasks(w, collectorID)
		return
	}
	if len(parts) == 2 && parts[1] == "reports" {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		s.handleCollectorReports(w, r, collectorID)
		return
	}
	// 下线 Collector（踢出）
	if len(parts) == 2 && parts[1] == "offline" {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		s.handleCollectorOffline(w, collectorID)
		return
	}
	// 获取 Collector 绑定的 Monitor 列表
	if len(parts) == 2 && parts[1] == "monitors" {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		s.handleCollectorMonitors(w, collectorID)
		return
	}
	w.WriteHeader(http.StatusNotFound)
}

func (s *Server) handleCollectorTasks(w http.ResponseWriter, collectorID string) {
	if s.registry == nil {
		writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector registry not configured")
		return
	}
	if !s.registry.Touch(collectorID) {
		writeErr(w, http.StatusNotFound, "COLLECTOR_NOT_FOUND", "collector not found")
		return
	}
	items := s.store.List()
	jobs := make([]model.Monitor, 0, len(items))
	for _, m := range items {
		if !m.Enabled {
			continue
		}
		n, err := s.registry.SelectByMonitor(m.ID)
		if err != nil || n.ID != collectorID {
			continue
		}
		jobs = append(jobs, m)
	}
	writeJSON(w, http.StatusOK, map[string]any{"items": jobs, "total": len(jobs), "page": 1, "page_size": len(jobs)})
}

func (s *Server) handleCollectorReports(w http.ResponseWriter, r *http.Request, collectorID string) {
	if s.registry != nil {
		if !s.registry.Touch(collectorID) {
			writeErr(w, http.StatusNotFound, "COLLECTOR_NOT_FOUND", "collector not found")
			return
		}
	}
	s.handleMetricPayload(w, r)
}

// handleCollectorOffline 处理 Collector 下线（踢出）
func (s *Server) handleCollectorOffline(w http.ResponseWriter, collectorID string) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector manager not configured")
		return
	}

	if err := s.collectorManager.GoOffline(collectorID); err != nil {
		writeErr(w, http.StatusInternalServerError, "OFFLINE_FAILED", err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"collector_id": collectorID,
		"status":       "offline",
		"message":      "Collector has been taken offline and tasks have been rebalanced",
	})
}

// handleCollectorMonitors 获取 Collector 绑定的 Monitor 列表
func (s *Server) handleCollectorMonitors(w http.ResponseWriter, collectorID string) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector manager not configured")
		return
	}

	// 获取绑定关系
	binds, err := s.collectorManager.GetCollectorStore().GetBindsByCollector(collectorID)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "DB_ERROR", err.Error())
		return
	}

	// 获取 Monitor 详情
	items := make([]map[string]any, 0, len(binds))
	for _, bind := range binds {
		monitor, err := s.store.Get(bind.MonitorID)
		if err != nil {
			continue
		}
		items = append(items, map[string]any{
			"monitor_id":   bind.MonitorID,
			"monitor_name": monitor.Name,
			"app":          monitor.App,
			"target":       monitor.Target,
			"status":       monitor.Status,
			"pinned":       bind.Pinned == 1,
			"created_at":   bind.CreatedAt.Format(time.RFC3339),
		})
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"items":     items,
		"total":     len(items),
		"page":      1,
		"page_size": len(items),
	})
}

func (s *Server) handleMetricsIngest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	s.handleMetricPayload(w, r)
}

func (s *Server) handleMetricPayload(w http.ResponseWriter, r *http.Request) {
	if s.ingestMetric == nil {
		writeErr(w, http.StatusNotImplemented, "METRIC_INGEST_UNAVAILABLE", "metric ingest not configured")
		return
	}
	var req struct {
		Items []model.MetricPoint `json:"items"`
	}
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	items := req.Items
	if len(items) == 0 {
		if req.Items == nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "items is required")
			return
		}
	}
	accepted := 0
	for _, point := range items {
		if err := s.ingestMetric(point); err != nil {
			writeErr(w, http.StatusBadGateway, "METRIC_DISPATCH_FAILED", err.Error())
			return
		}
		accepted++
	}
	writeJSON(w, http.StatusOK, map[string]any{"accepted": accepted})
}

func (s *Server) handleAlerts(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.alertStore == nil {
		writeJSON(w, http.StatusOK, map[string]any{"items": []alert.AlertRecord{}, "total": 0, "page": 1, "page_size": 20})
		return
	}
	page, pageSize := pageParams(r)
	scope := strings.TrimSpace(r.URL.Query().Get("scope"))
	status := strings.TrimSpace(r.URL.Query().Get("status"))
	items, total := s.alertStore.List(scope, status, page, pageSize)
	writeJSON(w, http.StatusOK, map[string]any{"items": items, "total": total, "page": page, "page_size": pageSize})
}

func (s *Server) handleAlertsHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.alertStore == nil {
		writeJSON(w, http.StatusOK, map[string]any{"items": []alert.AlertRecord{}, "total": 0, "page": 1, "page_size": 20})
		return
	}
	page, pageSize := pageParams(r)
	status := strings.TrimSpace(r.URL.Query().Get("status"))
	items, total := s.alertStore.List("history", status, page, pageSize)
	writeJSON(w, http.StatusOK, map[string]any{"items": items, "total": total, "page": page, "page_size": pageSize})
}

func (s *Server) handleAlertByID(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/alerts/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) != 2 {
		w.WriteHeader(http.StatusNotFound)
		return
	}
	id, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "invalid alert id")
		return
	}
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.alertStore == nil {
		writeErr(w, http.StatusNotImplemented, "ALERT_STORE_UNAVAILABLE", "alert store not configured")
		return
	}
	switch parts[1] {
	case "acknowledge":
		rec, err := s.alertStore.Acknowledge(id)
		if err != nil {
			writeAlertErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, rec)
	case "claim":
		var req struct {
			Assignee string `json:"assignee"`
			Operator string `json:"operator"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		assignee := strings.TrimSpace(req.Assignee)
		if assignee == "" {
			assignee = strings.TrimSpace(req.Operator)
		}
		rec, err := s.alertStore.Claim(id, assignee)
		if err != nil {
			writeAlertErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, rec)
	case "close":
		rec, err := s.alertStore.Close(id)
		if err != nil {
			writeAlertErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, rec)
	default:
		w.WriteHeader(http.StatusNotFound)
	}
}

func (s *Server) handleDeadLetters(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.deadLetterStore == nil {
		writeJSON(w, http.StatusOK, map[string]any{"items": []alert.DeadLetter{}, "total": 0, "page": 1, "page_size": 20})
		return
	}
	page, pageSize := pageParams(r)
	status := strings.TrimSpace(r.URL.Query().Get("status"))
	items, total := s.deadLetterStore.List(status, page, pageSize)
	writeJSON(w, http.StatusOK, map[string]any{"items": items, "total": total, "page": page, "page_size": pageSize})
}

func (s *Server) handleDeadLetterByID(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/dead-letters/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) != 2 || parts[1] != "retry" {
		w.WriteHeader(http.StatusNotFound)
		return
	}
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.retryDeadLetter == nil {
		writeErr(w, http.StatusNotImplemented, "DEAD_LETTER_RETRY_UNAVAILABLE", "dead letter retry not configured")
		return
	}
	id, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "invalid dead letter id")
		return
	}
	if err := s.retryDeadLetter(id); err != nil {
		writeErr(w, http.StatusBadRequest, "DEAD_LETTER_RETRY_FAILED", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (s *Server) handleAlertRules(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "alert-rules")
}

func (s *Server) handleAlertRuleByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/alert-rules/", "alert-rules")
}

func (s *Server) handleAlertIntegrations(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "alert-integrations")
}

func (s *Server) handleAlertIntegrationByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/alert-integrations/", "alert-integrations")
}

func (s *Server) handleAlertGroups(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "alert-groups")
}

func (s *Server) handleAlertGroupByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/alert-groups/", "alert-groups")
}

func (s *Server) handleAlertInhibits(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "alert-inhibits")
}

func (s *Server) handleAlertInhibitByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/alert-inhibits/", "alert-inhibits")
}

func (s *Server) handleAlertSilences(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "alert-silences")
}

func (s *Server) handleAlertSilenceByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/alert-silences/", "alert-silences")
}

func (s *Server) handleAlertNotices(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "alert-notices")
}

func (s *Server) handleAlertNoticeByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/alert-notices/", "alert-notices")
}

func (s *Server) handleLabels(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "labels")
}

func (s *Server) handleLabelByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/labels/", "labels")
}

func (s *Server) handleStatusPages(w http.ResponseWriter, r *http.Request) {
	s.handleResourceCollection(w, r, "status-pages")
}

func (s *Server) handleStatusPageByID(w http.ResponseWriter, r *http.Request) {
	s.handleResourceByID(w, r, "/api/v1/status-pages/", "status-pages")
}

func (s *Server) handleResourceCollection(w http.ResponseWriter, r *http.Request, name string) {
	st := s.resources.get(name)
	if st == nil {
		writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource store not found")
		return
	}
	switch r.Method {
	case http.MethodGet:
		page, pageSize := pageParams(r)
		items, total, err := st.list(page, pageSize)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"items":     items,
			"total":     total,
			"page":      page,
			"page_size": pageSize,
		})
	case http.MethodPost:
		payload, ok := decodeMapBody(w, r)
		if !ok {
			return
		}
		item, err := st.create(payload)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
			return
		}
		writeJSON(w, http.StatusCreated, item)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleResourceByID(w http.ResponseWriter, r *http.Request, prefix, name string) {
	st := s.resources.get(name)
	if st == nil {
		writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource store not found")
		return
	}
	path := strings.TrimPrefix(r.URL.Path, prefix)
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		w.WriteHeader(http.StatusNotFound)
		return
	}
	id := parts[0]
	if len(parts) == 1 {
		switch r.Method {
		case http.MethodPut:
			payload, ok := decodeMapBody(w, r)
			if !ok {
				return
			}
			item, exists, err := st.update(id, payload)
			if err != nil {
				writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
				return
			}
			if !exists {
				writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource not found")
				return
			}
			writeJSON(w, http.StatusOK, item)
		case http.MethodDelete:
			ok, err := st.delete(id)
			if err != nil {
				writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
				return
			}
			if !ok {
				writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource not found")
				return
			}
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
		return
	}
	if len(parts) == 2 {
		switch parts[1] {
		case "enable":
			if r.Method != http.MethodPatch {
				w.WriteHeader(http.StatusMethodNotAllowed)
				return
			}
			item, exists, err := st.setEnabled(id, true)
			if err != nil {
				writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
				return
			}
			if !exists {
				writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource not found")
				return
			}
			writeJSON(w, http.StatusOK, item)
			return
		case "disable":
			if r.Method != http.MethodPatch {
				w.WriteHeader(http.StatusMethodNotAllowed)
				return
			}
			item, exists, err := st.setEnabled(id, false)
			if err != nil {
				writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
				return
			}
			if !exists {
				writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource not found")
				return
			}
			writeJSON(w, http.StatusOK, item)
			return
		case "test":
			if r.Method != http.MethodPost {
				w.WriteHeader(http.StatusMethodNotAllowed)
				return
			}
			item, exists, err := st.get(id)
			if err != nil {
				writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
				return
			}
			if !exists {
				writeErr(w, http.StatusNotFound, "RESOURCE_NOT_FOUND", "resource not found")
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"status":    "ok",
				"resource":  item,
				"tested_at": time.Now().UTC().Format(time.RFC3339),
			})
			return
		}
	}
	w.WriteHeader(http.StatusNotFound)
}

func (s *Server) handleMonitorCRUD(w http.ResponseWriter, r *http.Request, id int64) {
	switch r.Method {
	case http.MethodGet:
		m, err := s.store.Get(id)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, m)
	case http.MethodPut:
		var in model.MonitorUpdateInput
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		m, err := s.store.Update(id, in)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, m)
	case http.MethodDelete:
		version, err := strconv.ParseInt(r.URL.Query().Get("version"), 10, 64)
		if err != nil || version <= 0 {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "version is required")
			return
		}
		if err := s.store.Delete(id, version); err != nil {
			writeStoreErr(w, err)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleEnableDisable(w http.ResponseWriter, r *http.Request, id int64, enabled bool) {
	var req struct {
		Version int64 `json:"version"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	m, err := s.store.SetEnabled(id, enabled, req.Version)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, m)
}

func writeStoreErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeErr(w, http.StatusNotFound, "MONITOR_NOT_FOUND", err.Error())
	case errors.Is(err, store.ErrVersionConflict):
		writeErr(w, http.StatusConflict, "MONITOR_CONFLICT", err.Error())
	case errors.Is(err, store.ErrInvalidInput):
		writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
	default:
		writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
	}
}

func writeAlertErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, alert.ErrAlertNotFound):
		writeErr(w, http.StatusNotFound, "ALERT_NOT_FOUND", err.Error())
	default:
		writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
	}
}

func writeErr(w http.ResponseWriter, status int, code string, msg string) {
	writeJSON(w, status, map[string]any{
		"error": map[string]any{
			"code":    code,
			"message": msg,
		},
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func pageParams(r *http.Request) (int, int) {
	page := atoiDefault(r.URL.Query().Get("page"), 1)
	pageSize := atoiDefault(r.URL.Query().Get("page_size"), 20)
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}
	if pageSize > 200 {
		pageSize = 200
	}
	return page, pageSize
}

func atoiDefault(raw string, def int) int {
	if strings.TrimSpace(raw) == "" {
		return def
	}
	v, err := strconv.Atoi(raw)
	if err != nil {
		return def
	}
	return v
}

func decodeMapBody(w http.ResponseWriter, r *http.Request) (map[string]any, bool) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return nil, false
	}
	if payload == nil {
		payload = map[string]any{}
	}
	return payload, true
}

package httpapi

import (
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"manager-go/internal/alert"
	"manager-go/internal/collector"
	"manager-go/internal/license"
	"manager-go/internal/metrics"
	"manager-go/internal/model"
	"manager-go/internal/notify"
	"manager-go/internal/store"
	templ "manager-go/internal/template"
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
	licenseManager   *license.Manager
	vmQuery          *metrics.VMClient
	stringLatest     func(monitorID int64, names []string) map[string]StringLatestValue
}

type Option func(*Server)

type StringLatestValue struct {
	Value     string
	Timestamp int64
}

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

func WithLicenseManager(mgr *license.Manager) Option {
	return func(s *Server) {
		s.licenseManager = mgr
	}
}

func WithVMQueryClient(client *metrics.VMClient) Option {
	return func(s *Server) {
		s.vmQuery = client
	}
}

func WithStringLatestProvider(provider func(monitorID int64, names []string) map[string]StringLatestValue) Option {
	return func(s *Server) {
		s.stringLatest = provider
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
	s.mux.HandleFunc("/api/v1/license/status", s.handleLicenseStatus)
	s.mux.HandleFunc("/api/v1/license/upload", s.handleLicenseUpload)
	s.mux.HandleFunc("/api/v1/monitors", s.handleMonitors)
	s.mux.HandleFunc("/api/v1/monitors/", s.handleMonitorByID)
	s.mux.HandleFunc("/api/v1/notify/test", s.handleNotifyTest)
	// 注意：更具体的路由必须在通用路由之前注册
	s.mux.HandleFunc("/api/v1/collectors/register", s.handleCollectorRegister)
	s.mux.HandleFunc("/api/v1/collectors/assignments", s.handleCollectorAssignments)
	s.mux.HandleFunc("/api/v1/collectors/", s.handleCollectorByID)
	s.mux.HandleFunc("/api/v1/collectors", s.handleCollectors)
	s.mux.HandleFunc("/api/v1/metrics/series", s.handleMetricsSeries)
	s.mux.HandleFunc("/api/v1/metrics/query-range", s.handleMetricsQueryRange)
	s.mux.HandleFunc("/api/v1/metrics/latest", s.handleMetricsLatest)
	s.mux.HandleFunc("/api/v1/metrics/export", s.handleMetricsExport)
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
		if in.Enabled && s.licenseManager != nil {
			if err := s.licenseManager.ValidateEnableAllowed(); err != nil {
				writeErr(w, http.StatusPaymentRequired, "LICENSE_LIMIT_EXCEEDED", err.Error())
				return
			}
		}
		candidate := model.Monitor{
			ID:              0,
			Name:            in.Name,
			App:             in.App,
			Target:          in.Target,
			TemplateID:      in.TemplateID,
			IntervalSeconds: normalizeInterval(in.IntervalSeconds, in.Interval),
			Params:          in.Params,
			Enabled:         in.Enabled,
		}
		in.Params = s.sanitizePersistableParams(&candidate, in.Params)
		candidate.Params = in.Params
		if err := s.preCompileAndAudit(&candidate, "create"); err != nil {
			writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
			return
		}
		m, err := s.store.Create(in)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		if s.collectorManager != nil && m.Enabled {
			task, _, err := s.collectorManager.BuildCollectTaskStrict(&m)
			if err != nil {
				writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
				return
			}
			if err := s.collectorManager.DispatchTaskByMonitor(m.ID, task); err != nil {
				writeErr(w, http.StatusBadGateway, "COLLECTOR_DISPATCH_FAILED", err.Error())
				return
			}
		}
		writeJSON(w, http.StatusCreated, m)
	case http.MethodGet:
		items := filterMonitors(s.store.List(), r)
		page, pageSize := pageParams(r)
		start := (page - 1) * pageSize
		end := start + pageSize
		total := len(items)
		if start > total {
			start = total
		}
		if end > total {
			end = total
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"items":     items[start:end],
			"page":      page,
			"page_size": pageSize,
			"total":     total,
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
	if len(parts) == 2 && parts[1] == "connectivity-test" {
		if r.Method == http.MethodPost {
			s.handleMonitorConnectivityTest(w, r, id)
			return
		}
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if len(parts) == 2 && parts[1] == "collector" {
		switch r.Method {
		case http.MethodPost:
			s.handleAssignMonitorCollector(w, r, id)
		case http.MethodDelete:
			s.handleUnassignMonitorCollector(w, id)
		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
		}
		return
	}
	if len(parts) == 2 && r.Method == http.MethodPatch && (parts[1] == "enable" || parts[1] == "disable") {
		s.handleEnableDisable(w, r, id, parts[1] == "enable")
		return
	}
	if len(parts) == 2 && parts[1] == "recompile" && r.Method == http.MethodPost {
		s.handleManualRecompile(w, id)
		return
	}
	if len(parts) == 2 && parts[1] == "template-upgrade" && r.Method == http.MethodPost {
		s.handleTemplateUpgrade(w, r, id)
		return
	}
	if len(parts) == 2 && parts[1] == "compile-logs" && r.Method == http.MethodGet {
		s.handleCompileLogs(w, r, id)
		return
	}
	if len(parts) == 2 && parts[1] == "metrics-view" {
		s.handleMonitorMetricsView(w, r, id)
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
		// 优先走 collectorManager（数据库 + gRPC 客户端连接池）
		// collector-go 的 HTTP 心跳是注册保活信号，不应依赖旧 registry。
		if s.collectorManager != nil {
			if _, err := s.collectorManager.GetClient(collectorID); err == nil {
				writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
				return
			}
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

func (s *Server) handleAssignMonitorCollector(w http.ResponseWriter, r *http.Request, monitorID int64) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector manager not configured")
		return
	}
	var req struct {
		CollectorID string `json:"collector_id"`
		Pinned      *bool  `json:"pinned"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	req.CollectorID = strings.TrimSpace(req.CollectorID)
	if req.CollectorID == "" {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "collector_id is required")
		return
	}
	pinned := true
	if req.Pinned != nil {
		pinned = *req.Pinned
	}
	if err := s.collectorManager.AssignCollector(monitorID, req.CollectorID, pinned); err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeErr(w, http.StatusNotFound, "MONITOR_NOT_FOUND", err.Error())
			return
		}
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"monitor_id":   monitorID,
		"collector_id": req.CollectorID,
		"pinned":       pinned,
	})
}

func (s *Server) handleUnassignMonitorCollector(w http.ResponseWriter, monitorID int64) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusNotImplemented, "COLLECTOR_UNAVAILABLE", "collector manager not configured")
		return
	}
	if err := s.collectorManager.UnassignCollector(monitorID); err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeErr(w, http.StatusNotFound, "MONITOR_NOT_FOUND", err.Error())
			return
		}
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"monitor_id": monitorID,
		"unassigned": true,
	})
}

func (s *Server) handleMetricsSeries(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.vmQuery == nil {
		writeErr(w, http.StatusNotImplemented, "METRIC_QUERY_UNAVAILABLE", "vm query not configured")
		return
	}
	monitorID, err := strconv.ParseInt(strings.TrimSpace(r.URL.Query().Get("monitor_id")), 10, 64)
	if err != nil || monitorID <= 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "monitor_id is required")
		return
	}
	start, end, err := resolveRangeWindow(r)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	matchers := []string{fmt.Sprintf(`{__monitor_id__="%d"}`, monitorID)}
	if extra := strings.TrimSpace(r.URL.Query().Get("match")); extra != "" {
		matchers = append(matchers, extra)
	}
	series, err := s.vmQuery.ListSeries(r.Context(), matchers, start, end)
	if err != nil {
		writeErr(w, http.StatusBadGateway, "UPSTREAM_UNAVAILABLE", err.Error())
		return
	}
	sort.Slice(series, func(i, j int) bool {
		return strings.TrimSpace(series[i]["__name__"]) < strings.TrimSpace(series[j]["__name__"])
	})
	writeJSON(w, http.StatusOK, map[string]any{
		"items": series,
		"total": len(series),
		"from":  start.UTC().Format(time.RFC3339),
		"to":    end.UTC().Format(time.RFC3339),
	})
}

func (s *Server) handleMetricsQueryRange(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.vmQuery == nil {
		writeErr(w, http.StatusNotImplemented, "METRIC_QUERY_UNAVAILABLE", "vm query not configured")
		return
	}
	monitorID, err := strconv.ParseInt(strings.TrimSpace(r.URL.Query().Get("monitor_id")), 10, 64)
	if err != nil || monitorID <= 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "monitor_id is required")
		return
	}
	start, end, err := resolveRangeWindow(r)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	stepSec := atoiDefault(r.URL.Query().Get("step"), 60)
	if stepSec <= 0 {
		stepSec = 60
	}
	names := parseCSVNames(r.URL.Query().Get("names"))
	if name := strings.TrimSpace(r.URL.Query().Get("name")); name != "" {
		names = append(names, name)
	}
	if len(names) == 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "name or names is required")
		return
	}
	out := make([]metrics.RangeSeries, 0, len(names))
	for _, name := range names {
		query := fmt.Sprintf(`%s{__monitor_id__="%d"}`, strings.TrimSpace(name), monitorID)
		series, err := s.vmQuery.QueryRange(r.Context(), query, start, end, time.Duration(stepSec)*time.Second)
		if err != nil {
			writeErr(w, http.StatusBadGateway, "UPSTREAM_UNAVAILABLE", err.Error())
			return
		}
		out = append(out, series...)
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"items": out,
		"total": len(out),
		"from":  start.UTC().Format(time.RFC3339),
		"to":    end.UTC().Format(time.RFC3339),
		"step":  stepSec,
	})
}

func (s *Server) handleMetricsLatest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.vmQuery == nil {
		writeErr(w, http.StatusNotImplemented, "METRIC_QUERY_UNAVAILABLE", "vm query not configured")
		return
	}
	monitorID, err := strconv.ParseInt(strings.TrimSpace(r.URL.Query().Get("monitor_id")), 10, 64)
	if err != nil || monitorID <= 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "monitor_id is required")
		return
	}
	start, end, err := resolveRangeWindow(r)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	stepSec := atoiDefault(r.URL.Query().Get("step"), 60)
	if stepSec <= 0 {
		stepSec = 60
	}
	staleSeconds := atoiDefault(r.URL.Query().Get("stale_seconds"), stepSec*2)
	if staleSeconds <= 0 {
		staleSeconds = stepSec * 2
	}
	names := parseCSVNames(r.URL.Query().Get("names"))
	if name := strings.TrimSpace(r.URL.Query().Get("name")); name != "" {
		names = append(names, name)
	}
	if len(names) == 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "name or names is required")
		return
	}

	type latestItem struct {
		Name      string   `json:"name"`
		Value     *float64 `json:"value,omitempty"`
		Text      *string  `json:"text,omitempty"`
		Timestamp *int64   `json:"timestamp,omitempty"`
		Stale     bool     `json:"stale"`
	}

	stringLatest := map[string]StringLatestValue{}
	if s.stringLatest != nil {
		stringLatest = s.stringLatest(monitorID, names)
	}

	out := make([]latestItem, 0, len(names))
	for _, name := range names {
		query := fmt.Sprintf(`%s{__monitor_id__="%d"}`, strings.TrimSpace(name), monitorID)
		series, err := s.vmQuery.QueryRange(r.Context(), query, start, end, time.Duration(stepSec)*time.Second)
		if err != nil {
			// 字符串字段可能不是合法 PromQL metric name，若本地快照命中则降级返回字符串值。
			if _, hasString := stringLatest[name]; !hasString {
				writeErr(w, http.StatusBadGateway, "UPSTREAM_UNAVAILABLE", err.Error())
				return
			}
			series = nil
		}
		var latestTs int64
		var latestVal float64
		var hasValue bool
		for _, one := range series {
			for _, point := range one.Points {
				if !hasValue || point.Timestamp >= latestTs {
					latestTs = point.Timestamp
					latestVal = point.Value
					hasValue = true
				}
			}
		}
		item := latestItem{Name: name, Stale: true}
		if hasValue {
			item.Value = &latestVal
			item.Timestamp = &latestTs
			item.Stale = end.Sub(time.UnixMilli(latestTs)) > time.Duration(staleSeconds)*time.Second
		}
		if latest, ok := stringLatest[name]; ok {
			text := strings.TrimSpace(latest.Value)
			if text != "" {
				item.Text = &text
			}
			if !hasValue && latest.Timestamp > 0 {
				ts := latest.Timestamp
				item.Timestamp = &ts
				item.Stale = end.Sub(time.UnixMilli(ts)) > time.Duration(staleSeconds)*time.Second
			}
		}
		out = append(out, item)
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"items": out,
		"total": len(out),
		"from":  start.UTC().Format(time.RFC3339),
		"to":    end.UTC().Format(time.RFC3339),
		"step":  stepSec,
	})
}

func (s *Server) handleMetricsExport(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.vmQuery == nil {
		writeErr(w, http.StatusNotImplemented, "METRIC_QUERY_UNAVAILABLE", "vm query not configured")
		return
	}
	monitorID, err := strconv.ParseInt(strings.TrimSpace(r.URL.Query().Get("monitor_id")), 10, 64)
	if err != nil || monitorID <= 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "monitor_id is required")
		return
	}
	monitor, err := s.store.Get(monitorID)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeErr(w, http.StatusNotFound, "MONITOR_NOT_FOUND", err.Error())
			return
		}
		writeStoreErr(w, err)
		return
	}

	start, end, err := resolveRangeWindow(r)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	stepSec := atoiDefault(r.URL.Query().Get("step"), 60)
	if stepSec <= 0 {
		stepSec = 60
	}
	names := parseCSVNames(r.URL.Query().Get("names"))
	if name := strings.TrimSpace(r.URL.Query().Get("name")); name != "" {
		names = append(names, name)
	}
	if len(names) == 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "name or names is required")
		return
	}

	type metricRow struct {
		MetricName string
		Timestamp  int64
		Value      float64
	}
	rows := make([]metricRow, 0, 256)
	for _, name := range names {
		query := fmt.Sprintf(`%s{__monitor_id__="%d"}`, strings.TrimSpace(name), monitorID)
		series, err := s.vmQuery.QueryRange(r.Context(), query, start, end, time.Duration(stepSec)*time.Second)
		if err != nil {
			writeErr(w, http.StatusBadGateway, "UPSTREAM_UNAVAILABLE", err.Error())
			return
		}
		for _, one := range series {
			for _, point := range one.Points {
				rows = append(rows, metricRow{
					MetricName: name,
					Timestamp:  point.Timestamp,
					Value:      point.Value,
				})
			}
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].MetricName == rows[j].MetricName {
			return rows[i].Timestamp < rows[j].Timestamp
		}
		return rows[i].MetricName < rows[j].MetricName
	})

	ts := time.Now().UTC().Format("20060102_150405")
	base := fmt.Sprintf("monitor_%d_metrics", monitorID)
	if len(names) == 1 {
		base = sanitizeFilename(names[0])
		if base == "" {
			base = fmt.Sprintf("monitor_%d_metric", monitorID)
		}
	}
	filename := fmt.Sprintf("%s_%s.csv", base, ts)
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	w.Header().Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, filename))
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("\uFEFF"))

	writer := csv.NewWriter(w)
	_ = writer.Write([]string{
		"monitor_id",
		"monitor_name",
		"app",
		"ci_code",
		"target",
		"metric_name",
		"timestamp",
		"time",
		"value",
	})
	for _, row := range rows {
		_ = writer.Write([]string{
			strconv.FormatInt(monitorID, 10),
			monitor.Name,
			monitor.App,
			monitor.CICode,
			monitor.Target,
			row.MetricName,
			strconv.FormatInt(row.Timestamp, 10),
			time.UnixMilli(row.Timestamp).UTC().Format(time.RFC3339),
			strconv.FormatFloat(row.Value, 'f', -1, 64),
		})
	}
	writer.Flush()
	if err := writer.Error(); err != nil {
		return
	}
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
	if s.resources == nil {
		writeErr(w, http.StatusServiceUnavailable, "SERVICE_UNAVAILABLE", "资源配置由 Python Web 管理，请访问 /api/v1/ 下的对应端点")
		return
	}
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
	if s.resources == nil {
		writeErr(w, http.StatusServiceUnavailable, "SERVICE_UNAVAILABLE", "资源配置由 Python Web 管理，请访问 /api/v1/ 下的对应端点")
		return
	}
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
		current, err := s.store.Get(id)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		candidate := model.Monitor{
			ID:              id,
			Name:            in.Name,
			App:             in.App,
			Target:          in.Target,
			TemplateID:      in.TemplateID,
			IntervalSeconds: normalizeInterval(in.IntervalSeconds, in.Interval),
			Params:          in.Params,
			Enabled:         in.Enabled,
			Version:         current.Version,
		}
		in.Params = s.sanitizePersistableParams(&candidate, in.Params)
		candidate.Params = in.Params
		if err := s.preCompileAndAudit(&candidate, "update"); err != nil {
			writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
			return
		}
		if !current.Enabled && in.Enabled && s.licenseManager != nil {
			if err := s.licenseManager.ValidateEnableAllowed(); err != nil {
				writeErr(w, http.StatusPaymentRequired, "LICENSE_LIMIT_EXCEEDED", err.Error())
				return
			}
		}
		m, err := s.store.Update(id, in)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		if s.collectorManager != nil {
			task, _, err := s.collectorManager.BuildCollectTaskStrict(&m)
			if err != nil {
				writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
				return
			}
			if m.Enabled {
				if err := s.collectorManager.DispatchTaskByMonitor(m.ID, task); err != nil {
					writeErr(w, http.StatusBadGateway, "COLLECTOR_DISPATCH_FAILED", err.Error())
					return
				}
			} else {
				_ = s.collectorManager.DeleteTaskByMonitor(m.ID, task.JobId)
			}
		}
		writeJSON(w, http.StatusOK, m)
	case http.MethodDelete:
		m, err := s.store.Get(id)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		version, err := strconv.ParseInt(r.URL.Query().Get("version"), 10, 64)
		if err != nil || version <= 0 {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "version is required")
			return
		}
		if err := s.store.Delete(id, version); err != nil {
			writeStoreErr(w, err)
			return
		}
		if s.collectorManager != nil {
			task, _ := s.collectorManager.BuildCollectTask(&m)
			_ = s.collectorManager.DeleteTaskByMonitor(id, task.JobId)
			_ = s.collectorManager.UnassignCollector(id)
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) sanitizePersistableParams(monitor *model.Monitor, params map[string]string) map[string]string {
	if len(params) == 0 {
		return nil
	}
	if s.collectorManager == nil {
		return params
	}
	return s.collectorManager.FilterPersistableParams(monitor, params)
}

func (s *Server) handleEnableDisable(w http.ResponseWriter, r *http.Request, id int64, enabled bool) {
	var req struct {
		Version int64 `json:"version"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	if enabled {
		current, err := s.store.Get(id)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		if !current.Enabled && s.licenseManager != nil {
			if err := s.licenseManager.ValidateEnableAllowed(); err != nil {
				writeErr(w, http.StatusPaymentRequired, "LICENSE_LIMIT_EXCEEDED", err.Error())
				return
			}
		}
		if err := s.preCompileAndAudit(&current, "enable"); err != nil {
			writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
			return
		}
	}
	m, err := s.store.SetEnabled(id, enabled, req.Version)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	if s.collectorManager != nil {
		if enabled {
			task, _, err := s.collectorManager.BuildCollectTaskStrict(&m)
			if err != nil {
				writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
				return
			}
			if err := s.collectorManager.DispatchTaskByMonitor(m.ID, task); err != nil {
				writeErr(w, http.StatusBadGateway, "COLLECTOR_DISPATCH_FAILED", err.Error())
				return
			}
		} else {
			task, _ := s.collectorManager.BuildCollectTask(&m)
			_ = s.collectorManager.DeleteTaskByMonitor(m.ID, task.JobId)
		}
	}
	writeJSON(w, http.StatusOK, m)
}

func (s *Server) handleLicenseStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.licenseManager == nil {
		writeJSON(w, http.StatusOK, map[string]any{
			"has_license":      false,
			"expired":          false,
			"machine_code":     "",
			"max_monitors":     0,
			"enabled_monitors": 0,
			"halted":           false,
		})
		return
	}
	writeJSON(w, http.StatusOK, s.licenseManager.Status())
}

func (s *Server) handleLicenseUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if s.licenseManager == nil {
		writeErr(w, http.StatusServiceUnavailable, "LICENSE_UNAVAILABLE", "license manager not configured")
		return
	}
	var raw []byte
	contentType := strings.ToLower(strings.TrimSpace(r.Header.Get("Content-Type")))
	if strings.Contains(contentType, "application/json") {
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		value := strings.TrimSpace(fmt.Sprintf("%v", payload["license"]))
		if value == "" {
			value = strings.TrimSpace(fmt.Sprintf("%v", payload["content"]))
		}
		raw = []byte(value)
	} else {
		buf, err := io.ReadAll(r.Body)
		if err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		raw = buf
	}
	if len(raw) == 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "license content required")
		return
	}
	claims, err := s.licenseManager.Install(raw)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "LICENSE_INVALID", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"machine_code": claims.MachineCode,
		"expire_time":  claims.ExpireTime,
		"max_monitors": claims.MaxMonitors,
	})
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

func (s *Server) handleManualRecompile(w http.ResponseWriter, id int64) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusServiceUnavailable, "SERVICE_UNAVAILABLE", "collector manager not configured")
		return
	}
	m, err := s.store.Get(id)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	task, _, err := s.collectorManager.BuildCollectTaskStrict(&m)
	if err != nil {
		s.auditCompileResult(m.ID, m.App, "recompile", err)
		writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
		return
	}
	s.auditCompileResult(m.ID, m.App, "recompile", nil)
	dispatched := false
	if m.Enabled {
		if err := s.collectorManager.DispatchTaskByMonitor(m.ID, task); err != nil {
			writeErr(w, http.StatusBadGateway, "COLLECTOR_DISPATCH_FAILED", err.Error())
			return
		}
		dispatched = true
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"monitor_id":    m.ID,
		"compiled":      true,
		"dispatched":    dispatched,
		"metrics_tasks": len(task.GetTasks()),
		"timestamp":     time.Now().UTC().Format(time.RFC3339),
	})
}

func (s *Server) handleMonitorConnectivityTest(w http.ResponseWriter, r *http.Request, id int64) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusServiceUnavailable, "SERVICE_UNAVAILABLE", "collector manager not configured")
		return
	}
	timeoutMs := atoiDefault(strings.TrimSpace(r.URL.Query().Get("timeout_ms")), 15000)
	if timeoutMs < 1000 {
		timeoutMs = 1000
	}
	result, err := s.collectorManager.ProbeMonitorConnection(id, time.Duration(timeoutMs)*time.Millisecond)
	if err != nil {
		if errors.Is(err, store.ErrNotFound) {
			writeStoreErr(w, err)
			return
		}
		writeErr(w, http.StatusBadGateway, "CONNECTIVITY_TEST_FAILED", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, result)
}

func (s *Server) handleTemplateUpgrade(w http.ResponseWriter, r *http.Request, id int64) {
	if s.collectorManager == nil {
		writeErr(w, http.StatusServiceUnavailable, "SERVICE_UNAVAILABLE", "collector manager not configured")
		return
	}
	var req struct {
		TemplateID int64 `json:"template_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	if req.TemplateID <= 0 {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "template_id is required")
		return
	}
	current, err := s.store.Get(id)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	candidate := current
	candidate.TemplateID = req.TemplateID
	if err := s.preCompileAndAudit(&candidate, "upgrade_validate"); err != nil {
		writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
		return
	}
	upIn := buildUpdateInputFromMonitor(current)
	upIn.TemplateID = req.TemplateID
	updated, err := s.store.Update(id, upIn)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	task, _, err := s.collectorManager.BuildCollectTaskStrict(&updated)
	if err != nil {
		s.auditCompileResult(updated.ID, updated.App, "upgrade_apply", err)
		writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
		return
	}
	s.auditCompileResult(updated.ID, updated.App, "upgrade_apply", nil)
	dispatched := false
	if updated.Enabled {
		if err := s.collectorManager.DispatchTaskByMonitor(updated.ID, task); err != nil {
			writeErr(w, http.StatusBadGateway, "COLLECTOR_DISPATCH_FAILED", err.Error())
			return
		}
		dispatched = true
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"monitor_id":      updated.ID,
		"template_id":     updated.TemplateID,
		"compiled":        true,
		"dispatched":      dispatched,
		"monitor_version": updated.Version,
		"timestamp":       time.Now().UTC().Format(time.RFC3339),
	})
}

func (s *Server) handleCompileLogs(w http.ResponseWriter, r *http.Request, id int64) {
	limit := atoiDefault(r.URL.Query().Get("limit"), 20)
	items, err := s.store.ListCompileLogs(id, limit)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"items": items,
		"total": len(items),
	})
}

func (s *Server) handleMonitorMetricsView(w http.ResponseWriter, r *http.Request, id int64) {
	switch r.Method {
	case http.MethodGet:
		item, err := s.store.GetMetricsViewPref(id)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		if item.VisibleFieldsByGroup == nil {
			item.VisibleFieldsByGroup = map[string][]string{}
		}
		writeJSON(w, http.StatusOK, item)
	case http.MethodPut:
		var req struct {
			VisibleFieldsByGroup map[string][]string `json:"visible_fields_by_group"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		item, err := s.store.UpsertMetricsViewPref(id, req.VisibleFieldsByGroup)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, item)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) preCompileAndAudit(monitor *model.Monitor, stage string) error {
	if s.collectorManager == nil {
		return nil
	}
	err := s.collectorManager.ValidateMonitorTemplate(monitor)
	s.auditCompileResult(monitor.ID, monitor.App, stage, err)
	return err
}

func (s *Server) auditCompileResult(monitorID int64, app string, stage string, err error) {
	if s.store == nil {
		return
	}
	if err == nil {
		_ = s.store.AddCompileLog(monitorID, app, stage, "success", "", "")
		return
	}
	path := ""
	reason := err.Error()
	if ce, ok := templ.AsCompileError(err); ok {
		path = ce.Path
		reason = ce.Reason
	}
	_ = s.store.AddCompileLog(monitorID, app, stage, "failed", path, reason)
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

func filterMonitors(items []model.Monitor, r *http.Request) []model.Monitor {
	q := strings.TrimSpace(strings.ToLower(r.URL.Query().Get("q")))
	app := strings.TrimSpace(strings.ToLower(r.URL.Query().Get("app")))
	status := strings.TrimSpace(strings.ToLower(r.URL.Query().Get("status")))

	out := make([]model.Monitor, 0, len(items))
	for _, item := range items {
		if app != "" && strings.ToLower(strings.TrimSpace(item.App)) != app {
			continue
		}
		if status != "" {
			enabled := status == "enabled" || status == "up" || status == "running"
			if item.Enabled != enabled {
				continue
			}
		}
		if q != "" {
			hay := strings.ToLower(strings.Join([]string{
				item.Name,
				item.Target,
				item.CIName,
				item.CICode,
				item.App,
				item.JobID,
			}, " "))
			if !strings.Contains(hay, q) {
				continue
			}
		}
		out = append(out, item)
	}
	return out
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

func normalizeInterval(primary int, fallback int) int {
	if primary > 0 {
		return primary
	}
	return fallback
}

func buildUpdateInputFromMonitor(m model.Monitor) model.MonitorUpdateInput {
	return model.MonitorUpdateInput{
		CIID:            m.CIID,
		CIModelID:       m.CIModelID,
		CIName:          m.CIName,
		CICode:          m.CICode,
		Name:            m.Name,
		App:             m.App,
		Target:          m.Target,
		TemplateID:      m.TemplateID,
		IntervalSeconds: m.IntervalSeconds,
		Enabled:         m.Enabled,
		Labels:          m.Labels,
		Params:          m.Params,
		Version:         m.Version,
	}
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

func parseCSVNames(raw string) []string {
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	seen := make(map[string]struct{}, len(parts))
	for _, part := range parts {
		name := strings.TrimSpace(part)
		if name == "" {
			continue
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		out = append(out, name)
	}
	return out
}

func sanitizeFilename(raw string) string {
	value := strings.TrimSpace(raw)
	if value == "" {
		return ""
	}
	var b strings.Builder
	for _, ch := range value {
		if (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-' {
			b.WriteRune(ch)
			continue
		}
		b.WriteByte('_')
	}
	out := strings.Trim(b.String(), "_")
	if out == "" {
		return "metric"
	}
	return out
}

func resolveRangeWindow(r *http.Request) (time.Time, time.Time, error) {
	now := time.Now().UTC()
	end, err := parseTimeQuery(r.URL.Query().Get("to"), now)
	if err != nil {
		return time.Time{}, time.Time{}, fmt.Errorf("invalid to: %w", err)
	}
	start, err := parseTimeQuery(r.URL.Query().Get("from"), end.Add(-time.Hour))
	if err != nil {
		return time.Time{}, time.Time{}, fmt.Errorf("invalid from: %w", err)
	}
	if !start.Before(end) {
		return time.Time{}, time.Time{}, fmt.Errorf("from must be earlier than to")
	}
	return start, end, nil
}

func parseTimeQuery(raw string, fallback time.Time) (time.Time, error) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return fallback, nil
	}
	if i, err := strconv.ParseInt(value, 10, 64); err == nil {
		if i > 1_000_000_000_000 {
			return time.UnixMilli(i).UTC(), nil
		}
		if i > 0 {
			return time.Unix(i, 0).UTC(), nil
		}
	}
	if t, err := time.Parse(time.RFC3339, value); err == nil {
		return t.UTC(), nil
	}
	return time.Time{}, fmt.Errorf("unsupported time format %q", value)
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

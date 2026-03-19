package collector

import (
	"context"
	"errors"
	"fmt"
	"hash/fnv"
	"log"
	"net"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"

	"manager-go/internal/model"
	pb "manager-go/internal/pb/proto"
	"manager-go/internal/store"
	templ "manager-go/internal/template"
)

// Manager 管理所有 Collector 连接
type Manager struct {
	clients map[string]*Client
	mu      sync.RWMutex

	// 依赖
	monitorStore   *store.MonitorStore
	collectorStore *store.CollectorStore
	templateReg    *templ.Registry

	// 配置
	heartbeatInterval    time.Duration
	reconnectBackoff     time.Duration
	maxReconnectAttempts int

	// 回调
	onReport func(string, *pb.CollectRep)
	onAck    func(string, *pb.CommandAck)

	// 控制
	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// ManagerOption 配置选项
type ManagerOption func(*Manager)

func WithManagerHeartbeatInterval(d time.Duration) ManagerOption {
	return func(m *Manager) {
		m.heartbeatInterval = d
	}
}

func WithManagerReconnectBackoff(d time.Duration) ManagerOption {
	return func(m *Manager) {
		m.reconnectBackoff = d
	}
}

func WithManagerMaxReconnectAttempts(n int) ManagerOption {
	return func(m *Manager) {
		m.maxReconnectAttempts = n
	}
}

func WithManagerReportHandler(fn func(string, *pb.CollectRep)) ManagerOption {
	return func(m *Manager) {
		m.onReport = fn
	}
}

func WithManagerAckHandler(fn func(string, *pb.CommandAck)) ManagerOption {
	return func(m *Manager) {
		m.onAck = fn
	}
}

func WithManagerTemplateRegistry(reg *templ.Registry) ManagerOption {
	return func(m *Manager) {
		m.templateReg = reg
	}
}

// NewManager 创建 Collector 管理器
func NewManager(monitorStore *store.MonitorStore, collectorStore *store.CollectorStore, opts ...ManagerOption) *Manager {
	ctx, cancel := context.WithCancel(context.Background())
	m := &Manager{
		clients:              make(map[string]*Client),
		monitorStore:         monitorStore,
		collectorStore:       collectorStore,
		heartbeatInterval:    5 * time.Second,
		reconnectBackoff:     5 * time.Second,
		maxReconnectAttempts: 10,
		ctx:                  ctx,
		cancel:               cancel,
	}
	for _, opt := range opts {
		opt(m)
	}
	return m
}

func (m *Manager) SetReportHandler(fn func(string, *pb.CollectRep)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onReport = fn
}

func (m *Manager) SetAckHandler(fn func(string, *pb.CommandAck)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.onAck = fn
}

// Register 注册 Collector
func (m *Manager) Register(id, addr string) error {
	return m.RegisterWithInfo(id, addr, "", "", "public")
}

// RegisterWithInfo 注册 Collector（带详细信息）
func (m *Manager) RegisterWithInfo(id, addr, ip, version, mode string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	// 如果 Collector 已存在，先断开再重新注册（允许重新注册）
	if client, exists := m.clients[id]; exists {
		log.Printf("[Manager] Collector %s already registered, disconnecting and re-registering", id)
		client.Disconnect()
		delete(m.clients, id)
	}

	// 如果没有提供 IP，从 addr 解析
	if ip == "" {
		ip = addr
		if host, _, err := net.SplitHostPort(addr); err == nil {
			ip = host
		}
	}

	// 持久化到数据库
	if m.collectorStore != nil {
		_, err := m.collectorStore.CreateOrUpdate(id, ip, version, mode)
		if err != nil {
			log.Printf("[Manager] Failed to persist collector %s: %v", id, err)
		}
	}

	client := NewClient(id, addr,
		WithHeartbeatInterval(m.heartbeatInterval),
		WithReconnectBackoff(m.reconnectBackoff),
		WithMaxReconnectAttempts(m.maxReconnectAttempts),
		WithReportHandler(func(report *pb.CollectRep) {
			if m.onReport != nil {
				m.onReport(id, report)
			}
		}),
		WithAckHandler(func(ack *pb.CommandAck) {
			if m.onAck != nil {
				m.onAck(id, ack)
			}
		}),
		WithStateChangeHandler(func(collectorID string, state ConnectionState) {
			log.Printf("[Manager] Collector %s state changed to %s", collectorID, state)
			// 同步状态到数据库
			if m.collectorStore != nil {
				switch state {
				case StateConnected:
					m.collectorStore.SetOnline(collectorID)
					// Collector 重启后本地内存任务会丢失，这里在重连成功时主动重推一次所有启用监控任务。
					go func() {
						if err := m.SyncAllMonitors(); err != nil {
							log.Printf("[Manager] Failed to resync monitor tasks after collector %s connected: %v", collectorID, err)
						} else {
							log.Printf("[Manager] Resynced monitor tasks after collector %s connected", collectorID)
						}
					}()
				case StateDisconnected, StateReconnecting:
					m.collectorStore.SetOffline(collectorID)
				}
			}
		}),
	)

	m.clients[id] = client

	// 异步连接
	go func() {
		if err := client.Connect(); err != nil {
			log.Printf("[Manager] Failed to connect to collector %s: %v", id, err)
			// 连接失败，设置为离线
			if m.collectorStore != nil {
				m.collectorStore.SetOffline(id)
			}
		}
	}()

	log.Printf("[Manager] Registered collector %s at %s (ip=%s, version=%s, mode=%s)", id, addr, ip, version, mode)
	return nil
}

// Unregister 注销 Collector
func (m *Manager) Unregister(id string) {
	m.mu.Lock()
	client, exists := m.clients[id]
	if exists {
		delete(m.clients, id)
	}
	m.mu.Unlock()

	if exists {
		client.Disconnect()
		log.Printf("[Manager] Unregistered collector %s", id)
	}
}

// GetClient 获取指定 Collector 客户端
func (m *Manager) GetClient(id string) (*Client, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	client, exists := m.clients[id]
	if !exists {
		return nil, fmt.Errorf("collector %s not found", id)
	}
	return client, nil
}

// GetAllClients 获取所有 Collector 客户端
func (m *Manager) GetAllClients() map[string]*Client {
	m.mu.RLock()
	defer m.mu.RUnlock()

	clients := make(map[string]*Client, len(m.clients))
	for id, client := range m.clients {
		clients[id] = client
	}
	return clients
}

// GetConnectedClients 获取所有已连接的 Collector
func (m *Manager) GetConnectedClients() []*Client {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var connected []*Client
	for _, client := range m.clients {
		if client.GetState() == StateConnected {
			connected = append(connected, client)
		}
	}
	return connected
}

// SelectCollector 使用一致性哈希选择 Collector
func (m *Manager) SelectCollector(monitorID int64) (*Client, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var connected []*Client
	for _, client := range m.clients {
		if client.GetState() == StateConnected {
			connected = append(connected, client)
		}
	}

	if len(connected) == 0 {
		return nil, errors.New("no collector available")
	}

	// 使用一致性哈希选择
	key := strconv.FormatInt(monitorID, 10)
	selected := m.rendezvousHash(key, connected)
	return selected, nil
}

// rendezvousHash 一致性哈希算法
func (m *Manager) rendezvousHash(key string, clients []*Client) *Client {
	var selected *Client
	var maxScore uint64

	for _, client := range clients {
		score := hashScore(key, client.id)
		if selected == nil || score > maxScore {
			selected = client
			maxScore = score
		}
	}

	return selected
}

// hashScore 计算哈希分数
func hashScore(key, node string) uint64 {
	h := fnv.New64a()
	h.Write([]byte(key))
	h.Write([]byte{':'})
	h.Write([]byte(node))
	return h.Sum64()
}

// DispatchTask 分发任务到指定 Collector
func (m *Manager) DispatchTask(collectorID string, task *pb.CollectTask) error {
	client, err := m.GetClient(collectorID)
	if err != nil {
		return err
	}

	return client.SendTask(task)
}

// DispatchTaskByMonitor 根据 Monitor ID 自动选择 Collector 分发任务
func (m *Manager) DispatchTaskByMonitor(monitorID int64, task *pb.CollectTask) error {
	client, pinned, err := m.selectCollectorForMonitor(monitorID)
	if err != nil {
		return err
	}
	if err := client.SendTask(task); err != nil {
		return err
	}
	if err := m.persistBind(client.id, monitorID, pinned); err != nil {
		log.Printf("[Manager] Failed to persist bind monitor=%d collector=%s err=%v", monitorID, client.id, err)
	}
	return nil
}

// DeleteTask 删除指定 Collector 上的任务
func (m *Manager) DeleteTask(collectorID string, jobID int64) error {
	client, err := m.GetClient(collectorID)
	if err != nil {
		return err
	}

	return client.DeleteTask(jobID)
}

// DeleteTaskByMonitor 根据 Monitor ID 自动选择 Collector 删除任务
func (m *Manager) DeleteTaskByMonitor(monitorID int64, jobID int64) error {
	client, _, err := m.selectCollectorForMonitor(monitorID)
	if err != nil {
		return err
	}

	return client.DeleteTask(jobID)
}

// BuildCollectTask 从 Monitor 构建采集任务
func (m *Manager) BuildCollectTask(monitor *model.Monitor) (*pb.CollectTask, int64) {
	jobID := monitor.ID // 使用 monitor ID 作为 job ID

	task := &pb.CollectTask{
		JobId:      jobID,
		MonitorId:  monitor.ID,
		App:        monitor.App,
		IntervalMs: int64(monitor.IntervalSeconds) * 1000,
		CommandId:  time.Now().UnixNano(),
		Version:    monitor.Version,
		TraceId:    fmt.Sprintf("%d-%d", monitor.ID, time.Now().Unix()),
	}

	task.Tasks = m.buildMetricsTasks(monitor)

	return task, jobID
}

func (m *Manager) BuildCollectTaskStrict(monitor *model.Monitor) (*pb.CollectTask, int64, error) {
	jobID := monitor.ID
	task := &pb.CollectTask{
		JobId:      jobID,
		MonitorId:  monitor.ID,
		App:        monitor.App,
		IntervalMs: int64(monitor.IntervalSeconds) * 1000,
		CommandId:  time.Now().UnixNano(),
		Version:    monitor.Version,
		TraceId:    fmt.Sprintf("%d-%d", monitor.ID, time.Now().Unix()),
	}
	tasks, err := m.compileMetricsTasksStrict(monitor)
	if err != nil {
		return nil, jobID, err
	}
	task.Tasks = tasks
	return task, jobID, nil
}

func (m *Manager) ValidateMonitorTemplate(monitor *model.Monitor) error {
	_, err := m.compileMetricsTasksStrict(monitor)
	return err
}

// SyncAllMonitors 同步所有启用的 Monitor 到 Collector
func (m *Manager) SyncAllMonitors() error {
	monitors := m.monitorStore.List()

	for _, monitor := range monitors {
		if !monitor.Enabled {
			continue
		}

		task, _ := m.BuildCollectTask(&monitor)

		if err := m.DispatchTaskByMonitor(monitor.ID, task); err != nil {
			log.Printf("[Manager] Failed to dispatch task for monitor %d: %v", monitor.ID, err)
		}
	}

	return nil
}

// GetCollectorList 获取 Collector 列表（从数据库）
func (m *Manager) GetCollectorList() ([]*store.Collector, error) {
	if m.collectorStore == nil {
		return nil, errors.New("collector store not configured")
	}
	return m.collectorStore.List()
}

// GetCollectorStore 获取 Collector 存储
func (m *Manager) GetCollectorStore() *store.CollectorStore {
	return m.collectorStore
}

// GoOffline 主动下线 Collector（踢出）
func (m *Manager) GoOffline(collectorID string) error {
	log.Printf("[Manager] Going offline for collector %s", collectorID)

	// 1. 断开连接
	m.Unregister(collectorID)

	// 2. 更新数据库状态
	if m.collectorStore != nil {
		if err := m.collectorStore.SetOffline(collectorID); err != nil {
			log.Printf("[Manager] Failed to set collector %s offline: %v", collectorID, err)
		}

		// 3. 删除该 Collector 的所有绑定关系
		if err := m.collectorStore.DeleteBindsByCollector(collectorID); err != nil {
			log.Printf("[Manager] Failed to delete binds for collector %s: %v", collectorID, err)
		}
	}

	// 4. 重新平衡任务
	if err := m.ReBalanceJobs(); err != nil {
		log.Printf("[Manager] Failed to rebalance jobs after collector %s offline: %v", collectorID, err)
	}

	log.Printf("[Manager] Collector %s is now offline", collectorID)
	return nil
}

// ReBalanceJobs 重新平衡所有任务
func (m *Manager) ReBalanceJobs() error {
	log.Printf("[Manager] Rebalancing all jobs...")

	monitors := m.monitorStore.List()
	for _, monitor := range monitors {
		if !monitor.Enabled {
			continue
		}

		// 检查是否有固定绑定
		if m.collectorStore != nil {
			bind, err := m.collectorStore.GetBindByMonitor(monitor.ID)
			if err == nil && bind != nil && bind.Pinned == 1 {
				// 固定绑定，跳过
				continue
			}
		}

		// 重新分配
		task, _ := m.BuildCollectTask(&monitor)
		if err := m.DispatchTaskByMonitor(monitor.ID, task); err != nil {
			log.Printf("[Manager] Failed to rebalance task for monitor %d: %v", monitor.ID, err)
		}
	}

	log.Printf("[Manager] Rebalance completed")
	return nil
}

func (m *Manager) AssignCollector(monitorID int64, collectorID string, pinned bool) error {
	if _, err := m.monitorStore.Get(monitorID); err != nil {
		return err
	}
	client, err := m.GetClient(collectorID)
	if err != nil {
		return err
	}
	if client.GetState() != StateConnected {
		return fmt.Errorf("collector %s is not connected", collectorID)
	}
	flag := int8(0)
	if pinned {
		flag = 1
	}
	if err := m.persistBind(collectorID, monitorID, pinned); err != nil {
		return err
	}
	if m.collectorStore != nil {
		// persistBind keeps current relation when unchanged. Force pinned flag update when requested.
		if bind, err := m.collectorStore.GetBindByMonitor(monitorID); err == nil && bind != nil && bind.Pinned != flag {
			_ = m.collectorStore.DeleteBindByMonitor(monitorID)
			if _, err := m.collectorStore.CreateBind(collectorID, monitorID, flag); err != nil {
				return err
			}
		}
	}
	monitor, err := m.monitorStore.Get(monitorID)
	if err != nil {
		return err
	}
	if monitor.Enabled {
		task, _ := m.BuildCollectTask(&monitor)
		return m.DispatchTask(collectorID, task)
	}
	return nil
}

func (m *Manager) UnassignCollector(monitorID int64) error {
	if m.collectorStore == nil {
		return nil
	}
	if err := m.collectorStore.DeleteBindByMonitor(monitorID); err != nil {
		return err
	}
	monitor, err := m.monitorStore.Get(monitorID)
	if err != nil {
		return err
	}
	if !monitor.Enabled {
		return nil
	}
	task, _ := m.BuildCollectTask(&monitor)
	return m.DispatchTaskByMonitor(monitorID, task)
}

func (m *Manager) selectCollectorForMonitor(monitorID int64) (*Client, bool, error) {
	if m.collectorStore != nil {
		if bind, err := m.collectorStore.GetBindByMonitor(monitorID); err == nil && bind != nil && bind.Pinned == 1 {
			client, err := m.GetClient(bind.Collector)
			if err == nil && client.GetState() == StateConnected {
				return client, true, nil
			}
		}
	}
	client, err := m.SelectCollector(monitorID)
	if err != nil {
		return nil, false, err
	}
	return client, false, nil
}

func (m *Manager) persistBind(collectorID string, monitorID int64, pinned bool) error {
	if m.collectorStore == nil {
		return nil
	}
	wantPinned := int8(0)
	if pinned {
		wantPinned = 1
	}
	bind, err := m.collectorStore.GetBindByMonitor(monitorID)
	if err == nil && bind != nil {
		if bind.Collector == collectorID && bind.Pinned == wantPinned {
			return nil
		}
		if bind.Pinned == 1 && !pinned {
			// Keep user-pinned assignment untouched when doing auto dispatch.
			return nil
		}
		if err := m.collectorStore.DeleteBindByMonitor(monitorID); err != nil {
			return err
		}
	}
	_, err = m.collectorStore.CreateBind(collectorID, monitorID, wantPinned)
	return err
}

func (m *Manager) buildMetricsTasks(monitor *model.Monitor) []*pb.MetricsTask {
	if m.templateReg != nil {
		if rt, ok := m.getTemplateForMonitor(monitor); ok {
			if tasks, err := templ.CompileMetricsTasks(rt, monitor); err == nil && len(tasks) > 0 {
				return tasks
			} else if err != nil {
				log.Printf("[Manager] template compile fallback app=%s monitor=%d template_id=%d err=%v", monitor.App, monitor.ID, monitor.TemplateID, err)
			}
		}
	}
	app := strings.TrimSpace(strings.ToLower(monitor.App))
	switch app {
	case "redis", "valkey":
		return buildRedisTasks(monitor)
	default:
		return buildDefaultTasks(monitor)
	}
}

func (m *Manager) compileMetricsTasksStrict(monitor *model.Monitor) ([]*pb.MetricsTask, error) {
	if m.templateReg == nil {
		return nil, errors.New("template registry not configured")
	}
	rt, ok := m.getTemplateForMonitor(monitor)
	if !ok {
		if monitor.TemplateID > 0 {
			return nil, fmt.Errorf("template not loaded for template_id=%d app=%s", monitor.TemplateID, strings.TrimSpace(monitor.App))
		}
		return nil, fmt.Errorf("template not loaded for app=%s", strings.TrimSpace(monitor.App))
	}
	if strings.TrimSpace(strings.ToLower(rt.App)) != strings.TrimSpace(strings.ToLower(monitor.App)) {
		return nil, fmt.Errorf("template app mismatch: monitor=%s template=%s", strings.TrimSpace(monitor.App), strings.TrimSpace(rt.App))
	}
	tasks, err := templ.CompileMetricsTasks(rt, monitor)
	if err != nil {
		return nil, err
	}
	if len(tasks) == 0 {
		return nil, errors.New("compiled metrics tasks are empty")
	}
	return tasks, nil
}

func (m *Manager) getTemplateForMonitor(monitor *model.Monitor) (templ.RuntimeTemplate, bool) {
	if m.templateReg == nil || monitor == nil {
		return templ.RuntimeTemplate{}, false
	}
	if monitor.TemplateID > 0 {
		if rt, ok := m.templateReg.GetByID(monitor.TemplateID); ok {
			return rt, true
		}
	}
	return m.templateReg.Get(monitor.App)
}

func buildDefaultTasks(monitor *model.Monitor) []*pb.MetricsTask {
	protocolName := strings.TrimSpace(strings.ToLower(monitor.App))
	if protocolName == "" {
		protocolName = "http"
	}
	switch protocolName {
	case "mysql", "mariadb", "postgres", "postgresql":
		protocolName = "jdbc"
	case "valkey":
		protocolName = "redis"
	}
	params := cloneStringMap(monitor.Params)
	if params == nil {
		params = make(map[string]string)
	}
	if protocolName == "http" {
		if _, ok := params["url"]; !ok {
			params["url"] = monitor.Target
		}
	}
	return []*pb.MetricsTask{
		{
			Name:      protocolName,
			Protocol:  protocolName,
			TimeoutMs: int64(readIntParam(params, "timeout", 5000)),
			Priority:  0,
			Params:    params,
			ExecKind:  "pull",
		},
	}
}

func buildRedisTasks(monitor *model.Monitor) []*pb.MetricsTask {
	params := cloneStringMap(monitor.Params)
	if params == nil {
		params = make(map[string]string)
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host, port = splitHostPortFallback(monitor.Target)
	}
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "6379"
	}
	timeout := readIntParam(params, "timeout", 3000)
	sections := []string{"server", "clients", "memory", "stats"}
	if raw := strings.TrimSpace(params["sections"]); raw != "" {
		userSections := strings.Split(raw, ",")
		sections = make([]string, 0, len(userSections))
		for _, item := range userSections {
			sec := strings.TrimSpace(strings.ToLower(item))
			if sec == "" {
				continue
			}
			sections = append(sections, sec)
		}
		if len(sections) == 0 {
			sections = []string{"server", "clients", "memory", "stats"}
		}
	}
	tasks := make([]*pb.MetricsTask, 0, len(sections))
	for idx, sec := range sections {
		taskParams := map[string]string{
			"host":     host,
			"port":     port,
			"timeout":  strconv.Itoa(timeout),
			"section":  sec,
			"username": strings.TrimSpace(params["username"]),
			"password": strings.TrimSpace(params["password"]),
		}
		tasks = append(tasks, &pb.MetricsTask{
			Name:      sec,
			Protocol:  "redis",
			TimeoutMs: int64(timeout),
			Priority:  int32(idx),
			Params:    taskParams,
			ExecKind:  "pull",
		})
	}
	return tasks
}

func splitHostPortFallback(target string) (string, string) {
	raw := strings.TrimSpace(target)
	if raw == "" {
		return "", ""
	}
	if strings.Contains(raw, "://") {
		if u, err := url.Parse(raw); err == nil {
			host := strings.TrimSpace(u.Hostname())
			port := strings.TrimSpace(u.Port())
			return host, port
		}
	}
	if host, port, err := net.SplitHostPort(raw); err == nil {
		return strings.TrimSpace(host), strings.TrimSpace(port)
	}
	parts := strings.Split(raw, ":")
	if len(parts) == 2 {
		return strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
	}
	return raw, ""
}

func readIntParam(params map[string]string, key string, def int) int {
	if params == nil {
		return def
	}
	raw := strings.TrimSpace(params[key])
	if raw == "" {
		return def
	}
	v, err := strconv.Atoi(raw)
	if err != nil || v <= 0 {
		return def
	}
	return v
}

func cloneStringMap(in map[string]string) map[string]string {
	if len(in) == 0 {
		return nil
	}
	out := make(map[string]string, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}

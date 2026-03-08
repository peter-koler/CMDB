package collector

import (
	"context"
	"errors"
	"fmt"
	"hash/fnv"
	"log"
	"net"
	"strconv"
	"sync"
	"time"

	"manager-go/internal/model"
	pb "manager-go/internal/pb/proto"
	"manager-go/internal/store"
)

// Manager 管理所有 Collector 连接
type Manager struct {
	clients map[string]*Client
	mu      sync.RWMutex

	// 依赖
	monitorStore   *store.MonitorStore
	collectorStore *store.CollectorStore

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

// Register 注册 Collector
func (m *Manager) Register(id, addr string) error {
	return m.RegisterWithInfo(id, addr, "", "", "public")
}

// RegisterWithInfo 注册 Collector（带详细信息）
func (m *Manager) RegisterWithInfo(id, addr, ip, version, mode string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.clients[id]; exists {
		return fmt.Errorf("collector %s already registered", id)
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
	client, err := m.SelectCollector(monitorID)
	if err != nil {
		return err
	}

	return client.SendTask(task)
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
	client, err := m.SelectCollector(monitorID)
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
		Version:    1,
		TraceId:    fmt.Sprintf("%d-%d", monitor.ID, time.Now().Unix()),
	}

	// 这里需要根据 monitor.App 从模板获取具体的 metrics 任务
	// 简化版本，实际应该从模板服务获取
	task.Tasks = []*pb.MetricsTask{
		{
			Name:      "default",
			Protocol:  "http", // 根据实际配置
			TimeoutMs: 10000,
			Priority:  0,
			Params:    make(map[string]string),
		},
	}

	return task, jobID
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

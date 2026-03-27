package collector

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"sync"
	"time"

	pb "manager-go/internal/pb/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"
)

// ConnectionState 表示 Collector 连接状态
type ConnectionState int

const (
	StateDisconnected ConnectionState = iota
	StateConnecting
	StateConnected
	StateReconnecting
)

func (s ConnectionState) String() string {
	switch s {
	case StateDisconnected:
		return "disconnected"
	case StateConnecting:
		return "connecting"
	case StateConnected:
		return "connected"
	case StateReconnecting:
		return "reconnecting"
	default:
		return "unknown"
	}
}

// Client 管理单个 Collector 的 gRPC 连接
type Client struct {
	id     string
	addr   string
	state  ConnectionState
	conn   *grpc.ClientConn
	stream pb.CollectorService_ConnectClient
	jobs   map[int64]*pb.CollectTask // 已下发任务缓存
	mu     sync.RWMutex

	// 配置
	heartbeatInterval    time.Duration
	reconnectBackoff     time.Duration
	maxReconnectAttempts int

	// 回调函数
	onReport      func(*pb.CollectRep)
	onAck         func(*pb.CommandAck)
	onStateChange func(string, ConnectionState)

	// 控制
	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// ClientOption 配置选项
type ClientOption func(*Client)

func WithHeartbeatInterval(d time.Duration) ClientOption {
	return func(c *Client) {
		c.heartbeatInterval = d
	}
}

func WithReconnectBackoff(d time.Duration) ClientOption {
	return func(c *Client) {
		c.reconnectBackoff = d
	}
}

func WithMaxReconnectAttempts(n int) ClientOption {
	return func(c *Client) {
		c.maxReconnectAttempts = n
	}
}

func WithReportHandler(fn func(*pb.CollectRep)) ClientOption {
	return func(c *Client) {
		c.onReport = fn
	}
}

func WithAckHandler(fn func(*pb.CommandAck)) ClientOption {
	return func(c *Client) {
		c.onAck = fn
	}
}

func WithStateChangeHandler(fn func(string, ConnectionState)) ClientOption {
	return func(c *Client) {
		c.onStateChange = fn
	}
}

// NewClient 创建新的 Collector 客户端
func NewClient(id, addr string, opts ...ClientOption) *Client {
	ctx, cancel := context.WithCancel(context.Background())
	c := &Client{
		id:                   id,
		addr:                 addr,
		state:                StateDisconnected,
		jobs:                 make(map[int64]*pb.CollectTask),
		heartbeatInterval:    5 * time.Second,
		reconnectBackoff:     5 * time.Second,
		maxReconnectAttempts: 10,
		ctx:                  ctx,
		cancel:               cancel,
	}
	for _, opt := range opts {
		opt(c)
	}
	return c
}

// Connect 建立 gRPC 连接
func (c *Client) Connect() error {
	c.mu.Lock()
	if c.state == StateConnected || c.state == StateConnecting {
		c.mu.Unlock()
		return errors.New("already connected or connecting")
	}
	c.setState(StateConnecting)
	c.mu.Unlock()

	// 创建 gRPC 连接
	conn, err := grpc.Dial(c.addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		c.setState(StateReconnecting)
		return fmt.Errorf("dial failed: %w", err)
	}

	// 创建双向流
	client := pb.NewCollectorServiceClient(conn)
	stream, err := client.Connect(c.ctx)
	if err != nil {
		conn.Close()
		c.setState(StateReconnecting)
		return fmt.Errorf("connect stream failed: %w", err)
	}

	c.mu.Lock()
	c.conn = conn
	c.stream = stream
	c.setState(StateConnected)
	c.mu.Unlock()

	log.Printf("[Collector %s] Connected to %s", c.id, c.addr)

	// 启动后台 goroutines
	c.wg.Add(3)
	go c.heartbeatLoop()
	go c.receiveLoop()
	go c.connectionMonitor()

	// 重新下发所有任务
	c.resendJobs()

	return nil
}

// Disconnect 断开连接
func (c *Client) Disconnect() {
	c.cancel()
	c.wg.Wait()

	c.mu.Lock()
	if c.stream != nil {
		c.stream.CloseSend()
	}
	if c.conn != nil {
		c.conn.Close()
	}
	c.conn = nil
	c.stream = nil
	c.setState(StateDisconnected)
	c.mu.Unlock()

	log.Printf("[Collector %s] Disconnected", c.id)
}

// SendTask 发送采集任务
func (c *Client) SendTask(task *pb.CollectTask) error {
	c.mu.RLock()
	stream := c.stream
	state := c.state
	c.mu.RUnlock()

	if state != StateConnected {
		return errors.New("not connected")
	}

	// 仅缓存周期任务；一次性探测任务不应在重连时被重发。
	if task.GetIntervalMs() > 0 {
		c.mu.Lock()
		c.jobs[task.JobId] = task
		c.mu.Unlock()
	}

	frame := &pb.CollectorFrame{
		Payload: &pb.CollectorFrame_Upsert{Upsert: task},
	}

	if err := stream.Send(frame); err != nil {
		return fmt.Errorf("send task failed: %w", err)
	}

	log.Printf("[Collector %s] Sent task %d (monitor %d)", c.id, task.JobId, task.MonitorId)
	return nil
}

// DeleteTask 删除采集任务
func (c *Client) DeleteTask(jobID int64) error {
	c.mu.RLock()
	stream := c.stream
	state := c.state
	c.mu.RUnlock()

	if state != StateConnected {
		return errors.New("not connected")
	}

	// 从缓存中删除
	c.mu.Lock()
	delete(c.jobs, jobID)
	c.mu.Unlock()

	frame := &pb.CollectorFrame{
		Payload: &pb.CollectorFrame_Delete{Delete: &pb.DeleteJobCommand{JobId: jobID}},
	}

	if err := stream.Send(frame); err != nil {
		return fmt.Errorf("send delete failed: %w", err)
	}

	log.Printf("[Collector %s] Deleted task %d", c.id, jobID)
	return nil
}

// GetState 获取连接状态
func (c *Client) GetState() ConnectionState {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.state
}

// GetAddr 获取 Collector 地址
func (c *Client) GetAddr() string {
	return c.addr
}

// GetJobs 获取已下发的任务列表
func (c *Client) GetJobs() []*pb.CollectTask {
	c.mu.RLock()
	defer c.mu.RUnlock()

	tasks := make([]*pb.CollectTask, 0, len(c.jobs))
	for _, job := range c.jobs {
		tasks = append(tasks, job)
	}
	return tasks
}

// setState 设置状态并触发回调
func (c *Client) setState(state ConnectionState) {
	oldState := c.state
	c.state = state
	if oldState != state && c.onStateChange != nil {
		go c.onStateChange(c.id, state)
	}
}

// heartbeatLoop 心跳循环
func (c *Client) heartbeatLoop() {
	defer c.wg.Done()

	ticker := time.NewTicker(c.heartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case <-c.ctx.Done():
			return
		case <-ticker.C:
			c.mu.RLock()
			stream := c.stream
			state := c.state
			c.mu.RUnlock()

			if state != StateConnected || stream == nil {
				continue
			}

			frame := &pb.CollectorFrame{
				Payload: &pb.CollectorFrame_Heartbeat{
					Heartbeat: &pb.Heartbeat{UnixMs: time.Now().UnixMilli()},
				},
			}

			if err := stream.Send(frame); err != nil {
				log.Printf("[Collector %s] Heartbeat failed: %v", c.id, err)
				// 触发重连
				go c.reconnect()
				return
			}
		}
	}
}

// receiveLoop 接收循环
func (c *Client) receiveLoop() {
	defer c.wg.Done()

	for {
		select {
		case <-c.ctx.Done():
			return
		default:
		}

		c.mu.RLock()
		stream := c.stream
		c.mu.RUnlock()

		if stream == nil {
			time.Sleep(100 * time.Millisecond)
			continue
		}

		frame, err := stream.Recv()
		if err != nil {
			if errors.Is(err, io.EOF) || c.ctx.Err() != nil {
				return
			}
			log.Printf("[Collector %s] Receive error: %v", c.id, err)
			go c.reconnect()
			return
		}

		// 处理接收到的消息
		c.handleFrame(frame)
	}
}

// handleFrame 处理接收到的帧
func (c *Client) handleFrame(frame *pb.ManagerFrame) {
	switch payload := frame.Payload.(type) {
	case *pb.ManagerFrame_Report:
		if c.onReport != nil {
			c.onReport(payload.Report)
		}
	case *pb.ManagerFrame_Ack:
		c.handleAck(payload.Ack)
		if c.onAck != nil {
			c.onAck(payload.Ack)
		}
	case *pb.ManagerFrame_Heartbeat:
		// 收到心跳响应，更新状态
		//	log.Printf("[Collector %s] Received heartbeat ack", c.id)
	}
}

// handleAck 处理命令确认
func (c *Client) handleAck(ack *pb.CommandAck) {
	log.Printf("[Collector %s] Received ack: command=%d job=%d status=%v reason=%s",
		c.id, ack.CommandId, ack.JobId, ack.Status, ack.Reason)
}

// connectionMonitor 连接状态监控
func (c *Client) connectionMonitor() {
	defer c.wg.Done()

	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-c.ctx.Done():
			return
		case <-ticker.C:
			c.mu.RLock()
			conn := c.conn
			state := c.state
			c.mu.RUnlock()

			if conn != nil && state == StateConnected {
				if conn.GetState() == connectivity.TransientFailure ||
					conn.GetState() == connectivity.Shutdown {
					log.Printf("[Collector %s] Connection state changed to %v", c.id, conn.GetState())
					go c.reconnect()
					return
				}
			}
		}
	}
}

// reconnect 重新连接
func (c *Client) reconnect() {
	c.mu.Lock()
	if c.state == StateReconnecting {
		c.mu.Unlock()
		return
	}
	c.setState(StateReconnecting)
	c.mu.Unlock()

	log.Printf("[Collector %s] Reconnecting...", c.id)

	// 关闭旧连接
	if c.conn != nil {
		c.conn.Close()
	}

	// 重连循环
	attempts := 0
	for {
		if c.ctx.Err() != nil {
			return
		}

		attempts++
		if c.maxReconnectAttempts > 0 && attempts > c.maxReconnectAttempts {
			log.Printf("[Collector %s] Max reconnect attempts reached", c.id)
			c.setState(StateDisconnected)
			return
		}

		log.Printf("[Collector %s] Reconnect attempt %d/%d", c.id, attempts, c.maxReconnectAttempts)

		if err := c.Connect(); err != nil {
			log.Printf("[Collector %s] Reconnect failed: %v", c.id, err)
			time.Sleep(c.reconnectBackoff)
			continue
		}

		return
	}
}

// resendJobs 重新下发所有任务
func (c *Client) resendJobs() {
	c.mu.RLock()
	jobs := make([]*pb.CollectTask, 0, len(c.jobs))
	for _, job := range c.jobs {
		jobs = append(jobs, job)
	}
	stream := c.stream
	c.mu.RUnlock()

	if stream == nil {
		return
	}

	for _, job := range jobs {
		frame := &pb.CollectorFrame{
			Payload: &pb.CollectorFrame_Upsert{Upsert: job},
		}
		if err := stream.Send(frame); err != nil {
			log.Printf("[Collector %s] Failed to resend job %d: %v", c.id, job.JobId, err)
		} else {
			log.Printf("[Collector %s] Resent job %d", c.id, job.JobId)
		}
	}
}

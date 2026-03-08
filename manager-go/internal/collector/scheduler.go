package collector

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"manager-go/internal/model"
	pb "manager-go/internal/pb/proto"
	"manager-go/internal/store"
)

// TaskScheduler 负责任务下发调度
type TaskScheduler struct {
	manager      *Manager
	monitorStore *store.MonitorStore

	// 任务队列
	taskQueue chan *TaskItem

	// 配置
	batchSize      int
	batchInterval  time.Duration
	workerCount    int

	// 控制
	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

// TaskItem 任务项
type TaskItem struct {
	Action    string // upsert | delete
	MonitorID int64
	JobID     int64
	Task      *pb.CollectTask
}

// SchedulerOption 配置选项
type SchedulerOption func(*TaskScheduler)

func WithBatchSize(size int) SchedulerOption {
	return func(s *TaskScheduler) {
		s.batchSize = size
	}
}

func WithBatchInterval(d time.Duration) SchedulerOption {
	return func(s *TaskScheduler) {
		s.batchInterval = d
	}
}

func WithWorkerCount(n int) SchedulerOption {
	return func(s *TaskScheduler) {
		s.workerCount = n
	}
}

// NewTaskScheduler 创建任务调度器
func NewTaskScheduler(manager *Manager, monitorStore *store.MonitorStore, opts ...SchedulerOption) *TaskScheduler {
	ctx, cancel := context.WithCancel(context.Background())
	s := &TaskScheduler{
		manager:       manager,
		monitorStore:  monitorStore,
		taskQueue:     make(chan *TaskItem, 1000),
		batchSize:     100,
		batchInterval: 1 * time.Second,
		workerCount:   4,
		ctx:           ctx,
		cancel:        cancel,
	}
	for _, opt := range opts {
		opt(s)
	}
	return s
}

// Start 启动调度器
func (s *TaskScheduler) Start() {
	// 启动工作协程
	for i := 0; i < s.workerCount; i++ {
		s.wg.Add(1)
		go s.worker(i)
	}

	// 启动批量处理协程
	s.wg.Add(1)
	go s.batchProcessor()

	log.Printf("[TaskScheduler] Started with %d workers", s.workerCount)
}

// Stop 停止调度器
func (s *TaskScheduler) Stop() {
	s.cancel()
	close(s.taskQueue)
	s.wg.Wait()
	log.Printf("[TaskScheduler] Stopped")
}

// ScheduleUpsert 调度添加/更新任务
func (s *TaskScheduler) ScheduleUpsert(monitor *model.Monitor) error {
	task, jobID := s.manager.BuildCollectTask(monitor)

	item := &TaskItem{
		Action:    "upsert",
		MonitorID: monitor.ID,
		JobID:     jobID,
		Task:      task,
	}

	select {
	case s.taskQueue <- item:
		return nil
	case <-s.ctx.Done():
		return fmt.Errorf("scheduler stopped")
	default:
		return fmt.Errorf("task queue full")
	}
}

// ScheduleDelete 调度删除任务
func (s *TaskScheduler) ScheduleDelete(monitorID, jobID int64) error {
	item := &TaskItem{
		Action:    "delete",
		MonitorID: monitorID,
		JobID:     jobID,
	}

	select {
	case s.taskQueue <- item:
		return nil
	case <-s.ctx.Done():
		return fmt.Errorf("scheduler stopped")
	default:
		return fmt.Errorf("task queue full")
	}
}

// worker 工作协程
func (s *TaskScheduler) worker(id int) {
	defer s.wg.Done()

	log.Printf("[TaskScheduler] Worker %d started", id)

	for {
		select {
		case <-s.ctx.Done():
			return
		case item, ok := <-s.taskQueue:
			if !ok {
				return
			}
			s.processTask(item)
		}
	}
}

// processTask 处理单个任务
func (s *TaskScheduler) processTask(item *TaskItem) {
	switch item.Action {
	case "upsert":
		if err := s.manager.DispatchTaskByMonitor(item.MonitorID, item.Task); err != nil {
			log.Printf("[TaskScheduler] Failed to dispatch task for monitor %d: %v", item.MonitorID, err)
		} else {
			log.Printf("[TaskScheduler] Dispatched task for monitor %d", item.MonitorID)
		}
	case "delete":
		if err := s.manager.DeleteTaskByMonitor(item.MonitorID, item.JobID); err != nil {
			log.Printf("[TaskScheduler] Failed to delete task %d: %v", item.JobID, err)
		} else {
			log.Printf("[TaskScheduler] Deleted task %d", item.JobID)
		}
	}
}

// batchProcessor 批量处理协程（用于优化大量任务场景）
func (s *TaskScheduler) batchProcessor() {
	defer s.wg.Done()

	ticker := time.NewTicker(s.batchInterval)
	defer ticker.Stop()

	batch := make([]*TaskItem, 0, s.batchSize)

	for {
		select {
		case <-s.ctx.Done():
			// 处理剩余任务
			if len(batch) > 0 {
				s.processBatch(batch)
			}
			return

		case item, ok := <-s.taskQueue:
			if !ok {
				// 队列关闭，处理剩余任务
				if len(batch) > 0 {
					s.processBatch(batch)
				}
				return
			}
			batch = append(batch, item)

			// 达到批量大小，立即处理
			if len(batch) >= s.batchSize {
				s.processBatch(batch)
				batch = make([]*TaskItem, 0, s.batchSize)
			}

		case <-ticker.C:
			// 超时处理
			if len(batch) > 0 {
				s.processBatch(batch)
				batch = make([]*TaskItem, 0, s.batchSize)
			}
		}
	}
}

// processBatch 批量处理任务
func (s *TaskScheduler) processBatch(items []*TaskItem) {
	if len(items) == 0 {
		return
	}

	log.Printf("[TaskScheduler] Processing batch of %d tasks", len(items))

	// 按 MonitorID 分组，批量下发到同一个 Collector
	groups := make(map[int64][]*TaskItem)
	for _, item := range items {
		groups[item.MonitorID] = append(groups[item.MonitorID], item)
	}

	for monitorID, group := range groups {
		for _, item := range group {
			s.processTask(item)
		}
		log.Printf("[TaskScheduler] Processed %d tasks for monitor %d", len(group), monitorID)
	}
}

// SyncMonitor 同步单个 Monitor
func (s *TaskScheduler) SyncMonitor(monitor *model.Monitor) error {
	if !monitor.Enabled {
		// 如果禁用，删除任务
		return s.ScheduleDelete(monitor.ID, monitor.ID)
	}
	// 启用，添加/更新任务
	return s.ScheduleUpsert(monitor)
}

// SyncAllMonitors 同步所有 Monitor
func (s *TaskScheduler) SyncAllMonitors() error {
	monitors := s.monitorStore.List()

	for _, monitor := range monitors {
		if err := s.SyncMonitor(&monitor); err != nil {
			log.Printf("[TaskScheduler] Failed to sync monitor %d: %v", monitor.ID, err)
		}
	}

	return nil
}

// GetQueueStats 获取队列统计
func (s *TaskScheduler) GetQueueStats() map[string]interface{} {
	return map[string]interface{}{
		"queue_length": len(s.taskQueue),
		"queue_cap":    cap(s.taskQueue),
	}
}

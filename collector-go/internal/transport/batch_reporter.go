package transport

import (
	"context"
	"log"
	"sync"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/pb"
)

// BatchReporter 批量上报管理器
type BatchReporter struct {
	results   chan model.Result
	batchSize int
	interval  time.Duration
	sender    func([]*pb.CollectRep) error

	mu        sync.Mutex
	buffer    []*pb.CollectRep
	ticker    *time.Ticker
	ctx       context.Context
	cancel    context.CancelFunc
	wg        sync.WaitGroup
}

// NewBatchReporter 创建批量上报器
func NewBatchReporter(batchSize int, interval time.Duration, sender func([]*pb.CollectRep) error) *BatchReporter {
	ctx, cancel := context.WithCancel(context.Background())
	return &BatchReporter{
		results:   make(chan model.Result, 10000),
		batchSize: batchSize,
		interval:  interval,
		sender:    sender,
		buffer:    make([]*pb.CollectRep, 0, batchSize),
		ticker:    time.NewTicker(interval),
		ctx:       ctx,
		cancel:    cancel,
	}
}

// Start 启动批量上报
func (br *BatchReporter) Start() {
	br.wg.Add(1)
	go br.loop()
	log.Printf("[BatchReporter] Started with batch size %d, interval %v", br.batchSize, br.interval)
}

// Stop 停止批量上报
func (br *BatchReporter) Stop() {
	br.cancel()
	br.ticker.Stop()
	close(br.results)
	br.wg.Wait()

	// 刷新剩余数据
	br.flush()
	log.Printf("[BatchReporter] Stopped")
}

// Submit 提交采集结果
func (br *BatchReporter) Submit(result model.Result) error {
	select {
	case br.results <- result:
		return nil
	case <-br.ctx.Done():
		return context.Canceled
	default:
		// 队列满，丢弃最旧的数据
		select {
		case <-br.results:
			br.results <- result
			log.Printf("[BatchReporter] Queue full, dropped oldest result")
			return nil
		default:
			return context.Canceled
		}
	}
}

// loop 主循环
func (br *BatchReporter) loop() {
	defer br.wg.Done()

	for {
		select {
		case <-br.ctx.Done():
			return
		case result, ok := <-br.results:
			if !ok {
				return
			}
			br.add(toCollectRep(result))
		case <-br.ticker.C:
			br.flush()
		}
	}
}

// add 添加结果到缓冲区
func (br *BatchReporter) add(rep *pb.CollectRep) {
	br.mu.Lock()
	defer br.mu.Unlock()

	br.buffer = append(br.buffer, rep)

	// 达到批量大小，立即发送
	if len(br.buffer) >= br.batchSize {
		br.mu.Unlock()
		br.flush()
		br.mu.Lock()
	}
}

// flush 刷新缓冲区
func (br *BatchReporter) flush() {
	br.mu.Lock()
	if len(br.buffer) == 0 {
		br.mu.Unlock()
		return
	}

	batch := make([]*pb.CollectRep, len(br.buffer))
	copy(batch, br.buffer)
	br.buffer = br.buffer[:0]
	br.mu.Unlock()

	// 异步发送
	go func() {
		if err := br.sender(batch); err != nil {
			log.Printf("[BatchReporter] Failed to send batch of %d: %v", len(batch), err)
			// 重新入队（简化处理，实际应该有限制）
			br.requeue(batch)
		} else {
			log.Printf("[BatchReporter] Sent batch of %d", len(batch))
		}
	}()
}

// requeue 重新入队
func (br *BatchReporter) requeue(batch []*pb.CollectRep) {
	// 简化处理：直接丢弃，避免无限重试导致内存溢出
	// 实际生产环境应该有更复杂的重试策略（如指数退避、死信队列等）
	log.Printf("[BatchReporter] Dropped batch of %d after send failure", len(batch))
}

// GetStats 获取统计信息
func (br *BatchReporter) GetStats() map[string]interface{} {
	br.mu.Lock()
	defer br.mu.Unlock()

	return map[string]interface{}{
		"buffer_size": len(br.buffer),
		"queue_len":   len(br.results),
		"queue_cap":   cap(br.results),
	}
}

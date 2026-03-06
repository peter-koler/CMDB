package queue

import (
	"fmt"
	"strings"

	"collector-go/internal/config"
)

func NewFromConfig(cfg config.Config) (ResultQueue, error) {
	switch strings.ToLower(cfg.Queue.Backend) {
	case "memory", "":
		return NewMemoryQueue(cfg.Queue.Memory.Size), nil
	case "kafka":
		primary := NewMemoryQueue(cfg.Queue.Memory.Size)
		kq := NewKafkaExecQueue(cfg.Queue.Kafka.Brokers, cfg.Queue.Kafka.Topic, cfg.Queue.Kafka.Bin)
		return NewFanoutQueue(primary, kq), nil
	default:
		return nil, fmt.Errorf("unsupported queue backend: %s", cfg.Queue.Backend)
	}
}

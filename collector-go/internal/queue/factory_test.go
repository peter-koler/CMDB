package queue

import (
	"testing"

	"collector-go/internal/config"
)

func TestNewFromConfigMemory(t *testing.T) {
	cfg := config.Default()
	cfg.Queue.Backend = "memory"
	q, err := NewFromConfig(cfg)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := q.(*MemoryQueue); !ok {
		t.Fatalf("expected MemoryQueue, got %T", q)
	}
}

func TestNewFromConfigKafka(t *testing.T) {
	cfg := config.Default()
	cfg.Queue.Backend = "kafka"
	cfg.Queue.Kafka.Brokers = []string{"127.0.0.1:9092"}
	cfg.Queue.Kafka.Topic = "collector.metrics"
	q, err := NewFromConfig(cfg)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := q.(*FanoutQueue); !ok {
		t.Fatalf("expected FanoutQueue, got %T", q)
	}
}

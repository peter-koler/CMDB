package queue

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"

	"collector-go/internal/model"
)

// KafkaExecQueue sends metrics to Kafka by shelling out to kcat.
// This keeps the project stdlib-only in offline environments.
type KafkaExecQueue struct {
	brokers string
	topic   string
	bin     string
}

func NewKafkaExecQueue(brokers []string, topic string, bin string) *KafkaExecQueue {
	if bin == "" {
		bin = "kcat"
	}
	return &KafkaExecQueue{brokers: strings.Join(brokers, ","), topic: topic, bin: bin}
}

func (q *KafkaExecQueue) Push(ctx context.Context, result model.Result) error {
	if q.brokers == "" || q.topic == "" {
		return fmt.Errorf("kafka config missing brokers/topic")
	}
	payload, err := json.Marshal(result)
	if err != nil {
		return err
	}
	cmd := exec.CommandContext(ctx, q.bin, "-P", "-b", q.brokers, "-t", q.topic)
	cmd.Stdin = bytes.NewReader(payload)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("kcat push failed: %w, output=%s", err, string(out))
	}
	return nil
}

func (q *KafkaExecQueue) Pop(ctx context.Context) (model.Result, error) {
	return model.Result{}, fmt.Errorf("kafka queue does not support local Pop")
}

func (q *KafkaExecQueue) Len() int { return 0 }

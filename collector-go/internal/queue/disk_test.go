package queue

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"collector-go/internal/model"
)

func TestDiskQueuePersistAndReload(t *testing.T) {
	path := filepath.Join(t.TempDir(), "queue.jsonl")
	q, err := NewDiskQueue(path)
	if err != nil {
		t.Fatalf("new disk queue failed: %v", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	in := model.Result{
		JobID:     1,
		MonitorID: 1001,
		App:       "linux",
		Metrics:   "cpu",
		Protocol:  "linux",
		Success:   true,
		Message:   "ok",
	}
	if err := q.Push(ctx, in); err != nil {
		t.Fatalf("push failed: %v", err)
	}

	q2, err := NewDiskQueue(path)
	if err != nil {
		t.Fatalf("reload disk queue failed: %v", err)
	}
	got, err := q2.Pop(ctx)
	if err != nil {
		t.Fatalf("pop failed: %v", err)
	}
	if got.JobID != in.JobID || got.MonitorID != in.MonitorID || got.Metrics != in.Metrics {
		t.Fatalf("reloaded item mismatch got=%+v want=%+v", got, in)
	}
}

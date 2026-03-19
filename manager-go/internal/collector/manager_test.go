package collector

import (
	"testing"

	"manager-go/internal/model"
)

func TestBuildDefaultTasksValkeyUsesRedisProtocol(t *testing.T) {
	monitor := &model.Monitor{
		App:    "valkey",
		Target: "127.0.0.1:6379",
		Params: map[string]string{"host": "127.0.0.1", "port": "6379"},
	}
	tasks := buildDefaultTasks(monitor)
	if len(tasks) != 1 {
		t.Fatalf("expected one task, got=%d", len(tasks))
	}
	if tasks[0].Protocol != "redis" {
		t.Fatalf("protocol want=redis got=%s", tasks[0].Protocol)
	}
}

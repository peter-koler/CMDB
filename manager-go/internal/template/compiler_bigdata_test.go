package template

import (
	"testing"

	"manager-go/internal/model"
)

func TestCompileMetricsTasks_JMX(t *testing.T) {
	rt := RuntimeTemplate{
		App: "hadoop",
		Content: `
app: hadoop
metrics:
  - name: jvm
    priority: 1
    protocol: jmx
    fields:
      - field: heap_memory_used
        type: 0
    aliasFields:
      - HeapMemoryUsage.used
    jmx:
      host: ^_^host^_^
      port: ^_^port^_^
      url: /jmx
      objectName: java.lang:type=Memory
      timeout: 5000
`,
	}
	monitor := &model.Monitor{
		ID:     10,
		App:    "hadoop",
		Target: "10.0.0.8:9870",
	}

	tasks, err := CompileMetricsTasks(rt, monitor)
	if err != nil {
		t.Fatalf("compile failed: %v", err)
	}
	if len(tasks) != 1 {
		t.Fatalf("expected 1 task, got %d", len(tasks))
	}
	task := tasks[0]
	if task.GetProtocol() != "jmx" {
		t.Fatalf("unexpected protocol: %s", task.GetProtocol())
	}
	if task.GetParams()["host"] != "10.0.0.8" {
		t.Fatalf("unexpected host params: %+v", task.GetParams())
	}
	if task.GetParams()["port"] != "9870" {
		t.Fatalf("unexpected port params: %+v", task.GetParams())
	}
	if task.GetParams()["objectName"] != "java.lang:type=Memory" {
		t.Fatalf("unexpected jmx objectName: %+v", task.GetParams())
	}
	if got := task.GetParams()["alias_fields"]; got != "HeapMemoryUsage.used" {
		t.Fatalf("unexpected alias_fields: %q", got)
	}
}

func TestCompileMetricsTasks_ClickHouseJDBC(t *testing.T) {
	rt := RuntimeTemplate{
		App: "clickhouse",
		Content: `
app: clickhouse
metrics:
  - name: status
    protocol: jdbc
    fields:
      - field: threads
        type: 0
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      database: system
      queryType: columns
      sql: select count() as threads from system.processes
      platform: clickhouse
`,
	}
	monitor := &model.Monitor{
		ID:     11,
		App:    "clickhouse",
		Target: "10.0.0.9:8123",
		Params: map[string]string{
			"username": "default",
			"password": "",
		},
	}

	tasks, err := CompileMetricsTasks(rt, monitor)
	if err != nil {
		t.Fatalf("compile failed: %v", err)
	}
	if len(tasks) != 1 {
		t.Fatalf("expected 1 task, got %d", len(tasks))
	}
	task := tasks[0]
	if task.GetProtocol() != "jdbc" {
		t.Fatalf("unexpected protocol: %s", task.GetProtocol())
	}
	if task.GetParams()["platform"] != "clickhouse" {
		t.Fatalf("unexpected jdbc platform params: %+v", task.GetParams())
	}
	if task.GetParams()["host"] != "10.0.0.9" || task.GetParams()["port"] != "8123" {
		t.Fatalf("unexpected target params: %+v", task.GetParams())
	}
}

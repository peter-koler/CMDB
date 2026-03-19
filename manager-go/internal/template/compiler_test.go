package template

import (
	"testing"

	"manager-go/internal/model"
)

func TestCompileMetricsTasks_MySQL(t *testing.T) {
	rt := RuntimeTemplate{
		App: "mysql",
		Content: `
app: mysql
params:
  - field: timeout
    defaultValue: 6000
metrics:
  - name: cache
    priority: 1
    protocol: jdbc
    fields:
      - field: query_cache_hit_rate
        type: 0
      - field: cache_hits
        type: 0
    calculates:
      - query_cache_hit_rate=(Qcache_hits + 1) / (Qcache_hits + Qcache_inserts + 1) * 100
      - cache_hits=Qcache_hits
    aliasFields:
      - Qcache_hits
      - Qcache_inserts
    units:
      - cache_hits=B->KB
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      timeout: ^_^timeout^_^
      queryType: columns
      sql: show global status like 'QCache%';
      platform: mysql
`,
	}
	monitor := &model.Monitor{
		ID:     1,
		App:    "mysql",
		Target: "127.0.0.1:3306",
		Params: map[string]string{
			"username": "root",
			"password": "pwd",
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
	if task.GetParams()["host"] != "127.0.0.1" {
		t.Fatalf("unexpected host: %+v", task.GetParams())
	}
	if task.GetParams()["port"] != "3306" {
		t.Fatalf("unexpected port: %+v", task.GetParams())
	}
	if len(task.GetCalculateSpecs()) != 2 {
		t.Fatalf("unexpected calculates: %+v", task.GetCalculateSpecs())
	}
	if got := task.GetParams()["alias_fields"]; got != "Qcache_hits,Qcache_inserts" {
		t.Fatalf("unexpected alias_fields: %q", got)
	}
	if len(task.GetTransform()) != 1 || task.GetTransform()[0].GetField() != "cache_hits" {
		t.Fatalf("unexpected unit transforms: %+v", task.GetTransform())
	}
	if task.GetFieldSpecs()[0].GetField() != "query_cache_hit_rate" {
		t.Fatalf("unexpected field specs: %+v", task.GetFieldSpecs())
	}
}

func TestCompileMetricsTasks_RedisSectionInfer(t *testing.T) {
	rt := RuntimeTemplate{
		App: "redis",
		Content: `
app: redis
params:
  - field: timeout
    defaultValue: 3000
metrics:
  - name: memory
    priority: 1
    protocol: redis
    fields:
      - field: used_memory
        type: 0
    redis:
      host: ^_^host^_^
      port: ^_^port^_^
      timeout: ^_^timeout^_^
`,
	}
	monitor := &model.Monitor{
		ID:     2,
		App:    "redis",
		Target: "10.1.1.2:6379",
	}
	tasks, err := CompileMetricsTasks(rt, monitor)
	if err != nil {
		t.Fatalf("compile failed: %v", err)
	}
	if len(tasks) != 1 {
		t.Fatalf("expected 1 task, got %d", len(tasks))
	}
	if tasks[0].GetParams()["section"] != "memory" {
		t.Fatalf("expected section=memory, got %+v", tasks[0].GetParams())
	}
}

func TestCompileMetricsTasks_MySQLSqlMerge(t *testing.T) {
	rt := RuntimeTemplate{
		App: "mysql",
		Content: `
app: mysql
params:
  - field: timeout
    defaultValue: 6000
metrics:
  - name: cache
    priority: 1
    protocol: jdbc
    fields:
      - field: cache_hits
        type: 0
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      timeout: ^_^timeout^_^
      queryType: columns
      platform: mysql
      sql: show global status like 'QCache%';
  - name: status
    priority: 2
    protocol: jdbc
    fields:
      - field: threads_connected
        type: 0
    jdbc:
      host: ^_^host^_^
      port: ^_^port^_^
      username: ^_^username^_^
      password: ^_^password^_^
      timeout: ^_^timeout^_^
      queryType: columns
      platform: mysql
      sql: show global status where Variable_name = 'Threads_connected';
`,
	}
	monitor := &model.Monitor{
		ID:     3,
		App:    "mysql",
		Target: "127.0.0.1:3306",
		Params: map[string]string{
			"username": "root",
			"password": "pwd",
		},
	}
	tasks, err := CompileMetricsTasks(rt, monitor)
	if err != nil {
		t.Fatalf("compile failed: %v", err)
	}
	if len(tasks) != 2 {
		t.Fatalf("expected 2 tasks, got %d", len(tasks))
	}
	for _, task := range tasks {
		if got := task.GetParams()["sql"]; got != "show global status;" {
			t.Fatalf("expected merged sql, got: %s", got)
		}
	}
}

func TestCompileMetricsTasks_CalculateInvalidFormat(t *testing.T) {
	rt := RuntimeTemplate{
		App: "mysql",
		Content: `
app: mysql
metrics:
  - name: cache
    protocol: jdbc
    fields:
      - field: cache_hits
        type: 0
    calculates:
      - hit_rate:(Qcache_hits + 1) / (Qcache_inserts + 1) * 100
    jdbc:
      sql: show global status;
      queryType: columns
      platform: mysql
`,
	}
	_, err := CompileMetricsTasks(rt, &model.Monitor{App: "mysql", Target: "127.0.0.1:3306"})
	if err == nil {
		t.Fatal("expected compile error")
	}
	ce, ok := AsCompileError(err)
	if !ok {
		t.Fatalf("expected compile error type, got: %T %v", err, err)
	}
	if ce.Path != "metrics[0].calculates[0]" {
		t.Fatalf("unexpected error path: %s", ce.Path)
	}
}

func TestCompileMetricsTasks_FieldMissing(t *testing.T) {
	rt := RuntimeTemplate{
		App: "redis",
		Content: `
app: redis
metrics:
  - name: memory
    protocol: redis
    fields:
      - type: 0
    redis:
      section: memory
`,
	}
	_, err := CompileMetricsTasks(rt, &model.Monitor{App: "redis", Target: "127.0.0.1:6379"})
	if err == nil {
		t.Fatal("expected compile error")
	}
	ce, ok := AsCompileError(err)
	if !ok {
		t.Fatalf("expected compile error type, got: %T %v", err, err)
	}
	if ce.Path != "metrics[0].fields[0].field" {
		t.Fatalf("unexpected error path: %s", ce.Path)
	}
}

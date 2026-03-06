package model

import "time"

// Job is issued once by manager and then scheduled locally in collector.
type Job struct {
	ID       int64         `json:"id"`
	Monitor  int64         `json:"monitor_id"`
	App      string        `json:"app"`
	Interval time.Duration `json:"interval"`
	Tasks    []MetricsTask `json:"tasks"`
}

type MetricsTask struct {
	Name      string            `json:"name"`
	Protocol  string            `json:"protocol"`
	Timeout   time.Duration     `json:"timeout"`
	Priority  int               `json:"priority"`
	Params    map[string]string `json:"params"`
	Transform []Transform       `json:"transform"`
}

type Transform struct {
	Field string `json:"field"`
	Op    string `json:"op"` // ms_to_s, bytes_to_mb, to_int, mul:n
}

type Result struct {
	JobID      int64             `json:"job_id"`
	MonitorID  int64             `json:"monitor_id"`
	App        string            `json:"app"`
	Metrics    string            `json:"metrics"`
	Protocol   string            `json:"protocol"`
	Code       string            `json:"code"`
	Time       time.Time         `json:"time"`
	Success    bool              `json:"success"`
	Message    string            `json:"message"`
	Fields     map[string]string `json:"fields"`
	RawLatency time.Duration     `json:"raw_latency"`
}

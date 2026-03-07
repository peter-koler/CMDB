package model

type MetricPoint struct {
	MonitorID int64             `json:"monitor_id"`
	App       string            `json:"app"`
	Metrics   string            `json:"metrics"`
	Field     string            `json:"field"`
	Value     float64           `json:"value"`
	UnixMs    int64             `json:"unix_ms"`
	Instance  string            `json:"instance"`
	Labels    map[string]string `json:"labels,omitempty"`
}

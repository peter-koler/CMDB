package model

import "time"

type MonitorStatus string

const (
	StatusUnknown MonitorStatus = "unknown"
)

type Monitor struct {
	ID              int64             `json:"id"`
	JobID           string            `json:"job_id"`
	CIID            int64             `json:"ci_id,omitempty"`
	CIModelID       int64             `json:"ci_model_id,omitempty"`
	CIName          string            `json:"ci_name,omitempty"`
	CICode          string            `json:"ci_code,omitempty"`
	Name            string            `json:"name"`
	App             string            `json:"app"`
	Target          string            `json:"target"`
	TemplateID      int64             `json:"template_id"`
	IntervalSeconds int               `json:"interval_seconds"`
	Enabled         bool              `json:"enabled"`
	Status          MonitorStatus     `json:"status"`
	Labels          map[string]string `json:"labels,omitempty"`
	Params          map[string]string `json:"params,omitempty"`
	Version         int64             `json:"version"`
	CreatedAt       time.Time         `json:"created_at"`
	UpdatedAt       time.Time         `json:"updated_at"`
}

type MonitorCreateInput struct {
	CIID            int64             `json:"ci_id,omitempty"`
	CIModelID       int64             `json:"ci_model_id,omitempty"`
	CIName          string            `json:"ci_name,omitempty"`
	CICode          string            `json:"ci_code,omitempty"`
	Name            string            `json:"name"`
	App             string            `json:"app"`
	Target          string            `json:"target"`
	TemplateID      int64             `json:"template_id"`
	IntervalSeconds int               `json:"interval_seconds"`
	Interval        int               `json:"interval"`
	Enabled         bool              `json:"enabled"`
	Labels          map[string]string `json:"labels,omitempty"`
	Params          map[string]string `json:"params,omitempty"`
}

type MonitorUpdateInput struct {
	CIID            int64             `json:"ci_id,omitempty"`
	CIModelID       int64             `json:"ci_model_id,omitempty"`
	CIName          string            `json:"ci_name,omitempty"`
	CICode          string            `json:"ci_code,omitempty"`
	Name            string            `json:"name"`
	App             string            `json:"app"`
	Target          string            `json:"target"`
	TemplateID      int64             `json:"template_id"`
	IntervalSeconds int               `json:"interval_seconds"`
	Interval        int               `json:"interval"`
	Enabled         bool              `json:"enabled"`
	Labels          map[string]string `json:"labels,omitempty"`
	Params          map[string]string `json:"params,omitempty"`
	Version         int64             `json:"version"`
}

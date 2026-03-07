package model

import "time"

type MonitorStatus string

const (
	StatusUnknown MonitorStatus = "unknown"
)

type Monitor struct {
	ID              int64         `json:"id"`
	Name            string        `json:"name"`
	App             string        `json:"app"`
	Target          string        `json:"target"`
	TemplateID      int64         `json:"template_id"`
	IntervalSeconds int           `json:"interval_seconds"`
	Enabled         bool          `json:"enabled"`
	Status          MonitorStatus `json:"status"`
	Version         int64         `json:"version"`
	CreatedAt       time.Time     `json:"created_at"`
	UpdatedAt       time.Time     `json:"updated_at"`
}

type MonitorCreateInput struct {
	Name            string            `json:"name"`
	App             string            `json:"app"`
	Target          string            `json:"target"`
	TemplateID      int64             `json:"template_id"`
	IntervalSeconds int               `json:"interval_seconds"`
	Enabled         bool              `json:"enabled"`
	Labels          map[string]string `json:"labels,omitempty"`
	Params          map[string]string `json:"params,omitempty"`
}

type MonitorUpdateInput struct {
	Name            string            `json:"name"`
	App             string            `json:"app"`
	Target          string            `json:"target"`
	TemplateID      int64             `json:"template_id"`
	IntervalSeconds int               `json:"interval_seconds"`
	Enabled         bool              `json:"enabled"`
	Labels          map[string]string `json:"labels,omitempty"`
	Params          map[string]string `json:"params,omitempty"`
	Version         int64             `json:"version"`
}

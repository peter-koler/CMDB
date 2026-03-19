package jmxcollector

import (
	"context"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("jmx", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	cfg, err := parseTaskConfig(task)
	if err != nil {
		return nil, "", err
	}
	payload, err := fetchJMXPayload(ctx, cfg)
	if err != nil {
		return nil, "", err
	}
	beans := extractBeans(payload)
	fields := collectFromBeans(beans, task)
	return fields, "ok", nil
}

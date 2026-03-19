package snmpcollector

import (
	"context"
	"fmt"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("snmp", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	opts, err := parseOptions(task)
	if err != nil {
		return nil, "", err
	}
	fields := map[string]string{}
	if opts.Operation == "walk" {
		for _, field := range opts.Order {
			oid := opts.OIDs[field]
			raw, oneErr := runSNMPCmd(ctx, "snmpwalk", buildArgs(opts, oid)...)
			if oneErr != nil {
				return map[string]string{"output": raw}, "snmpwalk failed", oneErr
			}
			vals := parseWalkValues(raw)
			if len(vals) == 0 {
				continue
			}
			fields[field] = vals[0]
			fields[field+"_count"] = fmt.Sprintf("%d", len(vals))
			for idx, item := range vals {
				fields[fmt.Sprintf("row%d_%s", idx+1, field)] = item
			}
		}
		return fields, "ok", nil
	}
	for _, field := range opts.Order {
		oid := opts.OIDs[field]
		raw, oneErr := runSNMPCmd(ctx, "snmpget", buildArgs(opts, oid)...)
		if oneErr != nil {
			return map[string]string{"output": raw}, "snmpget failed", oneErr
		}
		fields[field] = parseSNMPValue(raw)
	}
	return fields, "ok", nil
}

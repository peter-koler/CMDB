package snmpcollector

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
)

type options struct {
	Address   string
	Community string
	Version   string
	Operation string
	TimeoutS  int
	OIDs      map[string]string
	Order     []string
}

func parseOptions(task model.MetricsTask) (options, error) {
	host := strings.TrimSpace(task.Params["host"])
	if host == "" {
		return options{}, fmt.Errorf("missing host")
	}
	port := strings.TrimSpace(task.Params["port"])
	if port == "" {
		port = "161"
	}
	community := strings.TrimSpace(task.Params["community"])
	if community == "" {
		community = "public"
	}
	version := normalizeVersion(task.Params["version"], task.Params["snmpVersion"])
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 3 * time.Second
	}
	sec := int(timeout.Seconds())
	if sec < 1 {
		sec = 1
	}
	operation := strings.TrimSpace(strings.ToLower(task.Params["operation"]))
	if operation == "" {
		operation = "get"
	}
	if operation != "get" && operation != "walk" {
		operation = "get"
	}
	oids := collectOIDs(task.Params)
	if len(oids) == 0 {
		return options{}, fmt.Errorf("missing oid/oids")
	}
	order := make([]string, 0, len(oids))
	for key := range oids {
		order = append(order, key)
	}
	sort.Strings(order)
	return options{
		Address:   host + ":" + port,
		Community: community,
		Version:   version,
		Operation: operation,
		TimeoutS:  sec,
		OIDs:      oids,
		Order:     order,
	}, nil
}

func collectOIDs(params map[string]string) map[string]string {
	out := map[string]string{}
	for key, val := range params {
		if !strings.HasPrefix(key, "oids.") {
			continue
		}
		field := strings.TrimSpace(strings.TrimPrefix(key, "oids."))
		oid := strings.TrimSpace(val)
		if field == "" || oid == "" {
			continue
		}
		out[field] = oid
	}
	if len(out) == 0 {
		if oid := strings.TrimSpace(params["oid"]); oid != "" {
			out["value"] = oid
		}
	}
	return out
}

func normalizeVersion(candidates ...string) string {
	for _, raw := range candidates {
		v := strings.TrimSpace(strings.ToLower(raw))
		switch v {
		case "0", "v1", "1c":
			return "1"
		case "1", "2", "2c", "v2c":
			return "2c"
		case "3", "v3":
			return "3"
		}
		if iv, err := strconv.Atoi(v); err == nil {
			if iv <= 0 {
				return "1"
			}
			if iv == 1 || iv == 2 {
				return "2c"
			}
		}
	}
	return "2c"
}

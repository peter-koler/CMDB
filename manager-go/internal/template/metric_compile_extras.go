package template

import (
	"strconv"
	"strings"

	pb "manager-go/internal/pb/proto"
)

func compileAliasFields(items []any) []string {
	if len(items) == 0 {
		return nil
	}
	out := make([]string, 0, len(items))
	seen := make(map[string]struct{}, len(items))
	for _, item := range items {
		field := strings.TrimSpace(asString(item))
		if field == "" {
			continue
		}
		if _, ok := seen[field]; ok {
			continue
		}
		seen[field] = struct{}{}
		out = append(out, field)
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func compileUnitTransforms(items []any) []*pb.Transform {
	if len(items) == 0 {
		return nil
	}
	out := make([]*pb.Transform, 0, len(items))
	seen := make(map[string]struct{}, len(items))
	for _, item := range items {
		raw := strings.TrimSpace(asString(item))
		if raw == "" {
			continue
		}
		eq := strings.Index(raw, "=")
		arrow := strings.Index(raw, "->")
		if eq <= 0 || arrow <= eq+1 || arrow >= len(raw)-2 {
			continue
		}
		field := strings.TrimSpace(raw[:eq])
		fromUnit := strings.ToUpper(strings.TrimSpace(raw[eq+1 : arrow]))
		toUnit := strings.ToUpper(strings.TrimSpace(raw[arrow+2:]))
		if field == "" || fromUnit == "" || toUnit == "" {
			continue
		}
		if !metricNameRegexp.MatchString(field) {
			continue
		}
		factor, ok := unitFactor(fromUnit, toUnit)
		if !ok {
			continue
		}
		op := "mul:" + strconv.FormatFloat(factor, 'f', -1, 64)
		key := field + ":" + op
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, &pb.Transform{
			Field: field,
			Op:    op,
		})
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func unitFactor(fromUnit string, toUnit string) (float64, bool) {
	if fromUnit == toUnit {
		return 1, true
	}
	sizeBase := map[string]float64{
		"B":  1,
		"KB": 1024,
		"MB": 1024 * 1024,
		"GB": 1024 * 1024 * 1024,
	}
	if fromBytes, ok := sizeBase[fromUnit]; ok {
		if toBytes, ok2 := sizeBase[toUnit]; ok2 && toBytes > 0 {
			return fromBytes / toBytes, true
		}
	}

	timeBase := map[string]float64{
		"NS": 1,
		"US": 1000,
		"MS": 1000 * 1000,
		"S":  1000 * 1000 * 1000,
	}
	if fromNS, ok := timeBase[fromUnit]; ok {
		if toNS, ok2 := timeBase[toUnit]; ok2 && toNS > 0 {
			return fromNS / toNS, true
		}
	}
	return 0, false
}

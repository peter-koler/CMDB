package pipeline

import (
	"fmt"
	"strconv"
	"strings"

	"collector-go/internal/model"
)

func Apply(fields map[string]string, transforms []model.Transform) (map[string]string, error) {
	if len(transforms) == 0 {
		return fields, nil
	}
	out := make(map[string]string, len(fields))
	for k, v := range fields {
		out[k] = v
	}
	for _, t := range transforms {
		v, ok := out[t.Field]
		if !ok {
			continue
		}
		nv, err := applyOp(v, t.Op)
		if err != nil {
			return nil, err
		}
		out[t.Field] = nv
	}
	return out, nil
}

func applyOp(v string, op string) (string, error) {
	switch {
	case op == "ms_to_s":
		f, err := strconv.ParseFloat(v, 64)
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("%.3f", f/1000.0), nil
	case op == "bytes_to_mb":
		f, err := strconv.ParseFloat(v, 64)
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("%.3f", f/1024.0/1024.0), nil
	case op == "to_int":
		i, err := strconv.Atoi(strings.Split(v, ".")[0])
		if err != nil {
			return "", err
		}
		return strconv.Itoa(i), nil
	case strings.HasPrefix(op, "mul:"):
		m, err := strconv.ParseFloat(strings.TrimPrefix(op, "mul:"), 64)
		if err != nil {
			return "", err
		}
		f, err := strconv.ParseFloat(v, 64)
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("%.3f", f*m), nil
	default:
		return v, nil
	}
}

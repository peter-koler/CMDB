package servicecollector

import (
	"context"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"
)

func timeoutFrom(params map[string]string, fallback time.Duration, keys ...string) time.Duration {
	for _, key := range keys {
		raw := strings.TrimSpace(params[key])
		if raw == "" {
			continue
		}
		v, err := strconv.Atoi(raw)
		if err != nil || v <= 0 {
			continue
		}
		return time.Duration(v) * time.Millisecond
	}
	if fallback > 0 {
		return fallback
	}
	return 5 * time.Second
}

func firstNonEmpty(params map[string]string, keys ...string) string {
	for _, key := range keys {
		if value := strings.TrimSpace(params[key]); value != "" {
			return value
		}
	}
	return ""
}

func boolFrom(params map[string]string, def bool, keys ...string) bool {
	raw := strings.ToLower(strings.TrimSpace(firstNonEmpty(params, keys...)))
	if raw == "" {
		return def
	}
	switch raw {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return def
	}
}

func dialTCP(ctx context.Context, host, port string, timeout time.Duration) (net.Conn, time.Duration, error) {
	if strings.TrimSpace(host) == "" || strings.TrimSpace(port) == "" {
		return nil, 0, fmt.Errorf("missing host or port")
	}
	address := net.JoinHostPort(strings.TrimSpace(host), strings.TrimSpace(port))
	dialer := &net.Dialer{Timeout: timeout}
	start := time.Now()
	conn, err := dialer.DialContext(ctx, "tcp", address)
	if err != nil {
		return nil, 0, err
	}
	return conn, time.Since(start), nil
}

func parsePort(params map[string]string, defaultPort string, keys ...string) string {
	port := firstNonEmpty(params, keys...)
	if port == "" {
		return defaultPort
	}
	return port
}

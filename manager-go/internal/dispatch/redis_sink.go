package dispatch

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"strconv"
	"time"

	"manager-go/internal/model"
)

type RedisSink struct {
	Addr    string
	Key     string
	Timeout time.Duration
}

func NewRedisSink(addr, key string, timeout time.Duration) *RedisSink {
	if addr == "" {
		addr = "127.0.0.1:6379"
	}
	if key == "" {
		key = "monitor:metrics"
	}
	if timeout <= 0 {
		timeout = 500 * time.Millisecond
	}
	return &RedisSink{Addr: addr, Key: key, Timeout: timeout}
}

func (s *RedisSink) Name() string { return "redis" }

func (s *RedisSink) Write(ctx context.Context, key string, point model.MetricPoint) error {
	payload, err := json.Marshal(map[string]any{
		"idempotency_key": key,
		"point":           point,
	})
	if err != nil {
		return err
	}
	d := net.Dialer{Timeout: s.Timeout}
	conn, err := d.DialContext(ctx, "tcp", s.Addr)
	if err != nil {
		return err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(s.Timeout))
	cmd := encodeRedisCommand("LPUSH", s.Key, string(payload))
	if _, err := conn.Write([]byte(cmd)); err != nil {
		return err
	}
	reply := make([]byte, 64)
	n, err := conn.Read(reply)
	if err != nil {
		return err
	}
	if n > 0 && reply[0] == '-' {
		return fmt.Errorf("redis error: %s", string(reply[:n]))
	}
	return nil
}

func encodeRedisCommand(parts ...string) string {
	out := "*" + strconv.Itoa(len(parts)) + "\r\n"
	for _, p := range parts {
		out += "$" + strconv.Itoa(len(p)) + "\r\n" + p + "\r\n"
	}
	return out
}

package servicecollector

import (
	"context"
	"encoding/hex"
	"fmt"
	"net"
	"strings"
	"time"

	"collector-go/internal/model"
)

type UDPCollector struct{}

func (c *UDPCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "udp.host")
	port := parsePort(params, "53", "port", "udp.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "udp.timeout")
	content := strings.TrimSpace(firstNonEmpty(params, "content", "udp.content"))

	payload := []byte("hertzbeat")
	if content != "" {
		decoded, err := hex.DecodeString(strings.TrimPrefix(content, "0x"))
		if err != nil {
			return nil, "invalid hex payload", err
		}
		payload = decoded
	}
	address := net.JoinHostPort(host, port)
	dialer := &net.Dialer{Timeout: timeout}
	conn, err := dialer.DialContext(ctx, "udp", address)
	if err != nil {
		return nil, "udp dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	start := time.Now()
	if _, err := conn.Write(payload); err != nil {
		return nil, "udp write failed", err
	}
	buf := make([]byte, 2048)
	if _, err := conn.Read(buf); err != nil {
		return nil, "udp read failed", err
	}
	latency := time.Since(start)
	return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds())}, "ok", nil
}

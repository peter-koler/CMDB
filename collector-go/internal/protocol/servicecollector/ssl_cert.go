package servicecollector

import (
	"context"
	"crypto/tls"
	"fmt"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
)

type SSLCertCollector struct{}

func (c *SSLCertCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "http.host")
	if host == "" {
		return nil, "missing host", fmt.Errorf("missing host")
	}
	port := parsePort(params, "443", "port", "http.port")
	verify := boolFrom(params, true, "verify", "ssl", "http.ssl")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "http.timeout")

	dialer := &tls.Dialer{Config: &tls.Config{ServerName: host, InsecureSkipVerify: !verify}}
	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	start := time.Now()
	conn, err := dialer.DialContext(ctx2, "tcp", host+":"+port)
	if err != nil {
		return nil, "tls handshake failed", err
	}
	latency := time.Since(start)
	defer conn.Close()

	tlsConn, ok := conn.(*tls.Conn)
	if !ok {
		return nil, "invalid tls connection", fmt.Errorf("invalid tls connection")
	}
	state := tlsConn.ConnectionState()
	if len(state.PeerCertificates) == 0 {
		return nil, "peer cert missing", fmt.Errorf("peer cert missing")
	}
	cert := state.PeerCertificates[0]
	now := time.Now()
	startTS := cert.NotBefore.UnixMilli()
	endTS := cert.NotAfter.UnixMilli()
	daysRemaining := int(cert.NotAfter.Sub(now).Hours() / 24)
	if daysRemaining < 0 {
		daysRemaining = 0
	}
	subject := cert.Subject.CommonName
	if subject == "" {
		subject = strings.TrimSpace(cert.Subject.String())
	}

	return map[string]string{
		"responseTime":    fmt.Sprintf("%d", latency.Milliseconds()),
		"subject":         subject,
		"expired":         strconv.FormatBool(now.After(cert.NotAfter)),
		"start_time":      cert.NotBefore.Format(time.RFC3339),
		"start_timestamp": fmt.Sprintf("%d", startTS),
		"end_time":        cert.NotAfter.Format(time.RFC3339),
		"end_timestamp":   fmt.Sprintf("%d", endTS),
		"days_remaining":  fmt.Sprintf("%d", daysRemaining),
	}, "ok", nil
}

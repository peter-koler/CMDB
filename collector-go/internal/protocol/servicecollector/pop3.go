package servicecollector

import (
	"bufio"
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"strings"
	"time"

	"collector-go/internal/model"
)

type POP3Collector struct{}

func (c *POP3Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "pop3.host")
	port := parsePort(params, "110", "port", "pop3.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "pop3.timeout")
	ssl := boolFrom(params, false, "ssl", "pop3.ssl")
	user := firstNonEmpty(params, "email", "username", "pop3.email", "pop3.username")
	pass := firstNonEmpty(params, "authorize", "password", "pop3.authorize", "pop3.password")

	conn, latency, err := dialMailConn(ctx, host, port, timeout, ssl)
	if err != nil {
		return nil, "pop3 dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))
	r := bufio.NewReader(conn)
	w := bufio.NewWriter(conn)

	line, err := readLine(r)
	if err != nil || !strings.HasPrefix(line, "+OK") {
		if err == nil {
			err = fmt.Errorf("unexpected banner: %s", line)
		}
		return nil, "pop3 banner failed", err
	}
	if user != "" {
		if err := writeLine(w, "USER "+user); err != nil {
			return nil, "pop3 user failed", err
		}
		if line, err = readLine(r); err != nil || !strings.HasPrefix(line, "+OK") {
			if err == nil {
				err = fmt.Errorf("user rejected: %s", line)
			}
			return nil, "pop3 user rejected", err
		}
	}
	if pass != "" {
		if err := writeLine(w, "PASS "+pass); err != nil {
			return nil, "pop3 pass failed", err
		}
		if line, err = readLine(r); err != nil || !strings.HasPrefix(line, "+OK") {
			if err == nil {
				err = fmt.Errorf("pass rejected: %s", line)
			}
			return nil, "pop3 pass rejected", err
		}
	}
	if err := writeLine(w, "STAT"); err != nil {
		return nil, "pop3 stat failed", err
	}
	statLine, err := readLine(r)
	if err != nil || !strings.HasPrefix(statLine, "+OK") {
		if err == nil {
			err = fmt.Errorf("stat rejected: %s", statLine)
		}
		return nil, "pop3 stat rejected", err
	}
	count, size := parsePop3Stat(statLine)
	_ = writeLine(w, "QUIT")
	_, _ = readLine(r)

	return map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
		"email_count":  count,
		"mailbox_size": size,
	}, "ok", nil
}

func parsePop3Stat(line string) (string, string) {
	parts := strings.Fields(line)
	if len(parts) >= 3 {
		return parts[1], parts[2]
	}
	return "0", "0"
}

func dialMailConn(ctx context.Context, host, port string, timeout time.Duration, ssl bool) (net.Conn, time.Duration, error) {
	if ssl {
		dialer := &net.Dialer{Timeout: timeout}
		start := time.Now()
		conn, err := tls.DialWithDialer(dialer, "tcp", net.JoinHostPort(host, port), &tls.Config{ServerName: host, InsecureSkipVerify: true})
		if err != nil {
			return nil, 0, err
		}
		return conn, time.Since(start), nil
	}
	return dialTCP(ctx, host, port, timeout)
}

func readLine(r *bufio.Reader) (string, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(line), nil
}

func writeLine(w *bufio.Writer, line string) error {
	if _, err := w.WriteString(line + "\r\n"); err != nil {
		return err
	}
	return w.Flush()
}

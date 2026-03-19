package servicecollector

import (
	"context"
	"fmt"
	"net/textproto"
	"strings"
	"time"

	"collector-go/internal/model"
)

type SMTPCollector struct{}

func (c *SMTPCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "smtp.host")
	port := parsePort(params, "25", "port", "smtp.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "smtp.timeout")
	email := firstNonEmpty(params, "email", "smtp.email")
	if email == "" {
		email = "hertzbeat@example.com"
	}
	conn, latency, err := dialTCP(ctx, host, port, timeout)
	if err != nil {
		return nil, "smtp dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))
	tp := textproto.NewConn(conn)
	defer tp.Close()

	banner, err := readSMTPLine(tp)
	if err != nil {
		return nil, "smtp read banner failed", err
	}
	domain := smtpDomain(email)
	heloReply, heloErr := tp.Cmd("HELO %s", domain)
	if heloErr != nil {
		return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds()), "response": "false", "smtpBanner": banner, "heloInfo": heloErr.Error()}, "smtp helo failed", heloErr
	}
	tp.StartResponse(heloReply)
	heloLine, _ := readSMTPLine(tp)
	tp.EndResponse(heloReply)
	_, _ = tp.Cmd("QUIT")
	return map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
		"response":     "true",
		"smtpBanner":   banner,
		"heloInfo":     heloLine,
	}, "ok", nil
}

func readSMTPLine(tp *textproto.Conn) (string, error) {
	line, err := tp.ReadLine()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(line), nil
}

func smtpDomain(email string) string {
	parts := strings.Split(strings.TrimSpace(email), "@")
	if len(parts) == 2 && strings.TrimSpace(parts[1]) != "" {
		return strings.TrimSpace(parts[1])
	}
	return "localhost"
}

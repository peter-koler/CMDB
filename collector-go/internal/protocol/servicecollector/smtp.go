package servicecollector

import (
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"net/textproto"
	"strings"
	"time"

	"collector-go/internal/model"
)

type SMTPCollector struct{}

func (c *SMTPCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "smtp.host")
	sslOn := boolFrom(params, false, "ssl", "smtp.ssl")
	startTLS := boolFrom(params, false, "starttls", "smtp.starttls")
	if sslOn && startTLS {
		return nil, "invalid smtp tls mode", fmt.Errorf("ssl and starttls cannot both be enabled")
	}
	defaultPort := "25"
	if sslOn {
		defaultPort = "465"
	} else if startTLS {
		defaultPort = "587"
	}
	port := parsePort(params, defaultPort, "port", "smtp.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "smtp.timeout")
	email := firstNonEmpty(params, "email", "smtp.email")
	if email == "" {
		email = "hertzbeat@example.com"
	}
	conn, latency, err := dialMailConn(ctx, host, port, timeout, sslOn)
	if err != nil {
		return nil, "smtp dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))
	tp := textproto.NewConn(conn)
	defer tp.Close()

	banner, err := readSMTPBanner(tp)
	if err != nil {
		return nil, "smtp read banner failed", err
	}
	domain := smtpDomain(email)

	heloInfo, heloErr := smtpEHLO(tp, domain)
	if heloErr != nil {
		heloInfo, heloErr = smtpHELO(tp, domain)
		if heloErr != nil {
			return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds()), "response": "false", "smtpBanner": banner, "heloInfo": heloErr.Error()}, "smtp helo failed", heloErr
		}
	}

	if startTLS {
		upperInfo := strings.ToUpper(heloInfo)
		if !strings.Contains(upperInfo, "STARTTLS") {
			err := fmt.Errorf("server does not advertise STARTTLS")
			return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds()), "response": "false", "smtpBanner": banner, "heloInfo": err.Error()}, "smtp starttls unsupported", err
		}
		if err := smtpStartTLS(tp); err != nil {
			return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds()), "response": "false", "smtpBanner": banner, "heloInfo": err.Error()}, "smtp starttls failed", err
		}
		tlsConn := tls.Client(conn, &tls.Config{
			ServerName:         host,
			InsecureSkipVerify: true,
		})
		_ = tlsConn.SetDeadline(time.Now().Add(timeout))
		if err := tlsConn.HandshakeContext(ctx); err != nil {
			return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds()), "response": "false", "smtpBanner": banner, "heloInfo": err.Error()}, "smtp tls handshake failed", err
		}
		conn = tlsConn
		tp = textproto.NewConn(conn)
		defer tp.Close()
		heloInfo, heloErr = smtpEHLO(tp, domain)
		if heloErr != nil {
			heloInfo, heloErr = smtpHELO(tp, domain)
			if heloErr != nil {
				return map[string]string{"responseTime": fmt.Sprintf("%d", latency.Milliseconds()), "response": "false", "smtpBanner": banner, "heloInfo": heloErr.Error()}, "smtp helo after starttls failed", heloErr
			}
		}
	}
	_ = smtpQuit(tp)
	return map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
		"response":     "true",
		"smtpBanner":   banner,
		"heloInfo":     heloInfo,
	}, "ok", nil
}

func readSMTPBanner(tp *textproto.Conn) (string, error) {
	code, line, err := tp.ReadResponse(220)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(fmt.Sprintf("%d %s", code, line)), nil
}

func smtpCmdResponse(tp *textproto.Conn, expectCode int, format string, args ...any) (string, error) {
	id, err := tp.Cmd(format, args...)
	if err != nil {
		return "", err
	}
	tp.StartResponse(id)
	defer tp.EndResponse(id)
	_, line, err := tp.ReadResponse(expectCode)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(line), nil
}

func smtpEHLO(tp *textproto.Conn, domain string) (string, error) {
	return smtpCmdResponse(tp, 250, "EHLO %s", domain)
}

func smtpHELO(tp *textproto.Conn, domain string) (string, error) {
	return smtpCmdResponse(tp, 250, "HELO %s", domain)
}

func smtpStartTLS(tp *textproto.Conn) error {
	_, err := smtpCmdResponse(tp, 220, "STARTTLS")
	return err
}

func smtpQuit(tp *textproto.Conn) error {
	_, err := smtpCmdResponse(tp, 221, "QUIT")
	if err != nil {
		// best effort: some servers may close without 221.
		if ne, ok := err.(net.Error); ok && ne.Timeout() {
			return nil
		}
		return nil
	}
	return nil
}

func smtpDomain(email string) string {
	parts := strings.Split(strings.TrimSpace(email), "@")
	if len(parts) == 2 && strings.TrimSpace(parts[1]) != "" {
		return strings.TrimSpace(parts[1])
	}
	return "localhost"
}

package servicecollector

import (
	"bufio"
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
)

type IMAPCollector struct{}

func (c *IMAPCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "imap.host")
	port := parsePort(params, "993", "port", "imap.port")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "imap.timeout")
	ssl := boolFrom(params, true, "ssl", "imap.ssl")
	user := firstNonEmpty(params, "email", "username", "imap.email", "imap.username")
	pass := firstNonEmpty(params, "authorize", "password", "imap.authorize", "imap.password")

	conn, latency, err := dialMailConn(ctx, host, port, timeout, ssl)
	if err != nil {
		return nil, "imap dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))
	r := bufio.NewReader(conn)
	w := bufio.NewWriter(conn)

	if _, err := readLine(r); err != nil {
		return nil, "imap banner failed", err
	}
	if user != "" {
		if err := writeLine(w, fmt.Sprintf("a1 LOGIN %s %s", user, pass)); err != nil {
			return nil, "imap login failed", err
		}
		ok, err := readIMAPTagged(r, "a1")
		if err != nil || !ok {
			if err == nil {
				err = fmt.Errorf("imap login rejected")
			}
			return nil, "imap login rejected", err
		}
	}
	if err := writeLine(w, "a2 STATUS INBOX (MESSAGES)"); err != nil {
		return nil, "imap status failed", err
	}
	messages, ok, err := readIMAPStatus(r, "a2")
	if err != nil || !ok {
		if err == nil {
			err = fmt.Errorf("imap status rejected")
		}
		return nil, "imap status rejected", err
	}
	_ = writeLine(w, "a3 LOGOUT")

	return map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
		"email_count":  strconv.Itoa(messages),
		"mailbox_size": "0",
	}, "ok", nil
}

func readIMAPTagged(r *bufio.Reader, tag string) (bool, error) {
	for {
		line, err := readLine(r)
		if err != nil {
			return false, err
		}
		if strings.HasPrefix(strings.ToUpper(line), strings.ToUpper(tag)+" ") {
			return strings.Contains(strings.ToUpper(line), " OK"), nil
		}
	}
}

func readIMAPStatus(r *bufio.Reader, tag string) (int, bool, error) {
	messages := 0
	for {
		line, err := readLine(r)
		if err != nil {
			return 0, false, err
		}
		upper := strings.ToUpper(line)
		if strings.Contains(upper, "STATUS INBOX") && strings.Contains(upper, "MESSAGES") {
			messages = parseIMAPMessages(line)
		}
		if strings.HasPrefix(upper, strings.ToUpper(tag)+" ") {
			return messages, strings.Contains(upper, " OK"), nil
		}
	}
}

func parseIMAPMessages(line string) int {
	idx := strings.Index(strings.ToUpper(line), "MESSAGES")
	if idx < 0 {
		return 0
	}
	rest := strings.TrimSpace(line[idx+len("MESSAGES"):])
	parts := strings.Fields(rest)
	if len(parts) == 0 {
		return 0
	}
	v, _ := strconv.Atoi(strings.Trim(parts[0], ")"))
	return v
}

package rediscollector

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("redis", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	host := strings.TrimSpace(task.Params["host"])
	port := strings.TrimSpace(task.Params["port"])
	if host == "" {
		return nil, "", fmt.Errorf("missing host")
	}
	if port == "" {
		port = "6379"
	}
	address := net.JoinHostPort(host, port)
	timeout := resolveTimeout(task)

	dialer := net.Dialer{Timeout: timeout}
	conn, err := dialer.DialContext(ctx, "tcp", address)
	if err != nil {
		return nil, "", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))
	reader := bufio.NewReader(conn)

	username := strings.TrimSpace(task.Params["username"])
	password := strings.TrimSpace(task.Params["password"])
	if password != "" {
		authArgs := []string{"AUTH"}
		if username != "" {
			authArgs = append(authArgs, username, password)
		} else {
			authArgs = append(authArgs, password)
		}
		if _, err := sendCommand(conn, reader, authArgs...); err != nil {
			return nil, "", fmt.Errorf("auth failed: %w", err)
		}
	}

	section := strings.TrimSpace(task.Params["section"])
	var infoResp any
	if section == "" {
		infoResp, err = sendCommand(conn, reader, "INFO")
	} else {
		infoResp, err = sendCommand(conn, reader, "INFO", section)
	}
	if err != nil {
		return nil, "", fmt.Errorf("info command failed: %w", err)
	}

	raw, err := toString(infoResp)
	if err != nil {
		return nil, "", err
	}
	fields := parseInfo(raw)
	fields["identity"] = address
	if section != "" {
		fields["section"] = section
	}
	return fields, "ok", nil
}

func resolveTimeout(task model.MetricsTask) time.Duration {
	if task.Timeout > 0 {
		return task.Timeout
	}
	if raw := strings.TrimSpace(task.Params["timeout"]); raw != "" {
		if ms, err := strconv.Atoi(raw); err == nil && ms > 0 {
			return time.Duration(ms) * time.Millisecond
		}
	}
	return 3 * time.Second
}

func sendCommand(conn net.Conn, reader *bufio.Reader, args ...string) (any, error) {
	if err := writeCommand(conn, args...); err != nil {
		return nil, err
	}
	return readRESP(reader)
}

func writeCommand(w io.Writer, args ...string) error {
	if _, err := fmt.Fprintf(w, "*%d\r\n", len(args)); err != nil {
		return err
	}
	for _, arg := range args {
		if _, err := fmt.Fprintf(w, "$%d\r\n%s\r\n", len(arg), arg); err != nil {
			return err
		}
	}
	return nil
}

func readRESP(r *bufio.Reader) (any, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return nil, err
	}
	line = strings.TrimSuffix(line, "\n")
	line = strings.TrimSuffix(line, "\r")
	if line == "" {
		return nil, errors.New("empty redis response")
	}

	switch line[0] {
	case '+':
		return line[1:], nil
	case '-':
		return nil, errors.New(line[1:])
	case ':':
		return strconv.ParseInt(line[1:], 10, 64)
	case '$':
		n, err := strconv.Atoi(line[1:])
		if err != nil {
			return nil, err
		}
		if n < 0 {
			return "", nil
		}
		buf := make([]byte, n+2)
		if _, err := io.ReadFull(r, buf); err != nil {
			return nil, err
		}
		return string(buf[:n]), nil
	case '*':
		n, err := strconv.Atoi(line[1:])
		if err != nil {
			return nil, err
		}
		if n < 0 {
			return nil, nil
		}
		items := make([]any, 0, n)
		for i := 0; i < n; i++ {
			item, err := readRESP(r)
			if err != nil {
				return nil, err
			}
			items = append(items, item)
		}
		return items, nil
	default:
		return nil, fmt.Errorf("unsupported redis response: %s", line)
	}
}

func toString(v any) (string, error) {
	switch value := v.(type) {
	case string:
		return value, nil
	case []byte:
		return string(value), nil
	default:
		return "", fmt.Errorf("unexpected redis response type %T", v)
	}
}

func parseInfo(raw string) map[string]string {
	result := make(map[string]string)
	lines := strings.Split(raw, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(strings.TrimSuffix(line, "\r"))
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])
		if key == "" {
			continue
		}
		// commandstats style: cmdstat_get:calls=2,usec=10,usec_per_call=5.00
		if strings.Contains(value, "=") && strings.Contains(value, ",") {
			segments := strings.Split(value, ",")
			expanded := false
			for _, seg := range segments {
				pair := strings.SplitN(strings.TrimSpace(seg), "=", 2)
				if len(pair) != 2 {
					continue
				}
				result[key+"_"+strings.TrimSpace(pair[0])] = strings.TrimSpace(pair[1])
				expanded = true
			}
			if expanded {
				continue
			}
		}
		result[key] = value
	}
	return result
}

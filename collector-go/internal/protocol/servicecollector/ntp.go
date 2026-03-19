package servicecollector

import (
	"context"
	"encoding/binary"
	"fmt"
	"net"
	"time"

	"collector-go/internal/model"
)

type NTPCollector struct{}

const ntpEpochOffset = 2208988800

func (c *NTPCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "ntp.host")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "ntp.timeout")
	address := net.JoinHostPort(host, "123")
	dialer := &net.Dialer{Timeout: timeout}
	conn, err := dialer.DialContext(ctx, "udp", address)
	if err != nil {
		return nil, "ntp dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	req := make([]byte, 48)
	req[0] = 0x1b // LI=0, VN=3, Mode=3(client)
	t1 := time.Now()
	if _, err := conn.Write(req); err != nil {
		return nil, "ntp write failed", err
	}
	resp := make([]byte, 48)
	if _, err := conn.Read(resp); err != nil {
		return nil, "ntp read failed", err
	}
	t4 := time.Now()
	latency := t4.Sub(t1)

	version := int((resp[0] >> 3) & 0x07)
	mode := int(resp[0] & 0x07)
	stratum := int(resp[1])
	precision := int(int8(resp[3]))
	referenceID := string(resp[12:16])

	txSec := binary.BigEndian.Uint32(resp[40:44])
	txFrac := binary.BigEndian.Uint32(resp[44:48])
	serverTime := ntpToTime(txSec, txFrac)
	offset := serverTime.Sub(t4).Milliseconds()

	return map[string]string{
		"responseTime": fmt.Sprintf("%d", latency.Milliseconds()),
		"time":         fmt.Sprintf("%d", serverTime.UnixMilli()),
		"date":         serverTime.Format(time.RFC3339),
		"offset":       fmt.Sprintf("%d", offset),
		"delay":        fmt.Sprintf("%d", latency.Milliseconds()),
		"version":      fmt.Sprintf("%d", version),
		"mode":         fmt.Sprintf("%d", mode),
		"stratum":      fmt.Sprintf("%d", stratum),
		"referenceId":  referenceID,
		"precision":    fmt.Sprintf("%d", precision),
	}, "ok", nil
}

func ntpToTime(sec, frac uint32) time.Time {
	unixSec := int64(sec) - ntpEpochOffset
	nsec := (int64(frac) * 1e9) >> 32
	return time.Unix(unixSec, nsec)
}

package ipmicollector

import (
	"context"
	"strings"
	"time"
)

func collectByNative(ctx context.Context, host, port, user, pass, typ string, timeout time.Duration) (map[string]string, error) {
	client, err := newNativeClient(host, port, user, pass, timeout)
	if err != nil {
		return nil, err
	}
	if err := connectNativeClient(ctx, client, timeout); err != nil {
		return nil, err
	}
	defer closeNativeClient(client)

	switch strings.ToLower(strings.TrimSpace(typ)) {
	case "sensor":
		return collectSensorByNative(ctx, client, timeout)
	default:
		return collectChassisByNative(ctx, client, timeout)
	}
}

func withCollectTimeout(ctx context.Context, timeout time.Duration) (context.Context, context.CancelFunc) {
	return context.WithTimeout(ctx, timeout)
}

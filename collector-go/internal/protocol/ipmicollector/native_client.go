package ipmicollector

import (
	"context"
	"fmt"
	"strconv"
	"time"

	ipmi "github.com/bougou/go-ipmi"
)

func newNativeClient(host, port, user, pass string, timeout time.Duration) (*ipmi.Client, error) {
	portNum, err := strconv.Atoi(port)
	if err != nil || portNum <= 0 || portNum > 65535 {
		return nil, fmt.Errorf("invalid ipmi port: %s", port)
	}
	client, err := ipmi.NewClient(host, portNum, user, pass)
	if err != nil {
		return nil, err
	}
	client.WithInterface(ipmi.InterfaceLanplus)
	client.WithTimeout(timeout)
	return client, nil
}

func connectNativeClient(ctx context.Context, client *ipmi.Client, timeout time.Duration) error {
	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	return client.Connect(ctx2)
}

func closeNativeClient(client *ipmi.Client) {
	if client == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = client.Close(ctx)
}

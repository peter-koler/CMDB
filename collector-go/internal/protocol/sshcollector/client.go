package sshcollector

import (
	"context"
	"fmt"
	"net"
	"sync"
	"time"

	"golang.org/x/crypto/ssh"
)

type pooledClient struct {
	client   *ssh.Client
	lastUsed time.Time
}

var (
	poolMu    sync.Mutex
	clientMap = map[string]*pooledClient{}
)

func getClient(ctx context.Context, opts options) (*ssh.Client, error) {
	if !opts.ReuseConnection {
		return dialClient(ctx, opts)
	}
	key := opts.poolKey()
	poolMu.Lock()
	entry, ok := clientMap[key]
	poolMu.Unlock()
	if ok && entry != nil && entry.client != nil {
		if isAlive(entry.client) {
			entry.lastUsed = time.Now()
			return entry.client, nil
		}
		_ = entry.client.Close()
		poolMu.Lock()
		delete(clientMap, key)
		poolMu.Unlock()
	}
	client, err := dialClient(ctx, opts)
	if err != nil {
		return nil, err
	}
	poolMu.Lock()
	clientMap[key] = &pooledClient{client: client, lastUsed: time.Now()}
	poolMu.Unlock()
	return client, nil
}

func isAlive(client *ssh.Client) bool {
	session, err := client.NewSession()
	if err != nil {
		return false
	}
	_ = session.Close()
	return true
}

func dialClient(ctx context.Context, opts options) (*ssh.Client, error) {
	if opts.UseProxy {
		return dialViaProxy(ctx, opts)
	}
	cfg, err := buildSSHConfig(opts, false)
	if err != nil {
		return nil, err
	}
	dialer := &net.Dialer{Timeout: opts.Timeout}
	conn, err := dialer.DialContext(ctx, "tcp", opts.targetAddress())
	if err != nil {
		return nil, err
	}
	c, chans, reqs, err := ssh.NewClientConn(conn, opts.targetAddress(), cfg)
	if err != nil {
		_ = conn.Close()
		return nil, err
	}
	return ssh.NewClient(c, chans, reqs), nil
}

func dialViaProxy(ctx context.Context, opts options) (*ssh.Client, error) {
	if opts.ProxyHost == "" || opts.ProxyUsername == "" {
		return nil, fmt.Errorf("ssh proxy enabled but missing proxy host/username")
	}
	proxyCfg, err := buildSSHConfig(opts, true)
	if err != nil {
		return nil, err
	}
	dialer := &net.Dialer{Timeout: opts.Timeout}
	proxyRawConn, err := dialer.DialContext(ctx, "tcp", opts.proxyAddress())
	if err != nil {
		return nil, err
	}
	pc, pchans, preqs, err := ssh.NewClientConn(proxyRawConn, opts.proxyAddress(), proxyCfg)
	if err != nil {
		_ = proxyRawConn.Close()
		return nil, err
	}
	proxyClient := ssh.NewClient(pc, pchans, preqs)

	targetConn, err := proxyClient.Dial("tcp", opts.targetAddress())
	if err != nil {
		_ = proxyClient.Close()
		return nil, err
	}
	targetCfg, err := buildSSHConfig(opts, false)
	if err != nil {
		_ = targetConn.Close()
		_ = proxyClient.Close()
		return nil, err
	}
	tc, tchans, treqs, err := ssh.NewClientConn(targetConn, opts.targetAddress(), targetCfg)
	if err != nil {
		_ = targetConn.Close()
		_ = proxyClient.Close()
		return nil, err
	}
	return ssh.NewClient(tc, tchans, treqs), nil
}

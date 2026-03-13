package registration

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"strings"
	"time"

	"collector-go/internal/config"
)

// Client 用于向 Manager 注册
type Client struct {
	cfg        config.Config
	listenAddr string
	ip         string
	managerAddr string
	advertiseAddr string
}

// NewClient 创建注册客户端
func NewClient(cfg config.Config, listenAddr string) *Client {
	managerAddr := strings.TrimSpace(cfg.Manager.Addr)
	// macOS/dev 环境常见 localhost -> ::1，而 manager 可能仅监听 IPv4，导致 connect refused。
	if strings.HasPrefix(strings.ToLower(managerAddr), "localhost:") {
		managerAddr = "127.0.0.1" + managerAddr[len("localhost"):]
	}
	localIP := getLocalIP()
	advertiseIP := strings.TrimSpace(cfg.Manager.IP)
	if advertiseIP == "" {
		advertiseIP = localIP
	}
	if advertiseIP == "" {
		advertiseIP = "127.0.0.1"
	}
	return &Client{
		cfg:        cfg,
		listenAddr: listenAddr,
		ip:         localIP,
		managerAddr: managerAddr,
		advertiseAddr: normalizeAdvertiseAddr(listenAddr, advertiseIP),
	}
}

func normalizeAdvertiseAddr(listenAddr, advertiseIP string) string {
	addr := strings.TrimSpace(listenAddr)
	if addr == "" {
		return addr
	}
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		if strings.HasPrefix(addr, ":") && advertiseIP != "" {
			return net.JoinHostPort(advertiseIP, strings.TrimPrefix(addr, ":"))
		}
		return addr
	}
	host = strings.TrimSpace(host)
	if host == "" || host == "0.0.0.0" || host == "::" || host == "[::]" {
		if advertiseIP != "" {
			return net.JoinHostPort(advertiseIP, port)
		}
	}
	return addr
}

// getLocalIP 获取本机 IP 地址
func getLocalIP() string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return ""
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return ""
}

// Register 向 Manager 注册 Collector
func (c *Client) Register(ctx context.Context) error {
	url := fmt.Sprintf("http://%s/api/v1/collectors/register", c.managerAddr)

	// 使用配置的 IP 或自动检测的 IP
	ip := c.cfg.Manager.IP
	if ip == "" {
		ip = c.ip
	}

	payload := map[string]string{
		"id":      c.cfg.Manager.CollectorID,
		"addr":    c.advertiseAddr,
		"version": c.cfg.Manager.Version,
		"mode":    c.cfg.Manager.Mode,
		"ip":      ip,
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal register payload failed: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("create register request failed: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: c.cfg.ConnectionTimeout()}
	resp, err := client.Do(req)
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(ctx.Err(), context.Canceled) {
			return context.Canceled
		}
		return fmt.Errorf("send register request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("register failed with status: %d", resp.StatusCode)
	}

	log.Printf("[Registration] Successfully registered collector %s to manager %s", c.cfg.Manager.CollectorID, c.managerAddr)
	return nil
}

// Unregister 向 Manager 注销 Collector
func (c *Client) Unregister(ctx context.Context) error {
	url := fmt.Sprintf("http://%s/api/v1/collectors/%s", c.managerAddr, c.cfg.Manager.CollectorID)

	req, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("create unregister request failed: %w", err)
	}

	client := &http.Client{Timeout: c.cfg.ConnectionTimeout()}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("send unregister request failed: %w", err)
	}
	defer resp.Body.Close()

	log.Printf("[Registration] Successfully unregistered collector %s from manager %s", c.cfg.Manager.CollectorID, c.managerAddr)
	return nil
}

// Start 启动注册并保持心跳（如果需要）
func (c *Client) Start(ctx context.Context) error {
	// 首次注册（带重试）
	if err := c.registerWithRetry(ctx); err != nil {
		return err
	}

	// 启动心跳
	go c.heartbeatLoop(ctx)

	// 监听上下文取消，进行注销
	go func() {
		<-ctx.Done()
		// 使用新的上下文进行注销，避免主上下文已取消
		unregisterCtx, cancel := context.WithTimeout(context.Background(), c.cfg.ConnectionTimeout())
		defer cancel()
		if err := c.Unregister(unregisterCtx); err != nil {
			log.Printf("[Registration] Unregister failed: %v", err)
		}
	}()

	return nil
}

// registerWithRetry 带重试的注册
func (c *Client) registerWithRetry(ctx context.Context) error {
	maxAttempts := c.cfg.Connection.ReconnectMaxAttempts
	if maxAttempts <= 0 {
		maxAttempts = 10
	}

	interval := c.cfg.ReconnectInterval()

	for attempt := 1; attempt <= maxAttempts; attempt++ {
		if err := c.Register(ctx); err != nil {
			if errors.Is(err, context.Canceled) || errors.Is(ctx.Err(), context.Canceled) {
				return context.Canceled
			}
			log.Printf("[Registration] Register attempt %d/%d failed: %v", attempt, maxAttempts, err)
			if attempt < maxAttempts {
				select {
				case <-ctx.Done():
					return ctx.Err()
				case <-time.After(interval):
					continue
				}
			}
			return fmt.Errorf("register failed after %d attempts: %w", maxAttempts, err)
		}
		return nil
	}
	return fmt.Errorf("register failed after %d attempts", maxAttempts)
}

// heartbeatLoop 心跳循环
func (c *Client) heartbeatLoop(ctx context.Context) {
	ticker := time.NewTicker(c.cfg.HeartbeatInterval())
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := c.sendHeartbeat(ctx); err != nil {
				if errors.Is(err, context.Canceled) || errors.Is(ctx.Err(), context.Canceled) {
					return
				}
				log.Printf("[Registration] Heartbeat failed: %v", err)
				// 心跳失败时尝试重新注册
				if err := c.registerWithRetry(ctx); err != nil {
					if errors.Is(err, context.Canceled) || errors.Is(ctx.Err(), context.Canceled) {
						return
					}
					log.Printf("[Registration] Re-register failed: %v", err)
				}
			}
		}
	}
}

// sendHeartbeat 发送心跳
func (c *Client) sendHeartbeat(ctx context.Context) error {
	url := fmt.Sprintf("http://%s/api/v1/collectors/%s/heartbeat", c.managerAddr, c.cfg.Manager.CollectorID)

	req, err := http.NewRequestWithContext(ctx, "POST", url, nil)
	if err != nil {
		return fmt.Errorf("create heartbeat request failed: %w", err)
	}

	client := &http.Client{Timeout: c.cfg.ConnectionTimeout()}
	resp, err := client.Do(req)
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(ctx.Err(), context.Canceled) {
			return context.Canceled
		}
		return fmt.Errorf("send heartbeat request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("heartbeat failed with status: %d", resp.StatusCode)
	}

	return nil
}

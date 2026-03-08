package config

import (
	"encoding/json"
	"os"
	"runtime"
	"time"
)

type Config struct {
	Server struct {
		Addr string `json:"addr"`
	} `json:"server"`
	// Manager 配置 - 用于向 Manager 注册
	Manager struct {
		Addr        string `json:"addr"`         // Manager 地址，如 localhost:8080
		CollectorID string `json:"collector_id"` // Collector 唯一标识
		Mode        string `json:"mode"`         // public | private
		Version     string `json:"version"`      // 版本号
		IP          string `json:"ip"`           // IP 地址（可选，自动检测）
	} `json:"manager"`
	// Connection 连接配置
	Connection struct {
		HeartbeatIntervalSec int `json:"heartbeat_interval_sec"` // 心跳间隔（秒），默认 5
		ReconnectMaxAttempts int `json:"reconnect_max_attempts"` // 最大重连次数，默认 10
		ReconnectIntervalSec int `json:"reconnect_interval_sec"` // 重连间隔（秒），默认 5
		ConnectTimeoutSec    int `json:"connect_timeout_sec"`    // 连接超时（秒），默认 10
	} `json:"connection"`
	Scheduler struct {
		TickMs    int `json:"tick_ms"`
		WheelSize int `json:"wheel_size"`
	} `json:"scheduler"`
	Worker struct {
		Size      int `json:"size"`
		QueueSize int `json:"queue_size"`
	} `json:"worker"`
	Queue struct {
		Backend string `json:"backend"` // memory | kafka | disk
		Memory  struct {
			Size int `json:"size"`
		} `json:"memory"`
		Disk struct {
			Path string `json:"path"`
		} `json:"disk"`
		Kafka struct {
			Brokers []string `json:"brokers"`
			Topic   string   `json:"topic"`
			Bin     string   `json:"bin"` // kcat executable path
		} `json:"kafka"`
	} `json:"queue"`
	Stream struct {
		HeartbeatMs int `json:"heartbeat_ms"`
	} `json:"stream"`
	Precompute struct {
		Enabled bool `json:"enabled"`
		Rules   []struct {
			Metrics   string  `json:"metrics"`
			Protocol  string  `json:"protocol"`
			Field     string  `json:"field"`
			Op        string  `json:"op"`
			Threshold float64 `json:"threshold"`
			Summary   string  `json:"summary"`
		} `json:"rules"`
	} `json:"precompute"`
}

func Default() Config {
	var c Config
	c.Server.Addr = ":50051"
	c.Manager.Addr = "localhost:8080"
	c.Manager.CollectorID = "collector-1"
	c.Manager.Mode = "public"
	c.Manager.Version = "1.0.0"
	c.Manager.IP = ""
	c.Connection.HeartbeatIntervalSec = 5
	c.Connection.ReconnectMaxAttempts = 10
	c.Connection.ReconnectIntervalSec = 5
	c.Connection.ConnectTimeoutSec = 10
	c.Scheduler.TickMs = 1000
	c.Scheduler.WheelSize = 512
	c.Worker.Size = runtime.NumCPU() * 2
	c.Worker.QueueSize = 2048
	c.Queue.Backend = "memory"
	c.Queue.Memory.Size = 2048
	c.Queue.Disk.Path = "data/result-queue.jsonl"
	c.Queue.Kafka.Topic = "collector.metrics"
	c.Queue.Kafka.Bin = "kcat"
	c.Stream.HeartbeatMs = 10000
	c.Precompute.Enabled = false
	return c
}

func Load(path string) (Config, error) {
	c := Default()
	if path == "" {
		return c, nil
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return c, err
	}
	if err := json.Unmarshal(b, &c); err != nil {
		return c, err
	}
	return c, nil
}

func (c Config) TickDuration() time.Duration {
	if c.Scheduler.TickMs <= 0 {
		return time.Second
	}
	return time.Duration(c.Scheduler.TickMs) * time.Millisecond
}

func (c Config) HeartbeatDuration() time.Duration {
	if c.Stream.HeartbeatMs <= 0 {
		return 10 * time.Second
	}
	return time.Duration(c.Stream.HeartbeatMs) * time.Millisecond
}

// ConnectionTimeout 返回连接超时时间
func (c Config) ConnectionTimeout() time.Duration {
	if c.Connection.ConnectTimeoutSec <= 0 {
		return 10 * time.Second
	}
	return time.Duration(c.Connection.ConnectTimeoutSec) * time.Second
}

// HeartbeatInterval 返回心跳间隔时间
func (c Config) HeartbeatInterval() time.Duration {
	if c.Connection.HeartbeatIntervalSec <= 0 {
		return 5 * time.Second
	}
	return time.Duration(c.Connection.HeartbeatIntervalSec) * time.Second
}

// ReconnectInterval 返回重连间隔时间
func (c Config) ReconnectInterval() time.Duration {
	if c.Connection.ReconnectIntervalSec <= 0 {
		return 5 * time.Second
	}
	return time.Duration(c.Connection.ReconnectIntervalSec) * time.Second
}

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
	Scheduler struct {
		TickMs    int `json:"tick_ms"`
		WheelSize int `json:"wheel_size"`
	} `json:"scheduler"`
	Worker struct {
		Size      int `json:"size"`
		QueueSize int `json:"queue_size"`
	} `json:"worker"`
	Queue struct {
		Backend string `json:"backend"` // memory | kafka
		Memory  struct {
			Size int `json:"size"`
		} `json:"memory"`
		Kafka struct {
			Brokers []string `json:"brokers"`
			Topic   string   `json:"topic"`
			Bin     string   `json:"bin"` // kcat executable path
		} `json:"kafka"`
	} `json:"queue"`
	Stream struct {
		HeartbeatMs int `json:"heartbeat_ms"`
	} `json:"stream"`
}

func Default() Config {
	var c Config
	c.Server.Addr = ":50051"
	c.Scheduler.TickMs = 1000
	c.Scheduler.WheelSize = 512
	c.Worker.Size = runtime.NumCPU() * 2
	c.Worker.QueueSize = 2048
	c.Queue.Backend = "memory"
	c.Queue.Memory.Size = 2048
	c.Queue.Kafka.Topic = "collector.metrics"
	c.Queue.Kafka.Bin = "kcat"
	c.Stream.HeartbeatMs = 10000
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

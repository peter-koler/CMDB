package main

import (
	"context"
	"flag"
	"log"
	"net"
	"os/signal"
	"syscall"

	_ "collector-go/internal/bootstrap"
	"collector-go/internal/config"
	"collector-go/internal/dispatcher"
	"collector-go/internal/precompute"
	"collector-go/internal/queue"
	"collector-go/internal/registration"
	"collector-go/internal/scheduler"
	"collector-go/internal/transport"
	"collector-go/internal/worker"
)

func main() {
	configPath := flag.String("config", "config/collector.json", "collector config path")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	resultQueue, err := queue.NewFromConfig(cfg)
	if err != nil {
		log.Fatalf("create queue failed: %v", err)
	}
	pool := worker.New(cfg.Worker.Size, cfg.Worker.QueueSize)
	wheel := scheduler.NewWheel(cfg.TickDuration(), cfg.Scheduler.WheelSize)
	d := dispatcher.New(wheel, pool, resultQueue)
	rules := make([]precompute.Rule, 0, len(cfg.Precompute.Rules))
	for _, r := range cfg.Precompute.Rules {
		rules = append(rules, precompute.Rule{
			Metrics:   r.Metrics,
			Protocol:  r.Protocol,
			Field:     r.Field,
			Op:        r.Op,
			Threshold: r.Threshold,
			Summary:   r.Summary,
		})
	}
	d.SetPrecomputeEvaluator(precompute.New(cfg.Precompute.Enabled, rules))
	server := transport.NewGRPCServer(cfg.Server.Addr, d, resultQueue, cfg.HeartbeatDuration())

	pool.Start(ctx)
	go wheel.Start(ctx)

	// 先绑定监听端口，再向 manager 注册，避免 manager 立即回连时出现 connection refused。
	ln, err := net.Listen("tcp", cfg.Server.Addr)
	if err != nil {
		log.Fatalf("collector listen failed: %v", err)
	}
	serveErrCh := make(chan error, 1)
	go func() {
		serveErrCh <- server.ServeWithListener(ctx, ln)
	}()

	// 向 Manager 注册
	if cfg.Manager.Addr != "" {
		regClient := registration.NewClient(cfg, cfg.Server.Addr)
		if err := regClient.Start(ctx); err != nil {
			log.Printf("[Main] Failed to register to manager: %v", err)
			// 注册失败不退出，继续启动服务
		}
	}

	log.Printf("collector start on %s, queue=%s, manager=%s", cfg.Server.Addr, cfg.Queue.Backend, cfg.Manager.Addr)
	select {
	case err := <-serveErrCh:
		if err != nil {
			log.Fatalf("collector stopped with error: %v", err)
		}
	case <-ctx.Done():
		// graceful shutdown
	}
}

package main

import (
	"context"
	"flag"
	"log"
	"time"

	"collector-go/internal/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:50051", "collector grpc address")
	flag.Parse()

	conn, err := grpc.NewClient(*addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	client := pb.NewCollectorServiceClient(conn)
	ctx := context.Background()
	stream, err := client.Connect(ctx)
	if err != nil {
		log.Fatalf("connect stream: %v", err)
	}

	go func() {
		for {
			frame, err := stream.Recv()
			if err != nil {
				log.Printf("recv end: %v", err)
				return
			}
			if hb := frame.GetHeartbeat(); hb != nil {
				log.Printf("heartbeat %d", hb.GetUnixMs())
			}
			if rep := frame.GetReport(); rep != nil {
				log.Printf("report job=%d metric=%s success=%v fields=%v", rep.GetJobId(), rep.GetMetrics(), rep.GetSuccess(), rep.GetFields())
			}
		}
	}()

	err = stream.Send(&pb.CollectorFrame{Payload: &pb.CollectorFrame_Upsert{Upsert: &pb.CollectTask{
		JobId:      1,
		MonitorId:  1001,
		App:        "linux",
		IntervalMs: 5000,
		Tasks: []*pb.MetricsTask{{
			Name:      "linux_basic",
			Protocol:  "linux",
			TimeoutMs: 2000,
			Priority:  5,
		}},
	}}})
	if err != nil {
		log.Fatalf("send upsert: %v", err)
	}

	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		_ = stream.Send(&pb.CollectorFrame{Payload: &pb.CollectorFrame_Heartbeat{Heartbeat: &pb.Heartbeat{UnixMs: time.Now().UnixMilli()}}})
	}
}

package tests

import (
	"context"
	"net"
	"testing"
	"time"

	"collector-go/internal/dispatcher"
	"collector-go/internal/model"
	"collector-go/internal/pb"
	"collector-go/internal/protocol"
	"collector-go/internal/queue"
	"collector-go/internal/scheduler"
	"collector-go/internal/transport"
	"collector-go/internal/worker"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type mockCollector struct{}

func (m *mockCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	return map[string]string{"latency_ms": "200", "value": "10"}, "ok", nil
}

func TestManagerSendOnceCollectorLoopsLocally(t *testing.T) {
	protocol.Register("mock", &mockCollector{})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	q := queue.NewMemoryQueue(1024)
	pool := worker.New(4, 64)
	wheel := scheduler.NewWheel(20*time.Millisecond, 64)
	d := dispatcher.New(wheel, pool, q)
	server := transport.NewGRPCServer("127.0.0.1:0", d, q, 2*time.Second)

	pool.Start(ctx)
	go wheel.Start(ctx)

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer ln.Close()
	go func() { _ = server.ServeWithListener(ctx, ln) }()

	conn, err := grpc.NewClient(ln.Addr().String(), grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		t.Fatalf("dial grpc: %v", err)
	}
	defer conn.Close()
	client := pb.NewCollectorServiceClient(conn)
	stream, err := client.Connect(ctx)
	if err != nil {
		t.Fatalf("connect stream: %v", err)
	}

	err = stream.Send(&pb.CollectorFrame{Payload: &pb.CollectorFrame_Upsert{Upsert: &pb.CollectTask{
		JobId:      1,
		MonitorId:  1001,
		App:        "demo",
		IntervalMs: 50,
		Tasks: []*pb.MetricsTask{{
			Name:      "m1",
			Protocol:  "mock",
			TimeoutMs: int64(time.Second / time.Millisecond),
			Priority:  5,
			Transform: []*pb.Transform{{
				Field: "latency_ms",
				Op:    "ms_to_s",
			}},
		}},
	}}})
	if err != nil {
		t.Fatalf("send upsert: %v", err)
	}

	deadline := time.After(2 * time.Second)
	count := 0
	frameCh := make(chan *pb.ManagerFrame, 8)
	go func() {
		for {
			frame, err := stream.Recv()
			if err != nil {
				close(frameCh)
				return
			}
			frameCh <- frame
		}
	}()
	for count < 2 {
		select {
		case <-deadline:
			t.Fatalf("expected >=2 runs from local loop, got %d", count)
		case frame, ok := <-frameCh:
			if !ok {
				t.Fatalf("stream closed before receiving enough reports, got %d", count)
			}
			rep := frame.GetReport()
			if rep == nil {
				continue
			}
			if rep.GetFields()["latency_ms"] != "0.200" {
				t.Fatalf("expected transformed field 0.200, got %s", rep.GetFields()["latency_ms"])
			}
			count++
		}
	}
}

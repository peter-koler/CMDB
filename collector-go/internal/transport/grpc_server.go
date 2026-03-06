package transport

import (
	"context"
	"errors"
	"net"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/pb"
	"collector-go/internal/queue"
	"google.golang.org/grpc"
)

type JobHandler interface {
	RegisterJob(job model.Job)
	RemoveJob(jobID int64)
}

type GRPCServer struct {
	pb.UnimplementedCollectorServiceServer

	addr      string
	handler   JobHandler
	results   queue.ResultQueue
	heartbeat time.Duration
}

func NewGRPCServer(addr string, handler JobHandler, results queue.ResultQueue, heartbeat time.Duration) *GRPCServer {
	return &GRPCServer{addr: addr, handler: handler, results: results, heartbeat: heartbeat}
}

func (s *GRPCServer) Serve(ctx context.Context) error {
	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return err
	}
	return s.ServeWithListener(ctx, ln)
}

func (s *GRPCServer) ServeWithListener(ctx context.Context, ln net.Listener) error {
	defer ln.Close()
	gs := grpc.NewServer()
	pb.RegisterCollectorServiceServer(gs, s)

	errCh := make(chan error, 1)
	go func() {
		if err := gs.Serve(ln); err != nil {
			errCh <- err
		}
	}()

	select {
	case <-ctx.Done():
		gs.GracefulStop()
		return nil
	case err := <-errCh:
		if errors.Is(err, grpc.ErrServerStopped) {
			return nil
		}
		return err
	}
}

func (s *GRPCServer) Connect(stream grpc.BidiStreamingServer[pb.CollectorFrame, pb.ManagerFrame]) error {
	ctx := stream.Context()
	recvErr := make(chan error, 1)
	go func() {
		for {
			frame, err := stream.Recv()
			if err != nil {
				recvErr <- err
				return
			}
			if task := frame.GetUpsert(); task != nil {
				s.handler.RegisterJob(toJob(task))
			}
			if id := frame.GetDeleteJobId(); id > 0 {
				s.handler.RemoveJob(id)
			}
		}
	}()

	ticker := time.NewTicker(s.heartbeat)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil
		case err := <-recvErr:
			return err
		case <-ticker.C:
			if err := stream.Send(&pb.ManagerFrame{Payload: &pb.ManagerFrame_Heartbeat{Heartbeat: &pb.Heartbeat{UnixMs: time.Now().UnixMilli()}}}); err != nil {
				return err
			}
		default:
			popCtx, cancel := context.WithTimeout(ctx, 200*time.Millisecond)
			res, err := s.results.Pop(popCtx)
			cancel()
			if err != nil {
				if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
					continue
				}
				return err
			}
			if err := stream.Send(&pb.ManagerFrame{Payload: &pb.ManagerFrame_Report{Report: toCollectRep(res)}}); err != nil {
				return err
			}
		}
	}
}

func toJob(task *pb.CollectTask) model.Job {
	job := model.Job{
		ID:       task.GetJobId(),
		Monitor:  task.GetMonitorId(),
		App:      task.GetApp(),
		Interval: time.Duration(task.GetIntervalMs()) * time.Millisecond,
		Tasks:    make([]model.MetricsTask, 0, len(task.GetTasks())),
	}
	for _, mt := range task.GetTasks() {
		transforms := make([]model.Transform, 0, len(mt.GetTransform()))
		for _, tr := range mt.GetTransform() {
			transforms = append(transforms, model.Transform{Field: tr.GetField(), Op: tr.GetOp()})
		}
		job.Tasks = append(job.Tasks, model.MetricsTask{
			Name:      mt.GetName(),
			Protocol:  mt.GetProtocol(),
			Timeout:   time.Duration(mt.GetTimeoutMs()) * time.Millisecond,
			Priority:  int(mt.GetPriority()),
			Params:    mt.GetParams(),
			Transform: transforms,
		})
	}
	return job
}

func toCollectRep(res model.Result) *pb.CollectRep {
	return &pb.CollectRep{
		JobId:       res.JobID,
		MonitorId:   res.MonitorID,
		App:         res.App,
		Metrics:     res.Metrics,
		Protocol:    res.Protocol,
		TimeUnixMs:  res.Time.UnixMilli(),
		Success:     res.Success,
		Message:     res.Message,
		Fields:      res.Fields,
		RawLatencyMs: res.RawLatency.Milliseconds(),
	}
}

package telnetcollector

import (
	"context"
	"net"
	"testing"
	"time"

	"collector-go/internal/model"
)

func TestParseTelnetResultZookeeper(t *testing.T) {
	fields := parseTelnetResult(model.MetricsTask{Params: map[string]string{"app": "zookeeper"}}, "Environment:\nclientPort=2181\ndataDir=/tmp/zookeeper\n")
	if fields["clientPort"] != "2181" {
		t.Fatalf("clientPort want=2181 got=%s", fields["clientPort"])
	}
	if fields["dataDir"] != "/tmp/zookeeper" {
		t.Fatalf("dataDir want=/tmp/zookeeper got=%s", fields["dataDir"])
	}
}

func TestParseTelnetResultStats(t *testing.T) {
	fields := parseTelnetResult(model.MetricsTask{}, "zk_version\t3.8.4\nzk_avg_latency\t10\n")
	if fields["zk_version"] != "3.8.4" {
		t.Fatalf("zk_version want=3.8.4 got=%s", fields["zk_version"])
	}
	if fields["zk_avg_latency"] != "10" {
		t.Fatalf("zk_avg_latency want=10 got=%s", fields["zk_avg_latency"])
	}
}

func TestCollectWithoutCommandUsesTCPConnectivity(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed: %v", err)
	}
	defer ln.Close()

	done := make(chan struct{})
	go func() {
		defer close(done)
		conn, acceptErr := ln.Accept()
		if acceptErr == nil {
			_ = conn.Close()
		}
	}()

	host, port, err := net.SplitHostPort(ln.Addr().String())
	if err != nil {
		t.Fatalf("split host/port failed: %v", err)
	}

	fields, msg, err := (&Collector{}).Collect(context.Background(), model.MetricsTask{
		Timeout: 2 * time.Second,
		Params: map[string]string{
			"host": host,
			"port": port,
		},
	})
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if msg != "ok" {
		t.Fatalf("unexpected message: %s", msg)
	}
	if fields["responseTime"] == "" {
		t.Fatalf("expected responseTime, got %+v", fields)
	}
	<-done
}

package memcachedcollector

import (
	"context"
	"fmt"
	"net"
	"strings"
	"testing"
	"time"

	"collector-go/internal/model"
)

func TestParseKVLine(t *testing.T) {
	fields := map[string]string{}
	parseKVLine(fields, "STAT pid 123")
	if fields["pid"] != "123" {
		t.Fatalf("pid want=123 got=%s", fields["pid"])
	}
}

func TestParseSizesLine(t *testing.T) {
	fields := map[string]string{}
	parseSizesLine(fields, "STAT 96 12")
	if fields["item_size"] != "96" {
		t.Fatalf("item_size want=96 got=%s", fields["item_size"])
	}
	if fields["item_count"] != "12" {
		t.Fatalf("item_count want=12 got=%s", fields["item_count"])
	}
}

func TestCollect(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer ln.Close()

	done := make(chan struct{})
	go func() {
		defer close(done)
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		buf := make([]byte, 1024)
		for {
			n, err := conn.Read(buf)
			if err != nil {
				return
			}
			cmd := strings.TrimSpace(string(buf[:n]))
			switch cmd {
			case "stats":
				_, _ = fmt.Fprint(conn, "STAT pid 1\r\nSTAT uptime 2\r\nSTAT curr_connections 3\r\nEND\r\n")
			case "stats settings":
				_, _ = fmt.Fprint(conn, "STAT threads 4\r\nEND\r\n")
			case "stats sizes":
				_, _ = fmt.Fprint(conn, "STAT 128 5\r\nEND\r\n")
				return
			default:
				_, _ = fmt.Fprint(conn, "ERROR\r\n")
				return
			}
		}
	}()

	host, port, _ := net.SplitHostPort(ln.Addr().String())
	task := model.MetricsTask{
		Protocol: "memcached",
		Params: map[string]string{
			"host":    host,
			"port":    port,
			"timeout": "2000",
		},
		Timeout: 2 * time.Second,
	}
	c := &Collector{}
	fields, msg, err := c.Collect(context.Background(), task)
	if err != nil {
		t.Fatalf("collect: %v", err)
	}
	if msg != "ok" {
		t.Fatalf("msg want=ok got=%s", msg)
	}
	if fields["pid"] != "1" || fields["uptime"] != "2" || fields["threads"] != "4" {
		t.Fatalf("unexpected fields: %#v", fields)
	}
	if fields["item_size"] != "128" || fields["item_count"] != "5" {
		t.Fatalf("unexpected size fields: %#v", fields)
	}
	if fields["responseTime"] == "" {
		t.Fatal("expected responseTime")
	}
	<-done
}

package telnetcollector

import (
	"testing"

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

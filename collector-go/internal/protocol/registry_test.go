package protocol_test

import (
	"testing"

	_ "collector-go/internal/bootstrap"
	"collector-go/internal/protocol"
)

func TestBuiltinCollectorsRegistered(t *testing.T) {
	s := protocol.Snapshot()
	if _, ok := s["http"]; !ok {
		t.Fatal("http collector is not registered")
	}
	if _, ok := s["icmp"]; !ok {
		t.Fatal("icmp collector is not registered")
	}
	if _, ok := s["snmp"]; !ok {
		t.Fatal("snmp collector is not registered")
	}
	if _, ok := s["jdbc"]; !ok {
		t.Fatal("jdbc collector is not registered")
	}
	if _, ok := s["linux"]; !ok {
		t.Fatal("linux collector is not registered")
	}
}

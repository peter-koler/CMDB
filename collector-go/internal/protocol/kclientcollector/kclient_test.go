package kclientcollector

import "testing"

func TestBrokerPort(t *testing.T) {
	if got := brokerPort("127.0.0.1:9092"); got != "9092" {
		t.Fatalf("brokerPort want=9092 got=%s", got)
	}
}

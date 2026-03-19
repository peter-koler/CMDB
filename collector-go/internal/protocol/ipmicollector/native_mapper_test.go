package ipmicollector

import (
	"testing"

	ipmi "github.com/bougou/go-ipmi"
)

func TestBuildLastPowerEvent(t *testing.T) {
	res := &ipmi.GetChassisStatusResponse{
		LastPowerDownByPowerFault: true,
		ACFailed:                  true,
	}
	got := buildLastPowerEvent(res)
	if got != "power-fault,ac-failed" {
		t.Fatalf("unexpected event: %s", got)
	}
}

func TestBuildLastPowerEventNone(t *testing.T) {
	res := &ipmi.GetChassisStatusResponse{}
	got := buildLastPowerEvent(res)
	if got != "none" {
		t.Fatalf("unexpected event: %s", got)
	}
}

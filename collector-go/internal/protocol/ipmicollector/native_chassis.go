package ipmicollector

import (
	"context"
	"strings"
	"time"

	ipmi "github.com/bougou/go-ipmi"
)

func collectChassisByNative(ctx context.Context, client *ipmi.Client, timeout time.Duration) (map[string]string, error) {
	ctx2, cancel := withCollectTimeout(ctx, timeout)
	defer cancel()

	res, err := client.GetChassisStatus(ctx2)
	if err != nil {
		return nil, err
	}

	out := map[string]string{
		"system_power":               boolToOnOff(res.PowerIsOn),
		"power_overload":             boolToString(res.PowerOverload),
		"power_interlock":            boolToString(res.InterLock),
		"power_fault":                boolToString(res.PowerFault),
		"power_control_fault":        boolToString(res.PowerControlFault),
		"power_restore_policy":       strings.TrimSpace(res.PowerRestorePolicy.String()),
		"last_power_event":           buildLastPowerEvent(res),
		"fan_fault":                  boolToString(res.CollingFanFault),
		"drive_fault":                boolToString(res.DriveFault),
		"front_panel_lockout_active": boolToString(res.FrontPanelLockoutActive),
	}
	return out, nil
}

func buildLastPowerEvent(res *ipmi.GetChassisStatusResponse) string {
	events := make([]string, 0, 5)
	if res.LastPowerOnByCommand {
		events = append(events, "power-on-command")
	}
	if res.LastPowerDownByPowerFault {
		events = append(events, "power-fault")
	}
	if res.LastPowerDownByPowerInterlockActivated {
		events = append(events, "power-interlock")
	}
	if res.LastPowerDownByPowerOverload {
		events = append(events, "power-overload")
	}
	if res.ACFailed {
		events = append(events, "ac-failed")
	}
	if len(events) == 0 {
		return "none"
	}
	return strings.Join(events, ",")
}

func boolToOnOff(v bool) string {
	if v {
		return "on"
	}
	return "off"
}

func boolToString(v bool) string {
	if v {
		return "true"
	}
	return "false"
}

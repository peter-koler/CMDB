package ipmicollector

import "strings"

var chassisFieldMap = map[string]string{
	"system power":               "system_power",
	"power overload":             "power_overload",
	"power interlock":            "power_interlock",
	"main power fault":           "power_fault",
	"power control fault":        "power_control_fault",
	"power restore policy":       "power_restore_policy",
	"last power event":           "last_power_event",
	"drive fault":                "drive_fault",
	"cooling/fan fault":          "fan_fault",
	"front-panel lockout":        "front_panel_lockout_active",
	"front-panel lockout active": "front_panel_lockout_active",
}

func parseChassisOutput(raw string) map[string]string {
	out := map[string]string{}
	lines := strings.Split(raw, "\n")
	for _, line := range lines {
		parts := strings.SplitN(strings.TrimSpace(line), ":", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.ToLower(strings.TrimSpace(parts[0]))
		value := strings.TrimSpace(parts[1])
		if mapped, ok := chassisFieldMap[key]; ok {
			out[mapped] = value
		}
	}
	return out
}

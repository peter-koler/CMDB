package redfishcollector

import "strings"

func defaultSchema(metricName string) string {
	switch strings.TrimSpace(metricName) {
	case "Chassis":
		return "/redfish/v1/Chassis"
	case "Fan":
		return "/redfish/v1/Chassis/{ChassisId}/ThermalSubsystem/Fans"
	case "Battery":
		return "/redfish/v1/Chassis/{ChassisId}/PowerSubsystem/Batteries"
	case "PowerSupply":
		return "/redfish/v1/Chassis/{ChassisId}/PowerSubsystem/PowerSupplies"
	default:
		return ""
	}
}

func splitCSV(raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, item := range parts {
		item = strings.TrimSpace(item)
		if item != "" {
			out = append(out, item)
		}
	}
	return out
}

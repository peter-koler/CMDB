package ipmicollector

import (
	"fmt"
	"strings"
)

func parseSensorOutput(raw string) map[string]string {
	out := map[string]string{}
	lines := strings.Split(raw, "\n")
	row := 0
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.Split(line, "|")
		if len(parts) < 2 {
			continue
		}
		sensorID := strings.TrimSpace(parts[0])
		reading := strings.TrimSpace(parts[1])
		entity := ""
		if len(parts) >= 4 {
			entity = strings.TrimSpace(parts[3])
		}
		sensorType := inferSensorType(sensorID)
		row++
		prefix := fmt.Sprintf("row%d_", row)
		out[prefix+"sensor_id"] = sensorID
		out[prefix+"sensor_reading"] = reading
		out[prefix+"entity_id"] = entity
		out[prefix+"sensor_type"] = sensorType
		if row == 1 {
			out["sensor_id"] = sensorID
			out["sensor_reading"] = reading
			out["entity_id"] = entity
			out["sensor_type"] = sensorType
		}
	}
	return out
}

func inferSensorType(sensorID string) string {
	name := strings.ToLower(strings.TrimSpace(sensorID))
	switch {
	case strings.Contains(name, "temp"):
		return "Temperature"
	case strings.Contains(name, "fan"):
		return "Fan"
	case strings.Contains(name, "volt"):
		return "Voltage"
	case strings.Contains(name, "power"):
		return "Power"
	default:
		return "Generic"
	}
}

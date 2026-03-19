package ipmicollector

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	ipmi "github.com/bougou/go-ipmi"
)

func collectSensorByNative(ctx context.Context, client *ipmi.Client, timeout time.Duration) (map[string]string, error) {
	ctx2, cancel := withCollectTimeout(ctx, timeout)
	defer cancel()

	sensors, err := client.GetSensors(ctx2)
	if err != nil {
		return nil, err
	}
	if len(sensors) == 0 {
		return nil, fmt.Errorf("no sensors returned")
	}

	out := map[string]string{}
	for i, sensor := range sensors {
		prefix := "row" + strconv.Itoa(i+1) + "_"
		sensorID := strings.TrimSpace(sensor.Name)
		if sensorID == "" {
			sensorID = fmt.Sprintf("sensor-%d", sensor.Number)
		}
		entityID := fmt.Sprintf("%d.%d", uint8(sensor.EntityID), uint8(sensor.EntityInstance))
		sensorType := strings.TrimSpace(sensor.SensorType.String())
		if sensorType == "" || sensorType == "Reserved" {
			sensorType = inferSensorType(sensorID)
		}
		reading := strings.TrimSpace(sensor.HumanStr())
		if reading == "" {
			reading = "N/A"
		}

		out[prefix+"sensor_id"] = sensorID
		out[prefix+"sensor_reading"] = reading
		out[prefix+"entity_id"] = entityID
		out[prefix+"sensor_type"] = sensorType

		if i == 0 {
			out["sensor_id"] = sensorID
			out["sensor_reading"] = reading
			out["entity_id"] = entityID
			out["sensor_type"] = sensorType
		}
	}
	return out, nil
}

package ipmicollector

import "testing"

func TestParseChassisOutput(t *testing.T) {
	raw := "System Power : on\nPower Overload : false\nCooling/Fan Fault : false\n"
	out := parseChassisOutput(raw)
	if out["system_power"] != "on" {
		t.Fatalf("system_power want=on got=%s", out["system_power"])
	}
	if out["fan_fault"] != "false" {
		t.Fatalf("fan_fault want=false got=%s", out["fan_fault"])
	}
}

func TestParseSensorOutput(t *testing.T) {
	raw := "Temp1 | 34 degrees C | ok | 7.1\nFan1 | 4800 RPM | ok | 29.1\n"
	out := parseSensorOutput(raw)
	if out["sensor_id"] != "Temp1" {
		t.Fatalf("sensor_id want=Temp1 got=%s", out["sensor_id"])
	}
	if out["sensor_type"] != "Temperature" {
		t.Fatalf("sensor_type want=Temperature got=%s", out["sensor_type"])
	}
	if out["row2_sensor_id"] != "Fan1" {
		t.Fatalf("row2_sensor_id want=Fan1 got=%s", out["row2_sensor_id"])
	}
}

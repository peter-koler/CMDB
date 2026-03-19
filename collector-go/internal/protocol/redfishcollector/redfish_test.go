package redfishcollector

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"collector-go/internal/model"
)

func TestCollectFan(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/redfish/v1/Chassis":
			_, _ = w.Write([]byte(`{"Members":[{"@odata.id":"/redfish/v1/Chassis/1"}]}`))
		case r.URL.Path == "/redfish/v1/Chassis/1/ThermalSubsystem/Fans":
			_, _ = w.Write([]byte(`{"Members":[{"@odata.id":"/redfish/v1/Chassis/1/ThermalSubsystem/Fans/Fan1"}]}`))
		case strings.HasPrefix(r.URL.Path, "/redfish/v1/Chassis/1/ThermalSubsystem/Fans/Fan1"):
			_, _ = w.Write([]byte(`{"@odata.id":"` + r.URL.Path + `","Name":"Fan1","Status":{"State":"Enabled","Health":"OK"},"SpeedPercent":{"Reading":41,"SpeedRPM":4020}}`))
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer srv.Close()

	hostPort := strings.TrimPrefix(srv.URL, "http://")
	parts := strings.Split(hostPort, ":")
	task := model.MetricsTask{
		Name:     "Fan",
		Protocol: "redfish",
		Params: map[string]string{
			"host":     parts[0],
			"port":     parts[1],
			"ssl":      "false",
			"timeout":  "3000",
			"schema":   "/redfish/v1/Chassis/{ChassisId}/ThermalSubsystem/Fans",
			"jsonPath": "$.['@odata.id'],$.Name,$.Status.State,$.Status.Health,$.SpeedPercent.Reading,$.SpeedPercent.SpeedRPM",
		},
		FieldSpecs: []model.FieldSpec{
			{Field: "id"}, {Field: "name"}, {Field: "state"}, {Field: "health"}, {Field: "temperature"}, {Field: "speed"},
		},
	}
	c := &Collector{}
	fields, _, err := c.Collect(context.Background(), task)
	if err != nil {
		t.Fatalf("collect failed: %v", err)
	}
	if fields["name"] != "Fan1" || fields["speed"] != "4020" || fields["health"] != "OK" {
		t.Fatalf("unexpected fields: %+v", fields)
	}
}

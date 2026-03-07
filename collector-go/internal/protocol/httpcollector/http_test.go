package httpcollector

import (
	"context"
	"testing"

	"collector-go/internal/model"
)

func TestCollectMissingURL(t *testing.T) {
	c := &Collector{}
	_, _, err := c.Collect(context.Background(), model.MetricsTask{
		Name:     "m1",
		Protocol: "http",
		Params:   map[string]string{},
	})
	if err == nil {
		t.Fatal("expected missing url error")
	}
}

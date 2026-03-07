package alert

import (
	"context"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestVMClientQueryValue(t *testing.T) {
	c := NewVMClient("http://vm.test", time.Second)
	c.Client = &http.Client{
		Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
			if req.URL.Path != "/api/v1/query" {
				return &http.Response{
					StatusCode: http.StatusNotFound,
					Body:       io.NopCloser(strings.NewReader("")),
					Header:     make(http.Header),
				}, nil
			}
			body := `{"status":"success","data":{"resultType":"vector","result":[{"value":[1710000000,"82.5"]}]}}`
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader(body)),
				Header:     make(http.Header),
			}, nil
		}),
	}
	v, err := c.QueryValue(context.Background(), `avg_over_time(cpu_usage[5m])`, time.Unix(1710000000, 0))
	if err != nil {
		t.Fatalf("query failed: %v", err)
	}
	if v != 82.5 {
		t.Fatalf("want=82.5 got=%v", v)
	}
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

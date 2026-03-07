package dispatch

import (
	"context"

	"manager-go/internal/model"
)

type Sink interface {
	Name() string
	Write(ctx context.Context, key string, point model.MetricPoint) error
}

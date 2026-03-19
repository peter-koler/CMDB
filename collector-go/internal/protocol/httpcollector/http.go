package httpcollector

import "collector-go/internal/protocol"

type Collector struct{}

func init() {
	protocol.Register("http", &Collector{})
}

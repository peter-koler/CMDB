package ipmicollector

import "sync"

var (
	ipmiToolResolveOnce sync.Once
	ipmiToolResolved    string
	ipmiToolResolveErr  error
)

func resolveIPMIToolPathCached() (string, error) {
	ipmiToolResolveOnce.Do(func() {
		ipmiToolResolved, ipmiToolResolveErr = resolveIPMIToolPath()
	})
	return ipmiToolResolved, ipmiToolResolveErr
}

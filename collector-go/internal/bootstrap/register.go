package bootstrap

import (
	_ "collector-go/internal/protocol/httpcollector"
	_ "collector-go/internal/protocol/ipmicollector"
	_ "collector-go/internal/protocol/jdbccollector"
	_ "collector-go/internal/protocol/jmxcollector"
	_ "collector-go/internal/protocol/kclientcollector"
	_ "collector-go/internal/protocol/linuxcollector"
	_ "collector-go/internal/protocol/memcachedcollector"
	_ "collector-go/internal/protocol/pingcollector"
	_ "collector-go/internal/protocol/redfishcollector"
	_ "collector-go/internal/protocol/rediscollector"
	_ "collector-go/internal/protocol/rocketmqcollector"
	_ "collector-go/internal/protocol/servicecollector"
	_ "collector-go/internal/protocol/snmpcollector"
	_ "collector-go/internal/protocol/sshcollector"
	_ "collector-go/internal/protocol/telnetcollector"
)

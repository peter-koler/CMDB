package bootstrap

import (
	_ "collector-go/internal/protocol/httpcollector"
	_ "collector-go/internal/protocol/jdbccollector"
	_ "collector-go/internal/protocol/linuxcollector"
	_ "collector-go/internal/protocol/pingcollector"
	_ "collector-go/internal/protocol/snmpcollector"
)

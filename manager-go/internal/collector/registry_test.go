package collector

import (
	"testing"
	"time"
)

func TestRegistryUpsertSelectAndRebalance(t *testing.T) {
	r := NewRegistry()
	r.Upsert("c1", "10.0.0.1:6001")
	r.Upsert("c2", "10.0.0.2:6001")
	r.Upsert("c3", "10.0.0.3:6001")

	before := map[int64]string{}
	for i := int64(1000); i < 1100; i++ {
		n, err := r.SelectByMonitor(i)
		if err != nil {
			t.Fatalf("select before remove failed: %v", err)
		}
		before[i] = n.ID
	}

	if ok := r.Remove("c2"); !ok {
		t.Fatal("expected remove c2 true")
	}

	moved := 0
	for i := int64(1000); i < 1100; i++ {
		n, err := r.SelectByMonitor(i)
		if err != nil {
			t.Fatalf("select after remove failed: %v", err)
		}
		if before[i] != n.ID {
			moved++
		}
	}
	if moved == 0 {
		t.Fatal("expected at least some monitors rebalanced after node removal")
	}
}

func TestRegistryReapExpired(t *testing.T) {
	r := NewRegistry()
	n1 := r.Upsert("c1", "10.0.0.1:6001")
	r.Upsert("c2", "10.0.0.2:6001")
	now := n1.LastSeen.Add(31 * time.Second)
	expired := r.ReapExpired(30*time.Second, now)
	if len(expired) != 2 {
		t.Fatalf("expected 2 expired collectors, got %d", len(expired))
	}
	if len(r.List()) != 0 {
		t.Fatal("expected empty registry after reap")
	}
}

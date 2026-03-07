package store

import (
	"sync"
	"testing"

	"manager-go/internal/model"
)

func TestConcurrentUpdateOptimisticLock(t *testing.T) {
	st := NewMonitorStore()
	created, err := st.Create(model.MonitorCreateInput{
		Name:            "demo",
		App:             "linux",
		Target:          "127.0.0.1",
		TemplateID:      1,
		IntervalSeconds: 10,
		Enabled:         true,
	})
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}

	var wg sync.WaitGroup
	var okCount, conflictCount int
	var mu sync.Mutex
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			_, e := st.Update(created.ID, model.MonitorUpdateInput{
				Name:            "demo-updated",
				App:             "linux",
				Target:          "127.0.0.1",
				TemplateID:      1,
				IntervalSeconds: 10,
				Enabled:         true,
				Version:         created.Version,
			})
			mu.Lock()
			defer mu.Unlock()
			if e == nil {
				okCount++
				return
			}
			if e == ErrVersionConflict {
				conflictCount++
				return
			}
			t.Errorf("unexpected error: %v", e)
		}(i)
	}
	wg.Wait()
	if okCount != 1 || conflictCount != 1 {
		t.Fatalf("expected 1 success and 1 conflict, got success=%d conflict=%d", okCount, conflictCount)
	}
}

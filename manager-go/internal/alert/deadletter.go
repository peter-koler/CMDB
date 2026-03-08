package alert

import (
	"sort"
	"sync"
	"time"
)

type DeadLetterStatus string

const (
	DeadLetterPending DeadLetterStatus = "pending"
	DeadLetterRetried DeadLetterStatus = "retried"
)

type DeadLetter struct {
	ID        int64            `json:"id"`
	Task      NotifyTask       `json:"task"`
	Reason    string           `json:"reason"`
	Status    DeadLetterStatus `json:"status"`
	CreatedAt time.Time        `json:"created_at"`
	RetriedAt *time.Time       `json:"retried_at,omitempty"`
}

type DeadLetterStore struct {
	mu     sync.Mutex
	nextID int64
	items  map[int64]DeadLetter
	order  []int64
}

func NewDeadLetterStore() *DeadLetterStore {
	return &DeadLetterStore{
		items: make(map[int64]DeadLetter),
	}
}

func (s *DeadLetterStore) Save(task NotifyTask, reason string) DeadLetter {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	entry := DeadLetter{
		ID:        s.nextID,
		Task:      task,
		Reason:    reason,
		Status:    DeadLetterPending,
		CreatedAt: time.Now(),
	}
	s.items[entry.ID] = entry
	s.order = append(s.order, entry.ID)
	return entry
}

func (s *DeadLetterStore) List(status string, page, pageSize int) ([]DeadLetter, int) {
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	filtered := make([]DeadLetter, 0, len(s.order))
	for i := len(s.order) - 1; i >= 0; i-- {
		id := s.order[i]
		item, ok := s.items[id]
		if !ok {
			continue
		}
		if status != "" && string(item.Status) != status {
			continue
		}
		filtered = append(filtered, item)
	}
	total := len(filtered)
	start := (page - 1) * pageSize
	if start >= total {
		return []DeadLetter{}, total
	}
	end := start + pageSize
	if end > total {
		end = total
	}
	return filtered[start:end], total
}

func (s *DeadLetterStore) Retry(id int64) (NotifyTask, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.items[id]
	if !ok || item.Status != DeadLetterPending {
		return NotifyTask{}, false
	}
	now := time.Now()
	task := item.Task
	task.Attempt = 0
	item.Status = DeadLetterRetried
	item.RetriedAt = &now
	s.items[id] = item
	return task, true
}

func (s *DeadLetterStore) IDs() []int64 {
	s.mu.Lock()
	defer s.mu.Unlock()
	ids := make([]int64, 0, len(s.items))
	for id := range s.items {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool { return ids[i] < ids[j] })
	return ids
}

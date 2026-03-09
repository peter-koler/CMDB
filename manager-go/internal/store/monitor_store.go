package store

import (
	"errors"
	"fmt"
	"sort"
	"sync"
	"time"

	"manager-go/internal/model"
)

var (
	ErrNotFound        = errors.New("monitor not found")
	ErrVersionConflict = errors.New("monitor version conflict")
	ErrInvalidInput    = errors.New("invalid monitor input")
)

type MonitorStore struct {
	mu      sync.RWMutex
	nextID  int64
	records map[int64]model.Monitor
}

func NewMonitorStore() *MonitorStore {
	return &MonitorStore{
		nextID:  1,
		records: map[int64]model.Monitor{},
	}
}

func (s *MonitorStore) Create(in model.MonitorCreateInput) (model.Monitor, error) {
	if err := validateCreate(in); err != nil {
		return model.Monitor{}, err
	}
	interval := normalizedInterval(in.IntervalSeconds, in.Interval)
	now := time.Now()
	s.mu.Lock()
	defer s.mu.Unlock()
	id := s.nextID
	s.nextID++
	m := model.Monitor{
		ID:              id,
		JobID:           buildJobID(id, now),
		CIID:            in.CIID,
		CIModelID:       in.CIModelID,
		CIName:          in.CIName,
		CICode:          in.CICode,
		Name:            in.Name,
		App:             in.App,
		Target:          in.Target,
		TemplateID:      in.TemplateID,
		IntervalSeconds: interval,
		Enabled:         in.Enabled,
		Status:          model.StatusUnknown,
		Labels:          cloneStringMap(in.Labels),
		Params:          cloneStringMap(in.Params),
		Version:         1,
		CreatedAt:       now,
		UpdatedAt:       now,
	}
	s.records[id] = m
	return m, nil
}

func (s *MonitorStore) Get(id int64) (model.Monitor, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	m, ok := s.records[id]
	if !ok {
		return model.Monitor{}, ErrNotFound
	}
	return m, nil
}

func (s *MonitorStore) List() []model.Monitor {
	s.mu.RLock()
	defer s.mu.RUnlock()
	items := make([]model.Monitor, 0, len(s.records))
	for _, m := range s.records {
		items = append(items, m)
	}
	sort.Slice(items, func(i, j int) bool { return items[i].ID < items[j].ID })
	return items
}

func (s *MonitorStore) Update(id int64, in model.MonitorUpdateInput) (model.Monitor, error) {
	if err := validateUpdate(in); err != nil {
		return model.Monitor{}, err
	}
	interval := normalizedInterval(in.IntervalSeconds, in.Interval)
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.records[id]
	if !ok {
		return model.Monitor{}, ErrNotFound
	}
	if cur.Version != in.Version {
		return model.Monitor{}, ErrVersionConflict
	}
	cur.CIID = in.CIID
	cur.CIModelID = in.CIModelID
	cur.CIName = in.CIName
	cur.CICode = in.CICode
	cur.Name = in.Name
	cur.App = in.App
	cur.Target = in.Target
	cur.TemplateID = in.TemplateID
	cur.IntervalSeconds = interval
	cur.Enabled = in.Enabled
	cur.Labels = cloneStringMap(in.Labels)
	cur.Params = cloneStringMap(in.Params)
	cur.Version++
	cur.UpdatedAt = time.Now()
	s.records[id] = cur
	return cur, nil
}

func (s *MonitorStore) SetEnabled(id int64, enabled bool, version int64) (model.Monitor, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.records[id]
	if !ok {
		return model.Monitor{}, ErrNotFound
	}
	if cur.Version != version {
		return model.Monitor{}, ErrVersionConflict
	}
	cur.Enabled = enabled
	cur.Version++
	cur.UpdatedAt = time.Now()
	s.records[id] = cur
	return cur, nil
}

func (s *MonitorStore) Delete(id int64, version int64) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	cur, ok := s.records[id]
	if !ok {
		return ErrNotFound
	}
	if cur.Version != version {
		return ErrVersionConflict
	}
	delete(s.records, id)
	return nil
}

func validateCreate(in model.MonitorCreateInput) error {
	interval := normalizedInterval(in.IntervalSeconds, in.Interval)
	if in.Name == "" || in.App == "" || in.Target == "" || in.TemplateID <= 0 || interval < 10 {
		return ErrInvalidInput
	}
	return nil
}

func validateUpdate(in model.MonitorUpdateInput) error {
	if in.Version <= 0 {
		return ErrInvalidInput
	}
	return validateCreate(model.MonitorCreateInput{
		Name:            in.Name,
		App:             in.App,
		Target:          in.Target,
		TemplateID:      in.TemplateID,
		IntervalSeconds: in.IntervalSeconds,
		Interval:        in.Interval,
		Enabled:         in.Enabled,
	})
}

func normalizedInterval(primary int, fallback int) int {
	if primary > 0 {
		return primary
	}
	return fallback
}

func cloneStringMap(src map[string]string) map[string]string {
	if len(src) == 0 {
		return nil
	}
	out := make(map[string]string, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

func buildJobID(id int64, now time.Time) string {
	return fmt.Sprintf("job-%d-%d", id, now.UnixMilli())
}

package alert

import (
	"errors"
	"sort"
	"sync"
	"time"
)

var ErrAlertNotFound = errors.New("alert not found")

type AlertStatus string

const (
	AlertPending    AlertStatus = "pending"
	AlertProcessing AlertStatus = "processing"
	AlertClosed     AlertStatus = "closed"
)

type AlertRecord struct {
	ID             int64       `json:"id"`
	RuleID         int64       `json:"rule_id"`
	MonitorID      int64       `json:"monitor_id"`
	Severity       string      `json:"severity"`
	Status         AlertStatus `json:"status"`
	AlertName      string      `json:"alert_name"`
	Expression     string      `json:"expression"`
	ElapsedMs      int64       `json:"elapsed_ms"`
	TriggeredAt    time.Time   `json:"triggered_at"`
	AcknowledgedAt *time.Time  `json:"acknowledged_at,omitempty"`
	ClaimedBy      string      `json:"claimed_by,omitempty"`
	ClosedAt       *time.Time  `json:"closed_at,omitempty"`
}

type AlertStore struct {
	mu     sync.Mutex
	nextID int64
	items  map[int64]AlertRecord
	order  []int64
}

func NewAlertStore() *AlertStore {
	return &AlertStore{
		items: make(map[int64]AlertRecord),
	}
}

func (s *AlertStore) Fire(ev Event) AlertRecord {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	rec := AlertRecord{
		ID:          s.nextID,
		RuleID:      ev.RuleID,
		MonitorID:   ev.MonitorID,
		Severity:    ev.Severity,
		Status:      AlertPending,
		AlertName:   ev.RuleName,
		Expression:  ev.Expression,
		ElapsedMs:   ev.ElapsedMs,
		TriggeredAt: ev.TriggeredAt,
	}
	s.items[rec.ID] = rec
	s.order = append(s.order, rec.ID)
	return rec
}

func (s *AlertStore) List(scope, status string, page, pageSize int) ([]AlertRecord, int) {
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	matches := make([]AlertRecord, 0, len(s.order))
	for i := len(s.order) - 1; i >= 0; i-- {
		id := s.order[i]
		rec, ok := s.items[id]
		if !ok {
			continue
		}
		if status != "" && string(rec.Status) != status {
			continue
		}
		switch scope {
		case "current":
			if rec.Status == AlertClosed {
				continue
			}
		case "history":
			if rec.Status != AlertClosed {
				continue
			}
		}
		matches = append(matches, rec)
	}
	total := len(matches)
	start := (page - 1) * pageSize
	if start >= total {
		return []AlertRecord{}, total
	}
	end := start + pageSize
	if end > total {
		end = total
	}
	return matches[start:end], total
}

func (s *AlertStore) Acknowledge(id int64) (AlertRecord, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rec, ok := s.items[id]
	if !ok {
		return AlertRecord{}, ErrAlertNotFound
	}
	now := time.Now()
	rec.Status = AlertProcessing
	rec.AcknowledgedAt = &now
	s.items[id] = rec
	return rec, nil
}

func (s *AlertStore) Claim(id int64, assignee string) (AlertRecord, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rec, ok := s.items[id]
	if !ok {
		return AlertRecord{}, ErrAlertNotFound
	}
	now := time.Now()
	rec.Status = AlertProcessing
	rec.AcknowledgedAt = &now
	rec.ClaimedBy = assignee
	s.items[id] = rec
	return rec, nil
}

func (s *AlertStore) Close(id int64) (AlertRecord, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rec, ok := s.items[id]
	if !ok {
		return AlertRecord{}, ErrAlertNotFound
	}
	now := time.Now()
	rec.Status = AlertClosed
	rec.ClosedAt = &now
	s.items[id] = rec
	return rec, nil
}

func (s *AlertStore) IDs() []int64 {
	s.mu.Lock()
	defer s.mu.Unlock()
	ids := make([]int64, 0, len(s.items))
	for id := range s.items {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool { return ids[i] < ids[j] })
	return ids
}

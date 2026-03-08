package httpapi

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"sync"
	"time"
)

type resourceRepo interface {
	create(payload map[string]any) (map[string]any, error)
	list(page, pageSize int) ([]map[string]any, int, error)
	get(id string) (map[string]any, bool, error)
	update(id string, payload map[string]any) (map[string]any, bool, error)
	delete(id string) (bool, error)
	setEnabled(id string, enabled bool) (map[string]any, bool, error)
}

type resourceStore struct {
	mu     sync.Mutex
	nextID int64
	items  map[string]map[string]any
	order  []string
	saver  func(*resourceStore) error
}

func newResourceStore() *resourceStore {
	return &resourceStore{items: make(map[string]map[string]any)}
}

func (s *resourceStore) create(payload map[string]any) (map[string]any, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	id := strconv.FormatInt(s.nextID, 10)
	now := time.Now().UTC().Format(time.RFC3339)
	item := cloneMap(payload)
	item["id"] = s.nextID
	if _, ok := item["enabled"]; !ok {
		item["enabled"] = true
	}
	item["created_at"] = now
	item["updated_at"] = now
	if _, ok := item["version"]; !ok {
		item["version"] = int64(1)
	}
	s.items[id] = item
	s.order = append(s.order, id)
	_ = s.persistLocked()
	return cloneMap(item), nil
}

func (s *resourceStore) list(page, pageSize int) ([]map[string]any, int, error) {
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = 20
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	items := make([]map[string]any, 0, len(s.order))
	for i := len(s.order) - 1; i >= 0; i-- {
		id := s.order[i]
		item, ok := s.items[id]
		if !ok {
			continue
		}
		items = append(items, cloneMap(item))
	}
	total := len(items)
	start := (page - 1) * pageSize
	if start >= total {
		return []map[string]any{}, total, nil
	}
	end := start + pageSize
	if end > total {
		end = total
	}
	return items[start:end], total, nil
}

func (s *resourceStore) get(id string) (map[string]any, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.items[id]
	if !ok {
		return nil, false, nil
	}
	return cloneMap(item), true, nil
}

func (s *resourceStore) update(id string, payload map[string]any) (map[string]any, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.items[id]
	if !ok {
		return nil, false, nil
	}
	for k, v := range payload {
		if k == "id" || k == "created_at" {
			continue
		}
		item[k] = v
	}
	item["updated_at"] = time.Now().UTC().Format(time.RFC3339)
	if v, ok := item["version"].(int64); ok {
		item["version"] = v + 1
	} else {
		item["version"] = int64(1)
	}
	s.items[id] = item
	_ = s.persistLocked()
	return cloneMap(item), true, nil
}

func (s *resourceStore) delete(id string) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.items[id]; !ok {
		return false, nil
	}
	delete(s.items, id)
	_ = s.persistLocked()
	return true, nil
}

func (s *resourceStore) setEnabled(id string, enabled bool) (map[string]any, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	item, ok := s.items[id]
	if !ok {
		return nil, false, nil
	}
	item["enabled"] = enabled
	item["updated_at"] = time.Now().UTC().Format(time.RFC3339)
	if v, ok := item["version"].(int64); ok {
		item["version"] = v + 1
	} else {
		item["version"] = int64(1)
	}
	s.items[id] = item
	_ = s.persistLocked()
	return cloneMap(item), true, nil
}

func (s *resourceStore) persistLocked() error {
	if s.saver == nil {
		return nil
	}
	return s.saver(s)
}

func cloneMap(in map[string]any) map[string]any {
	out := make(map[string]any, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}

type resourceHub struct {
	stores map[string]resourceRepo
}

func newResourceHub() *resourceHub {
	return newResourceHubWithFactory(nil)
}

func newResourceHubWithFactory(factory func(name string) resourceRepo) *resourceHub {
	names := []string{
		"alert-rules",
		"alert-integrations",
		"alert-groups",
		"alert-inhibits",
		"alert-silences",
		"alert-notices",
		"labels",
		"status-pages",
	}
	stores := make(map[string]resourceRepo, len(names))
	for _, name := range names {
		if factory != nil {
			stores[name] = factory(name)
		} else {
			stores[name] = newResourceStore()
		}
	}
	return &resourceHub{stores: stores}
}

func (h *resourceHub) get(name string) resourceRepo {
	return h.stores[name]
}

func (h *resourceHub) names() []string {
	out := make([]string, 0, len(h.stores))
	for k := range h.stores {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

type persistedStoreState struct {
	NextID int64                     `json:"next_id"`
	Items  map[string]map[string]any `json:"items"`
	Order  []string                  `json:"order"`
}

func NewPersistentResourceHub(dataDir string) (*resourceHub, error) {
	if dataDir == "" {
		dataDir = "data/resources"
	}
	if err := os.MkdirAll(dataDir, 0o755); err != nil {
		return nil, err
	}
	hub := newResourceHubWithFactory(func(name string) resourceRepo {
		st := newResourceStore()
		path := filepath.Join(dataDir, name+".json")
		st.saver = func(s *resourceStore) error {
			return saveStore(path, s)
		}
		_ = loadStore(path, st)
		return st
	})
	return hub, nil
}

func saveStore(path string, st *resourceStore) error {
	state := persistedStoreState{NextID: st.nextID, Items: st.items, Order: st.order}
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func loadStore(path string, st *resourceStore) error {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	var state persistedStoreState
	if err := json.Unmarshal(data, &state); err != nil {
		return err
	}
	if state.Items == nil {
		state.Items = map[string]map[string]any{}
	}
	st.nextID = state.NextID
	st.items = state.Items
	st.order = state.Order
	return nil
}

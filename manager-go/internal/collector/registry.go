package collector

import (
	"errors"
	"sort"
	"strconv"
	"sync"
	"time"
)

var ErrNoCollector = errors.New("no collector available")

type Node struct {
	ID        string    `json:"id"`
	Addr      string    `json:"addr"`
	LastSeen  time.Time `json:"last_seen"`
	CreatedAt time.Time `json:"created_at"`
}

type Registry struct {
	mu    sync.RWMutex
	nodes map[string]Node
}

func NewRegistry() *Registry {
	return &Registry{nodes: map[string]Node{}}
}

func (r *Registry) Upsert(id, addr string) Node {
	now := time.Now()
	r.mu.Lock()
	defer r.mu.Unlock()
	cur, ok := r.nodes[id]
	if !ok {
		cur = Node{
			ID:        id,
			Addr:      addr,
			CreatedAt: now,
		}
	}
	cur.Addr = addr
	cur.LastSeen = now
	r.nodes[id] = cur
	return cur
}

func (r *Registry) Touch(id string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	cur, ok := r.nodes[id]
	if !ok {
		return false
	}
	cur.LastSeen = time.Now()
	r.nodes[id] = cur
	return true
}

func (r *Registry) Remove(id string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.nodes[id]; !ok {
		return false
	}
	delete(r.nodes, id)
	return true
}

func (r *Registry) ReapExpired(timeout time.Duration, now time.Time) []string {
	if timeout <= 0 {
		return nil
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	expired := make([]string, 0)
	for id, node := range r.nodes {
		if now.Sub(node.LastSeen) > timeout {
			expired = append(expired, id)
			delete(r.nodes, id)
		}
	}
	sort.Strings(expired)
	return expired
}

func (r *Registry) List() []Node {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]Node, 0, len(r.nodes))
	for _, n := range r.nodes {
		out = append(out, n)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// SelectByMonitor chooses collector using rendezvous hashing.
func (r *Registry) SelectByMonitor(monitorID int64) (Node, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	if len(r.nodes) == 0 {
		return Node{}, ErrNoCollector
	}
	key := strconv.FormatInt(monitorID, 10)
	var selected Node
	var best uint64
	first := true
	for _, node := range r.nodes {
		score := hashScore(key, node.ID)
		if first || score > best {
			selected = node
			best = score
			first = false
		}
	}
	return selected, nil
}



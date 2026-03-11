package template

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"
)

type RuntimeTemplate struct {
	ID       int64  `json:"id"`
	App      string `json:"app"`
	Name     string `json:"name"`
	Category string `json:"category"`
	Version  int64  `json:"version"`
	Hash     string `json:"hash"`
	LoadedAt string `json:"loaded_at"`

	// Raw YAML content. Keep in memory for compilation in later phases.
	Content string `json:"-"`

	// Diagnostics for partial compatibility / load warnings.
	Warnings []string `json:"warnings,omitempty"`
}

type Registry struct {
	mu             sync.RWMutex
	templatesByApp map[string]RuntimeTemplate // app -> latest template
	templatesByID  map[int64]RuntimeTemplate  // template_id -> template
	loadedAt       time.Time
}

func NewRegistry() *Registry {
	return &Registry{
		templatesByApp: map[string]RuntimeTemplate{},
		templatesByID:  map[int64]RuntimeTemplate{},
	}
}

func (r *Registry) LoadedAt() time.Time {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.loadedAt
}

func (r *Registry) Get(app string) (RuntimeTemplate, bool) {
	key := strings.TrimSpace(strings.ToLower(app))
	r.mu.RLock()
	defer r.mu.RUnlock()
	tpl, ok := r.templatesByApp[key]
	return tpl, ok
}

func (r *Registry) GetByID(id int64) (RuntimeTemplate, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	tpl, ok := r.templatesByID[id]
	return tpl, ok
}

func (r *Registry) List() []RuntimeTemplate {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]RuntimeTemplate, 0, len(r.templatesByID))
	for _, tpl := range r.templatesByID {
		// Avoid returning the full YAML content in runtime listing.
		tpl.Content = ""
		out = append(out, tpl)
	}
	// Deterministic order for UI/debugging.
	sortRuntimeTemplates(out)
	return out
}

func (r *Registry) ReloadFromStore(st *Store) error {
	if st == nil {
		return fmt.Errorf("template store is nil")
	}
	rows, err := st.ListVisibleTemplates()
	if err != nil {
		return err
	}
	now := time.Now()
	nextByApp := make(map[string]RuntimeTemplate, len(rows))
	nextByID := make(map[int64]RuntimeTemplate, len(rows))
	for _, row := range rows {
		app := strings.TrimSpace(strings.ToLower(row.App))
		if app == "" {
			continue
		}
		warnings := make([]string, 0, 2)
		if contentApp := extractYAMLScalar(row.Content, "app"); contentApp != "" && strings.ToLower(contentApp) != app {
			warnings = append(warnings, fmt.Sprintf("content app mismatch: yaml=%s db=%s", contentApp, app))
		}
		sum := sha256.Sum256([]byte(row.Content))
		rt := RuntimeTemplate{
			ID:       row.ID,
			App:      row.App,
			Name:     row.Name,
			Category: row.Category,
			Version:  row.Version,
			Hash:     hex.EncodeToString(sum[:]),
			LoadedAt: now.Format(time.RFC3339),
			Content:  row.Content,
			Warnings: warnings,
		}
		nextByID[row.ID] = rt
		if cur, exists := nextByApp[app]; !exists || rt.Version > cur.Version || (rt.Version == cur.Version && rt.ID > cur.ID) {
			nextByApp[app] = rt
		}
	}

	r.mu.Lock()
	r.templatesByApp = nextByApp
	r.templatesByID = nextByID
	r.loadedAt = now
	r.mu.Unlock()
	return nil
}

var yamlScalarLine = regexp.MustCompile(`(?m)^\s*([a-zA-Z0-9_-]+)\s*:\s*([^\n#]+)\s*$`)

func extractYAMLScalar(content string, key string) string {
	key = strings.TrimSpace(key)
	if key == "" {
		return ""
	}
	matches := yamlScalarLine.FindAllStringSubmatch(content, -1)
	for _, m := range matches {
		if len(m) != 3 {
			continue
		}
		if strings.TrimSpace(m[1]) != key {
			continue
		}
		return strings.Trim(strings.TrimSpace(m[2]), `"'`)
	}
	return ""
}

func sortRuntimeTemplates(items []RuntimeTemplate) {
	// Small n, simple O(n^2) sort keeps dependencies minimal.
	for i := 0; i < len(items); i++ {
		for j := i + 1; j < len(items); j++ {
			aj := strings.ToLower(items[j].App)
			ai := strings.ToLower(items[i].App)
			if aj < ai || (aj == ai && (items[j].Version > items[i].Version || (items[j].Version == items[i].Version && items[j].ID > items[i].ID))) {
				items[i], items[j] = items[j], items[i]
			}
		}
	}
}

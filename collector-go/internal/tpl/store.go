package tpl

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

type Template struct {
	App      string
	FilePath string
	Content  string
}

type Store struct {
	items map[string]Template
}

func LoadFromDir(root string) (*Store, error) {
	items := make(map[string]Template)
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		ext := strings.ToLower(filepath.Ext(path))
		if ext != ".yml" && ext != ".yaml" {
			return nil
		}
		base := strings.ToLower(filepath.Base(path))
		if !strings.HasPrefix(base, "app-") {
			return nil
		}
		app := strings.TrimSuffix(strings.TrimPrefix(base, "app-"), ext)
		b, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		items[app] = Template{App: app, FilePath: filepath.Clean(path), Content: string(b)}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return &Store{items: items}, nil
}

func (s *Store) Get(app string) (Template, bool) {
	t, ok := s.items[app]
	return t, ok
}

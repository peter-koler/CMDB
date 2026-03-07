package queue

import (
	"bufio"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"

	"collector-go/internal/model"
)

type DiskQueue struct {
	path string

	mu    sync.Mutex
	items []model.Result
}

func NewDiskQueue(path string) (*DiskQueue, error) {
	if path == "" {
		path = "data/result-queue.jsonl"
	}
	q := &DiskQueue{path: path, items: make([]model.Result, 0)}
	if err := q.ensureDir(); err != nil {
		return nil, err
	}
	if err := q.load(); err != nil {
		return nil, err
	}
	return q, nil
}

func (q *DiskQueue) ensureDir() error {
	dir := filepath.Dir(q.path)
	return os.MkdirAll(dir, 0o755)
}

func (q *DiskQueue) load() error {
	f, err := os.Open(q.path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		var item model.Result
		if err := json.Unmarshal(sc.Bytes(), &item); err == nil {
			q.items = append(q.items, item)
		}
	}
	return sc.Err()
}

func (q *DiskQueue) Push(ctx context.Context, result model.Result) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	q.items = append(q.items, result)
	return q.flushLocked()
}

func (q *DiskQueue) Pop(ctx context.Context) (model.Result, error) {
	for {
		select {
		case <-ctx.Done():
			return model.Result{}, ctx.Err()
		default:
		}
		q.mu.Lock()
		if len(q.items) > 0 {
			item := q.items[0]
			q.items = q.items[1:]
			err := q.flushLocked()
			q.mu.Unlock()
			if err != nil {
				return model.Result{}, err
			}
			return item, nil
		}
		q.mu.Unlock()
		time.Sleep(20 * time.Millisecond)
	}
}

func (q *DiskQueue) Len() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}

func (q *DiskQueue) flushLocked() error {
	tmp := q.path + ".tmp"
	f, err := os.Create(tmp)
	if err != nil {
		return err
	}
	w := bufio.NewWriter(f)
	for _, item := range q.items {
		b, err := json.Marshal(item)
		if err != nil {
			_ = f.Close()
			return err
		}
		if _, err := w.Write(append(b, '\n')); err != nil {
			_ = f.Close()
			return err
		}
	}
	if err := w.Flush(); err != nil {
		_ = f.Close()
		return err
	}
	if err := f.Close(); err != nil {
		return err
	}
	return os.Rename(tmp, q.path)
}

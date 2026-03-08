package store

import (
	"database/sql"
	"errors"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

var (
	ErrCollectorNotFound = errors.New("collector not found")
)

// Collector 采集器实体
type Collector struct {
	ID        int64     `json:"id"`
	Name      string    `json:"name"`
	IP        string    `json:"ip"`
	Version   string    `json:"version"`
	Status    int8      `json:"status"` // 0-online, 1-offline
	Mode      string    `json:"mode"`   // public/private
	Creator   string    `json:"creator"`
	Modifier  string    `json:"modifier"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// CollectorStore 采集器存储
type CollectorStore struct {
	db *sql.DB
}

// NewCollectorStore 创建采集器存储
func NewCollectorStore(db *sql.DB) *CollectorStore {
	return &CollectorStore{db: db}
}

// NewCollectorStoreWithPath 从文件路径创建采集器存储
func NewCollectorStoreWithPath(dbPath string) (*CollectorStore, error) {
	// 确保目录存在
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create directory failed: %w", err)
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite db failed: %w", err)
	}

	// 设置连接池
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)

	return &CollectorStore{db: db}, nil
}

// InitTable 初始化表结构
func (s *CollectorStore) InitTable() error {
	sql := `
CREATE TABLE IF NOT EXISTS collectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ip TEXT NOT NULL,
    version TEXT,
    status INTEGER NOT NULL DEFAULT 1,
    mode TEXT NOT NULL DEFAULT 'public',
    creator TEXT,
    modifier TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collectors_name ON collectors(name);
CREATE INDEX IF NOT EXISTS idx_collectors_status ON collectors(status);

CREATE TABLE IF NOT EXISTS collector_monitor_binds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collector TEXT NOT NULL,
    monitor_id INTEGER NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0,
    creator TEXT,
    modifier TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collector, monitor_id)
);

CREATE INDEX IF NOT EXISTS idx_binds_collector ON collector_monitor_binds(collector);
CREATE INDEX IF NOT EXISTS idx_binds_monitor ON collector_monitor_binds(monitor_id);
`
	if _, err := s.db.Exec(sql); err != nil {
		return err
	}

	// 尝试添加可能缺失的列（兼容旧表）
	_ = s.addColumnIfNotExists("collector_monitor_binds", "creator", "TEXT")
	_ = s.addColumnIfNotExists("collector_monitor_binds", "modifier", "TEXT")

	return nil
}

// addColumnIfNotExists 如果列不存在则添加
func (s *CollectorStore) addColumnIfNotExists(table, column, colType string) error {
	// SQLite 不支持 IF NOT EXISTS 添加列，需要检查
	var count int
	err := s.db.QueryRow(
		"SELECT COUNT(*) FROM pragma_table_info(?) WHERE name = ?",
		table, column,
	).Scan(&count)
	if err != nil {
		return err
	}
	if count == 0 {
		_, err = s.db.Exec(fmt.Sprintf("ALTER TABLE %s ADD COLUMN %s %s", table, column, colType))
		if err != nil {
			return err
		}
		log.Printf("[CollectorStore] Added column %s to table %s", column, table)
	}
	return nil
}

// CreateOrUpdate 创建或更新采集器
func (s *CollectorStore) CreateOrUpdate(name, ip, version, mode string) (*Collector, error) {
	// 先尝试更新
	result, err := s.db.Exec(`
UPDATE collectors 
SET ip = ?, version = ?, status = 0, mode = ?, updated_at = ?
WHERE name = ?
`, ip, version, mode, time.Now(), name)
	if err != nil {
		return nil, fmt.Errorf("update collector failed: %w", err)
	}

	affected, _ := result.RowsAffected()
	if affected > 0 {
		// 更新成功，返回更新后的记录
		return s.GetByName(name)
	}

	// 不存在，创建新记录
	result, err = s.db.Exec(`
INSERT INTO collectors (name, ip, version, status, mode, created_at, updated_at)
VALUES (?, ?, ?, 0, ?, ?, ?)
`, name, ip, version, mode, time.Now(), time.Now())
	if err != nil {
		return nil, fmt.Errorf("create collector failed: %w", err)
	}

	id, _ := result.LastInsertId()
	return s.GetByID(id)
}

// GetByID 根据ID获取采集器
func (s *CollectorStore) GetByID(id int64) (*Collector, error) {
	var c Collector
	var createdAt, updatedAt string
	var creator, modifier sql.NullString

	err := s.db.QueryRow(`
SELECT id, name, ip, version, status, mode, creator, modifier, created_at, updated_at
FROM collectors WHERE id = ?
`, id).Scan(&c.ID, &c.Name, &c.IP, &c.Version, &c.Status, &c.Mode,
		&creator, &modifier, &createdAt, &updatedAt)

	if err == sql.ErrNoRows {
		return nil, ErrCollectorNotFound
	}
	if err != nil {
		return nil, err
	}

	c.Creator = creator.String
	c.Modifier = modifier.String
	c.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	c.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return &c, nil
}

// GetByName 根据名称获取采集器
func (s *CollectorStore) GetByName(name string) (*Collector, error) {
	var c Collector
	var createdAt, updatedAt string
	var creator, modifier sql.NullString

	err := s.db.QueryRow(`
SELECT id, name, ip, version, status, mode, creator, modifier, created_at, updated_at
FROM collectors WHERE name = ?
`, name).Scan(&c.ID, &c.Name, &c.IP, &c.Version, &c.Status, &c.Mode,
		&creator, &modifier, &createdAt, &updatedAt)

	if err == sql.ErrNoRows {
		return nil, ErrCollectorNotFound
	}
	if err != nil {
		return nil, err
	}

	c.Creator = creator.String
	c.Modifier = modifier.String
	c.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	c.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return &c, nil
}

// UpdateStatus 更新采集器状态
func (s *CollectorStore) UpdateStatus(name string, status int8) error {
	_, err := s.db.Exec(`
UPDATE collectors SET status = ?, updated_at = ? WHERE name = ?
`, status, time.Now(), name)
	return err
}

// SetOffline 设置采集器离线
func (s *CollectorStore) SetOffline(name string) error {
	return s.UpdateStatus(name, 1)
}

// SetOnline 设置采集器在线
func (s *CollectorStore) SetOnline(name string) error {
	return s.UpdateStatus(name, 0)
}

// List 获取采集器列表
func (s *CollectorStore) List() ([]*Collector, error) {
	rows, err := s.db.Query(`
SELECT id, name, ip, version, status, mode, creator, modifier, created_at, updated_at
FROM collectors ORDER BY id DESC
`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var collectors []*Collector
	for rows.Next() {
		c := &Collector{}
		var createdAt, updatedAt string
		var creator, modifier sql.NullString
		err := rows.Scan(&c.ID, &c.Name, &c.IP, &c.Version, &c.Status, &c.Mode,
			&creator, &modifier, &createdAt, &updatedAt)
		if err != nil {
			continue
		}
		c.Creator = creator.String
		c.Modifier = modifier.String
		c.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
		c.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
		collectors = append(collectors, c)
	}

	return collectors, nil
}

// ListByStatus 根据状态获取采集器列表
func (s *CollectorStore) ListByStatus(status int8) ([]*Collector, error) {
	rows, err := s.db.Query(`
SELECT id, name, ip, version, status, mode, creator, modifier, created_at, updated_at
FROM collectors WHERE status = ? ORDER BY id DESC
`, status)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var collectors []*Collector
	for rows.Next() {
		c := &Collector{}
		var createdAt, updatedAt string
		var creator, modifier sql.NullString
		err := rows.Scan(&c.ID, &c.Name, &c.IP, &c.Version, &c.Status, &c.Mode,
			&creator, &modifier, &createdAt, &updatedAt)
		if err != nil {
			continue
		}
		c.Creator = creator.String
		c.Modifier = modifier.String
		c.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
		c.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
		collectors = append(collectors, c)
	}

	return collectors, nil
}

// Delete 删除采集器
func (s *CollectorStore) Delete(name string) error {
	_, err := s.db.Exec(`DELETE FROM collectors WHERE name = ?`, name)
	return err
}

// Count 统计采集器数量
func (s *CollectorStore) Count() (int, error) {
	var count int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM collectors`).Scan(&count)
	return count, err
}

// CountByStatus 按状态统计采集器数量
func (s *CollectorStore) CountByStatus(status int8) (int, error) {
	var count int
	err := s.db.QueryRow(`SELECT COUNT(*) FROM collectors WHERE status = ?`, status).Scan(&count)
	return count, err
}

// GetStats 获取统计信息
func (s *CollectorStore) GetStats() (map[string]interface{}, error) {
	total, err := s.Count()
	if err != nil {
		return nil, err
	}

	online, err := s.CountByStatus(0)
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"total":      total,
		"online":     online,
		"offline":    total - online,
		"onlineRate": float64(online) / float64(total) * 100,
	}, nil
}

// ==================== Collector-Monitor 绑定管理 ====================

// CollectorMonitorBind Collector-Monitor 绑定关系
// @Description 采集器与监控任务的绑定关系，支持用户固定指定或自动分配
type CollectorMonitorBind struct {
	ID         int64     `json:"id"`
	Collector  string    `json:"collector"`   // Collector 名称
	MonitorID  int64     `json:"monitor_id"`  // 监控任务 ID
	Pinned     int8      `json:"pinned"`      // 0-自动分配, 1-用户固定指定
	Creator    *string   `json:"creator"`
	Modifier   *string   `json:"modifier"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

// CreateBind 创建绑定关系
func (s *CollectorStore) CreateBind(collector string, monitorID int64, pinned int8) (*CollectorMonitorBind, error) {
	result, err := s.db.Exec(`
		INSERT INTO collector_monitor_binds (collector, monitor_id, pinned, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?)
	`, collector, monitorID, pinned, time.Now(), time.Now())
	if err != nil {
		return nil, fmt.Errorf("create bind failed: %w", err)
	}

	id, _ := result.LastInsertId()
	return s.GetBindByID(id)
}

// GetBindByID 根据 ID 获取绑定关系
func (s *CollectorStore) GetBindByID(id int64) (*CollectorMonitorBind, error) {
	var bind CollectorMonitorBind
	var createdAt, updatedAt string
	err := s.db.QueryRow(`
		SELECT id, collector, monitor_id, pinned, creator, modifier, created_at, updated_at
		FROM collector_monitor_binds WHERE id = ?
	`, id).Scan(&bind.ID, &bind.Collector, &bind.MonitorID, &bind.Pinned,
		&bind.Creator, &bind.Modifier, &createdAt, &updatedAt)
	if err != nil {
		return nil, err
	}
	bind.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	bind.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return &bind, nil
}

// GetBindByMonitor 根据监控任务 ID 获取绑定关系
func (s *CollectorStore) GetBindByMonitor(monitorID int64) (*CollectorMonitorBind, error) {
	var bind CollectorMonitorBind
	var createdAt, updatedAt string
	err := s.db.QueryRow(`
		SELECT id, collector, monitor_id, pinned, creator, modifier, created_at, updated_at
		FROM collector_monitor_binds WHERE monitor_id = ?
	`, monitorID).Scan(&bind.ID, &bind.Collector, &bind.MonitorID, &bind.Pinned,
		&bind.Creator, &bind.Modifier, &createdAt, &updatedAt)
	if err != nil {
		return nil, err
	}
	bind.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	bind.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return &bind, nil
}

// GetBindsByCollector 获取指定 Collector 的所有绑定
func (s *CollectorStore) GetBindsByCollector(collector string) ([]*CollectorMonitorBind, error) {
	rows, err := s.db.Query(`
		SELECT id, collector, monitor_id, pinned, creator, modifier, created_at, updated_at
		FROM collector_monitor_binds WHERE collector = ?
	`, collector)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var binds []*CollectorMonitorBind
	for rows.Next() {
		var bind CollectorMonitorBind
		var createdAt, updatedAt string
		err := rows.Scan(&bind.ID, &bind.Collector, &bind.MonitorID, &bind.Pinned,
			&bind.Creator, &bind.Modifier, &createdAt, &updatedAt)
		if err != nil {
			continue
		}
		bind.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
		bind.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
		binds = append(binds, &bind)
	}
	return binds, nil
}

// DeleteBind 删除绑定关系
func (s *CollectorStore) DeleteBind(id int64) error {
	_, err := s.db.Exec(`DELETE FROM collector_monitor_binds WHERE id = ?`, id)
	return err
}

// DeleteBindByMonitor 根据监控任务 ID 删除绑定
func (s *CollectorStore) DeleteBindByMonitor(monitorID int64) error {
	_, err := s.db.Exec(`DELETE FROM collector_monitor_binds WHERE monitor_id = ?`, monitorID)
	return err
}

// DeleteBindsByCollector 删除指定 Collector 的所有绑定
func (s *CollectorStore) DeleteBindsByCollector(collector string) error {
	_, err := s.db.Exec(`DELETE FROM collector_monitor_binds WHERE collector = ?`, collector)
	return err
}

// ListPinnedBinds 获取所有用户固定指定的绑定
func (s *CollectorStore) ListPinnedBinds() ([]*CollectorMonitorBind, error) {
	rows, err := s.db.Query(`
		SELECT id, collector, monitor_id, pinned, creator, modifier, created_at, updated_at
		FROM collector_monitor_binds WHERE pinned = 1
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var binds []*CollectorMonitorBind
	for rows.Next() {
		var bind CollectorMonitorBind
		var createdAt, updatedAt string
		err := rows.Scan(&bind.ID, &bind.Collector, &bind.MonitorID, &bind.Pinned,
			&bind.Creator, &bind.Modifier, &createdAt, &updatedAt)
		if err != nil {
			continue
		}
		bind.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
		bind.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
		binds = append(binds, &bind)
	}
	return binds, nil
}

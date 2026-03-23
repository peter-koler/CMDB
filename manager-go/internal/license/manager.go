package license

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/url"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"

	"manager-go/internal/store"

	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3"
)

const (
	configLicenseClaimsJSON = "license_claims_json"
	configLicenseRaw        = "license_raw"
	configLastRunningTime   = "last_running_time"
	watermarkInterval       = 4 * time.Hour
)

var (
	ErrLicenseMalformed       = errors.New("license format invalid")
	ErrLicenseSignature       = errors.New("license signature invalid")
	ErrLicenseMachineMismatch = errors.New("license machine code mismatch")
	ErrLicenseExpired         = errors.New("license expired")
	ErrLicenseLimitExceeded   = errors.New("license enabled monitor limit exceeded")
)

type Claims struct {
	MachineCode string `json:"machine_code"`
	ExpireTime  string `json:"expire_time"`
	MaxMonitors int    `json:"max_monitors"`
	IssuedAt    string `json:"issued_at,omitempty"`
}

type Status struct {
	HasLicense      bool   `json:"has_license"`
	Expired         bool   `json:"expired"`
	MachineCode     string `json:"machine_code"`
	ExpireTime      string `json:"expire_time,omitempty"`
	MaxMonitors     int    `json:"max_monitors"`
	EnabledMonitors int    `json:"enabled_monitors"`
	Halted          bool   `json:"halted"`
	HaltReason      string `json:"halt_reason,omitempty"`
	LastRunningTime string `json:"last_running_time,omitempty"`
}

type envelope struct {
	Alg        string `json:"alg"`
	Nonce      string `json:"nonce"`
	Ciphertext string `json:"ciphertext"`
	Signature  string `json:"signature"`
	IssuedAt   string `json:"issued_at,omitempty"`
}

type Manager struct {
	mu              sync.RWMutex
	db              *sql.DB
	driver          string
	store           *store.MonitorStore
	machineCode     string
	claims          *Claims
	lastRunningTime time.Time
	lastWriteAt     time.Time
	halted          bool
	haltReason      string
	encKey          []byte
	signKey         []byte
}

func NewManager(dbPath string, st *store.MonitorStore) (*Manager, error) {
	driver, dsn := resolveDBDriverAndDSN(dbPath)
	db, err := sql.Open(driver, dsn)
	if err != nil {
		return nil, err
	}
	m := &Manager{
		db:          db,
		driver:      driver,
		store:       st,
		machineCode: machineCode(),
		encKey:      normalizeKey(os.Getenv("LICENSE_ENC_KEY"), "arco-license-enc-key", 32),
		signKey:     normalizeKey(os.Getenv("LICENSE_SIGN_KEY"), "arco-license-sign-key", 32),
	}
	if err := m.initSchema(); err != nil {
		return nil, err
	}
	if err := m.loadPersisted(); err != nil {
		return nil, err
	}
	return m, nil
}

func (m *Manager) MachineCode() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.machineCode
}

func (m *Manager) Install(raw []byte) (*Claims, error) {
	claims, err := m.parseAndValidate(raw)
	if err != nil {
		return nil, err
	}
	claimsJSON, _ := json.Marshal(claims)
	now := time.Now()
	if err := m.setConfig(configLicenseClaimsJSON, string(claimsJSON)); err != nil {
		return nil, err
	}
	if err := m.setConfig(configLicenseRaw, strings.TrimSpace(string(raw))); err != nil {
		return nil, err
	}

	m.mu.Lock()
	m.claims = claims
	m.halted = false
	m.haltReason = ""
	if m.lastRunningTime.IsZero() {
		m.lastRunningTime = now
		m.lastWriteAt = now
		_ = m.setConfig(configLastRunningTime, now.Format(time.RFC3339))
	}
	m.mu.Unlock()
	return claims, nil
}

func (m *Manager) Status() Status {
	m.mu.RLock()
	defer m.mu.RUnlock()
	status := Status{
		MachineCode: m.machineCode,
		Halted:      m.halted,
		HaltReason:  m.haltReason,
	}
	if !m.lastRunningTime.IsZero() {
		status.LastRunningTime = m.lastRunningTime.Format(time.RFC3339)
	}
	status.EnabledMonitors = m.enabledMonitorCount()
	if m.claims == nil {
		return status
	}
	expire, _ := parseLocalTime(m.claims.ExpireTime)
	now := time.Now()
	status.HasLicense = true
	status.ExpireTime = m.claims.ExpireTime
	status.MaxMonitors = m.claims.MaxMonitors
	status.Expired = !expire.IsZero() && now.After(expire)
	return status
}

func (m *Manager) CheckClockRollback(now time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if now.IsZero() {
		now = time.Now()
	}
	if m.lastRunningTime.IsZero() {
		m.lastRunningTime = now
		m.lastWriteAt = now
		return m.setConfig(configLastRunningTime, now.Format(time.RFC3339))
	}
	if now.Before(m.lastRunningTime) {
		m.halted = true
		m.haltReason = "system clock rollback detected"
		return errors.New(m.haltReason)
	}
	if now.Sub(m.lastWriteAt) >= watermarkInterval {
		m.lastRunningTime = now
		m.lastWriteAt = now
		return m.setConfig(configLastRunningTime, now.Format(time.RFC3339))
	}
	return nil
}

func (m *Manager) AllowCollection(now time.Time) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.halted {
		return false
	}
	if m.claims == nil {
		return true
	}
	expire, err := parseLocalTime(m.claims.ExpireTime)
	if err != nil || expire.IsZero() {
		return false
	}
	if now.IsZero() {
		now = time.Now()
	}
	return !now.After(expire)
}

func (m *Manager) ValidateEnableAllowed() error {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if m.halted {
		return errors.New(m.haltReason)
	}
	if m.claims == nil {
		return nil
	}
	now := time.Now()
	expire, err := parseLocalTime(m.claims.ExpireTime)
	if err != nil {
		return ErrLicenseMalformed
	}
	if now.After(expire) {
		return ErrLicenseExpired
	}
	if m.claims.MaxMonitors > 0 && m.enabledMonitorCount() >= m.claims.MaxMonitors {
		return ErrLicenseLimitExceeded
	}
	return nil
}

func (m *Manager) enabledMonitorCount() int {
	if m.store == nil {
		return 0
	}
	items := m.store.List()
	count := 0
	for _, item := range items {
		if item.Enabled {
			count++
		}
	}
	return count
}

func (m *Manager) parseAndValidate(raw []byte) (*Claims, error) {
	trimmed := strings.TrimSpace(string(raw))
	if trimmed == "" {
		return nil, ErrLicenseMalformed
	}
	var env envelope
	if err := json.Unmarshal([]byte(trimmed), &env); err != nil {
		decoded, decErr := base64.StdEncoding.DecodeString(trimmed)
		if decErr != nil {
			return nil, ErrLicenseMalformed
		}
		if err := json.Unmarshal(decoded, &env); err != nil {
			return nil, ErrLicenseMalformed
		}
	}
	if strings.TrimSpace(env.Nonce) == "" || strings.TrimSpace(env.Ciphertext) == "" || strings.TrimSpace(env.Signature) == "" {
		return nil, ErrLicenseMalformed
	}
	expectedSig := signHex(m.signKey, env.Nonce+"."+env.Ciphertext)
	if !hmac.Equal([]byte(strings.ToLower(strings.TrimSpace(env.Signature))), []byte(expectedSig)) {
		return nil, ErrLicenseSignature
	}
	nonce, err := base64.StdEncoding.DecodeString(env.Nonce)
	if err != nil {
		return nil, ErrLicenseMalformed
	}
	ciphertext, err := base64.StdEncoding.DecodeString(env.Ciphertext)
	if err != nil {
		return nil, ErrLicenseMalformed
	}
	plain, err := decryptAESGCM(m.encKey, nonce, ciphertext)
	if err != nil {
		return nil, ErrLicenseMalformed
	}
	var claims Claims
	if err := json.Unmarshal(plain, &claims); err != nil {
		return nil, ErrLicenseMalformed
	}
	if strings.TrimSpace(claims.MachineCode) == "" || strings.TrimSpace(claims.ExpireTime) == "" || claims.MaxMonitors <= 0 {
		return nil, ErrLicenseMalformed
	}
	if !strings.EqualFold(strings.TrimSpace(claims.MachineCode), m.machineCode) {
		return nil, ErrLicenseMachineMismatch
	}
	expire, err := parseLocalTime(claims.ExpireTime)
	if err != nil || expire.IsZero() {
		return nil, ErrLicenseMalformed
	}
	if time.Now().After(expire) {
		return nil, ErrLicenseExpired
	}
	return &claims, nil
}

func (m *Manager) initSchema() error {
	if m.db == nil {
		return nil
	}
	if m.driver == "postgres" {
		_, err := m.db.Exec(`
CREATE TABLE IF NOT EXISTS system_configs (
  id SERIAL PRIMARY KEY,
  config_key VARCHAR(50) NOT NULL UNIQUE,
  config_value TEXT NOT NULL,
  description TEXT,
  updated_by INTEGER,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);
`)
		return err
	}
	_, err := m.db.Exec(`
CREATE TABLE IF NOT EXISTS system_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  config_key VARCHAR(50) NOT NULL UNIQUE,
  config_value TEXT NOT NULL,
  description TEXT,
  updated_by INTEGER,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);
`)
	return err
}

func (m *Manager) loadPersisted() error {
	if m.db == nil {
		return nil
	}
	query := `SELECT config_key, config_value FROM system_configs WHERE config_key IN (?, ?)`
	if m.driver == "postgres" {
		query = `SELECT config_key, config_value FROM system_configs WHERE config_key IN ($1, $2)`
	}
	rows, err := m.db.Query(query, configLicenseClaimsJSON, configLastRunningTime)
	if err != nil {
		return err
	}
	defer rows.Close()
	var (
		claimsRaw string
		lastRaw   string
	)
	for rows.Next() {
		var key, value string
		if err := rows.Scan(&key, &value); err != nil {
			return err
		}
		switch key {
		case configLicenseClaimsJSON:
			claimsRaw = value
		case configLastRunningTime:
			lastRaw = value
		}
	}
	if strings.TrimSpace(claimsRaw) != "" {
		var claims Claims
		if err := json.Unmarshal([]byte(claimsRaw), &claims); err == nil {
			m.claims = &claims
		}
	}
	if strings.TrimSpace(lastRaw) != "" {
		if tm, err := parseLocalTime(lastRaw); err == nil {
			m.lastRunningTime = tm
			m.lastWriteAt = tm
		}
	}
	return rows.Err()
}

func (m *Manager) setConfig(key string, value string) error {
	if m.db == nil {
		return nil
	}
	updateSQL := `UPDATE system_configs SET config_value = ?, updated_at = CURRENT_TIMESTAMP WHERE config_key = ?`
	insertSQL := `INSERT INTO system_configs (config_key, config_value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)`
	if m.driver == "postgres" {
		updateSQL = `UPDATE system_configs SET config_value = $1, updated_at = CURRENT_TIMESTAMP WHERE config_key = $2`
		insertSQL = `INSERT INTO system_configs (config_key, config_value, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP)`
	}
	res, err := m.db.Exec(updateSQL, value, key)
	if err != nil {
		return err
	}
	affected, _ := res.RowsAffected()
	if affected > 0 {
		return nil
	}
	_, err = m.db.Exec(insertSQL, key, value)
	return err
}

func resolveDBDriverAndDSN(raw string) (string, string) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return "sqlite3", "../backend/instance/it_ops.db"
	}
	if strings.HasPrefix(value, "postgresql+psycopg2://") {
		return "postgres", "postgresql://" + strings.TrimPrefix(value, "postgresql+psycopg2://")
	}
	if strings.HasPrefix(value, "postgres://") || strings.HasPrefix(value, "postgresql://") {
		return "postgres", value
	}
	if u, err := url.Parse(value); err == nil {
		switch strings.ToLower(u.Scheme) {
		case "postgres", "postgresql":
			return "postgres", value
		}
	}
	return "sqlite3", value
}

func normalizeKey(raw string, fallback string, size int) []byte {
	seed := strings.TrimSpace(raw)
	if seed == "" {
		seed = fallback
	}
	sum := sha256.Sum256([]byte(seed))
	if size <= len(sum) {
		out := make([]byte, size)
		copy(out, sum[:size])
		return out
	}
	out := make([]byte, size)
	for i := 0; i < size; i++ {
		out[i] = sum[i%len(sum)]
	}
	return out
}

func decryptAESGCM(key []byte, nonce []byte, ciphertext []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(nonce) != gcm.NonceSize() {
		return nil, fmt.Errorf("invalid nonce size")
	}
	return gcm.Open(nil, nonce, ciphertext, nil)
}

func signHex(key []byte, message string) string {
	h := hmac.New(sha256.New, key)
	_, _ = h.Write([]byte(message))
	return hex.EncodeToString(h.Sum(nil))
}

func parseLocalTime(raw string) (time.Time, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return time.Time{}, nil
	}
	layouts := []string{time.RFC3339Nano, time.RFC3339, "2006-01-02 15:04:05", "2006-01-02 15:04"}
	for _, layout := range layouts {
		if strings.Contains(layout, "Z07") {
			if tm, err := time.Parse(layout, raw); err == nil {
				return tm, nil
			}
			continue
		}
		if tm, err := time.ParseInLocation(layout, raw, time.Local); err == nil {
			return tm, nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid time")
}

func machineCode() string {
	raw := strings.TrimSpace(readLinuxMachineID())
	if raw == "" {
		raw = strings.TrimSpace(readMacPlatformUUID())
	}
	if raw == "" {
		raw = strings.TrimSpace(firstMAC())
	}
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}

func readLinuxMachineID() string {
	if runtime.GOOS != "linux" {
		return ""
	}
	data, err := os.ReadFile("/etc/machine-id")
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(data))
}

func readMacPlatformUUID() string {
	if runtime.GOOS != "darwin" {
		return ""
	}
	out, err := exec.Command("ioreg", "-rd1", "-c", "IOPlatformExpertDevice").Output()
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(out), "\n") {
		line = strings.TrimSpace(line)
		if !strings.Contains(line, "IOPlatformUUID") {
			continue
		}
		parts := strings.Split(line, "=")
		if len(parts) != 2 {
			continue
		}
		return strings.Trim(strings.TrimSpace(parts[1]), "\"")
	}
	return ""
}

func firstMAC() string {
	ifaces, err := net.Interfaces()
	if err != nil {
		return ""
	}
	for _, iface := range ifaces {
		if iface.Flags&net.FlagLoopback != 0 {
			continue
		}
		if iface.Flags&net.FlagUp == 0 {
			continue
		}
		mac := strings.TrimSpace(iface.HardwareAddr.String())
		if mac != "" {
			return mac
		}
	}
	return ""
}

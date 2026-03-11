package jdbccollector

import (
	"context"
	"database/sql"
	"fmt"
	"net"
	"strings"
	"sync"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"

	_ "github.com/go-sql-driver/mysql"
)

type Collector struct{}

var dbPool sync.Map // dsn -> *sql.DB

func init() {
	protocol.Register("jdbc", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	platform := strings.ToLower(strings.TrimSpace(task.Params["platform"]))
	if platform == "" {
		platform = strings.ToLower(strings.TrimSpace(task.Params["driver"]))
	}
	if platform == "" {
		platform = "mysql"
	}
	if platform != "mysql" {
		return nil, "", fmt.Errorf("unsupported jdbc platform: %s", platform)
	}
	sqlQuery := strings.TrimSpace(task.Params["sql"])
	if sqlQuery == "" {
		return nil, "", fmt.Errorf("missing sql")
	}
	queryType := strings.ToLower(strings.TrimSpace(task.Params["queryType"]))
	if queryType == "" {
		queryType = "columns"
	}

	dsn, err := buildMySQLDSN(task.Params)
	if err != nil {
		return nil, "", err
	}

	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	db, err := getOrCreateDB(dsn, timeout)
	if err != nil {
		return nil, "", err
	}

	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	if err := db.PingContext(ctx2); err != nil {
		return nil, "", fmt.Errorf("mysql ping failed: %w", err)
	}

	rows, err := db.QueryContext(ctx2, sqlQuery)
	if err != nil {
		return nil, "", fmt.Errorf("mysql query failed: %w", err)
	}
	defer rows.Close()

	switch queryType {
	case "columns":
		return collectColumns(rows)
	case "onerow":
		return collectOneRow(rows)
	case "multirow":
		return collectMultiRow(rows)
	default:
		return nil, "", fmt.Errorf("unsupported queryType: %s", queryType)
	}
}

func getOrCreateDB(dsn string, timeout time.Duration) (*sql.DB, error) {
	if raw, ok := dbPool.Load(dsn); ok {
		if db, ok2 := raw.(*sql.DB); ok2 {
			return db, nil
		}
	}
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, fmt.Errorf("open mysql failed: %w", err)
	}
	db.SetConnMaxIdleTime(2 * time.Minute)
	db.SetConnMaxLifetime(15 * time.Minute)
	db.SetMaxOpenConns(8)
	db.SetMaxIdleConns(4)
	actual, loaded := dbPool.LoadOrStore(dsn, db)
	if loaded {
		_ = db.Close()
		if pooled, ok := actual.(*sql.DB); ok {
			return pooled, nil
		}
		return nil, fmt.Errorf("invalid db pool entry")
	}
	return db, nil
}

func buildMySQLDSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		return rawURL, nil
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "3306"
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	database := strings.TrimSpace(params["database"])
	timeout := strings.TrimSpace(params["timeout"])
	if timeout == "" {
		timeout = "5000"
	}
	ms, err := time.ParseDuration(timeout + "ms")
	if err != nil {
		ms = 5 * time.Second
	}
	addr := net.JoinHostPort(host, port)
	return fmt.Sprintf("%s:%s@tcp(%s)/%s?timeout=%s&readTimeout=%s&writeTimeout=%s&parseTime=false",
		user, pass, addr, database, ms.String(), ms.String(), ms.String()), nil
}

func collectColumns(rows *sql.Rows) (map[string]string, string, error) {
	out := map[string]string{}
	for rows.Next() {
		var key sql.NullString
		var value sql.NullString
		if err := rows.Scan(&key, &value); err != nil {
			return nil, "", fmt.Errorf("scan columns query failed: %w", err)
		}
		if !key.Valid || strings.TrimSpace(key.String) == "" {
			continue
		}
		out[strings.TrimSpace(key.String)] = strings.TrimSpace(value.String)
	}
	if err := rows.Err(); err != nil {
		return nil, "", err
	}
	return out, "ok", nil
}

func collectOneRow(rows *sql.Rows) (map[string]string, string, error) {
	cols, err := rows.Columns()
	if err != nil {
		return nil, "", err
	}
	if !rows.Next() {
		return map[string]string{}, "ok", nil
	}
	data, err := scanRow(cols, rows)
	if err != nil {
		return nil, "", err
	}
	return data, "ok", nil
}

func collectMultiRow(rows *sql.Rows) (map[string]string, string, error) {
	cols, err := rows.Columns()
	if err != nil {
		return nil, "", err
	}
	out := map[string]string{}
	index := 0
	for rows.Next() {
		index++
		row, err := scanRow(cols, rows)
		if err != nil {
			return nil, "", err
		}
		for k, v := range row {
			out[fmt.Sprintf("row%d_%s", index, k)] = v
		}
	}
	if err := rows.Err(); err != nil {
		return nil, "", err
	}
	return out, "ok", nil
}

func scanRow(cols []string, rows *sql.Rows) (map[string]string, error) {
	raw := make([]sql.RawBytes, len(cols))
	args := make([]any, len(cols))
	for i := range raw {
		args[i] = &raw[i]
	}
	if err := rows.Scan(args...); err != nil {
		return nil, err
	}
	out := make(map[string]string, len(cols))
	for i, col := range cols {
		out[col] = string(raw[i])
	}
	return out, nil
}

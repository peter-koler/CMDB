package jdbccollector

import (
	"context"
	"database/sql"
	"fmt"
	"net"
	"net/url"
	"strings"
	"sync"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"

	_ "gitee.com/chunanyong/dm"
	_ "github.com/ClickHouse/clickhouse-go/v2"
	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
	_ "github.com/microsoft/go-mssqldb"
	_ "github.com/sijms/go-ora/v2"
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
	switch platform {
	case "postgresql":
		platform = "postgres"
	case "mariadb", "tidb", "oceanbase":
		platform = "mysql"
	case "kingbase", "greenplum", "vastbase", "opengauss":
		platform = "postgres"
	case "sql_server", "mssql":
		platform = "sqlserver"
	}
	if platform != "mysql" && platform != "clickhouse" && platform != "postgres" && platform != "sqlserver" && platform != "oracle" && platform != "dm" && platform != "db2" {
		return nil, "", fmt.Errorf("unsupported jdbc platform: %s (supported: mysql/mariadb/tidb/oceanbase, postgres/postgresql/kingbase/greenplum/vastbase/opengauss, sqlserver, oracle, dm, db2)", platform)
	}
	if platform == "db2" && !db2DriverEnabled {
		return nil, "", fmt.Errorf("db2 driver is not enabled in current build. rebuild collector-go with tags=db2 and set IBM_DB_HOME/CGO_* env for go_ibm_db")
	}
	sqlQuery := strings.TrimSpace(task.Params["sql"])
	if sqlQuery == "" {
		return nil, "", fmt.Errorf("missing sql")
	}
	queryType := strings.ToLower(strings.TrimSpace(task.Params["queryType"]))
	if queryType == "" {
		queryType = "columns"
	}
	aliasFields := parseAliasFields(task.Params["alias_fields"])

	dsn, err := buildDSN(task.Params, platform)
	if err != nil {
		return nil, "", err
	}

	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	db, err := getOrCreateDB(platform, dsn, timeout)
	if err != nil {
		return nil, "", err
	}

	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	if err := db.PingContext(ctx2); err != nil {
		return nil, "", fmt.Errorf("%s ping failed: %w", platform, err)
	}

	rows, err := db.QueryContext(ctx2, sqlQuery)
	if err != nil {
		if shouldSkipPostgresQueryError(platform, sqlQuery, err) {
			return map[string]string{}, "skip pg_stat_statements(not enabled)", nil
		}
		return nil, "", fmt.Errorf("%s query failed: %w", platform, err)
	}
	defer rows.Close()

	switch queryType {
	case "columns":
		return collectColumns(rows, aliasFields)
	case "onerow":
		return collectOneRow(rows, aliasFields)
	case "multirow":
		return collectMultiRow(rows, aliasFields)
	default:
		return nil, "", fmt.Errorf("unsupported queryType: %s", queryType)
	}
}

func shouldSkipPostgresQueryError(platform, sqlQuery string, err error) bool {
	if strings.TrimSpace(strings.ToLower(platform)) != "postgres" {
		return false
	}
	sqlText := strings.ToLower(strings.TrimSpace(sqlQuery))
	if !strings.Contains(sqlText, "pg_stat_statements") {
		return false
	}
	errText := strings.ToLower(strings.TrimSpace(err.Error()))
	if strings.Contains(errText, `relation "pg_stat_statements" does not exist`) {
		return true
	}
	if strings.Contains(errText, "pg_stat_statements must be loaded via shared_preload_libraries") {
		return true
	}
	return false
}

func getOrCreateDB(platform, dsn string, timeout time.Duration) (*sql.DB, error) {
	key := platform + "|" + dsn
	if raw, ok := dbPool.Load(key); ok {
		if db, ok2 := raw.(*sql.DB); ok2 {
			return db, nil
		}
	}
	driver := "mysql"
	switch platform {
	case "clickhouse":
		driver = "clickhouse"
	case "postgres":
		driver = "postgres"
	case "sqlserver":
		driver = "sqlserver"
	case "oracle":
		driver = "oracle"
	case "dm":
		driver = "dm"
	case "db2":
		driver = "go_ibm_db"
	}
	db, err := sql.Open(driver, dsn)
	if err != nil {
		return nil, fmt.Errorf("open %s failed: %w", platform, err)
	}
	db.SetConnMaxIdleTime(2 * time.Minute)
	db.SetConnMaxLifetime(15 * time.Minute)
	db.SetMaxOpenConns(8)
	db.SetMaxIdleConns(4)
	actual, loaded := dbPool.LoadOrStore(key, db)
	if loaded {
		_ = db.Close()
		if pooled, ok := actual.(*sql.DB); ok {
			return pooled, nil
		}
		return nil, fmt.Errorf("invalid db pool entry")
	}
	return db, nil
}

func buildDSN(params map[string]string, platform string) (string, error) {
	if platform == "clickhouse" {
		return buildClickHouseDSN(params)
	}
	if platform == "postgres" {
		return buildPostgresDSN(params)
	}
	if platform == "sqlserver" {
		return buildSQLServerDSN(params)
	}
	if platform == "oracle" {
		return buildOracleDSN(params)
	}
	if platform == "dm" {
		return buildDMDSN(params)
	}
	if platform == "db2" {
		return buildDB2DSN(params)
	}
	return buildMySQLDSN(params)
}

func buildPostgresDSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		lower := strings.ToLower(rawURL)
		// Accept explicit postgres URL DSN or lib/pq key-value DSN.
		if strings.HasPrefix(lower, "postgres://") || strings.HasPrefix(lower, "postgresql://") || strings.Contains(rawURL, "=") {
			return rawURL, nil
		}
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "5432"
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	database := strings.TrimSpace(params["database"])
	if database == "" {
		database = "postgres"
	}
	sslMode := strings.TrimSpace(params["sslmode"])
	if sslMode == "" {
		sslMode = "disable"
	}
	timeout := parseTimeoutDuration(strings.TrimSpace(params["timeout"]), 5*time.Second)
	connectSeconds := int(timeout / time.Second)
	if connectSeconds <= 0 {
		connectSeconds = 5
	}
	return fmt.Sprintf(
		"postgresql://%s:%s@%s/%s?sslmode=%s&connect_timeout=%d",
		url.QueryEscape(user),
		url.QueryEscape(pass),
		net.JoinHostPort(host, port),
		url.PathEscape(database),
		url.QueryEscape(sslMode),
		connectSeconds,
	), nil
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
	ms := parseTimeoutDuration(strings.TrimSpace(params["timeout"]), 5*time.Second)
	addr := net.JoinHostPort(host, port)
	return fmt.Sprintf("%s:%s@tcp(%s)/%s?timeout=%s&readTimeout=%s&writeTimeout=%s&parseTime=false",
		user, pass, addr, database, ms.String(), ms.String(), ms.String()), nil
}

func buildSQLServerDSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		lower := strings.ToLower(rawURL)
		if strings.HasPrefix(lower, "sqlserver://") || strings.Contains(rawURL, "=") {
			return rawURL, nil
		}
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "1433"
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	database := strings.TrimSpace(params["database"])
	timeout := parseTimeoutDuration(strings.TrimSpace(params["timeout"]), 5*time.Second)
	sec := int(timeout / time.Second)
	if sec <= 0 {
		sec = 5
	}
	query := url.Values{}
	if user != "" {
		query.Set("user id", user)
	}
	if pass != "" {
		query.Set("password", pass)
	}
	if database != "" {
		query.Set("database", database)
	}
	query.Set("connection timeout", fmt.Sprintf("%d", sec))
	return fmt.Sprintf("sqlserver://%s?%s", net.JoinHostPort(host, port), query.Encode()), nil
}

func buildOracleDSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		lower := strings.ToLower(rawURL)
		if strings.HasPrefix(lower, "oracle://") || strings.HasPrefix(lower, "jdbc:oracle:") || strings.Contains(rawURL, "=") {
			return rawURL, nil
		}
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "1521"
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	database := strings.TrimSpace(params["database"])
	if database == "" {
		database = "ORCL"
	}
	return fmt.Sprintf("oracle://%s:%s@%s/%s",
		url.QueryEscape(user),
		url.QueryEscape(pass),
		net.JoinHostPort(host, port),
		url.PathEscape(database),
	), nil
}

func buildDMDSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		lower := strings.ToLower(rawURL)
		if strings.HasPrefix(lower, "dm://") {
			return rawURL, nil
		}
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "5236"
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	schema := strings.TrimSpace(params["database"])

	base := "dm://"
	if user != "" {
		base += url.QueryEscape(user)
		if pass != "" {
			base += ":" + url.PathEscape(pass)
		}
		base += "@"
	}
	base += net.JoinHostPort(host, port)
	query := url.Values{}
	if schema != "" {
		query.Set("schema", schema)
	}
	if pass != "" {
		query.Set("escapeProcess", "true")
	}
	if encoded := query.Encode(); encoded != "" {
		base += "?" + encoded
	}
	return base, nil
}

func buildDB2DSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		lower := strings.ToLower(rawURL)
		if strings.Contains(rawURL, "=") || strings.HasPrefix(lower, "database=") || strings.HasPrefix(lower, "jdbc:db2://") {
			if strings.HasPrefix(lower, "jdbc:db2://") {
				return convertJdbcDB2ToGoDSN(rawURL, params)
			}
			return rawURL, nil
		}
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	database := strings.TrimSpace(params["database"])
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "50000"
	}
	if database == "" {
		return "", fmt.Errorf("missing database for db2")
	}
	parts := []string{
		"DATABASE=" + database,
		"HOSTNAME=" + host,
		"PORT=" + port,
		"PROTOCOL=TCPIP",
	}
	if user != "" {
		parts = append(parts, "UID="+user)
	}
	if pass != "" {
		parts = append(parts, "PWD="+pass)
	}
	return strings.Join(parts, ";"), nil
}

func convertJdbcDB2ToGoDSN(raw string, params map[string]string) (string, error) {
	base := strings.TrimSpace(raw)
	base = strings.TrimPrefix(base, "jdbc:")
	u, err := url.Parse(base)
	if err != nil {
		return "", fmt.Errorf("invalid db2 jdbc url: %w", err)
	}
	host := u.Hostname()
	port := u.Port()
	database := strings.TrimPrefix(u.Path, "/")
	if v := strings.TrimSpace(params["host"]); v != "" {
		host = v
	}
	if v := strings.TrimSpace(params["port"]); v != "" {
		port = v
	}
	if v := strings.TrimSpace(params["database"]); v != "" {
		database = v
	}
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "50000"
	}
	if database == "" {
		return "", fmt.Errorf("missing database for db2 jdbc url")
	}
	user := strings.TrimSpace(params["username"])
	pass := strings.TrimSpace(params["password"])
	parts := []string{
		"DATABASE=" + database,
		"HOSTNAME=" + host,
		"PORT=" + port,
		"PROTOCOL=TCPIP",
	}
	if user != "" {
		parts = append(parts, "UID="+user)
	}
	if pass != "" {
		parts = append(parts, "PWD="+pass)
	}
	return strings.Join(parts, ";"), nil
}

func collectColumns(rows *sql.Rows, aliasFields []string) (map[string]string, string, error) {
	out := make(map[string]string)
	valuesByLower := make(map[string]string)
	cols, err := rows.Columns()
	if err != nil {
		return nil, "", err
	}
	if len(cols) < 2 {
		return nil, "", fmt.Errorf("columns query requires at least 2 columns, got %d", len(cols))
	}

	for rows.Next() {
		raw := make([]sql.RawBytes, len(cols))
		args := make([]any, len(cols))
		for i := range raw {
			args[i] = &raw[i]
		}
		if err := rows.Scan(args...); err != nil {
			return nil, "", fmt.Errorf("scan columns query failed: %w", err)
		}
		k := strings.TrimSpace(string(raw[0]))
		if k == "" {
			continue
		}
		v := strings.TrimSpace(string(raw[1]))
		out[k] = v
		valuesByLower[strings.ToLower(k)] = v
	}
	if err := rows.Err(); err != nil {
		return nil, "", err
	}
	if len(aliasFields) > 0 {
		filtered := make(map[string]string, len(aliasFields))
		for _, alias := range aliasFields {
			if alias == "" {
				continue
			}
			if value, ok := valuesByLower[strings.ToLower(alias)]; ok {
				filtered[alias] = value
			}
		}
		return filtered, "ok", nil
	}
	return out, "ok", nil
}

func collectOneRow(rows *sql.Rows, aliasFields []string) (map[string]string, string, error) {
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
	data = projectRow(data, cols, aliasFields)
	return data, "ok", nil
}

func collectMultiRow(rows *sql.Rows, aliasFields []string) (map[string]string, string, error) {
	cols, err := rows.Columns()
	if err != nil {
		return nil, "", err
	}
	selected := aliasFields
	if len(selected) == 0 {
		selected = cols
	}
	out := map[string]string{}
	index := 0
	for rows.Next() {
		index++
		row, err := scanRow(cols, rows)
		if err != nil {
			return nil, "", err
		}
		projected := projectRow(row, cols, selected)
		for k, v := range projected {
			if index == 1 {
				// Keep first-row canonical fields for compatibility with field_specs/calculates.
				out[k] = v
			}
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

package jdbccollector

import (
	"fmt"
	"net"
	"net/url"
	"strings"
	"time"
)

func buildClickHouseDSN(params map[string]string) (string, error) {
	if rawURL := strings.TrimSpace(params["url"]); rawURL != "" {
		if strings.HasPrefix(strings.ToLower(rawURL), "jdbc:clickhouse://") {
			return "clickhouse://" + strings.TrimPrefix(rawURL, "jdbc:clickhouse://"), nil
		}
		return rawURL, nil
	}
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	if host == "" {
		host = "127.0.0.1"
	}
	if port == "" {
		port = "8123"
	}
	database := strings.TrimSpace(params["database"])
	if database == "" {
		database = "default"
	}
	username := strings.TrimSpace(params["username"])
	password := strings.TrimSpace(params["password"])
	timeout := parseTimeoutDuration(params["timeout"], 5*time.Second)

	query := url.Values{}
	query.Set("read_timeout", timeout.String())
	query.Set("dial_timeout", timeout.String())
	query.Set("max_execution_time", "60")
	if username != "" {
		query.Set("username", username)
	}
	if password != "" {
		query.Set("password", password)
	}
	addr := net.JoinHostPort(host, port)
	return fmt.Sprintf("clickhouse://%s/%s?%s", addr, database, query.Encode()), nil
}

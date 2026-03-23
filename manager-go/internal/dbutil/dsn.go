package dbutil

import (
	"net/url"
	"strings"
)

// ResolveDriverAndDSN resolves SQL driver and DSN from a raw value.
// Supported:
// - sqlite path (default fallback)
// - postgres://
// - postgresql://
// - postgresql+psycopg2:// (converted to postgresql://)
func ResolveDriverAndDSN(raw string, sqliteFallback string) (string, string) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return "sqlite3", sqliteFallback
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

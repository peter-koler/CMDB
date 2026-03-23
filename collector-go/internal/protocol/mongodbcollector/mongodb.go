package mongodbcollector

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"
	"sync"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type Collector struct{}

var mongoClientPool sync.Map // uri -> *mongo.Client

func init() {
	protocol.Register("mongodb", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	command := strings.TrimSpace(task.Params["command"])
	if command == "" {
		return nil, "", fmt.Errorf("missing command")
	}
	host := strings.TrimSpace(task.Params["host"])
	if host == "" {
		return nil, "", fmt.Errorf("missing host")
	}
	database := strings.TrimSpace(task.Params["database"])
	if database == "" {
		database = "admin"
	}

	timeout := resolveTimeout(task)
	uri := buildMongoURI(task.Params, host, database)

	client, err := getOrCreateMongoClient(uri, timeout)
	if err != nil {
		return nil, "", err
	}

	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	if err := client.Ping(ctx2, nil); err != nil {
		return nil, "", fmt.Errorf("mongodb ping failed: %w", err)
	}

	baseCommand, pathParts := splitCommand(command)
	doc := bson.M{}
	if err := client.Database(database).RunCommand(ctx2, bson.D{{Key: baseCommand, Value: 1}}).Decode(&doc); err != nil {
		return nil, "", fmt.Errorf("mongodb command failed: %w", err)
	}

	payload := any(doc)
	for _, part := range pathParts {
		next, ok := lookupPath(payload, part)
		if !ok {
			return map[string]string{}, "ok", nil
		}
		payload = next
	}

	fields := flattenMongoPayload(payload)
	return fields, "ok", nil
}

func resolveTimeout(task model.MetricsTask) time.Duration {
	if task.Timeout > 0 {
		return task.Timeout
	}
	raw := strings.TrimSpace(task.Params["timeout"])
	if raw == "" {
		return 5 * time.Second
	}
	if ms, err := time.ParseDuration(raw + "ms"); err == nil && ms > 0 {
		return ms
	}
	return 5 * time.Second
}

func buildMongoURI(params map[string]string, host string, database string) string {
	modelType := strings.ToLower(strings.TrimSpace(params["model"]))
	username := strings.TrimSpace(params["username"])
	password := strings.TrimSpace(params["password"])
	authDB := strings.TrimSpace(params["authenticationDatabase"])
	if authDB == "" {
		authDB = database
	}

	if modelType == "atlas" || modelType == "mongodb-atlas" || modelType == "mongodb_atlas" {
		if username == "" && password == "" {
			return fmt.Sprintf("mongodb+srv://%s/%s", host, database)
		}
		return fmt.Sprintf("mongodb+srv://%s:%s@%s/%s?authSource=%s",
			url.QueryEscape(username),
			url.QueryEscape(password),
			host,
			url.PathEscape(database),
			url.QueryEscape(authDB),
		)
	}

	port := strings.TrimSpace(params["port"])
	if port == "" {
		port = "27017"
	}
	if username == "" && password == "" {
		return fmt.Sprintf("mongodb://%s:%s/%s", host, port, url.PathEscape(database))
	}
	return fmt.Sprintf("mongodb://%s:%s@%s:%s/%s?authSource=%s",
		url.QueryEscape(username),
		url.QueryEscape(password),
		host,
		port,
		url.PathEscape(database),
		url.QueryEscape(authDB),
	)
}

func splitCommand(command string) (string, []string) {
	raw := strings.TrimSpace(command)
	if raw == "" {
		return "", nil
	}
	parts := strings.Split(raw, ".")
	base := strings.TrimSpace(parts[0])
	if len(parts) == 1 {
		return base, nil
	}
	tail := make([]string, 0, len(parts)-1)
	for _, p := range parts[1:] {
		p = strings.TrimSpace(p)
		if p != "" {
			tail = append(tail, p)
		}
	}
	return base, tail
}

func lookupPath(in any, key string) (any, bool) {
	switch m := in.(type) {
	case map[string]any:
		v, ok := m[key]
		return v, ok
	case bson.M:
		v, ok := m[key]
		return v, ok
	default:
		return nil, false
	}
}

func flattenMongoPayload(payload any) map[string]string {
	switch v := payload.(type) {
	case map[string]any:
		out := make(map[string]string, len(v))
		for k, item := range v {
			out[k] = anyToString(item)
		}
		return out
	case bson.M:
		out := make(map[string]string, len(v))
		for k, item := range v {
			out[k] = anyToString(item)
		}
		return out
	default:
		return map[string]string{
			"value": anyToString(v),
		}
	}
}

func anyToString(v any) string {
	switch t := v.(type) {
	case nil:
		return ""
	case string:
		return t
	case fmt.Stringer:
		return t.String()
	case int:
		return fmt.Sprintf("%d", t)
	case int8:
		return fmt.Sprintf("%d", t)
	case int16:
		return fmt.Sprintf("%d", t)
	case int32:
		return fmt.Sprintf("%d", t)
	case int64:
		return fmt.Sprintf("%d", t)
	case uint:
		return fmt.Sprintf("%d", t)
	case uint8:
		return fmt.Sprintf("%d", t)
	case uint16:
		return fmt.Sprintf("%d", t)
	case uint32:
		return fmt.Sprintf("%d", t)
	case uint64:
		return fmt.Sprintf("%d", t)
	case float32:
		return fmt.Sprintf("%v", t)
	case float64:
		return fmt.Sprintf("%v", t)
	case bool:
		if t {
			return "true"
		}
		return "false"
	default:
		raw, err := json.Marshal(t)
		if err != nil {
			return fmt.Sprintf("%v", t)
		}
		return string(raw)
	}
}

func getOrCreateMongoClient(uri string, timeout time.Duration) (*mongo.Client, error) {
	if raw, ok := mongoClientPool.Load(uri); ok {
		if client, ok2 := raw.(*mongo.Client); ok2 {
			return client, nil
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri).SetServerSelectionTimeout(timeout))
	if err != nil {
		return nil, fmt.Errorf("mongodb connect failed: %w", err)
	}

	actual, loaded := mongoClientPool.LoadOrStore(uri, client)
	if loaded {
		_ = client.Disconnect(context.Background())
		if pooled, ok := actual.(*mongo.Client); ok {
			return pooled, nil
		}
		return nil, fmt.Errorf("invalid mongo client pool entry")
	}
	return client, nil
}

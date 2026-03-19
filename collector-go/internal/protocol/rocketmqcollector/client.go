package rocketmqcollector

import (
	"context"
	"fmt"
	"net"
	"strings"
	"time"

	"collector-go/internal/model"

	mqadmin "github.com/apache/rocketmq-client-go/v2/admin"
	"github.com/apache/rocketmq-client-go/v2/primitive"
)

type adminClient interface {
	FetchAllTopicList(ctx context.Context) (*mqadmin.TopicList, error)
	FetchPublishMessageQueues(ctx context.Context, topic string) ([]*primitive.MessageQueue, error)
	Close() error
}

var newAdminClient = buildAdminClient

func buildAdminClient(task model.MetricsTask) (adminClient, string, error) {
	host := strings.TrimSpace(task.Params["host"])
	port := strings.TrimSpace(task.Params["port"])
	if host == "" {
		return nil, "", fmt.Errorf("missing namesrv host")
	}
	if port == "" {
		port = "9876"
	}
	addr := net.JoinHostPort(host, port)
	options := []mqadmin.AdminOption{
		mqadmin.WithResolver(primitive.NewPassthroughResolver([]string{addr})),
	}
	accessKey := strings.TrimSpace(task.Params["accessKey"])
	secretKey := strings.TrimSpace(task.Params["secretKey"])
	if accessKey != "" || secretKey != "" {
		options = append(options, mqadmin.WithCredentials(primitive.Credentials{
			AccessKey: accessKey,
			SecretKey: secretKey,
		}))
	}
	admin, err := mqadmin.NewAdmin(options...)
	if err != nil {
		return nil, "", err
	}
	return admin, addr, nil
}

func taskTimeout(task model.MetricsTask) time.Duration {
	if task.Timeout > 0 {
		return task.Timeout
	}
	return 5 * time.Second
}

package rocketmqcollector

import (
	"context"
	"errors"
	"testing"

	"collector-go/internal/model"

	mqadmin "github.com/apache/rocketmq-client-go/v2/admin"
	"github.com/apache/rocketmq-client-go/v2/primitive"
)

type fakeAdmin struct {
	topics []string
	queues map[string][]*primitive.MessageQueue
	errors map[string]error
}

func (f *fakeAdmin) FetchAllTopicList(context.Context) (*mqadmin.TopicList, error) {
	return &mqadmin.TopicList{TopicList: append([]string(nil), f.topics...)}, nil
}

func (f *fakeAdmin) FetchPublishMessageQueues(_ context.Context, topic string) ([]*primitive.MessageQueue, error) {
	if err := f.errors[topic]; err != nil {
		return nil, err
	}
	return f.queues[topic], nil
}

func (f *fakeAdmin) Close() error { return nil }

func TestCollectOverview(t *testing.T) {
	old := newAdminClient
	defer func() { newAdminClient = old }()
	newAdminClient = func(task model.MetricsTask) (adminClient, string, error) {
		return &fakeAdmin{
			topics: []string{"topic-a", "%RETRY%group-a", "TBW102"},
			queues: map[string][]*primitive.MessageQueue{
				"topic-a":        {&primitive.MessageQueue{Topic: "topic-a", BrokerName: "broker-a", QueueId: 0}, &primitive.MessageQueue{Topic: "topic-a", BrokerName: "broker-b", QueueId: 1}},
				"%RETRY%group-a": {&primitive.MessageQueue{Topic: "%RETRY%group-a", BrokerName: "broker-a", QueueId: 0}},
			},
			errors: map[string]error{"TBW102": errors.New("route unavailable")},
		}, "127.0.0.1:9876", nil
	}
	collector := &Collector{}
	fields, _, err := collector.Collect(context.Background(), model.MetricsTask{Params: map[string]string{"command": "overview"}})
	if err != nil {
		t.Fatalf("collect overview error: %v", err)
	}
	if fields["TopicCount"] != "3" || fields["NormalTopicCount"] != "1" || fields["RetryTopicCount"] != "1" || fields["SystemTopicCount"] != "1" {
		t.Fatalf("unexpected topic counters: %+v", fields)
	}
	if fields["BrokerCount"] != "2" || fields["QueueCount"] != "3" || fields["TopicRouteErrorCount"] != "1" {
		t.Fatalf("unexpected route counters: %+v", fields)
	}
}

func TestCollectTopicList(t *testing.T) {
	old := newAdminClient
	defer func() { newAdminClient = old }()
	newAdminClient = func(task model.MetricsTask) (adminClient, string, error) {
		return &fakeAdmin{
			topics: []string{"topic-a", "%DLQ%group-a"},
			queues: map[string][]*primitive.MessageQueue{
				"topic-a":      {&primitive.MessageQueue{Topic: "topic-a", BrokerName: "broker-a", QueueId: 0}},
				"%DLQ%group-a": {&primitive.MessageQueue{Topic: "%DLQ%group-a", BrokerName: "broker-b", QueueId: 0}},
			},
		}, "127.0.0.1:9876", nil
	}
	collector := &Collector{}
	fields, _, err := collector.Collect(context.Background(), model.MetricsTask{Params: map[string]string{"command": "topic-list"}})
	if err != nil {
		t.Fatalf("collect topic-list error: %v", err)
	}
	if fields["TopicName"] != "%DLQ%group-a" || fields["row2_TopicName"] != "topic-a" {
		t.Fatalf("unexpected row ordering: %+v", fields)
	}
	if fields["RouteStatus"] != "ok" || fields["row2_BrokerNames"] != "broker-a" {
		t.Fatalf("unexpected topic fields: %+v", fields)
	}
}

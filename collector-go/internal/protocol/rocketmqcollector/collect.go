package rocketmqcollector

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"strings"

	"collector-go/internal/model"
	"collector-go/internal/protocol"
)

type Collector struct{}

func init() {
	protocol.Register("rocketmq", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	admin, addr, err := newAdminClient(task)
	if err != nil {
		return nil, "", err
	}
	defer func() { _ = admin.Close() }()

	command := strings.ToLower(strings.TrimSpace(task.Params["command"]))
	if command == "" {
		command = "overview"
	}
	ctx2, cancel := context.WithTimeout(ctx, taskTimeout(task))
	defer cancel()

	switch command {
	case "overview":
		return collectOverview(ctx2, admin, addr)
	case "topic-list":
		return collectTopicList(ctx2, admin)
	default:
		return nil, "", fmt.Errorf("unsupported rocketmq command: %s", command)
	}
}

type topicSummary struct {
	Name        string
	TopicType   string
	QueueCount  int
	BrokerCount int
	BrokerNames []string
	RouteStatus string
}

func collectOverview(ctx context.Context, admin adminClient, namesrvAddr string) (map[string]string, string, error) {
	topics, err := admin.FetchAllTopicList(ctx)
	if err != nil {
		return nil, "", err
	}
	rows, counters := summarizeTopics(ctx, admin, topics.TopicList)
	avgQueueCount := 0.0
	if counters.topicCount > 0 {
		avgQueueCount = float64(counters.queueCount) / float64(counters.topicCount)
	}
	fields := map[string]string{
		"NamesrvAddress":        namesrvAddr,
		"TopicCount":            strconv.Itoa(counters.topicCount),
		"NormalTopicCount":      strconv.Itoa(counters.normalTopicCount),
		"RetryTopicCount":       strconv.Itoa(counters.retryTopicCount),
		"DeadLetterTopicCount":  strconv.Itoa(counters.deadLetterTopicCount),
		"SystemTopicCount":      strconv.Itoa(counters.systemTopicCount),
		"BrokerCount":           strconv.Itoa(len(counters.brokerSet)),
		"QueueCount":            strconv.Itoa(counters.queueCount),
		"AvgQueueCountPerTopic": strconv.FormatFloat(avgQueueCount, 'f', 2, 64),
		"MaxQueueCountPerTopic": strconv.Itoa(counters.maxQueueCount),
		"TopicRouteErrorCount":  strconv.Itoa(counters.routeErrorCount),
	}
	if len(rows) > 0 {
		fields["TopicName"] = rows[0].Name
	}
	return fields, "ok", nil
}

func collectTopicList(ctx context.Context, admin adminClient) (map[string]string, string, error) {
	topics, err := admin.FetchAllTopicList(ctx)
	if err != nil {
		return nil, "", err
	}
	rows, _ := summarizeTopics(ctx, admin, topics.TopicList)
	out := map[string]string{}
	for idx, row := range rows {
		no := idx + 1
		if no == 1 {
			out["TopicName"] = row.Name
			out["TopicType"] = row.TopicType
			out["QueueCount"] = strconv.Itoa(row.QueueCount)
			out["BrokerCount"] = strconv.Itoa(row.BrokerCount)
			out["BrokerNames"] = strings.Join(row.BrokerNames, ",")
			out["RouteStatus"] = row.RouteStatus
		}
		out[fmt.Sprintf("row%d_TopicName", no)] = row.Name
		out[fmt.Sprintf("row%d_TopicType", no)] = row.TopicType
		out[fmt.Sprintf("row%d_QueueCount", no)] = strconv.Itoa(row.QueueCount)
		out[fmt.Sprintf("row%d_BrokerCount", no)] = strconv.Itoa(row.BrokerCount)
		out[fmt.Sprintf("row%d_BrokerNames", no)] = strings.Join(row.BrokerNames, ",")
		out[fmt.Sprintf("row%d_RouteStatus", no)] = row.RouteStatus
	}
	return out, "ok", nil
}

type topicCounters struct {
	topicCount           int
	normalTopicCount     int
	retryTopicCount      int
	deadLetterTopicCount int
	systemTopicCount     int
	queueCount           int
	maxQueueCount        int
	routeErrorCount      int
	brokerSet            map[string]struct{}
}

func summarizeTopics(ctx context.Context, admin adminClient, topics []string) ([]topicSummary, topicCounters) {
	sorted := append([]string(nil), topics...)
	sort.Strings(sorted)
	counters := topicCounters{brokerSet: map[string]struct{}{}}
	rows := make([]topicSummary, 0, len(sorted))
	for _, topic := range sorted {
		typeName := classifyTopic(topic)
		switch typeName {
		case "normal":
			counters.normalTopicCount++
		case "retry":
			counters.retryTopicCount++
		case "dead_letter":
			counters.deadLetterTopicCount++
		default:
			counters.systemTopicCount++
		}
		counters.topicCount++
		queues, err := admin.FetchPublishMessageQueues(ctx, topic)
		row := topicSummary{Name: topic, TopicType: typeName, RouteStatus: "ok"}
		if err != nil {
			row.RouteStatus = "route_error"
			counters.routeErrorCount++
			rows = append(rows, row)
			continue
		}
		brokerSet := map[string]struct{}{}
		for _, queue := range queues {
			if queue == nil {
				continue
			}
			row.QueueCount++
			if queue.BrokerName != "" {
				brokerSet[queue.BrokerName] = struct{}{}
				counters.brokerSet[queue.BrokerName] = struct{}{}
			}
		}
		row.BrokerNames = sortedKeys(brokerSet)
		row.BrokerCount = len(row.BrokerNames)
		counters.queueCount += row.QueueCount
		if row.QueueCount > counters.maxQueueCount {
			counters.maxQueueCount = row.QueueCount
		}
		rows = append(rows, row)
	}
	return rows, counters
}

func sortedKeys(set map[string]struct{}) []string {
	keys := make([]string, 0, len(set))
	for key := range set {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func classifyTopic(topic string) string {
	switch {
	case strings.HasPrefix(topic, "%RETRY%"):
		return "retry"
	case strings.HasPrefix(topic, "%DLQ%"):
		return "dead_letter"
	case isSystemTopic(topic):
		return "system"
	default:
		return "normal"
	}
}

func isSystemTopic(topic string) bool {
	switch topic {
	case "TBW102", "SELF_TEST_TOPIC", "OFFSET_MOVED_EVENT", "SCHEDULE_TOPIC_XXXX", "BenchmarkTest", "TRANS_CHECK_MAX_TIME_TOPIC", "RMQ_SYS_TRANS_HALF_TOPIC", "RMQ_SYS_TRACE_TOPIC":
		return true
	default:
		return strings.HasPrefix(topic, "rmq_sys_")
	}
}

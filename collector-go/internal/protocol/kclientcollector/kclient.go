package kclientcollector

import (
	"context"
	"fmt"
	"net"
	"sort"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
	"collector-go/internal/protocol"

	"github.com/IBM/sarama"
)

type Collector struct{}

func init() {
	protocol.Register("kclient", &Collector{})
}

func (c *Collector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	admin, client, err := buildAdmin(task)
	if err != nil {
		return nil, "", err
	}
	defer func() {
		_ = admin.Close()
		_ = client.Close()
	}()
	command := strings.ToLower(strings.TrimSpace(task.Params["command"]))
	switch command {
	case "topic-list":
		return collectTopicList(admin, task)
	case "topic-describe":
		return collectTopicDescribe(admin, client, task)
	case "topic-offset":
		return collectTopicOffset(admin, client, task)
	case "consumer-detail":
		return collectConsumerDetail(admin, client, task)
	default:
		return nil, "", fmt.Errorf("unsupported kafka client command: %s", command)
	}
}

func buildAdmin(task model.MetricsTask) (sarama.ClusterAdmin, sarama.Client, error) {
	host := strings.TrimSpace(task.Params["host"])
	port := strings.TrimSpace(task.Params["port"])
	if host == "" || port == "" {
		return nil, nil, fmt.Errorf("missing kafka host or port")
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	cfg := sarama.NewConfig()
	cfg.Net.DialTimeout = timeout
	cfg.Net.ReadTimeout = timeout
	cfg.Net.WriteTimeout = timeout
	cfg.Admin.Timeout = timeout
	cfg.Version = sarama.V2_8_0_0
	broker := net.JoinHostPort(host, port)
	client, err := sarama.NewClient([]string{broker}, cfg)
	if err != nil {
		return nil, nil, err
	}
	admin, err := sarama.NewClusterAdminFromClient(client)
	if err != nil {
		_ = client.Close()
		return nil, nil, err
	}
	return admin, client, nil
}

func collectTopicList(admin sarama.ClusterAdmin, task model.MetricsTask) (map[string]string, string, error) {
	topics, err := admin.ListTopics()
	if err != nil {
		return nil, "", err
	}
	names := make([]string, 0, len(topics))
	for name := range topics {
		if skipInternalTopic(name, task) {
			continue
		}
		names = append(names, name)
	}
	sort.Strings(names)
	rows := make([]map[string]string, 0, len(names))
	for _, name := range names {
		rows = append(rows, map[string]string{"TopicName": name})
	}
	return flattenRows(rows), "ok", nil
}

func collectTopicDescribe(admin sarama.ClusterAdmin, client sarama.Client, task model.MetricsTask) (map[string]string, string, error) {
	topics, err := admin.ListTopics()
	if err != nil {
		return nil, "", err
	}
	names := make([]string, 0, len(topics))
	for name := range topics {
		if skipInternalTopic(name, task) {
			continue
		}
		names = append(names, name)
	}
	sort.Strings(names)
	meta, err := admin.DescribeTopics(names)
	if err != nil {
		return nil, "", err
	}
	rows := make([]map[string]string, 0, len(meta))
	for _, topic := range meta {
		if topic == nil {
			continue
		}
		for _, partition := range topic.Partitions {
			if partition == nil {
				continue
			}
			leader, err := client.Leader(topic.Name, partition.ID)
			if err != nil {
				return nil, "", err
			}
			replicas := make([]string, 0, len(partition.Replicas))
			for _, broker := range partition.Replicas {
				replicas = append(replicas, fmt.Sprintf("%d", broker))
			}
			rows = append(rows, map[string]string{
				"TopicName":             topic.Name,
				"PartitionNum":          strconv.Itoa(len(topic.Partitions)),
				"PartitionLeader":       strconv.Itoa(int(partition.ID)),
				"BrokerHost":            leader.Addr(),
				"BrokerPort":            brokerPort(leader.Addr()),
				"ReplicationFactorSize": strconv.Itoa(len(partition.Replicas)),
				"ReplicationFactor":     "[" + strings.Join(replicas, ",") + "]",
			})
		}
	}
	return flattenRows(rows), "ok", nil
}

func collectTopicOffset(admin sarama.ClusterAdmin, client sarama.Client, task model.MetricsTask) (map[string]string, string, error) {
	topics, err := admin.ListTopics()
	if err != nil {
		return nil, "", err
	}
	names := make([]string, 0, len(topics))
	for name := range topics {
		if skipInternalTopic(name, task) {
			continue
		}
		names = append(names, name)
	}
	sort.Strings(names)
	rows := make([]map[string]string, 0, len(names))
	for _, topic := range names {
		partitions, err := client.Partitions(topic)
		if err != nil {
			return nil, "", err
		}
		for _, partition := range partitions {
			earliest, err := client.GetOffset(topic, partition, sarama.OffsetOldest)
			if err != nil {
				return nil, "", err
			}
			latest, err := client.GetOffset(topic, partition, sarama.OffsetNewest)
			if err != nil {
				return nil, "", err
			}
			rows = append(rows, map[string]string{
				"TopicName":    topic,
				"PartitionNum": strconv.Itoa(int(partition)),
				"earliest":     strconv.FormatInt(earliest, 10),
				"latest":       strconv.FormatInt(latest, 10),
			})
		}
	}
	return flattenRows(rows), "ok", nil
}

func collectConsumerDetail(admin sarama.ClusterAdmin, client sarama.Client, task model.MetricsTask) (map[string]string, string, error) {
	groups, err := admin.ListConsumerGroups()
	if err != nil {
		return nil, "", err
	}
	groupIDs := make([]string, 0, len(groups))
	for groupID := range groups {
		groupIDs = append(groupIDs, groupID)
	}
	sort.Strings(groupIDs)
	desc, err := admin.DescribeConsumerGroups(groupIDs)
	if err != nil {
		return nil, "", err
	}
	rows := make([]map[string]string, 0, len(desc))
	for _, group := range desc {
		if group == nil {
			continue
		}
		offsets, err := admin.ListConsumerGroupOffsets(group.GroupId, nil)
		if err != nil {
			return nil, "", err
		}
		topics := sortedOffsetTopics(offsets)
		for _, topic := range topics {
			partitions := offsets.Blocks[topic]
			partitionOffsets := make([]string, 0, len(partitions))
			var totalLag int64
			partIDs := sortedPartitionKeys(partitions)
			for _, partition := range partIDs {
				block := partitions[partition]
				if block == nil {
					continue
				}
				latest, err := client.GetOffset(topic, partition, sarama.OffsetNewest)
				if err != nil {
					return nil, "", err
				}
				if block.Offset >= 0 {
					totalLag += latest - block.Offset
				}
				partitionOffsets = append(partitionOffsets, strconv.FormatInt(block.Offset, 10))
			}
			rows = append(rows, map[string]string{
				"GroupId":                 group.GroupId,
				"group_member_num":        strconv.Itoa(len(group.Members)),
				"Topic":                   topic,
				"offset_of_each_partition": "[" + strings.Join(partitionOffsets, ",") + "]",
				"Lag":                     strconv.FormatInt(totalLag, 10),
			})
		}
	}
	return flattenRows(rows), "ok", nil
}

func skipInternalTopic(topic string, task model.MetricsTask) bool {
	monitorInternal := strings.EqualFold(strings.TrimSpace(task.Params["monitorInternalTopic"]), "true")
	if monitorInternal {
		return false
	}
	return strings.HasPrefix(topic, "__")
}

func flattenRows(rows []map[string]string) map[string]string {
	out := map[string]string{}
	for idx, row := range rows {
		rowNo := idx + 1
		for key, value := range row {
			if rowNo == 1 {
				out[key] = value
			}
			out[fmt.Sprintf("row%d_%s", rowNo, key)] = value
		}
	}
	return out
}

func brokerPort(addr string) string {
	_, port, err := net.SplitHostPort(addr)
	if err != nil {
		return ""
	}
	return port
}

func sortedOffsetTopics(resp *sarama.OffsetFetchResponse) []string {
	if resp == nil || len(resp.Blocks) == 0 {
		return nil
	}
	out := make([]string, 0, len(resp.Blocks))
	for topic := range resp.Blocks {
		out = append(out, topic)
	}
	sort.Strings(out)
	return out
}

func sortedPartitionKeys(items map[int32]*sarama.OffsetFetchResponseBlock) []int32 {
	out := make([]int32, 0, len(items))
	for partition := range items {
		out = append(out, partition)
	}
	sort.Slice(out, func(i, j int) bool { return out[i] < out[j] })
	return out
}

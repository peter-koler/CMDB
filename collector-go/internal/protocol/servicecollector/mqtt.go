package servicecollector

import (
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"strings"
	"time"

	"collector-go/internal/model"
)

type MQTTCollector struct{}

func (c *MQTTCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "host", "mqtt.host")
	port := parsePort(params, "1883", "port", "mqtt.port")
	protocolName := strings.ToUpper(firstNonEmpty(params, "protocol", "mqtt.protocol"))
	if protocolName == "" {
		protocolName = "MQTT"
	}
	timeout := timeoutFrom(params, task.Timeout, "timeout", "mqtt.timeout")
	clientID := firstNonEmpty(params, "clientId", "mqtt.clientId")
	if clientID == "" {
		clientID = "hertzbeat-mqtt-client"
	}
	username := firstNonEmpty(params, "username", "mqtt.username")
	password := firstNonEmpty(params, "password", "mqtt.password")
	topic := firstNonEmpty(params, "topic", "mqtt.topic")
	if topic == "" {
		topic = "hertzbeat/test"
	}
	testMessage := firstNonEmpty(params, "testMessage", "mqtt.testMessage")
	if testMessage == "" {
		testMessage = "hertzbeat-check"
	}
	keepalive := 30
	if raw := firstNonEmpty(params, "keepalive", "mqtt.keepalive"); raw != "" {
		if v, err := time.ParseDuration(raw + "s"); err == nil && v > 0 {
			keepalive = int(v.Seconds())
		}
	}

	conn, latency, err := dialMQTT(ctx, host, port, timeout, protocolName == "MQTTS")
	if err != nil {
		return nil, "mqtt dial failed", err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	if _, err := conn.Write(mqttConnectPacket(clientID, username, password, keepalive)); err != nil {
		return nil, "mqtt connect packet failed", err
	}
	head, body, err := readMQTTPacket(conn)
	if err != nil || (head>>4) != 2 || len(body) < 2 || body[1] != 0 {
		if err == nil {
			err = fmt.Errorf("mqtt connack not accepted")
		}
		return nil, "mqtt connack failed", err
	}

	canSub := false
	canPub := false
	canRecv := false
	canUnSub := false

	if _, err := conn.Write(mqttSubscribePacket(1, topic)); err == nil {
		head, body, err = readMQTTPacket(conn)
		if err == nil && (head>>4) == 9 && len(body) >= 3 {
			canSub = true
		}
	}
	if _, err := conn.Write(mqttPublishPacket(topic, testMessage)); err == nil {
		canPub = true
	}
	deadline := time.Now().Add(timeout / 2)
	for time.Now().Before(deadline) {
		head, body, err = readMQTTPacket(conn)
		if err != nil {
			break
		}
		if (head>>4) == 3 && len(body) > 2 {
			canRecv = true
			break
		}
	}
	if _, err := conn.Write(mqttUnsubscribePacket(2, topic)); err == nil {
		head, _, err = readMQTTPacket(conn)
		if err == nil && (head>>4) == 11 {
			canUnSub = true
		}
	}

	return map[string]string{
		"responseTime":   fmt.Sprintf("%d", latency.Milliseconds()),
		"canSubscribe":   fmt.Sprintf("%t", canSub),
		"canPublish":     fmt.Sprintf("%t", canPub),
		"canReceive":     fmt.Sprintf("%t", canRecv),
		"canUnSubscribe": fmt.Sprintf("%t", canUnSub),
	}, "ok", nil
}

func dialMQTT(ctx context.Context, host, port string, timeout time.Duration, tlsOn bool) (net.Conn, time.Duration, error) {
	address := net.JoinHostPort(host, port)
	start := time.Now()
	if tlsOn {
		dialer := &net.Dialer{Timeout: timeout}
		conn, err := tls.DialWithDialer(dialer, "tcp", address, &tls.Config{ServerName: host, InsecureSkipVerify: true})
		if err != nil {
			return nil, 0, err
		}
		return conn, time.Since(start), nil
	}
	conn, err := (&net.Dialer{Timeout: timeout}).DialContext(ctx, "tcp", address)
	if err != nil {
		return nil, 0, err
	}
	return conn, time.Since(start), nil
}

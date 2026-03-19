package jmxcollector

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"
	"time"

	"collector-go/internal/model"
)

type taskConfig struct {
	Endpoint   string
	ObjectName string
	Username   string
	Password   string
	Timeout    time.Duration
}

func parseTaskConfig(task model.MetricsTask) (taskConfig, error) {
	params := task.Params
	host := strings.TrimSpace(params["host"])
	port := strings.TrimSpace(params["port"])
	rawURL := strings.TrimSpace(params["url"])
	objectName := strings.TrimSpace(params["objectName"])
	if objectName == "" {
		objectName = strings.TrimSpace(params["object_name"])
	}
	if objectName == "" {
		return taskConfig{}, fmt.Errorf("missing objectName")
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	if raw := strings.TrimSpace(params["timeout"]); raw != "" {
		if ms, err := strconv.Atoi(raw); err == nil && ms > 0 {
			timeout = time.Duration(ms) * time.Millisecond
		}
	}
	endpoint, err := resolveEndpoint(rawURL, host, port)
	if err != nil {
		return taskConfig{}, err
	}
	return taskConfig{
		Endpoint:   endpoint,
		ObjectName: objectName,
		Username:   strings.TrimSpace(params["username"]),
		Password:   strings.TrimSpace(params["password"]),
		Timeout:    timeout,
	}, nil
}

func resolveEndpoint(rawURL, host, port string) (string, error) {
	if strings.HasPrefix(rawURL, "http://") || strings.HasPrefix(rawURL, "https://") {
		return rawURL, nil
	}
	if strings.HasPrefix(strings.ToLower(rawURL), "service:jmx:rmi://") {
		h, p := parseHostPortFromServiceURL(rawURL)
		if h != "" {
			host = h
		}
		if p != "" {
			port = p
		}
		rawURL = "/jmx"
	}
	if host == "" {
		return "", fmt.Errorf("missing host")
	}
	if port == "" {
		port = "8080"
	}
	path := strings.TrimSpace(rawURL)
	if path == "" {
		path = "/jmx"
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	return "http://" + host + ":" + port + path, nil
}

func parseHostPortFromServiceURL(raw string) (string, string) {
	prefix := "service:jmx:rmi:///jndi/rmi://"
	if !strings.HasPrefix(strings.ToLower(raw), prefix) {
		return "", ""
	}
	rest := raw[len(prefix):]
	end := strings.Index(rest, "/")
	if end > 0 {
		rest = rest[:end]
	}
	u, err := url.Parse("tcp://" + rest)
	if err != nil {
		return "", ""
	}
	return strings.TrimSpace(u.Hostname()), strings.TrimSpace(u.Port())
}

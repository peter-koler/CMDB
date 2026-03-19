package sshcollector

import (
	"fmt"
	"strings"
	"time"

	"collector-go/internal/model"
)

type options struct {
	Host                      string
	Port                      string
	Username                  string
	Password                  string
	PrivateKey                string
	PrivateKeyPath            string
	PrivateKeyPassphrase      string
	KnownHostsPath            string
	StrictHostKeyChecking     bool
	HostKeyFingerprint        string
	ReuseConnection           bool
	UseProxy                  bool
	ProxyHost                 string
	ProxyPort                 string
	ProxyUsername             string
	ProxyPassword             string
	ProxyPrivateKey           string
	ProxyPrivateKeyPath       string
	ProxyPrivateKeyPassphrase string
	Script                    string
	ParseType                 string
	Timeout                   time.Duration
}

func parseOptions(task model.MetricsTask) (options, error) {
	host := firstNonEmpty(task.Params["host"], task.Params["ssh.host"])
	if strings.TrimSpace(host) == "" {
		return options{}, fmt.Errorf("missing ssh host")
	}
	port := firstNonEmpty(task.Params["port"], task.Params["ssh.port"])
	if strings.TrimSpace(port) == "" {
		port = "22"
	}
	username := firstNonEmpty(task.Params["username"], task.Params["ssh.username"])
	if strings.TrimSpace(username) == "" {
		return options{}, fmt.Errorf("missing ssh username")
	}
	script := firstNonEmpty(task.Params["script"], task.Params["ssh.script"])
	if strings.TrimSpace(script) == "" {
		return options{}, fmt.Errorf("missing ssh script")
	}
	parseType := strings.TrimSpace(strings.ToLower(firstNonEmpty(task.Params["parseType"], task.Params["ssh.parseType"])))
	if parseType == "" {
		parseType = "multirow"
	}
	timeout := task.Timeout
	if timeout <= 0 {
		timeout = 6 * time.Second
	}
	useProxy := parseBool(firstNonEmpty(task.Params["useProxy"], task.Params["ssh.useProxy"]), false)
	proxyHost := firstNonEmpty(task.Params["proxyHost"], task.Params["ssh.proxyHost"])
	proxyPort := firstNonEmpty(task.Params["proxyPort"], task.Params["ssh.proxyPort"])
	if strings.TrimSpace(proxyPort) == "" {
		proxyPort = "22"
	}
	return options{
		Host:                      strings.TrimSpace(host),
		Port:                      strings.TrimSpace(port),
		Username:                  strings.TrimSpace(username),
		Password:                  strings.TrimSpace(firstNonEmpty(task.Params["password"], task.Params["ssh.password"])),
		PrivateKey:                firstNonEmpty(task.Params["privateKey"], task.Params["ssh.privateKey"]),
		PrivateKeyPath:            firstNonEmpty(task.Params["privateKeyPath"], task.Params["ssh.privateKeyPath"]),
		PrivateKeyPassphrase:      firstNonEmpty(task.Params["privateKeyPassphrase"], task.Params["ssh.privateKeyPassphrase"]),
		KnownHostsPath:            firstNonEmpty(task.Params["knownHostsPath"], task.Params["ssh.knownHostsPath"]),
		StrictHostKeyChecking:     parseBool(firstNonEmpty(task.Params["strictHostKeyChecking"], task.Params["ssh.strictHostKeyChecking"]), false),
		HostKeyFingerprint:        strings.TrimSpace(firstNonEmpty(task.Params["hostKeyFingerprint"], task.Params["ssh.hostKeyFingerprint"])),
		ReuseConnection:           parseBool(firstNonEmpty(task.Params["reuseConnection"], task.Params["ssh.reuseConnection"]), true),
		UseProxy:                  useProxy,
		ProxyHost:                 strings.TrimSpace(proxyHost),
		ProxyPort:                 strings.TrimSpace(proxyPort),
		ProxyUsername:             strings.TrimSpace(firstNonEmpty(task.Params["proxyUsername"], task.Params["ssh.proxyUsername"])),
		ProxyPassword:             strings.TrimSpace(firstNonEmpty(task.Params["proxyPassword"], task.Params["ssh.proxyPassword"])),
		ProxyPrivateKey:           firstNonEmpty(task.Params["proxyPrivateKey"], task.Params["ssh.proxyPrivateKey"]),
		ProxyPrivateKeyPath:       firstNonEmpty(task.Params["proxyPrivateKeyPath"], task.Params["ssh.proxyPrivateKeyPath"]),
		ProxyPrivateKeyPassphrase: firstNonEmpty(task.Params["proxyPrivateKeyPassphrase"], task.Params["ssh.proxyPrivateKeyPassphrase"]),
		Script:                    script,
		ParseType:                 parseType,
		Timeout:                   timeout,
	}, nil
}

func (o options) targetAddress() string {
	return o.Host + ":" + o.Port
}

func (o options) proxyAddress() string {
	return o.ProxyHost + ":" + o.ProxyPort
}

func (o options) poolKey() string {
	return strings.Join([]string{
		o.Username, "@", o.Host, ":", o.Port,
		"|proxy=", fmt.Sprintf("%t", o.UseProxy), "|", o.ProxyUsername, "@", o.ProxyHost, ":", o.ProxyPort,
		"|strict=", fmt.Sprintf("%t", o.StrictHostKeyChecking),
	}, "")
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func parseBool(raw string, def bool) bool {
	v := strings.TrimSpace(strings.ToLower(raw))
	if v == "" {
		return def
	}
	switch v {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return def
	}
}

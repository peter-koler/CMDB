package sshcollector

import (
	"fmt"
	"net"
	"os"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
	"golang.org/x/crypto/ssh/agent"
	"golang.org/x/crypto/ssh/knownhosts"
)

func buildSSHConfig(opts options, asProxy bool) (*ssh.ClientConfig, error) {
	username := opts.Username
	password := opts.Password
	privateKey := opts.PrivateKey
	privateKeyPath := opts.PrivateKeyPath
	privateKeyPassphrase := opts.PrivateKeyPassphrase
	if asProxy {
		username = opts.ProxyUsername
		password = opts.ProxyPassword
		privateKey = opts.ProxyPrivateKey
		privateKeyPath = opts.ProxyPrivateKeyPath
		privateKeyPassphrase = opts.ProxyPrivateKeyPassphrase
	}
	methods, err := authMethods(password, privateKey, privateKeyPath, privateKeyPassphrase)
	if err != nil {
		return nil, err
	}
	if len(methods) == 0 {
		return nil, fmt.Errorf("ssh auth method missing")
	}

	cb, err := hostKeyCallback(opts)
	if err != nil {
		return nil, err
	}

	return &ssh.ClientConfig{
		User:            username,
		Auth:            methods,
		HostKeyCallback: cb,
		Timeout:         opts.Timeout,
	}, nil
}

func authMethods(password, privateKey, privateKeyPath, passphrase string) ([]ssh.AuthMethod, error) {
	methods := make([]ssh.AuthMethod, 0, 3)
	if strings.TrimSpace(password) != "" {
		methods = append(methods, ssh.Password(password))
	}
	signer, err := privateKeySigner(privateKey, privateKeyPath, passphrase)
	if err != nil {
		return nil, err
	}
	if signer != nil {
		methods = append(methods, ssh.PublicKeys(signer))
	}
	if sock := strings.TrimSpace(os.Getenv("SSH_AUTH_SOCK")); sock != "" {
		conn, dialErr := net.DialTimeout("unix", sock, 2*time.Second)
		if dialErr == nil {
			agentClient := agent.NewClient(conn)
			methods = append(methods, ssh.PublicKeysCallback(agentClient.Signers))
		}
	}
	return methods, nil
}

func privateKeySigner(privateKey, privateKeyPath, passphrase string) (ssh.Signer, error) {
	keyData := strings.TrimSpace(privateKey)
	if keyData == "" && strings.TrimSpace(privateKeyPath) != "" {
		raw, err := os.ReadFile(strings.TrimSpace(privateKeyPath))
		if err != nil {
			return nil, fmt.Errorf("read private key failed: %w", err)
		}
		keyData = string(raw)
	}
	if keyData == "" {
		return nil, nil
	}
	if strings.TrimSpace(passphrase) != "" {
		signer, err := ssh.ParsePrivateKeyWithPassphrase([]byte(keyData), []byte(passphrase))
		if err != nil {
			return nil, fmt.Errorf("parse private key with passphrase failed: %w", err)
		}
		return signer, nil
	}
	signer, err := ssh.ParsePrivateKey([]byte(keyData))
	if err != nil {
		return nil, fmt.Errorf("parse private key failed: %w", err)
	}
	return signer, nil
}

func hostKeyCallback(opts options) (ssh.HostKeyCallback, error) {
	if strings.TrimSpace(opts.HostKeyFingerprint) != "" {
		expected := normalizeFingerprint(opts.HostKeyFingerprint)
		return func(hostname string, remote net.Addr, key ssh.PublicKey) error {
			if normalizeFingerprint(ssh.FingerprintSHA256(key)) != expected {
				return fmt.Errorf("ssh host key fingerprint mismatch for %s", hostname)
			}
			return nil
		}, nil
	}
	if !opts.StrictHostKeyChecking {
		return ssh.InsecureIgnoreHostKey(), nil
	}
	paths := knownHostsPaths(opts.KnownHostsPath)
	cb, err := knownhosts.New(paths...)
	if err != nil {
		return nil, fmt.Errorf("known_hosts init failed: %w", err)
	}
	return cb, nil
}

func knownHostsPaths(explicit string) []string {
	path := strings.TrimSpace(explicit)
	if path != "" {
		return []string{path}
	}
	home, _ := os.UserHomeDir()
	if home == "" {
		return []string{".ssh/known_hosts"}
	}
	return []string{
		home + "/.ssh/known_hosts",
		home + "/.ssh/known_hosts2",
		"/etc/ssh/ssh_known_hosts",
	}
}

func normalizeFingerprint(raw string) string {
	return strings.TrimSpace(strings.ToLower(raw))
}

package notify

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/smtp"
	"strings"
	"time"
)

type ChannelType string

const (
	ChannelWebhook ChannelType = "webhook"
	ChannelEmail   ChannelType = "email"
	ChannelWeCom   ChannelType = "wecom"
	ChannelSystem  ChannelType = "system"
)

type TestSendRequest struct {
	Channel  ChannelType     `json:"channel"`
	Title    string          `json:"title"`
	Template string          `json:"template"`
	Data     map[string]any  `json:"data"`
	Config   json.RawMessage `json:"config"`
}

type WebhookConfig struct {
	URL    string            `json:"url"`
	Method string            `json:"method"`
	Header map[string]string `json:"header"`
}

type EmailConfig struct {
	Host     string `json:"host"`
	Port     int    `json:"port"`
	Username string `json:"username"`
	Password string `json:"password"`
	From     string `json:"from"`
	To       string `json:"to"`
}

type WeComConfig struct {
	WebhookURL string `json:"webhook_url"`
}

type HTTPDoer interface {
	Do(req *http.Request) (*http.Response, error)
}

type Service struct {
	httpClient HTTPDoer
	smtpSend   func(addr string, a smtp.Auth, from string, to []string, msg []byte) error
}

func NewService() *Service {
	return &Service{
		httpClient: &http.Client{Timeout: 5 * time.Second},
		smtpSend:   smtp.SendMail,
	}
}

func (s *Service) TestSend(ctx context.Context, req TestSendRequest) error {
	if req.Template == "" {
		return fmt.Errorf("template required")
	}
	body, err := Render(req.Template, req.Data)
	if err != nil {
		return err
	}
	switch req.Channel {
	case ChannelWebhook:
		return s.sendWebhook(ctx, body, req.Config)
	case ChannelEmail:
		return s.sendEmail(body, req.Config, req.Title)
	case ChannelWeCom:
		return s.sendWeCom(ctx, body, req.Config)
	case ChannelSystem:
		return fmt.Errorf("system channel should be handled by runtime store")
	default:
		return fmt.Errorf("unsupported channel: %s", req.Channel)
	}
}

func (s *Service) sendWebhook(ctx context.Context, body string, raw json.RawMessage) error {
	var cfg WebhookConfig
	if err := json.Unmarshal(raw, &cfg); err != nil {
		return err
	}
	if cfg.URL == "" {
		return fmt.Errorf("webhook url required")
	}
	method := strings.ToUpper(cfg.Method)
	if method == "" {
		method = http.MethodPost
	}
	req, err := http.NewRequestWithContext(ctx, method, cfg.URL, bytes.NewBufferString(body))
	if err != nil {
		return err
	}
	for k, v := range cfg.Header {
		req.Header.Set(k, v)
	}
	if req.Header.Get("Content-Type") == "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := s.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("webhook status=%d", resp.StatusCode)
	}
	return nil
}

func (s *Service) sendEmail(body string, raw json.RawMessage, title string) error {
	var cfg EmailConfig
	if err := json.Unmarshal(raw, &cfg); err != nil {
		return err
	}
	if cfg.Host == "" || cfg.Port <= 0 || cfg.From == "" || cfg.To == "" {
		return fmt.Errorf("email config invalid")
	}
	addr := fmt.Sprintf("%s:%d", cfg.Host, cfg.Port)
	var auth smtp.Auth
	if cfg.Username != "" {
		auth = smtp.PlainAuth("", cfg.Username, cfg.Password, cfg.Host)
	}
	toList := []string{}
	for _, part := range strings.Split(cfg.To, ",") {
		email := strings.TrimSpace(part)
		if email != "" {
			toList = append(toList, email)
		}
	}
	if len(toList) == 0 {
		return fmt.Errorf("email recipients empty")
	}
	msg := "To: " + cfg.To + "\r\n" +
		"Subject: " + title + "\r\n" +
		"Content-Type: text/plain; charset=UTF-8\r\n\r\n" +
		body + "\r\n"
	return s.smtpSend(addr, auth, cfg.From, toList, []byte(msg))
}

func (s *Service) sendWeCom(ctx context.Context, body string, raw json.RawMessage) error {
	var cfg WeComConfig
	if err := json.Unmarshal(raw, &cfg); err != nil {
		return err
	}
	if cfg.WebhookURL == "" {
		return fmt.Errorf("wecom webhook_url required")
	}
	payload := map[string]any{
		"msgtype": "markdown",
		"markdown": map[string]any{
			"content": body,
		},
	}
	b, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, cfg.WebhookURL, bytes.NewBuffer(b))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := s.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("wecom status=%d", resp.StatusCode)
	}
	return nil
}

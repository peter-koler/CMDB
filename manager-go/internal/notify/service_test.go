package notify

import (
	"context"
	"io"
	"net/http"
	"net/smtp"
	"strings"
	"testing"
)

type rtFunc func(*http.Request) (*http.Response, error)

func (f rtFunc) Do(req *http.Request) (*http.Response, error) { return f(req) }

func TestTemplateRender(t *testing.T) {
	out, err := Render("告警: {{.AlertName}} 值={{.MetricValue}}", map[string]any{
		"AlertName":   "CPU High",
		"MetricValue": 88.3,
	})
	if err != nil {
		t.Fatalf("render failed: %v", err)
	}
	if !strings.Contains(out, "CPU High") || !strings.Contains(out, "88.3") {
		t.Fatalf("render output unexpected: %s", out)
	}
}

func TestWebhookAndWeComSend(t *testing.T) {
	s := NewService()
	s.httpClient = rtFunc(func(req *http.Request) (*http.Response, error) {
		return &http.Response{
			StatusCode: http.StatusOK,
			Body:       io.NopCloser(strings.NewReader("ok")),
			Header:     make(http.Header),
		}, nil
	})
	reqWebhook := TestSendRequest{
		Channel:  ChannelWebhook,
		Title:    "t1",
		Template: `{"msg":"{{.Message}}"}`,
		Data:     map[string]any{"Message": "hello"},
		Config:   []byte(`{"url":"http://example.test/hook","method":"POST"}`),
	}
	if err := s.TestSend(context.Background(), reqWebhook); err != nil {
		t.Fatalf("webhook send failed: %v", err)
	}
	reqWeCom := TestSendRequest{
		Channel:  ChannelWeCom,
		Title:    "t2",
		Template: `{{.Message}}`,
		Data:     map[string]any{"Message": "critical"},
		Config:   []byte(`{"webhook_url":"http://example.test/wecom"}`),
	}
	if err := s.TestSend(context.Background(), reqWeCom); err != nil {
		t.Fatalf("wecom send failed: %v", err)
	}
}

func TestEmailSend(t *testing.T) {
	s := NewService()
	called := false
	s.smtpSend = func(addr string, _ smtp.Auth, from string, to []string, msg []byte) error {
		called = true
		if addr != "smtp.example.com:25" || from != "a@example.com" || len(to) != 1 || to[0] != "b@example.com" {
			t.Fatalf("smtp args invalid addr=%s from=%s to=%v", addr, from, to)
		}
		if !strings.Contains(string(msg), "Subject: test") {
			t.Fatalf("email subject missing: %s", string(msg))
		}
		return nil
	}
	req := TestSendRequest{
		Channel:  ChannelEmail,
		Title:    "test",
		Template: `hello {{.Name}}`,
		Data:     map[string]any{"Name": "ops"},
		Config: []byte(`{
			"host":"smtp.example.com",
			"port":25,
			"from":"a@example.com",
			"to":"b@example.com"
		}`),
	}
	if err := s.TestSend(context.Background(), req); err != nil {
		t.Fatalf("email send failed: %v", err)
	}
	if !called {
		t.Fatal("smtpSend not called")
	}
}

package httpcollector

import (
	"fmt"
	"net/url"
	"strings"

	"collector-go/internal/model"
)

type requestSpec struct {
	URL            string
	Method         string
	Body           string
	Headers        map[string]string
	BasicAuthUser  string
	BasicAuthPass  string
	DigestAuthUser string
	DigestAuthPass string
}

func buildRequestSpec(task model.MetricsTask) (requestSpec, error) {
	params := task.Params
	rawURL := strings.TrimSpace(firstNonEmpty(params["url"], params["http.url"]))
	if rawURL == "" {
		return requestSpec{}, fmt.Errorf("missing url")
	}
	fullURL, err := normalizeURL(params, rawURL)
	if err != nil {
		return requestSpec{}, err
	}
	method := strings.ToUpper(strings.TrimSpace(firstNonEmpty(params["method"], params["http.method"])))
	if method == "" {
		method = "GET"
	}
	headers := map[string]string{}
	if accept := strings.TrimSpace(firstNonEmpty(params["headers.Accept"], params["http.headers.Accept"])); accept != "" {
		headers["Accept"] = accept
	}
	if contentType := strings.TrimSpace(firstNonEmpty(params["headers.Content-Type"], params["http.headers.Content-Type"])); contentType != "" {
		headers["Content-Type"] = contentType
	}
	return requestSpec{
		URL:            fullURL,
		Method:         method,
		Body:           strings.TrimSpace(firstNonEmpty(params["body"], params["http.body"])),
		Headers:        headers,
		BasicAuthUser:  strings.TrimSpace(firstNonEmpty(params["authorization.basicAuthUsername"], params["http.authorization.basicAuthUsername"], params["username"])),
		BasicAuthPass:  strings.TrimSpace(firstNonEmpty(params["authorization.basicAuthPassword"], params["http.authorization.basicAuthPassword"], params["password"])),
		DigestAuthUser: strings.TrimSpace(firstNonEmpty(params["authorization.digestAuthUsername"], params["http.authorization.digestAuthUsername"])),
		DigestAuthPass: strings.TrimSpace(firstNonEmpty(params["authorization.digestAuthPassword"], params["http.authorization.digestAuthPassword"])),
	}, nil
}

func normalizeURL(params map[string]string, raw string) (string, error) {
	if strings.Contains(raw, "://") {
		if _, err := url.Parse(raw); err != nil {
			return "", err
		}
		return raw, nil
	}
	host := strings.TrimSpace(firstNonEmpty(params["host"], params["http.host"]))
	if host == "" {
		return "", fmt.Errorf("missing host")
	}
	port := strings.TrimSpace(firstNonEmpty(params["port"], params["http.port"]))
	scheme := "http"
	if isTruthy(firstNonEmpty(params["ssl"], params["http.ssl"])) {
		scheme = "https"
	}
	base := scheme + "://" + host
	if port != "" {
		base += ":" + port
	}
	if !strings.HasPrefix(raw, "/") {
		raw = "/" + raw
	}
	return base + raw, nil
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func isTruthy(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}

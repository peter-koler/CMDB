package httpcollector

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"time"
)

func executeRequest(client *http.Client, req *http.Request, spec requestSpec) (*http.Response, error) {
	if spec.DigestAuthUser == "" {
		return client.Do(req)
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusUnauthorized {
		return resp, nil
	}
	_ = resp.Body.Close()
	authHeader := strings.TrimSpace(resp.Header.Get("WWW-Authenticate"))
	if !strings.HasPrefix(strings.ToLower(authHeader), "digest ") {
		return nil, fmt.Errorf("digest auth challenge not found")
	}
	digestParams := parseDigestAuthHeader(authHeader)
	if digestParams["nonce"] == "" || digestParams["realm"] == "" {
		return nil, fmt.Errorf("invalid digest auth challenge")
	}
	authValue, err := buildDigestAuthorization(req, spec, digestParams)
	if err != nil {
		return nil, err
	}
	req2, err := http.NewRequestWithContext(req.Context(), req.Method, req.URL.String(), strings.NewReader(spec.Body))
	if err != nil {
		return nil, err
	}
	for key, value := range req.Header {
		for _, one := range value {
			req2.Header.Add(key, one)
		}
	}
	req2.Header.Set("Authorization", authValue)
	return client.Do(req2)
}

func parseDigestAuthHeader(header string) map[string]string {
	out := map[string]string{}
	raw := strings.TrimSpace(header)
	if idx := strings.Index(raw, " "); idx > 0 {
		raw = raw[idx+1:]
	}
	for _, part := range splitDigestParts(raw) {
		kv := strings.SplitN(part, "=", 2)
		if len(kv) != 2 {
			continue
		}
		key := strings.TrimSpace(kv[0])
		value := strings.Trim(strings.TrimSpace(kv[1]), `"`)
		if key != "" {
			out[strings.ToLower(key)] = value
		}
	}
	return out
}

func splitDigestParts(raw string) []string {
	parts := make([]string, 0, 8)
	var cur strings.Builder
	inQuote := false
	for i := 0; i < len(raw); i++ {
		ch := raw[i]
		if ch == '"' {
			inQuote = !inQuote
		}
		if ch == ',' && !inQuote {
			parts = append(parts, strings.TrimSpace(cur.String()))
			cur.Reset()
			continue
		}
		cur.WriteByte(ch)
	}
	if cur.Len() > 0 {
		parts = append(parts, strings.TrimSpace(cur.String()))
	}
	return parts
}

func buildDigestAuthorization(req *http.Request, spec requestSpec, params map[string]string) (string, error) {
	realm := params["realm"]
	nonce := params["nonce"]
	qop := strings.ToLower(strings.TrimSpace(params["qop"]))
	if strings.Contains(qop, ",") {
		// Prefer auth
		opts := strings.Split(qop, ",")
		qop = strings.TrimSpace(opts[0])
		for _, item := range opts {
			if strings.TrimSpace(strings.ToLower(item)) == "auth" {
				qop = "auth"
				break
			}
		}
	}
	uri := req.URL.RequestURI()
	if uri == "" {
		uri = "/"
	}
	if _, err := url.Parse(uri); err != nil {
		return "", err
	}
	ha1 := md5Hex(fmt.Sprintf("%s:%s:%s", spec.DigestAuthUser, realm, spec.DigestAuthPass))
	ha2 := md5Hex(fmt.Sprintf("%s:%s", req.Method, uri))
	nc := "00000001"
	cnonce := randomCNonce()
	var response string
	if qop != "" {
		response = md5Hex(fmt.Sprintf("%s:%s:%s:%s:%s:%s", ha1, nonce, nc, cnonce, qop, ha2))
	} else {
		response = md5Hex(fmt.Sprintf("%s:%s:%s", ha1, nonce, ha2))
	}

	segments := []string{
		fmt.Sprintf(`Digest username="%s"`, spec.DigestAuthUser),
		fmt.Sprintf(`realm="%s"`, realm),
		fmt.Sprintf(`nonce="%s"`, nonce),
		fmt.Sprintf(`uri="%s"`, uri),
		fmt.Sprintf(`response="%s"`, response),
	}
	if opaque := strings.TrimSpace(params["opaque"]); opaque != "" {
		segments = append(segments, fmt.Sprintf(`opaque="%s"`, opaque))
	}
	if algorithm := strings.TrimSpace(params["algorithm"]); algorithm != "" {
		segments = append(segments, fmt.Sprintf(`algorithm=%s`, algorithm))
	}
	if qop != "" {
		segments = append(segments, fmt.Sprintf(`qop=%s`, qop))
		segments = append(segments, fmt.Sprintf(`nc=%s`, nc))
		segments = append(segments, fmt.Sprintf(`cnonce="%s"`, cnonce))
	}
	return strings.Join(segments, ", "), nil
}

func md5Hex(raw string) string {
	sum := md5.Sum([]byte(raw))
	return hex.EncodeToString(sum[:])
}

func randomCNonce() string {
	const letters = "abcdef0123456789"
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	out := make([]byte, 16)
	for i := range out {
		out[i] = letters[r.Intn(len(letters))]
	}
	return string(out)
}

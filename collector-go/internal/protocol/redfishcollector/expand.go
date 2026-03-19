package redfishcollector

import (
	"context"
	"net/http"
	"regexp"
	"strings"
)

var placeholderRe = regexp.MustCompile(`\{[^{}]+\}`)

func expandResourceURIs(ctx context.Context, client *http.Client, baseURL string, username string, password string, schema string) ([]string, error) {
	schema = strings.TrimSpace(schema)
	if schema == "" {
		return nil, nil
	}
	fragments := placeholderRe.Split(schema, -1)
	uris := []string{}
	for idx, frag := range fragments {
		if idx == 0 {
			uris = []string{frag}
		} else {
			expanded := make([]string, 0, len(uris))
			for _, one := range uris {
				expanded = append(expanded, one+frag)
			}
			uris = expanded
		}
		next := make([]string, 0, len(uris))
		for _, one := range uris {
			collection := normalizeCollectionURI(one)
			payload, err := getJSON(ctx, client, baseURL+collection, username, password)
			if err != nil {
				continue
			}
			items := readMembers(payload)
			if len(items) == 0 {
				next = append(next, collection)
				continue
			}
			next = append(next, items...)
		}
		uris = next
	}
	return uris, nil
}

func normalizeCollectionURI(uri string) string {
	uri = strings.TrimSpace(uri)
	if uri == "" {
		return "/"
	}
	if strings.HasSuffix(uri, "/") && uri != "/" {
		return strings.TrimSuffix(uri, "/")
	}
	return uri
}

func readMembers(payload map[string]any) []string {
	raw, ok := payload["Members"]
	if !ok {
		return nil
	}
	list, ok := raw.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(list))
	for _, one := range list {
		obj, ok := one.(map[string]any)
		if !ok {
			continue
		}
		if id, ok := obj["@odata.id"]; ok {
			if s := strings.TrimSpace(toString(id)); s != "" {
				out = append(out, s)
			}
		}
	}
	return out
}

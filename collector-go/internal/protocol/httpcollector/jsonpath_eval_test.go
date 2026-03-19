package httpcollector

import "testing"

func TestEvalJSONExpression_FilterAndWildcard(t *testing.T) {
	payload := map[string]any{
		"availableTags": []any{
			map[string]any{"tag": "state", "values": []any{"RUNNABLE", "WAITING"}},
			map[string]any{"tag": "other", "values": []any{"x"}},
		},
	}
	got, err := evalJSONExpression(payload, `$.availableTags[?(@.tag == "state")].values[*]`)
	if err != nil {
		t.Fatalf("eval failed: %v", err)
	}
	items, ok := got.([]any)
	if !ok || len(items) != 2 {
		t.Fatalf("unexpected result: %#v", got)
	}
}

func TestEvalJSONExpression_BracketKey(t *testing.T) {
	payload := map[string]any{
		"propertySources": []any{
			map[string]any{
				"name": "systemProperties",
				"properties": map[string]any{
					"os.name": map[string]any{"value": "Linux"},
				},
			},
		},
	}
	got, err := evalJSONExpression(payload, `$.propertySources[?(@.name=='systemProperties')].properties['os.name'].value`)
	if err != nil {
		t.Fatalf("eval failed: %v", err)
	}
	if firstJSONString(got) != "Linux" {
		t.Fatalf("want Linux got=%s", firstJSONString(got))
	}
}

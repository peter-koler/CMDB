package notify

import (
	"bytes"
	"text/template"
)

func Render(tpl string, data map[string]any) (string, error) {
	t, err := template.New("notify").Parse(tpl)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	if err := t.Execute(&buf, data); err != nil {
		return "", err
	}
	return buf.String(), nil
}

package jmxcollector

import (
	"testing"

	"collector-go/internal/model"
)

func TestCollectFromBeansAliasAndFieldSpecs(t *testing.T) {
	beans := []map[string]any{
		{
			"Name": "Code Cache",
			"Usage": map[string]any{
				"committed": 123,
				"used":      45,
			},
		},
	}
	task := model.MetricsTask{
		Params: map[string]string{
			"alias_fields": "Name,Usage->committed,Usage->used",
		},
		FieldSpecs: []model.FieldSpec{
			{Field: "name"},
			{Field: "committed"},
			{Field: "used"},
		},
	}
	fields := collectFromBeans(beans, task)
	if fields["committed"] != "123" {
		t.Fatalf("committed want=123 got=%s", fields["committed"])
	}
	if fields["used"] != "45" {
		t.Fatalf("used want=45 got=%s", fields["used"])
	}
	if fields["row1_committed"] != "123" {
		t.Fatalf("row1_committed want=123 got=%s", fields["row1_committed"])
	}
}

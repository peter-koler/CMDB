package template

import (
	"errors"
	"fmt"
	"net"
	"net/url"
	"regexp"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"

	"manager-go/internal/model"
	pb "manager-go/internal/pb/proto"
)

var redisInfoSections = map[string]struct{}{
	"server":       {},
	"clients":      {},
	"memory":       {},
	"persistence":  {},
	"stats":        {},
	"replication":  {},
	"cpu":          {},
	"commandstats": {},
	"cluster":      {},
	"errorstats":   {},
	"keyspace":     {},
}

var metricNameRegexp = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)

type CompileError struct {
	Path   string
	Reason string
}

func (e *CompileError) Error() string {
	if e == nil {
		return ""
	}
	if e.Path == "" {
		return e.Reason
	}
	return fmt.Sprintf("%s: %s", e.Path, e.Reason)
}

func AsCompileError(err error) (*CompileError, bool) {
	var ce *CompileError
	if errors.As(err, &ce) {
		return ce, true
	}
	return nil, false
}

func compileErr(path string, reason string) error {
	return &CompileError{Path: strings.TrimSpace(path), Reason: strings.TrimSpace(reason)}
}

func CompileMetricsTasks(rt RuntimeTemplate, monitor *model.Monitor) ([]*pb.MetricsTask, error) {
	root, err := parseTemplateRoot(rt)
	if err != nil {
		return nil, err
	}
	metricsRaw := asSlice(root["metrics"])
	if len(metricsRaw) == 0 {
		return nil, compileErr("metrics", "template metrics is empty")
	}

	effective := buildEffectiveParams(root, monitor)
	tasks := make([]*pb.MetricsTask, 0, len(metricsRaw))
	for idx, item := range metricsRaw {
		mm := asMap(item)
		if len(mm) == 0 {
			return nil, compileErr(fmt.Sprintf("metrics[%d]", idx), "metric item must be object")
		}
		task, err := compileOneMetricTask(mm, effective, idx)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	if len(tasks) == 0 {
		return nil, compileErr("metrics", "no valid metric task compiled")
	}
	optimizeMySQLJDBCSQL(tasks)
	return tasks, nil
}

func FilterPersistableParams(rt RuntimeTemplate, params map[string]string) map[string]string {
	cloned := cloneMapString(params)
	if len(cloned) == 0 {
		return cloned
	}
	root, err := parseTemplateRoot(rt)
	if err != nil {
		return cloned
	}
	nonPersistable := collectNonPersistableFields(root)
	if len(nonPersistable) == 0 {
		return cloned
	}
	for field := range nonPersistable {
		delete(cloned, field)
	}
	if len(cloned) == 0 {
		return nil
	}
	return cloned
}

func compileOneMetricTask(metric map[string]any, effective map[string]string, metricIdx int) (*pb.MetricsTask, error) {
	metricPath := fmt.Sprintf("metrics[%d]", metricIdx)
	name := strings.TrimSpace(asString(metric["name"]))
	if name == "" {
		return nil, compileErr(metricPath+".name", "is required")
	}
	protocol := strings.TrimSpace(strings.ToLower(asString(metric["protocol"])))
	if protocol == "" {
		return nil, compileErr(metricPath+".protocol", "is required")
	}
	params := cloneMapString(effective)
	protocolCfg := asMap(metric[protocol])
	if len(protocolCfg) == 0 {
		return nil, compileErr(metricPath+"."+protocol, "protocol config is required")
	}
	flattenWithReplace(params, "", protocolCfg, effective)

	if protocol == "redis" {
		if _, ok := params["section"]; !ok {
			metricName := strings.ToLower(strings.TrimSpace(name))
			if _, matched := redisInfoSections[metricName]; matched {
				params["section"] = metricName
			}
		}
	}

	timeout := readInt(params["timeout"], 5000)
	fieldSpecs, knownFields, err := compileFieldSpecs(asSlice(metric["fields"]), metricIdx)
	if err != nil {
		return nil, err
	}
	calcSpecs, err := compileCalculateSpecs(asSlice(metric["calculates"]), metricIdx, knownFields)
	if err != nil {
		return nil, err
	}
	aliasFields := compileAliasFields(asSlice(metric["aliasFields"]))
	if len(aliasFields) > 0 {
		params["alias_fields"] = strings.Join(aliasFields, ",")
	}
	unitTransforms := compileUnitTransforms(asSlice(metric["units"]))
	priority := int32(readIntAny(metric["priority"], 0))

	return &pb.MetricsTask{
		Name:           name,
		Protocol:       protocol,
		TimeoutMs:      int64(timeout),
		Priority:       priority,
		Params:         params,
		ExecKind:       "pull",
		Transform:      unitTransforms,
		FieldSpecs:     fieldSpecs,
		CalculateSpecs: calcSpecs,
	}, nil
}

func buildEffectiveParams(root map[string]any, monitor *model.Monitor) map[string]string {
	effective := map[string]string{}
	nonPersistable := collectNonPersistableFields(root)
	for _, item := range asSlice(root["params"]) {
		pm := asMap(item)
		field := strings.TrimSpace(asString(pm["field"]))
		if field == "" {
			continue
		}
		if raw := strings.TrimSpace(asString(pm["defaultValue"])); raw != "" {
			effective[field] = raw
		}
	}
	for k, v := range monitor.Params {
		if _, blocked := nonPersistable[k]; blocked {
			continue
		}
		effective[k] = v
	}
	if _, ok := effective["host"]; !ok {
		host, port := splitHostPortFallback(monitor.Target)
		if host != "" {
			effective["host"] = host
		}
		if _, hasPort := effective["port"]; !hasPort && port != "" {
			effective["port"] = port
		}
	}
	if _, ok := effective["url"]; !ok && strings.TrimSpace(monitor.Target) != "" && templateUsesHTTPProtocol(root) {
		effective["url"] = strings.TrimSpace(monitor.Target)
	}
	return effective
}

func parseTemplateRoot(rt RuntimeTemplate) (map[string]any, error) {
	content := strings.TrimSpace(rt.Content)
	if content == "" {
		return nil, compileErr("content", "template content is empty")
	}
	var root map[string]any
	if err := yaml.Unmarshal([]byte(content), &root); err != nil {
		return nil, compileErr("content", fmt.Sprintf("yaml parse failed: %v", err))
	}
	return root, nil
}

func collectNonPersistableFields(root map[string]any) map[string]struct{} {
	out := map[string]struct{}{}
	for _, item := range asSlice(root["params"]) {
		pm := asMap(item)
		field := strings.TrimSpace(asString(pm["field"]))
		if field == "" {
			continue
		}
		if shouldPersistParam(pm) {
			continue
		}
		out[field] = struct{}{}
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

func shouldPersistParam(pm map[string]any) bool {
	raw, exists := pm["persist"]
	if !exists {
		return true
	}
	switch v := raw.(type) {
	case bool:
		return v
	case string:
		s := strings.TrimSpace(strings.ToLower(v))
		switch s {
		case "", "true", "1", "yes", "on":
			return true
		case "false", "0", "no", "off":
			return false
		default:
			return true
		}
	default:
		return true
	}
}

func templateUsesHTTPProtocol(root map[string]any) bool {
	for _, item := range asSlice(root["metrics"]) {
		metric := asMap(item)
		if strings.EqualFold(strings.TrimSpace(asString(metric["protocol"])), "http") {
			return true
		}
	}
	return false
}

func compileFieldSpecs(fields []any, metricIdx int) ([]*pb.FieldSpec, map[string]struct{}, error) {
	out := make([]*pb.FieldSpec, 0, len(fields))
	knownFields := make(map[string]struct{}, len(fields))
	for idx, item := range fields {
		fm := asMap(item)
		if len(fm) == 0 {
			return nil, nil, compileErr(fmt.Sprintf("metrics[%d].fields[%d]", metricIdx, idx), "field item must be object")
		}
		field := strings.TrimSpace(asString(fm["field"]))
		if field == "" {
			return nil, nil, compileErr(fmt.Sprintf("metrics[%d].fields[%d].field", metricIdx, idx), "is required")
		}
		if !metricNameRegexp.MatchString(field) {
			return nil, nil, compileErr(fmt.Sprintf("metrics[%d].fields[%d].field", metricIdx, idx), fmt.Sprintf("invalid field name %q", field))
		}
		if _, exists := knownFields[field]; exists {
			return nil, nil, compileErr(fmt.Sprintf("metrics[%d].fields[%d].field", metricIdx, idx), fmt.Sprintf("duplicate field %q", field))
		}
		knownFields[field] = struct{}{}
		out = append(out, &pb.FieldSpec{
			Field: field,
			Type:  normalizeFieldType(fm["type"]),
			Unit:  strings.TrimSpace(asString(fm["unit"])),
			Label: asBool(fm["label"]),
		})
	}
	return out, knownFields, nil
}

func compileCalculateSpecs(calculates []any, metricIdx int, knownFields map[string]struct{}) ([]*pb.CalculateSpec, error) {
	out := make([]*pb.CalculateSpec, 0, len(calculates))
	calcOutputSeen := make(map[string]struct{}, len(calculates))
	for calcIdx, item := range calculates {
		raw := strings.TrimSpace(asString(item))
		if raw == "" {
			continue
		}
		eqIdx := strings.Index(raw, "=")
		if eqIdx <= 0 {
			return nil, compileErr(fmt.Sprintf("metrics[%d].calculates[%d]", metricIdx, calcIdx), "must use format field=expression")
		}
		field := strings.TrimSpace(raw[:eqIdx])
		expr := strings.TrimSpace(strings.ReplaceAll(raw[eqIdx+1:], "\\#", "#"))
		if field == "" || expr == "" {
			return nil, compileErr(fmt.Sprintf("metrics[%d].calculates[%d]", metricIdx, calcIdx), "field and expression must be non-empty")
		}
		if !metricNameRegexp.MatchString(field) {
			return nil, compileErr(fmt.Sprintf("metrics[%d].calculates[%d]", metricIdx, calcIdx), fmt.Sprintf("invalid calculate field %q", field))
		}
		if _, exists := calcOutputSeen[field]; exists {
			return nil, compileErr(fmt.Sprintf("metrics[%d].calculates[%d]", metricIdx, calcIdx), fmt.Sprintf("duplicate output field %q", field))
		}
		calcOutputSeen[field] = struct{}{}
		knownFields[field] = struct{}{}
		out = append(out, &pb.CalculateSpec{Field: field, Expression: expr})
	}
	return out, nil
}

func normalizeFieldType(v any) string {
	switch n := v.(type) {
	case int:
		return mapFieldType(n)
	case int64:
		return mapFieldType(int(n))
	case float64:
		return mapFieldType(int(n))
	default:
		s := strings.TrimSpace(strings.ToLower(asString(v)))
		if s == "" {
			return "number"
		}
		return s
	}
}

func mapFieldType(n int) string {
	switch n {
	case 0:
		return "number"
	case 1:
		return "string"
	case 2:
		return "time"
	default:
		return "number"
	}
}

func flattenWithReplace(dst map[string]string, prefix string, in map[string]any, vars map[string]string) {
	for k, v := range in {
		key := strings.TrimSpace(k)
		if key == "" {
			continue
		}
		full := key
		if prefix != "" {
			full = prefix + "." + key
		}
		switch typed := v.(type) {
		case map[string]any:
			flattenWithReplace(dst, full, typed, vars)
		case []any:
			vals := make([]string, 0, len(typed))
			for _, sv := range typed {
				vals = append(vals, replacePlaceholder(asString(sv), vars))
			}
			dst[full] = strings.Join(vals, ",")
		default:
			dst[full] = replacePlaceholder(asString(typed), vars)
			if prefix == "" {
				// Keep direct protocol scalar keys without prefix for collector runtime.
				dst[key] = replacePlaceholder(asString(typed), vars)
			}
		}
	}
}

func replacePlaceholder(s string, vars map[string]string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return s
	}
	if strings.HasPrefix(s, "^_^") && strings.HasSuffix(s, "^_^") && len(s) > 6 {
		key := strings.TrimSpace(s[3 : len(s)-3])
		if v, ok := vars[key]; ok {
			return v
		}
		return ""
	}
	return s
}

func splitHostPortFallback(target string) (string, string) {
	raw := strings.TrimSpace(target)
	if raw == "" {
		return "", ""
	}
	if strings.Contains(raw, "://") {
		if u, err := url.Parse(raw); err == nil {
			return strings.TrimSpace(u.Hostname()), strings.TrimSpace(u.Port())
		}
	}
	if h, p, err := net.SplitHostPort(raw); err == nil {
		return strings.TrimSpace(h), strings.TrimSpace(p)
	}
	parts := strings.Split(raw, ":")
	if len(parts) == 2 {
		return strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
	}
	return raw, ""
}

func readInt(raw string, def int) int {
	v, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil || v <= 0 {
		return def
	}
	return v
}

func readIntAny(v any, def int) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	case string:
		return readInt(n, def)
	default:
		return def
	}
}

func asString(v any) string {
	switch t := v.(type) {
	case nil:
		return ""
	case string:
		return t
	case int:
		return strconv.Itoa(t)
	case int64:
		return strconv.FormatInt(t, 10)
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	case bool:
		if t {
			return "true"
		}
		return "false"
	default:
		return fmt.Sprintf("%v", v)
	}
}

func asMap(v any) map[string]any {
	if v == nil {
		return nil
	}
	if out, ok := v.(map[string]any); ok {
		return out
	}
	return nil
}

func asSlice(v any) []any {
	if v == nil {
		return nil
	}
	if out, ok := v.([]any); ok {
		return out
	}
	return nil
}

func asBool(v any) bool {
	switch b := v.(type) {
	case bool:
		return b
	case string:
		return strings.EqualFold(strings.TrimSpace(b), "true")
	default:
		return false
	}
}

func cloneMapString(src map[string]string) map[string]string {
	out := make(map[string]string, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

// optimizeMySQLJDBCSQL merges common MySQL status/variables SQL into fewer broad queries.
// Collector-side field whitelist/calculate keeps metric output bounded by template fields.
func optimizeMySQLJDBCSQL(tasks []*pb.MetricsTask) {
	for _, task := range tasks {
		if task == nil || strings.TrimSpace(strings.ToLower(task.GetProtocol())) != "jdbc" {
			continue
		}
		params := task.GetParams()
		if len(params) == 0 {
			continue
		}
		platform := strings.TrimSpace(strings.ToLower(params["platform"]))
		if platform == "" {
			platform = strings.TrimSpace(strings.ToLower(params["driver"]))
		}
		if platform != "mysql" {
			continue
		}
		queryType := strings.TrimSpace(strings.ToLower(params["queryType"]))
		if queryType == "" {
			queryType = "columns"
		}
		if queryType != "columns" {
			continue
		}
		sqlText := strings.TrimSpace(strings.ToLower(params["sql"]))
		if sqlText == "" {
			continue
		}
		if strings.HasPrefix(sqlText, "show global status") {
			params["sql"] = "show global status;"
			continue
		}
		if strings.HasPrefix(sqlText, "show global variables") {
			params["sql"] = "show global variables;"
			continue
		}
	}
}

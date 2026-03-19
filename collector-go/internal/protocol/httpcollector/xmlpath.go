package httpcollector

import (
	"bytes"
	"encoding/xml"
	"fmt"
	"io"
	"strconv"
	"strings"
)

type xmlNode struct {
	Name     string
	Text     string
	Children []*xmlNode
}

func (p parser) parseXMLPath() (map[string]string, error) {
	root, err := parseXMLTree(p.body)
	if err != nil {
		return nil, err
	}
	script := strings.TrimSpace(firstNonEmpty(p.task.Params["parseScript"], p.task.Params["http.parseScript"]))
	selected := selectXMLRoots(root, script)
	if len(selected) == 0 {
		selected = []*xmlNode{root}
	}
	requested := requestedFieldNames(p.task)
	out := map[string]string{
		"responseTime": strconv.FormatInt(p.latency.Milliseconds(), 10),
	}
	flat := map[string]string{}
	for _, node := range selected {
		if len(node.Children) == 0 {
			flattenXMLLeaves(node, "", flat)
			continue
		}
		for _, child := range node.Children {
			flattenXMLLeaves(child, "", flat)
		}
	}

	applyPathCalculates(out, flat, p.task)
	for _, spec := range p.task.FieldSpecs {
		field := strings.TrimSpace(spec.Field)
		if field == "" || field == "responseTime" {
			continue
		}
		if _, ok := out[field]; ok {
			continue
		}
		if val, ok := evalXMLExpression(selected, field); ok {
			out[field] = val
			continue
		}
		if val, ok := flat[field]; ok {
			out[field] = val
			continue
		}
	}
	if len(requested) > 0 {
		for key := range out {
			if key == "responseTime" {
				continue
			}
			if _, ok := requested[key]; !ok {
				delete(out, key)
			}
		}
	}
	return out, nil
}

func parseXMLTree(raw []byte) (*xmlNode, error) {
	decoder := xml.NewDecoder(bytes.NewReader(raw))
	var stack []*xmlNode
	var root *xmlNode
	for {
		tok, err := decoder.Token()
		if err != nil {
			if err == io.EOF {
				break
			}
			return nil, err
		}
		switch t := tok.(type) {
		case xml.StartElement:
			node := &xmlNode{Name: t.Name.Local}
			if len(stack) > 0 {
				parent := stack[len(stack)-1]
				parent.Children = append(parent.Children, node)
			} else {
				root = node
			}
			stack = append(stack, node)
		case xml.EndElement:
			if len(stack) > 0 {
				stack = stack[:len(stack)-1]
			}
		case xml.CharData:
			if len(stack) == 0 {
				continue
			}
			text := strings.TrimSpace(string(t))
			if text == "" {
				continue
			}
			cur := stack[len(stack)-1]
			if cur.Text == "" {
				cur.Text = text
			} else {
				cur.Text += text
			}
		}
	}
	if root == nil {
		return nil, fmt.Errorf("empty xml payload")
	}
	return root, nil
}

func selectXMLRoots(root *xmlNode, script string) []*xmlNode {
	script = strings.TrimSpace(script)
	if script == "" || script == "/" || script == "//" {
		return []*xmlNode{root}
	}
	if strings.HasPrefix(script, "//") {
		target := strings.TrimSpace(strings.TrimPrefix(script, "//"))
		if target == "" {
			return []*xmlNode{root}
		}
		var out []*xmlNode
		walkXML(root, func(node *xmlNode) {
			if node.Name == target {
				out = append(out, node)
			}
		})
		return out
	}
	path := strings.TrimPrefix(script, "/")
	segments := strings.Split(path, "/")
	current := []*xmlNode{root}
	for _, seg := range segments {
		seg = strings.TrimSpace(seg)
		if seg == "" {
			continue
		}
		next := make([]*xmlNode, 0)
		for _, node := range current {
			for _, child := range node.Children {
				if child.Name == seg {
					next = append(next, child)
				}
			}
		}
		current = next
	}
	return current
}

func walkXML(node *xmlNode, fn func(*xmlNode)) {
	if node == nil {
		return
	}
	fn(node)
	for _, child := range node.Children {
		walkXML(child, fn)
	}
}

func flattenXMLLeaves(node *xmlNode, prefix string, out map[string]string) {
	if node == nil {
		return
	}
	cur := node.Name
	if prefix != "" {
		cur = prefix + "/" + node.Name
	}
	if len(node.Children) == 0 {
		if strings.TrimSpace(node.Text) != "" {
			out[cur] = strings.TrimSpace(node.Text)
			if _, exists := out[node.Name]; !exists {
				out[node.Name] = strings.TrimSpace(node.Text)
			}
		}
		return
	}
	for _, child := range node.Children {
		flattenXMLLeaves(child, cur, out)
	}
}

func evalXMLExpression(roots []*xmlNode, expr string) (string, bool) {
	segments := strings.Split(strings.TrimSpace(expr), "/")
	current := roots
	for _, seg := range segments {
		seg = strings.TrimSpace(seg)
		if seg == "" {
			continue
		}
		name, filterName, filterVal := parseXMLSegment(seg)
		next := make([]*xmlNode, 0)
		for _, node := range current {
			for _, child := range node.Children {
				if child.Name != name {
					continue
				}
				if filterName != "" && !xmlChildEquals(child, filterName, filterVal) {
					continue
				}
				next = append(next, child)
			}
		}
		current = next
	}
	for _, node := range current {
		if strings.TrimSpace(node.Text) != "" {
			return strings.TrimSpace(node.Text), true
		}
	}
	return "", false
}

func parseXMLSegment(seg string) (string, string, string) {
	start := strings.Index(seg, "[")
	end := strings.LastIndex(seg, "]")
	if start < 0 || end <= start {
		return seg, "", ""
	}
	name := strings.TrimSpace(seg[:start])
	filterExpr := strings.TrimSpace(seg[start+1 : end])
	parts := strings.SplitN(filterExpr, "=", 2)
	if len(parts) != 2 {
		return name, "", ""
	}
	filterName := strings.TrimSpace(parts[0])
	filterVal := strings.Trim(strings.TrimSpace(parts[1]), `"'`)
	return name, filterName, filterVal
}

func xmlChildEquals(node *xmlNode, field string, want string) bool {
	for _, child := range node.Children {
		if child.Name == field && strings.TrimSpace(child.Text) == want {
			return true
		}
	}
	return false
}

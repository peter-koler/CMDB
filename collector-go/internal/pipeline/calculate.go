package pipeline

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"math"
	"strconv"
	"strings"

	"collector-go/internal/model"
)

func ApplyCalculates(fields map[string]string, calculates []model.CalculateSpec) (map[string]string, map[string]string) {
	if len(calculates) == 0 {
		return fields, nil
	}
	out := cloneMap(fields)
	debug := map[string]string{}
	for _, calc := range calculates {
		field := strings.TrimSpace(calc.Field)
		expr := strings.TrimSpace(calc.Expression)
		if field == "" || expr == "" {
			continue
		}
		value, err := evalExpression(expr, out)
		if err != nil {
			debug["calculate."+field] = err.Error()
			continue
		}
		out[field] = stringifyValue(value)
	}
	if len(debug) == 0 {
		return out, nil
	}
	return out, debug
}

func ApplyFieldWhitelist(fields map[string]string, specs []model.FieldSpec, captureDropped bool) (map[string]string, map[string]string) {
	if len(specs) == 0 {
		return fields, nil
	}
	allowed := make(map[string]struct{}, len(specs))
	for _, spec := range specs {
		field := strings.TrimSpace(spec.Field)
		if field != "" {
			allowed[field] = struct{}{}
		}
	}
	if len(allowed) == 0 {
		return map[string]string{}, nil
	}

	out := make(map[string]string, len(fields))
	var debug map[string]string
	if captureDropped {
		debug = map[string]string{}
	}
	for k, v := range fields {
		if _, ok := allowed[k]; ok {
			out[k] = v
			continue
		}
		if captureDropped {
			debug["dropped."+k] = "field not in field_specs"
		}
	}
	if len(debug) == 0 {
		return out, nil
	}
	return out, debug
}

func evalExpression(expression string, fields map[string]string) (any, error) {
	expr, err := parser.ParseExpr(expression)
	if err != nil {
		return nil, fmt.Errorf("invalid expression: %w", err)
	}
	return evalNode(expr, fields)
}

func evalNode(node ast.Expr, fields map[string]string) (any, error) {
	switch n := node.(type) {
	case *ast.BasicLit:
		return evalBasicLit(n)
	case *ast.ParenExpr:
		return evalNode(n.X, fields)
	case *ast.Ident:
		return evalIdent(n, fields)
	case *ast.UnaryExpr:
		return evalUnary(n, fields)
	case *ast.BinaryExpr:
		return evalBinary(n, fields)
	case *ast.CallExpr:
		return evalCall(n, fields)
	default:
		return nil, fmt.Errorf("unsupported expression node: %T", n)
	}
}

func evalBasicLit(lit *ast.BasicLit) (any, error) {
	switch lit.Kind {
	case token.INT, token.FLOAT:
		f, err := strconv.ParseFloat(lit.Value, 64)
		if err != nil {
			return nil, fmt.Errorf("invalid number %q: %w", lit.Value, err)
		}
		return f, nil
	case token.STRING:
		s, err := strconv.Unquote(lit.Value)
		if err != nil {
			return nil, fmt.Errorf("invalid string literal %q: %w", lit.Value, err)
		}
		return s, nil
	default:
		return nil, fmt.Errorf("unsupported literal kind: %s", lit.Kind)
	}
}

func evalIdent(ident *ast.Ident, fields map[string]string) (any, error) {
	raw, ok := fields[ident.Name]
	if !ok {
		return nil, fmt.Errorf("unknown variable: %s", ident.Name)
	}
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", nil
	}
	if f, err := strconv.ParseFloat(raw, 64); err == nil {
		return f, nil
	}
	return raw, nil
}

func evalUnary(expr *ast.UnaryExpr, fields map[string]string) (any, error) {
	v, err := evalNode(expr.X, fields)
	if err != nil {
		return nil, err
	}
	num, err := asNumber(v)
	if err != nil {
		return nil, fmt.Errorf("unary %s expects number: %w", expr.Op.String(), err)
	}
	switch expr.Op {
	case token.ADD:
		return num, nil
	case token.SUB:
		return -num, nil
	default:
		return nil, fmt.Errorf("unsupported unary operator: %s", expr.Op.String())
	}
}

func evalBinary(expr *ast.BinaryExpr, fields map[string]string) (any, error) {
	left, err := evalNode(expr.X, fields)
	if err != nil {
		return nil, err
	}
	right, err := evalNode(expr.Y, fields)
	if err != nil {
		return nil, err
	}
	switch expr.Op {
	case token.ADD:
		if isStringLike(left) || isStringLike(right) {
			return stringifyValue(left) + stringifyValue(right), nil
		}
		ln, err := asNumber(left)
		if err != nil {
			return nil, err
		}
		rn, err := asNumber(right)
		if err != nil {
			return nil, err
		}
		return ln + rn, nil
	case token.SUB, token.MUL, token.QUO:
		ln, err := asNumber(left)
		if err != nil {
			return nil, err
		}
		rn, err := asNumber(right)
		if err != nil {
			return nil, err
		}
		switch expr.Op {
		case token.SUB:
			return ln - rn, nil
		case token.MUL:
			return ln * rn, nil
		case token.QUO:
			if rn == 0 {
				return nil, fmt.Errorf("division by zero")
			}
			return ln / rn, nil
		}
	default:
		return nil, fmt.Errorf("unsupported binary operator: %s", expr.Op.String())
	}
	return nil, fmt.Errorf("unsupported binary operator: %s", expr.Op.String())
}

func evalCall(call *ast.CallExpr, fields map[string]string) (any, error) {
	ident, ok := call.Fun.(*ast.Ident)
	if !ok {
		return nil, fmt.Errorf("unsupported function expression")
	}
	name := strings.ToLower(strings.TrimSpace(ident.Name))
	switch name {
	case "abs":
		args, err := evalCallArgs(call.Args, fields)
		if err != nil {
			return nil, err
		}
		if len(args) != 1 {
			return nil, fmt.Errorf("abs expects 1 arg")
		}
		v, err := asNumber(args[0])
		if err != nil {
			return nil, err
		}
		return math.Abs(v), nil
	case "min", "max":
		args, err := evalCallArgs(call.Args, fields)
		if err != nil {
			return nil, err
		}
		if len(args) < 2 {
			return nil, fmt.Errorf("%s expects at least 2 args", name)
		}
		best, err := asNumber(args[0])
		if err != nil {
			return nil, err
		}
		for _, arg := range args[1:] {
			cur, err := asNumber(arg)
			if err != nil {
				return nil, err
			}
			if name == "min" && cur < best {
				best = cur
			}
			if name == "max" && cur > best {
				best = cur
			}
		}
		return best, nil
	case "round":
		args, err := evalCallArgs(call.Args, fields)
		if err != nil {
			return nil, err
		}
		if len(args) != 1 && len(args) != 2 {
			return nil, fmt.Errorf("round expects 1 or 2 args")
		}
		value, err := asNumber(args[0])
		if err != nil {
			return nil, err
		}
		precision := 0.0
		if len(args) == 2 {
			precision, err = asNumber(args[1])
			if err != nil {
				return nil, err
			}
		}
		pow := math.Pow(10, precision)
		return math.Round(value*pow) / pow, nil
	default:
		return nil, fmt.Errorf("unsupported function: %s", ident.Name)
	}
}

func evalCallArgs(args []ast.Expr, fields map[string]string) ([]any, error) {
	out := make([]any, 0, len(args))
	for _, arg := range args {
		v, err := evalNode(arg, fields)
		if err != nil {
			return nil, err
		}
		out = append(out, v)
	}
	return out, nil
}

func asNumber(v any) (float64, error) {
	switch n := v.(type) {
	case float64:
		return n, nil
	case int:
		return float64(n), nil
	case int64:
		return float64(n), nil
	case string:
		f, err := strconv.ParseFloat(strings.TrimSpace(n), 64)
		if err != nil {
			return 0, fmt.Errorf("not a number: %q", n)
		}
		return f, nil
	default:
		return 0, fmt.Errorf("not a number type: %T", v)
	}
}

func stringifyValue(v any) string {
	switch val := v.(type) {
	case nil:
		return ""
	case string:
		return val
	case float64:
		return strconv.FormatFloat(val, 'f', -1, 64)
	case int:
		return strconv.Itoa(val)
	case int64:
		return strconv.FormatInt(val, 10)
	default:
		return fmt.Sprintf("%v", val)
	}
}

func isStringLike(v any) bool {
	_, ok := v.(string)
	return ok
}

func cloneMap(src map[string]string) map[string]string {
	if len(src) == 0 {
		return map[string]string{}
	}
	dst := make(map[string]string, len(src))
	for k, v := range src {
		dst[k] = v
	}
	return dst
}

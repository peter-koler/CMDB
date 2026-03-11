package alert

import (
	"fmt"
	"sync"
	"time"
)

type Rule struct {
	ID              int64
	Name            string
	Expression      string
	DurationSeconds int
	Severity        string
	Enabled         bool
}

type State string

const (
	StateNormal  State = "normal"
	StatePending State = "pending"
	StateFiring  State = "firing"
)

type Event struct {
	RuleID       int64
	RuleName     string
	NoticeRuleID int64
	MonitorID    int64
	App          string
	Instance     string
	Severity     string
	Labels       map[string]string
	State        State
	Expression   string
	Content      string
	ElapsedMs    int64
	TriggeredAt  time.Time
}

type condState struct {
	firstTrueAt time.Time
	firing      bool
	trueCount   int
}

type Engine struct {
	mu     sync.Mutex
	states map[string]condState
}

func NewEngine() *Engine {
	return &Engine{states: map[string]condState{}}
}

func (e *Engine) Evaluate(rule Rule, monitorID int64, vars map[string]float64, now time.Time) (Event, bool, error) {
	if !rule.Enabled {
		return Event{}, false, nil
	}
	ok, err := evalExpression(rule.Expression, vars)
	if err != nil {
		return Event{}, false, err
	}
	key := fmt.Sprintf("%d:%d", rule.ID, monitorID)

	e.mu.Lock()
	defer e.mu.Unlock()
	st := e.states[key]
	if !ok {
		delete(e.states, key)
		return Event{
			RuleID:      rule.ID,
			RuleName:    rule.Name,
			MonitorID:   monitorID,
			Severity:    rule.Severity,
			State:       StateNormal,
			Expression:  rule.Expression,
			ElapsedMs:   0,
			TriggeredAt: now,
		}, true, nil
	}
	if st.firstTrueAt.IsZero() {
		st.firstTrueAt = now
	}
	st.trueCount++
	elapsed := now.Sub(st.firstTrueAt)
	required := rule.DurationSeconds
	if required <= 0 {
		required = 1
	}
	if st.trueCount >= required {
		st.firing = true
		e.states[key] = st
		return Event{
			RuleID:      rule.ID,
			RuleName:    rule.Name,
			MonitorID:   monitorID,
			Severity:    rule.Severity,
			State:       StateFiring,
			Expression:  rule.Expression,
			ElapsedMs:   elapsed.Milliseconds(),
			TriggeredAt: now,
		}, true, nil
	}
	e.states[key] = st
	return Event{
		RuleID:      rule.ID,
		RuleName:    rule.Name,
		MonitorID:   monitorID,
		Severity:    rule.Severity,
		State:       StatePending,
		Expression:  rule.Expression,
		ElapsedMs:   elapsed.Milliseconds(),
		TriggeredAt: now,
	}, true, nil
}

func evalExpression(expr string, vars map[string]float64) (bool, error) {
	tokens, err := scanTokens(expr)
	if err != nil {
		return false, err
	}
	p := &exprParser{
		tokens: tokens,
		vars:   vars,
	}
	out, err := p.parseBoolExpr()
	if err != nil {
		return false, err
	}
	if p.hasMore() {
		return false, fmt.Errorf("unexpected token: %s", p.peek().raw)
	}
	return out, nil
}

type tokenType int

const (
	tokenEOF tokenType = iota
	tokenNumber
	tokenIdent
	tokenLParen
	tokenRParen
	tokenPlus
	tokenMinus
	tokenMul
	tokenDiv
	tokenGT
	tokenGE
	tokenLT
	tokenLE
	tokenEQ
	tokenNE
	tokenAND
	tokenOR
)

type token struct {
	typ tokenType
	raw string
	num float64
}

type exprParser struct {
	tokens []token
	pos    int
	vars   map[string]float64
}

func (p *exprParser) hasMore() bool {
	return p.pos < len(p.tokens) && p.tokens[p.pos].typ != tokenEOF
}

func (p *exprParser) peek() token {
	if p.pos >= len(p.tokens) {
		return token{typ: tokenEOF}
	}
	return p.tokens[p.pos]
}

func (p *exprParser) next() token {
	t := p.peek()
	if p.pos < len(p.tokens) {
		p.pos++
	}
	return t
}

func (p *exprParser) parseBoolExpr() (bool, error) {
	return p.parseOr()
}

func (p *exprParser) parseOr() (bool, error) {
	left, err := p.parseAnd()
	if err != nil {
		return false, err
	}
	for p.peek().typ == tokenOR {
		p.next()
		right, err := p.parseAnd()
		if err != nil {
			return false, err
		}
		left = left || right
	}
	return left, nil
}

func (p *exprParser) parseAnd() (bool, error) {
	left, err := p.parseBoolAtom()
	if err != nil {
		return false, err
	}
	for p.peek().typ == tokenAND {
		p.next()
		right, err := p.parseBoolAtom()
		if err != nil {
			return false, err
		}
		left = left && right
	}
	return left, nil
}

func (p *exprParser) parseBoolAtom() (bool, error) {
	if p.peek().typ == tokenLParen {
		// Try parenthesized bool expression first.
		savedPos := p.pos
		p.next()
		out, err := p.parseBoolExpr()
		if err == nil && p.peek().typ == tokenRParen {
			p.next()
			return out, nil
		}
		// fallback to comparison path
		p.pos = savedPos
	}
	return p.parseComparison()
}

func (p *exprParser) parseComparison() (bool, error) {
	left, err := p.parseAddSub()
	if err != nil {
		return false, err
	}
	op := p.peek()
	switch op.typ {
	case tokenGT, tokenGE, tokenLT, tokenLE, tokenEQ, tokenNE:
		p.next()
	default:
		return false, fmt.Errorf("comparison operator expected near: %s", op.raw)
	}
	right, err := p.parseAddSub()
	if err != nil {
		return false, err
	}
	switch op.typ {
	case tokenGT:
		return left > right, nil
	case tokenGE:
		return left >= right, nil
	case tokenLT:
		return left < right, nil
	case tokenLE:
		return left <= right, nil
	case tokenEQ:
		return left == right, nil
	case tokenNE:
		return left != right, nil
	default:
		return false, fmt.Errorf("unsupported operator: %s", op.raw)
	}
}

func (p *exprParser) parseAddSub() (float64, error) {
	left, err := p.parseMulDiv()
	if err != nil {
		return 0, err
	}
	for {
		op := p.peek()
		if op.typ != tokenPlus && op.typ != tokenMinus {
			break
		}
		p.next()
		right, err := p.parseMulDiv()
		if err != nil {
			return 0, err
		}
		if op.typ == tokenPlus {
			left += right
		} else {
			left -= right
		}
	}
	return left, nil
}

func (p *exprParser) parseMulDiv() (float64, error) {
	left, err := p.parseUnary()
	if err != nil {
		return 0, err
	}
	for {
		op := p.peek()
		if op.typ != tokenMul && op.typ != tokenDiv {
			break
		}
		p.next()
		right, err := p.parseUnary()
		if err != nil {
			return 0, err
		}
		if op.typ == tokenMul {
			left *= right
		} else {
			if right == 0 {
				return 0, fmt.Errorf("division by zero")
			}
			left /= right
		}
	}
	return left, nil
}

func (p *exprParser) parseUnary() (float64, error) {
	switch p.peek().typ {
	case tokenPlus:
		p.next()
		return p.parseUnary()
	case tokenMinus:
		p.next()
		v, err := p.parseUnary()
		if err != nil {
			return 0, err
		}
		return -v, nil
	default:
		return p.parsePrimaryNumber()
	}
}

func (p *exprParser) parsePrimaryNumber() (float64, error) {
	tok := p.next()
	switch tok.typ {
	case tokenNumber:
		return tok.num, nil
	case tokenIdent:
		v, ok := p.vars[tok.raw]
		if !ok {
			return 0, fmt.Errorf("unknown variable: %s", tok.raw)
		}
		return v, nil
	case tokenLParen:
		v, err := p.parseAddSub()
		if err != nil {
			return 0, err
		}
		if p.peek().typ != tokenRParen {
			return 0, fmt.Errorf("missing ')'")
		}
		p.next()
		return v, nil
	default:
		return 0, fmt.Errorf("unexpected token: %s", tok.raw)
	}
}

func scanTokens(expr string) ([]token, error) {
	out := make([]token, 0, len(expr)/2)
	i := 0
	for i < len(expr) {
		ch := expr[i]
		if ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r' {
			i++
			continue
		}
		if i+1 < len(expr) {
			op2 := expr[i : i+2]
			switch op2 {
			case "&&":
				out = append(out, token{typ: tokenAND, raw: op2})
				i += 2
				continue
			case "||":
				out = append(out, token{typ: tokenOR, raw: op2})
				i += 2
				continue
			case ">=":
				out = append(out, token{typ: tokenGE, raw: op2})
				i += 2
				continue
			case "<=":
				out = append(out, token{typ: tokenLE, raw: op2})
				i += 2
				continue
			case "==":
				out = append(out, token{typ: tokenEQ, raw: op2})
				i += 2
				continue
			case "!=":
				out = append(out, token{typ: tokenNE, raw: op2})
				i += 2
				continue
			}
		}
		switch ch {
		case '(':
			out = append(out, token{typ: tokenLParen, raw: "("})
			i++
			continue
		case ')':
			out = append(out, token{typ: tokenRParen, raw: ")"})
			i++
			continue
		case '+':
			out = append(out, token{typ: tokenPlus, raw: "+"})
			i++
			continue
		case '-':
			out = append(out, token{typ: tokenMinus, raw: "-"})
			i++
			continue
		case '*':
			out = append(out, token{typ: tokenMul, raw: "*"})
			i++
			continue
		case '/':
			out = append(out, token{typ: tokenDiv, raw: "/"})
			i++
			continue
		case '>':
			out = append(out, token{typ: tokenGT, raw: ">"})
			i++
			continue
		case '<':
			out = append(out, token{typ: tokenLT, raw: "<"})
			i++
			continue
		}
		if isDigit(ch) || ch == '.' {
			start := i
			dotCount := 0
			for i < len(expr) && (isDigit(expr[i]) || expr[i] == '.') {
				if expr[i] == '.' {
					dotCount++
					if dotCount > 1 {
						return nil, fmt.Errorf("invalid number near: %s", expr[start:i+1])
					}
				}
				i++
			}
			raw := expr[start:i]
			var n float64
			if _, err := fmt.Sscanf(raw, "%f", &n); err != nil {
				return nil, fmt.Errorf("invalid number: %s", raw)
			}
			out = append(out, token{typ: tokenNumber, raw: raw, num: n})
			continue
		}
		if isIdentStart(ch) {
			start := i
			i++
			for i < len(expr) && isIdentPart(expr[i]) {
				i++
			}
			raw := expr[start:i]
			out = append(out, token{typ: tokenIdent, raw: raw})
			continue
		}
		return nil, fmt.Errorf("invalid character: %q", ch)
	}
	out = append(out, token{typ: tokenEOF})
	return out, nil
}

func isDigit(ch byte) bool {
	return ch >= '0' && ch <= '9'
}

func isIdentStart(ch byte) bool {
	return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch == '_' || ch == '$'
}

func isIdentPart(ch byte) bool {
	return isIdentStart(ch) || isDigit(ch)
}

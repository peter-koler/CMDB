package servicecollector

import (
	"context"
	"fmt"
	"net"
	"strings"
	"time"

	"collector-go/internal/model"
)

type DNSCollector struct{}

type dnsResult struct {
	responseTime time.Duration
	status       string
	question     string
	answers      []string
	authority    []string
	additional   []string
}

func (c *DNSCollector) Collect(ctx context.Context, task model.MetricsTask) (map[string]string, string, error) {
	params := task.Params
	host := firstNonEmpty(params, "dnsServerIP", "host", "dns.host")
	port := parsePort(params, "53", "port", "dns.port")
	address := firstNonEmpty(params, "address", "dns.address")
	recordType := strings.ToUpper(firstNonEmpty(params, "recordType", "dns.recordType"))
	if recordType == "" {
		recordType = "A"
	}
	queryClass := strings.ToUpper(firstNonEmpty(params, "queryClass", "dns.queryClass"))
	if queryClass == "" {
		queryClass = "IN"
	}
	useTCP := boolFrom(params, false, "tcp", "dns.tcp")
	timeout := timeoutFrom(params, task.Timeout, "timeout", "dns.timeout")
	if address == "" {
		return nil, "missing dns address", fmt.Errorf("missing dns address")
	}

	start := time.Now()
	result, lookupErr := lookupDNS(ctx, host, port, address, recordType, queryClass, useTCP, timeout)
	result.responseTime = time.Since(start)
	fields := map[string]string{
		"responseTime":       fmt.Sprintf("%d", result.responseTime.Milliseconds()),
		"opcode":             "QUERY",
		"status":             result.status,
		"flags":              defaultDNSFlags(useTCP),
		"questionRowCount":   "1",
		"answerRowCount":     fmt.Sprintf("%d", len(result.answers)),
		"authorityRowCount":  fmt.Sprintf("%d", len(result.authority)),
		"additionalRowCount": fmt.Sprintf("%d", len(result.additional)),
		"section":            result.question,
	}
	fillSectionFields(fields, result.answers)
	if task.Name == "authority" {
		fillSectionFields(fields, result.authority)
	}
	if task.Name == "additional" {
		fillSectionFields(fields, result.additional)
	}
	if lookupErr != nil {
		return fields, "dns lookup failed", lookupErr
	}
	return fields, "ok", nil
}

func lookupDNS(ctx context.Context, dnsHost, dnsPort, address, recordType, queryClass string, useTCP bool, timeout time.Duration) (dnsResult, error) {
	res := dnsResult{status: "NOERROR", question: fmt.Sprintf("%s %s %s", address, queryClass, recordType)}
	network := "udp"
	if useTCP {
		network = "tcp"
	}
	resolver := &net.Resolver{
		PreferGo: true,
		Dial: func(ctx context.Context, networkName, addressName string) (net.Conn, error) {
			d := net.Dialer{Timeout: timeout}
			return d.DialContext(ctx, network, net.JoinHostPort(dnsHost, dnsPort))
		},
	}
	ctx2, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	switch recordType {
	case "A", "AAAA", "ANY":
		ips, err := resolver.LookupIPAddr(ctx2, address)
		if err != nil {
			res.status = "SERVFAIL"
			return res, err
		}
		for _, ip := range ips {
			if recordType == "A" && ip.IP.To4() == nil {
				continue
			}
			if recordType == "AAAA" && ip.IP.To4() != nil {
				continue
			}
			res.answers = append(res.answers, ip.IP.String())
		}
	case "MX":
		records, err := resolver.LookupMX(ctx2, address)
		if err != nil {
			res.status = "SERVFAIL"
			return res, err
		}
		for _, one := range records {
			res.answers = append(res.answers, fmt.Sprintf("%d %s", one.Pref, strings.TrimSuffix(one.Host, ".")))
		}
	case "NS":
		records, err := resolver.LookupNS(ctx2, address)
		if err != nil {
			res.status = "SERVFAIL"
			return res, err
		}
		for _, one := range records {
			res.answers = append(res.answers, strings.TrimSuffix(one.Host, "."))
		}
	case "SRV":
		_, records, err := resolver.LookupSRV(ctx2, "", "", address)
		if err != nil {
			res.status = "SERVFAIL"
			return res, err
		}
		for _, one := range records {
			res.answers = append(res.answers, fmt.Sprintf("%d %d %d %s", one.Priority, one.Weight, one.Port, strings.TrimSuffix(one.Target, ".")))
		}
	default:
		ips, err := resolver.LookupIPAddr(ctx2, address)
		if err != nil {
			res.status = "SERVFAIL"
			return res, err
		}
		for _, ip := range ips {
			res.answers = append(res.answers, ip.IP.String())
		}
	}
	if len(res.answers) == 0 {
		res.status = "NOANSWER"
	}
	return res, nil
}

func fillSectionFields(out map[string]string, sections []string) {
	for i := 0; i < 10; i++ {
		key := fmt.Sprintf("section%d", i)
		if i < len(sections) {
			out[key] = sections[i]
		} else if _, ok := out[key]; !ok {
			out[key] = ""
		}
	}
}

func defaultDNSFlags(useTCP bool) string {
	if useTCP {
		return "rd ra tcp"
	}
	return "rd ra"
}

package jmxcollector

import "testing"

func TestParseHostPortFromServiceURL(t *testing.T) {
	host, port := parseHostPortFromServiceURL("service:jmx:rmi:///jndi/rmi://10.0.0.10:9999/jmxrmi")
	if host != "10.0.0.10" || port != "9999" {
		t.Fatalf("unexpected host/port: %s %s", host, port)
	}
}

func TestResolveEndpointFromServiceURL(t *testing.T) {
	endpoint, err := resolveEndpoint("service:jmx:rmi:///jndi/rmi://10.0.0.10:9999/jmxrmi", "127.0.0.1", "8080")
	if err != nil {
		t.Fatalf("resolve endpoint failed: %v", err)
	}
	if endpoint != "http://10.0.0.10:9999/jmx" {
		t.Fatalf("unexpected endpoint: %s", endpoint)
	}
}

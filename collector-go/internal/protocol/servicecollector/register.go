package servicecollector

import "collector-go/internal/protocol"

func init() {
	protocol.Register("udp", &UDPCollector{})
	protocol.Register("ssl_cert", &SSLCertCollector{})
	protocol.Register("nginx", &NginxCollector{})
	protocol.Register("smtp", &SMTPCollector{})
	protocol.Register("pop3", &POP3Collector{})
	protocol.Register("imap", &IMAPCollector{})
	protocol.Register("ntp", &NTPCollector{})
	protocol.Register("dns", &DNSCollector{})
	protocol.Register("ftp", &FTPCollector{})
	protocol.Register("websocket", &WebsocketCollector{})
	protocol.Register("mqtt", &MQTTCollector{})
}

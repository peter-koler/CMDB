from __future__ import annotations

SERVICE_TEMPLATE_META = {
    "website": {"name_zh": "网站监测", "name_en": "Website", "tier": "web"},
    "api": {"name_zh": "HTTP API", "name_en": "HTTP API", "tier": "web"},
    "api_code": {"name_zh": "HTTP API状态码", "name_en": "HTTP API Code", "tier": "web"},
    "ping": {"name_zh": "PING连通性", "name_en": "Ping", "tier": "network"},
    "port": {"name_zh": "TCP端口可用性", "name_en": "TCP Port", "tier": "network"},
    "udp_port": {"name_zh": "UDP端口可用性", "name_en": "UDP Port", "tier": "network"},
    "ssl_cert": {"name_zh": "SSL证书", "name_en": "SSL Certificate", "tier": "security"},
    "nginx": {"name_zh": "Nginx服务器", "name_en": "Nginx", "tier": "webserver"},
    "imap": {"name_zh": "IMAP邮件服务器", "name_en": "IMAP Mail", "tier": "mail"},
    "pop3": {"name_zh": "POP3邮件服务器", "name_en": "POP3 Mail", "tier": "mail"},
    "smtp": {"name_zh": "SMTP邮件服务器", "name_en": "SMTP Mail", "tier": "mail"},
    "ntp": {"name_zh": "NTP服务器", "name_en": "NTP", "tier": "network"},
    "dns": {"name_zh": "DNS服务器监控", "name_en": "DNS", "tier": "network"},
    "ftp": {"name_zh": "FTP服务器", "name_en": "FTP", "tier": "file-transfer"},
    "websocket": {"name_zh": "WebSocket", "name_en": "WebSocket", "tier": "realtime"},
    "mqtt": {"name_zh": "MQTT连接", "name_en": "MQTT", "tier": "iot"},
}

SOURCE_APPS = [
    "website",
    "api",
    "api_code",
    "ping",
    "port",
    "udp_port",
    "ssl_cert",
    "nginx",
    "pop3",
    "smtp",
    "ntp",
    "dns",
    "ftp",
    "websocket",
    "mqtt",
]

RENDER_ONLY_APPS = ["imap"]

ALL_SERVICE_APPS = SOURCE_APPS + RENDER_ONLY_APPS

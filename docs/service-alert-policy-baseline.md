# 应用服务默认告警策略基线

## 当前覆盖

- website, api, api_code
- ping, port, udp_port
- ssl_cert
- nginx
- imap, pop3, smtp
- ntp, dns
- ftp
- websocket
- mqtt

## 设计原则

- 可用性统一使用 `realtime_metric`
- 连接质量统一覆盖 `responseTime` 分级阈值
- 协议特有风险单独建模：
  - SSL：过期与剩余天数
  - DNS：状态码与无应答
  - WebSocket：握手状态码与升级头
  - MQTT：订阅/发布/接收能力
  - Nginx：连接积压与丢弃连接

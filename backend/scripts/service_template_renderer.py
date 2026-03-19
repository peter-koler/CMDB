from __future__ import annotations


def render_imap_template() -> str:
    return """category: service
app: imap
name:
  zh-CN: IMAP邮件服务器
  en-US: IMAP Email Server
help:
  zh-CN: 使用 IMAP 协议采集邮箱可用性与基础状态（响应时间、邮件数）。
  en-US: Collect mail availability and mailbox status through IMAP protocol.
params:
  - field: host
    name:
      zh-CN: 目标Host
      en-US: Target Host
    type: host
    required: true
  - field: port
    name:
      zh-CN: 端口
      en-US: Port
    type: number
    range: '[0,65535]'
    required: true
    defaultValue: 993
  - field: timeout
    name:
      zh-CN: 连接超时时间(ms)
      en-US: Connect Timeout(ms)
    type: number
    range: '[0,100000]'
    required: true
    defaultValue: 6000
  - field: ssl
    name:
      zh-CN: 启动SSL
      en-US: SSL
    type: boolean
    required: false
    defaultValue: true
  - field: email
    name:
      zh-CN: 邮箱地址
      en-US: Email
    type: text
    required: false
  - field: authorize
    name:
      zh-CN: 授权码
      en-US: Authorize Code
    type: password
    required: false
metrics:
  - name: available
    i18n:
      zh-CN: 可用性
      en-US: Available
    priority: 0
    fields:
      - field: responseTime
        type: 0
        unit: ms
    protocol: imap
    imap:
      host: ^_^host^_^
      port: ^_^port^_^
      timeout: ^_^timeout^_^
      ssl: ^_^ssl^_^
      email: ^_^email^_^
      authorize: ^_^authorize^_^
  - name: email_status
    i18n:
      zh-CN: 邮箱状态信息
      en-US: Email Status
    priority: 1
    fields:
      - field: email_count
        type: 0
      - field: mailbox_size
        type: 0
        unit: KB
    protocol: imap
    imap:
      host: ^_^host^_^
      port: ^_^port^_^
      timeout: ^_^timeout^_^
      ssl: ^_^ssl^_^
      email: ^_^email^_^
      authorize: ^_^authorize^_^
"""

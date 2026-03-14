"""
HertzBeat 数据模型定义
包含监控、告警、状态页、采集器等 23 张表
"""
import json
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, ForeignKey
from app import db


# ==================== 采集器管理 ====================

class Collector(db.Model):
    """采集器节点"""
    __tablename__ = "collectors"
    __table_args__ = (
        CheckConstraint("status in (0, 1)", name="ck_collectors_status"),
        CheckConstraint("mode in ('public', 'private')", name="ck_collectors_mode"),
        Index("idx_collectors_name", "name", unique=True),
        Index("idx_collectors_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    ip = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(50), nullable=True)
    status = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-online, 1-offline
    mode = db.Column(db.String(20), nullable=False, default="public")  # public/private
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CollectorMonitorBind(db.Model):
    """采集器-监控任务分配"""
    __tablename__ = "collector_monitor_binds"
    __table_args__ = (
        UniqueConstraint("collector", "monitor_id", name="uk_collector_monitor"),
        Index("idx_collector_monitor_collector", "collector"),
        Index("idx_collector_monitor_monitor_id", "monitor_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    collector = db.Column(db.String(100), nullable=False)
    monitor_id = db.Column(db.Integer, nullable=False)
    pinned = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-自动分配, 1-用户固定指定
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 监控配置 ====================

class Monitor(db.Model):
    """监控任务定义"""
    __tablename__ = "monitors"
    __table_args__ = (
        CheckConstraint("status in (0, 1, 2)", name="ck_monitors_status"),
        CheckConstraint("type in (0, 1, 2)", name="ck_monitors_type"),
        CheckConstraint("intervals >= 10", name="ck_monitors_intervals"),
        CheckConstraint("schedule_type in ('interval', 'cron')", name="ck_monitors_schedule_type"),
        Index("idx_monitors_app", "app"),
        Index("idx_monitors_instance", "instance"),
        Index("idx_monitors_name", "name"),
        Index("idx_monitors_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.BigInteger, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    app = db.Column(db.String(100), nullable=False)
    scrape = db.Column(db.String(100), nullable=True)  # static/http_sd/dns_sd/zookeeper_sd
    instance = db.Column(db.String(100), nullable=False)
    intervals = db.Column(db.Integer, nullable=False, default=60)
    schedule_type = db.Column(db.String(20), nullable=False, default="interval")
    cron_expression = db.Column(db.String(100), nullable=True)
    status = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-Paused, 1-Up, 2-Down
    type = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-Normal, 1-Push Auto, 2-Discovery Auto
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    annotations_json = db.Column(db.Text, nullable=False, default="{}")
    description = db.Column(db.String(255), nullable=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def labels(self) -> dict:
        try:
            return json.loads(self.labels_json or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def annotations(self) -> dict:
        try:
            return json.loads(self.annotations_json or "{}")
        except json.JSONDecodeError:
            return {}


class MonitorParam(db.Model):
    """监控任务参数"""
    __tablename__ = "monitor_params"
    __table_args__ = (
        UniqueConstraint("monitor_id", "field", name="uk_monitor_param"),
        CheckConstraint("type in (0, 1, 2, 3, 4)", name="ck_monitor_param_type"),
        Index("idx_monitor_params_monitor_id", "monitor_id"),
        Index("idx_monitor_params_field", "field"),
    )

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    field = db.Column(db.String(100), nullable=False)
    param_value = db.Column(db.String(8126), nullable=True)
    type = db.Column(db.SmallInteger, nullable=False, default=1)  # 0-number, 1-string, 2-encrypted, 3-json, 4-array
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitorBind(db.Model):
    """监控关系绑定"""
    __tablename__ = "monitor_binds"
    __table_args__ = (
        Index("idx_monitor_binds_biz_id", "biz_id"),
        Index("idx_monitor_binds_monitor_id", "monitor_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    key_str = db.Column(db.String(255), nullable=True)  # ip:port
    biz_id = db.Column(db.BigInteger, nullable=True)
    monitor_id = db.Column(db.Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitorDefine(db.Model):
    """监控模板定义"""
    __tablename__ = "monitor_defines"
    __table_args__ = (
        Index("idx_monitor_defines_app", "app"),
    )

    app = db.Column(db.String(100), primary_key=True)
    content = db.Column(db.Text, nullable=False)  # YAML format
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 基础数据 ====================

class Tag(db.Model):
    """监控标签"""
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("type in (0, 1, 2)", name="ck_tags_type"),
        UniqueConstraint("name", "tag_value", name="uk_tags_name_value"),
        Index("idx_tags_name", "name"),
        Index("idx_tags_type", "type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tag_value = db.Column(db.String(2048), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    type = db.Column(db.SmallInteger, nullable=False, default=1)  # 0-Auto, 1-User, 2-System
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 告警配置 ====================

class AlertDefine(db.Model):
    """告警规则定义"""
    __tablename__ = "alert_defines"
    __table_args__ = (
        CheckConstraint("type in ('realtime_metric', 'periodic_metric', 'realtime_log', 'periodic_log')", name="ck_alert_define_type"),
        CheckConstraint("times >= 1", name="ck_alert_define_times"),
        CheckConstraint("period >= 0", name="ck_alert_define_period"),
        Index("idx_alert_defines_name", "name"),
        Index("idx_alert_defines_type", "type"),
        Index("idx_alert_defines_enabled", "enabled"),
        Index("idx_alert_defines_notice_rule", "notice_rule_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="realtime_metric")
    expr = db.Column(db.String(2048), nullable=True)
    period = db.Column(db.Integer, nullable=True)
    times = db.Column(db.Integer, nullable=False, default=1)
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    annotations_json = db.Column(db.Text, nullable=False, default="{}")
    template = db.Column(db.String(2048), nullable=True)
    datasource_type = db.Column(db.String(100), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    # 关联通知规则
    notice_rule_id = db.Column(db.Integer, db.ForeignKey("notice_rules.id"), nullable=True)
    notice_rule = db.relationship("NoticeRule", backref="alert_defines", lazy="joined")
    notice_rule_ids_json = db.Column(db.Text, nullable=False, default="[]")
    escalation_config = db.Column(db.Text, nullable=False, default="")
    
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def labels(self) -> dict:
        try:
            return json.loads(self.labels_json or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def annotations(self) -> dict:
        try:
            return json.loads(self.annotations_json or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def notice_rule_ids(self) -> list[int]:
        try:
            raw = json.loads(self.notice_rule_ids_json or "[]")
        except json.JSONDecodeError:
            raw = []
        ids: list[int] = []
        if isinstance(raw, list):
            for item in raw:
                try:
                    val = int(item)
                except (TypeError, ValueError):
                    continue
                if val > 0:
                    ids.append(val)
        if not ids and self.notice_rule_id:
            ids = [int(self.notice_rule_id)]
        return ids


class AlertSilence(db.Model):
    """告警静默规则"""
    __tablename__ = "alert_silences"
    __table_args__ = (
        CheckConstraint("type in (0, 1)", name="ck_alert_silence_type"),
        CheckConstraint("match_type in (0, 1)", name="ck_alert_silence_match_type"),
        Index("idx_alert_silences_enabled", "enabled"),
        Index("idx_alert_silences_time", "start_time", "end_time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-one-time, 1-cyclic
    match_type = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-all, 1-partial
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    days_json = db.Column(db.Text, nullable=False, default="[]")  # 周期性静默的星期几 [1,2,3,4,5,6,7]
    times = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.BigInteger, nullable=True)
    end_time = db.Column(db.BigInteger, nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertInhibit(db.Model):
    """告警抑制规则"""
    __tablename__ = "alert_inhibits"
    __table_args__ = (
        Index("idx_alert_inhibits_enabled", "enabled"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source_labels_json = db.Column(db.Text, nullable=False, default="{}")
    target_labels_json = db.Column(db.Text, nullable=False, default="{}")
    equal_labels_json = db.Column(db.Text, nullable=False, default="{}")
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertGroup(db.Model):
    """告警分组收敛"""
    __tablename__ = "alert_groups"
    __table_args__ = (
        CheckConstraint("match_type in (0, 1)", name="ck_alert_group_match_type"),
        UniqueConstraint("group_key", name="uk_alert_groups_group_key"),
        Index("idx_alert_groups_group_key", "group_key", unique=True),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_key = db.Column(db.String(500), nullable=False, unique=True)
    match_type = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-all, 1-partial
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    group_wait = db.Column(db.Integer, nullable=True)
    group_interval = db.Column(db.Integer, nullable=True)
    repeat_interval = db.Column(db.Integer, nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertIntegration(db.Model):
    """外部告警集成配置 - 接收第三方系统告警"""
    __tablename__ = "alert_integrations"
    __table_args__ = (
        CheckConstraint("source in ('prometheus', 'zabbix', 'skywalking', 'nagios', 'custom')", name="ck_alert_integration_source"),
        CheckConstraint("auth_type in ('none', 'token', 'basic')", name="ck_alert_integration_auth_type"),
        Index("idx_alert_integrations_source", "source"),
        Index("idx_alert_integrations_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(50), nullable=False)  # prometheus, zabbix, skywalking, nagios, custom
    description = db.Column(db.String(500), nullable=True)
    webhook_token = db.Column(db.String(64), nullable=False, unique=True)  # Webhook URL 中的唯一标识
    severity_mapping = db.Column(db.Text, nullable=True)  # 级别映射配置，如 critical:critical\nwarning:warning
    default_labels = db.Column(db.Text, nullable=True)  # 默认标签，如 source=prometheus\nenv=production
    label_mapping = db.Column(db.Text, nullable=True)  # 标签映射规则，如 severity:level
    source_config = db.Column(db.Text, nullable=True)  # 源系统特定配置，JSON格式
    auth_type = db.Column(db.String(20), nullable=False, default="none")  # none, token, basic
    auth_token = db.Column(db.String(255), nullable=True)  # Token 认证时的密钥
    auth_username = db.Column(db.String(100), nullable=True)  # Basic Auth 用户名
    auth_password = db.Column(db.String(255), nullable=True)  # Basic Auth 密码
    status = db.Column(db.String(20), nullable=False, default="enabled")  # enabled, disabled
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def webhook_url(self) -> str:
        """生成 Webhook URL"""
        return f"/api/v1/alerts/webhook/{self.webhook_token}"


class NoticeRule(db.Model):
    """通知规则
    
    关联通知渠道(NoticeReceiver)来定义告警通知方式
    """
    __tablename__ = "notice_rules"
    __table_args__ = (
        CheckConstraint("notify_scale in ('single', 'batch')", name="ck_notice_rule_notify_scale"),
        Index("idx_notice_rules_receiver", "receiver_channel_id"),
        Index("idx_notice_rules_template", "template_id"),
        Index("idx_notice_rules_enable", "enable"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    receiver_channel_id = db.Column(db.Integer, db.ForeignKey("notice_receivers.id"), nullable=False)  # 关联的通知渠道ID
    receiver_name = db.Column(db.String(100), nullable=True)  # 接收者名称，用于显示
    receiver_type = db.Column(db.Integer, nullable=True)  # 渠道类型，用于显示
    notify_times = db.Column(db.Integer, nullable=True, default=1)
    notify_scale = db.Column(db.String(20), nullable=False, default="single")
    template_id = db.Column(db.Integer, nullable=True)  # 关联的通知模板ID
    template_name = db.Column(db.String(100), nullable=True)  # 模板名称，用于显示
    filter_all = db.Column(db.Boolean, nullable=False, default=True)  # 是否转发所有告警
    labels_json = db.Column(db.Text, nullable=False, default="{}")  # 标签过滤条件，如 {"severity": "critical"}
    days_json = db.Column(db.Text, nullable=False, default="[1,2,3,4,5,6,7]")  # 生效星期几 [1,2,3,4,5,6,7]
    period_start = db.Column(db.String(8), nullable=True)  # 生效时间开始，格式 HH:MM:SS
    period_end = db.Column(db.String(8), nullable=True)  # 生效时间结束，格式 HH:MM:SS
    recipient_type = db.Column(db.String(20), nullable=False, default="user")  # user/department
    recipient_ids_json = db.Column(db.Text, nullable=False, default="[]")  # 用户/部门ID列表
    include_sub_departments = db.Column(db.Boolean, nullable=False, default=True)
    enable = db.Column(db.Boolean, nullable=False, default=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    receiver = db.relationship("NoticeReceiver", backref="rules", lazy="joined")

    @property
    def labels(self) -> dict:
        try:
            return json.loads(self.labels_json or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def days(self) -> list:
        try:
            return json.loads(self.days_json or "[1,2,3,4,5,6,7]")
        except json.JSONDecodeError:
            return [1, 2, 3, 4, 5, 6, 7]

    @property
    def recipient_ids(self) -> list:
        try:
            return json.loads(self.recipient_ids_json or "[]")
        except json.JSONDecodeError:
            return []
    
    def to_dict(self) -> dict:
        """转换为字典，包含关联的渠道信息"""
        return {
            "id": self.id,
            "name": self.name,
            "receiver_channel_id": self.receiver_channel_id,
            "receiver_id": self.receiver_channel_id,  # 兼容前端字段名
            "receiver_name": self.receiver_name or (self.receiver.name if self.receiver else None),
            "receiver_type": self.receiver_type or (self.receiver.type if self.receiver else None),
            "notify_times": self.notify_times,
            "notify_scale": self.notify_scale,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "filter_all": self.filter_all,
            "labels": self.labels,
            "days": self.days,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "recipient_type": self.recipient_type,
            "recipient_ids": self.recipient_ids,
            "include_sub_departments": bool(self.include_sub_departments),
            "enable": self.enable,
            "creator": self.creator,
            "modifier": self.modifier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NoticeReceiver(db.Model):
    """通知接收人/通知渠道配置
    
    支持多种通知渠道类型，每种类型使用不同的配置字段
    """
    __tablename__ = "notice_receivers"
    __table_args__ = (
        Index("idx_notice_receivers_name", "name"),
        Index("idx_notice_receivers_type", "type"),
        Index("idx_notice_receivers_enable", "enable"),
    )

    # 通知渠道类型定义
    TYPE_SMS = 0           # 短信
    TYPE_EMAIL = 1         # 邮件
    TYPE_WEBHOOK = 2       # Webhook
    TYPE_WECHAT = 3        # 微信公众号
    TYPE_WECOM_ROBOT = 4   # 企业微信机器人
    TYPE_DINGTALK = 5      # 钉钉机器人
    TYPE_FEISHU = 6        # 飞书机器人
    TYPE_TELEGRAM = 7      # Telegram机器人 (已移除)
    TYPE_SLACK = 8         # Slack
    TYPE_DISCORD = 9       # Discord
    TYPE_WECOM_APP = 10    # 企业微信应用
    TYPE_SMN = 11          # 华为云SMN
    TYPE_SERVERCHAN = 12   # Server酱
    TYPE_GOTIFY = 13       # Gotify
    TYPE_FEISHU_APP = 14   # 飞书应用
    TYPE_SYSTEM = 15       # 系统通知
    
    TYPE_CHOICES = {
        TYPE_SMS: "短信",
        TYPE_EMAIL: "邮件",
        TYPE_WEBHOOK: "Webhook",
        TYPE_WECHAT: "微信公众号",
        TYPE_WECOM_ROBOT: "企业微信机器人",
        TYPE_DINGTALK: "钉钉机器人",
        TYPE_FEISHU: "飞书机器人",
        TYPE_SLACK: "Slack",
        TYPE_DISCORD: "Discord",
        TYPE_WECOM_APP: "企业微信应用",
        TYPE_SMN: "华为云SMN",
        TYPE_SERVERCHAN: "Server酱",
        TYPE_GOTIFY: "Gotify",
        TYPE_FEISHU_APP: "飞书应用",
        TYPE_SYSTEM: "系统通知",
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.SmallInteger, nullable=False, default=TYPE_EMAIL)
    enable = db.Column(db.Boolean, nullable=False, default=True)
    
    # 通用字段
    description = db.Column(db.String(500), nullable=True)
    
    # 邮件配置 (type=1)
    smtp_host = db.Column(db.String(255), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True, default=587)
    smtp_username = db.Column(db.String(255), nullable=True)
    smtp_password = db.Column(db.String(255), nullable=True)
    smtp_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    email_from = db.Column(db.String(255), nullable=True)  # 发件人地址
    email_to = db.Column(db.String(1000), nullable=True)   # 收件人地址（多个用逗号分隔）
    
    # Webhook配置 (type=2)
    hook_url = db.Column(db.String(1000), nullable=True)
    hook_auth_type = db.Column(db.String(50), nullable=True)  # None, Basic, Bearer
    hook_auth_token = db.Column(db.String(500), nullable=True)
    hook_method = db.Column(db.String(10), nullable=False, default="POST")  # GET/POST
    hook_content_type = db.Column(db.String(50), nullable=False, default="application/json")
    
    # 企业微信机器人配置 (type=4)
    wecom_key = db.Column(db.String(500), nullable=True)   # 机器人key
    wecom_mentioned_mobiles = db.Column(db.String(500), nullable=True)  # @手机号列表
    
    # 企业微信应用配置 (type=10)
    wecom_corp_id = db.Column(db.String(500), nullable=True)
    wecom_agent_id = db.Column(db.String(100), nullable=True)
    wecom_app_secret = db.Column(db.String(500), nullable=True)
    wecom_to_user = db.Column(db.String(1000), nullable=True)   # 指定成员
    wecom_to_party = db.Column(db.String(1000), nullable=True)  # 指定部门
    wecom_to_tag = db.Column(db.String(1000), nullable=True)    # 指定标签
    
    # 钉钉机器人配置 (type=5)
    dingtalk_access_token = db.Column(db.String(500), nullable=True)
    dingtalk_secret = db.Column(db.String(500), nullable=True)  # 加签密钥
    dingtalk_at_mobiles = db.Column(db.String(500), nullable=True)  # @手机号
    dingtalk_is_at_all = db.Column(db.Boolean, nullable=False, default=False)
    
    # 飞书机器人配置 (type=6)
    feishu_webhook_token = db.Column(db.String(500), nullable=True)
    feishu_secret = db.Column(db.String(500), nullable=True)  # 加签密钥
    
    # 飞书应用配置 (type=14)
    feishu_app_id = db.Column(db.String(500), nullable=True)
    feishu_app_secret = db.Column(db.String(500), nullable=True)
    feishu_receive_type = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-user, 1-chat
    feishu_user_id = db.Column(db.String(500), nullable=True)
    feishu_chat_id = db.Column(db.String(500), nullable=True)
    
    # Slack配置 (type=8)
    slack_webhook_url = db.Column(db.String(1000), nullable=True)
    
    # Discord配置 (type=9)
    discord_webhook_url = db.Column(db.String(1000), nullable=True)
    
    # 短信配置 (type=0)
    sms_provider = db.Column(db.String(50), nullable=True)  # aliyun, tencent, huawei
    sms_access_key = db.Column(db.String(500), nullable=True)
    sms_secret_key = db.Column(db.String(500), nullable=True)
    sms_sign_name = db.Column(db.String(100), nullable=True)
    sms_template_code = db.Column(db.String(100), nullable=True)
    sms_phone_numbers = db.Column(db.String(1000), nullable=True)  # 手机号列表
    
    # 华为云SMN配置 (type=11)
    smn_ak = db.Column(db.String(500), nullable=True)  # Access Key
    smn_sk = db.Column(db.String(500), nullable=True)  # Secret Key
    smn_project_id = db.Column(db.String(500), nullable=True)
    smn_region = db.Column(db.String(100), nullable=True)
    smn_topic_urn = db.Column(db.String(500), nullable=True)
    
    # Server酱配置 (type=12)
    serverchan_send_key = db.Column(db.String(500), nullable=True)
    
    # Gotify配置 (type=13)
    gotify_url = db.Column(db.String(1000), nullable=True)
    gotify_token = db.Column(db.String(500), nullable=True)
    gotify_priority = db.Column(db.Integer, nullable=False, default=5)
    
    # 审计字段
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def type_name(self) -> str:
        return self.TYPE_CHOICES.get(self.type, "未知")
    
    @property
    def type_icon(self) -> str:
        """获取渠道类型的图标"""
        icons = {
            self.TYPE_SMS: "message",
            self.TYPE_EMAIL: "mail",
            self.TYPE_WEBHOOK: "global",
            self.TYPE_WECHAT: "wechat",
            self.TYPE_WECOM_ROBOT: "robot",
            self.TYPE_DINGTALK: "dingding",
            self.TYPE_FEISHU: "feishu",
            self.TYPE_SLACK: "slack",
            self.TYPE_DISCORD: "discord",
            self.TYPE_WECOM_APP: "wecom",
            self.TYPE_SMN: "cloud",
            self.TYPE_SERVERCHAN: "notification",
            self.TYPE_GOTIFY: "mobile",
            self.TYPE_FEISHU_APP: "feishu",
            self.TYPE_SYSTEM: "notification",
        }
        return icons.get(self.type, "notification")
    
    def to_dict(self) -> dict:
        """转换为字典，根据类型返回相关配置"""
        base = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "type_name": self.type_name,
            "enable": self.enable,
            "description": self.description,
            "creator": self.creator,
            "modifier": self.modifier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # 根据类型添加特定配置
        if self.type == self.TYPE_EMAIL:
            base["config"] = {
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "smtp_username": self.smtp_username,
                "smtp_use_tls": self.smtp_use_tls,
                "email_from": self.email_from,
                "email_to": self.email_to,
            }
        elif self.type == self.TYPE_WEBHOOK:
            base["config"] = {
                "hook_url": self.hook_url,
                "hook_auth_type": self.hook_auth_type,
                "hook_method": self.hook_method,
                "hook_content_type": self.hook_content_type,
            }
        elif self.type == self.TYPE_WECOM_ROBOT:
            base["config"] = {
                "wecom_key": self.wecom_key,
                "wecom_mentioned_mobiles": self.wecom_mentioned_mobiles,
            }
        elif self.type == self.TYPE_WECOM_APP:
            base["config"] = {
                "wecom_corp_id": self.wecom_corp_id,
                "wecom_agent_id": self.wecom_agent_id,
                "wecom_to_user": self.wecom_to_user,
                "wecom_to_party": self.wecom_to_party,
                "wecom_to_tag": self.wecom_to_tag,
            }
        elif self.type == self.TYPE_DINGTALK:
            base["config"] = {
                "dingtalk_access_token": self.dingtalk_access_token,
                "dingtalk_at_mobiles": self.dingtalk_at_mobiles,
                "dingtalk_is_at_all": self.dingtalk_is_at_all,
            }
        elif self.type == self.TYPE_FEISHU:
            base["config"] = {
                "feishu_webhook_token": self.feishu_webhook_token,
            }
        elif self.type == self.TYPE_FEISHU_APP:
            base["config"] = {
                "feishu_app_id": self.feishu_app_id,
                "feishu_receive_type": self.feishu_receive_type,
                "feishu_user_id": self.feishu_user_id,
                "feishu_chat_id": self.feishu_chat_id,
            }
        elif self.type == self.TYPE_SLACK:
            base["config"] = {
                "slack_webhook_url": self.slack_webhook_url,
            }
        elif self.type == self.TYPE_DISCORD:
            base["config"] = {
                "discord_webhook_url": self.discord_webhook_url,
            }
        elif self.type == self.TYPE_SMS:
            base["config"] = {
                "sms_provider": self.sms_provider,
                "sms_sign_name": self.sms_sign_name,
                "sms_template_code": self.sms_template_code,
                "sms_phone_numbers": self.sms_phone_numbers,
            }
        elif self.type == self.TYPE_SMN:
            base["config"] = {
                "smn_region": self.smn_region,
                "smn_topic_urn": self.smn_topic_urn,
            }
        elif self.type == self.TYPE_SERVERCHAN:
            base["config"] = {
                "serverchan_send_key": self.serverchan_send_key,
            }
        elif self.type == self.TYPE_GOTIFY:
            base["config"] = {
                "gotify_url": self.gotify_url,
                "gotify_priority": self.gotify_priority,
            }
        
        return base


class NoticeTemplate(db.Model):
    """通知模板"""
    __tablename__ = "notice_templates"
    __table_args__ = (
        Index("idx_notice_templates_name", "name"),
        Index("idx_notice_templates_type", "type"),
        Index("idx_notice_templates_preset", "preset"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.SmallInteger, nullable=False)  # 0-SMS, 1-Email, 2-Webhook, ...
    preset = db.Column(db.Boolean, nullable=False, default=False)
    content = db.Column(db.Text, nullable=False)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertLabel(db.Model):
    """告警标签"""
    __tablename__ = "alert_labels"
    __table_args__ = (
        UniqueConstraint("name", "value", name="uk_alert_labels_name_value"),
        Index("idx_alert_labels_name_value", "name", "value", unique=True),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(2048), nullable=False)
    color = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 状态页 ====================

class StatusPageOrg(db.Model):
    """状态页组织"""
    __tablename__ = "status_page_orgs"
    __table_args__ = (
        CheckConstraint("state in (0, 1, 2)", name="ck_status_page_org_state"),
        Index("idx_status_page_orgs_name", "name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    home = db.Column(db.String(500), nullable=False)
    logo = db.Column(db.String(500), nullable=False)
    feedback = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    state = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-All Operational, 1-Some Abnormal, 2-All Abnormal
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class StatusPageComponent(db.Model):
    """状态页组件"""
    __tablename__ = "status_page_components"
    __table_args__ = (
        CheckConstraint("method in (0, 1)", name="ck_status_page_component_method"),
        CheckConstraint("config_state in (0, 1, 2)", name="ck_status_page_component_config_state"),
        Index("idx_status_page_components_org_id", "org_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, ForeignKey("status_page_orgs.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    method = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-auto, 1-manual
    config_state = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-Normal, 1-Abnormal, 2-unknown
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class StatusPageIncident(db.Model):
    """状态页事件"""
    __tablename__ = "status_page_incidents"
    __table_args__ = (
        CheckConstraint("state in (0, 1, 2, 3)", name="ck_status_page_incident_state"),
        Index("idx_status_page_incidents_org_id", "org_id"),
        Index("idx_status_page_incidents_state", "state"),
    )

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, ForeignKey("status_page_orgs.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-Investigating, 1-Identified, 2-Monitoring, 3-Resolved
    start_time = db.Column(db.BigInteger, nullable=True)
    end_time = db.Column(db.BigInteger, nullable=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 运行时数据 ====================

class SingleAlert(db.Model):
    """单条告警实例"""
    __tablename__ = "single_alerts"
    __table_args__ = (
        CheckConstraint("status in ('firing', 'resolved')", name="ck_single_alerts_status"),
        CheckConstraint("trigger_times >= 1", name="ck_single_alerts_trigger_times"),
        UniqueConstraint("fingerprint", name="uk_single_alerts_fingerprint"),
        Index("idx_single_alerts_fingerprint", "fingerprint", unique=True),
        Index("idx_single_alerts_status", "status"),
        Index("idx_single_alerts_time", "start_at", "end_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    fingerprint = db.Column(db.String(2048), nullable=False, unique=True)
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    annotations_json = db.Column(db.Text, nullable=False, default="{}")
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="firing")
    trigger_times = db.Column(db.Integer, nullable=False, default=1)
    start_at = db.Column(db.BigInteger, nullable=True)
    active_at = db.Column(db.BigInteger, nullable=True)
    end_at = db.Column(db.BigInteger, nullable=True)
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def labels(self) -> dict:
        try:
            return json.loads(self.labels_json or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def annotations(self) -> dict:
        try:
            return json.loads(self.annotations_json or "{}")
        except json.JSONDecodeError:
            return {}


class GroupAlert(db.Model):
    """分组告警"""
    __tablename__ = "group_alerts"
    __table_args__ = (
        CheckConstraint("status in ('firing', 'resolved')", name="ck_group_alerts_status"),
        UniqueConstraint("group_key", name="uk_group_alerts_group_key"),
        Index("idx_group_alerts_group_key", "group_key", unique=True),
        Index("idx_group_alerts_status", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    group_key = db.Column(db.String(2048), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default="firing")
    group_labels_json = db.Column(db.Text, nullable=False, default="{}")
    common_labels_json = db.Column(db.Text, nullable=False, default="{}")
    common_annotations_json = db.Column(db.Text, nullable=False, default="{}")
    alert_fingerprints_json = db.Column(db.Text, nullable=False, default="[]")
    creator = db.Column(db.String(100), nullable=True)
    modifier = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertHistory(db.Model):
    """告警历史"""
    __tablename__ = "alert_history"
    __table_args__ = (
        CheckConstraint("alert_type in ('single', 'group')", name="ck_alert_history_alert_type"),
        CheckConstraint("status in ('firing', 'resolved')", name="ck_alert_history_status"),
        Index("idx_alert_history_alert_id", "alert_id"),
        Index("idx_alert_history_type", "alert_type"),
        Index("idx_alert_history_status", "status"),
        Index("idx_alert_history_time", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # single/group
    labels_json = db.Column(db.Text, nullable=False, default="{}")
    annotations_json = db.Column(db.Text, nullable=False, default="{}")
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False)
    trigger_times = db.Column(db.Integer, nullable=False, default=1)
    start_at = db.Column(db.BigInteger, nullable=True)
    end_at = db.Column(db.BigInteger, nullable=True)
    duration_ms = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AlertNotification(db.Model):
    """告警通知记录"""
    __tablename__ = "alert_notifications"
    __table_args__ = (
        CheckConstraint("status in (0, 1, 2, 3)", name="ck_alert_notifications_status"),
        CheckConstraint("notify_type in ('email', 'sms', 'webhook', 'wecom', 'dingtalk', 'feishu')", name="ck_alert_notifications_notify_type"),
        Index("idx_alert_notifications_alert_id", "alert_id"),
        Index("idx_alert_notifications_status", "status"),
        Index("idx_alert_notifications_time", "sent_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, nullable=False)
    rule_id = db.Column(db.Integer, nullable=True)
    receiver_type = db.Column(db.String(20), nullable=True)
    receiver_id = db.Column(db.Integer, nullable=True)
    notify_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-pending, 1-sending, 2-success, 3-failed
    content = db.Column(db.Text, nullable=True)
    error_msg = db.Column(db.Text, nullable=True)
    retry_times = db.Column(db.Integer, nullable=False, default=0)
    sent_at = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 数据仓库 ====================

class MetricsHistory(db.Model):
    """指标历史数据"""
    __tablename__ = "metrics_history"
    __table_args__ = (
        CheckConstraint("metric_type in (0, 1)", name="ck_metrics_history_metric_type"),
        Index("idx_metrics_history_instance", "instance"),
        Index("idx_metrics_history_app", "app"),
        Index("idx_metrics_history_metrics", "metrics"),
        Index("idx_metrics_history_metric", "metric"),
        Index("idx_metrics_history_time", "timestamp"),
        Index("idx_metrics_history_query", "instance", "app", "metrics", "metric", "timestamp"),
    )

    id = db.Column(db.Integer, primary_key=True)
    instance = db.Column(db.String(255), nullable=False)
    app = db.Column(db.String(100), nullable=False)
    metrics = db.Column(db.String(100), nullable=False)
    metric = db.Column(db.String(100), nullable=False)
    metric_labels_json = db.Column(db.Text, nullable=False, default="{}")
    metric_type = db.Column(db.SmallInteger, nullable=False, default=0)  # 0-Number, 1-String
    str_value = db.Column(db.String(2048), nullable=True)
    int32_value = db.Column(db.Integer, nullable=True)
    double_value = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.BigInteger, nullable=False)

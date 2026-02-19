"""通知模块工具函数"""

from datetime import datetime
from typing import Optional
import markdown
import bleach


# Allowed HTML tags for notification content
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "a",
    "ul",
    "ol",
    "li",
    "code",
    "pre",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"], "code": ["class"]}


def render_markdown(content: str) -> str:
    """将Markdown内容渲染为安全HTML

    Args:
        content: Markdown格式的文本内容

    Returns:
        净化后的HTML字符串
    """
    # Convert markdown to HTML
    html = markdown.markdown(
        content, extensions=["nl2br", "fenced_code", "tables"], safe_mode="escape"
    )

    # Clean HTML to prevent XSS
    clean_html = bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )

    return clean_html


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """格式化日期时间为ISO格式字符串

    Args:
        dt: datetime对象

    Returns:
        ISO格式字符串或None
    """
    if dt:
        return dt.isoformat()
    return None


def parse_datetime(date_string: str) -> Optional[datetime]:
    """解析ISO格式日期时间字符串

    Args:
        date_string: ISO格式日期时间字符串

    Returns:
        datetime对象或None
    """
    if not date_string:
        return None

    try:
        # Try ISO format
        return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except ValueError:
        try:
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
        except Exception:
            pass

    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def validate_notification_content(
    title: str, content: str
) -> tuple[bool, Optional[str]]:
    """验证通知内容

    Args:
        title: 通知标题
        content: 通知内容

    Returns:
        (是否有效, 错误信息)
    """
    if not title or not title.strip():
        return False, "标题不能为空"

    if len(title) > 255:
        return False, "标题不能超过255个字符"

    if not content or not content.strip():
        return False, "内容不能为空"

    if len(content) > 10000:
        return False, "内容不能超过10000个字符"

    return True, None

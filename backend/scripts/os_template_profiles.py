from __future__ import annotations

OS_TEMPLATE_META: dict[str, dict[str, str]] = {
    "linux": {"name_zh": "Linux操作系统", "name_en": "OS Linux", "profile": "server"},
    "ubuntu": {"name_zh": "Ubuntu操作系统", "name_en": "OS Ubuntu", "profile": "server"},
    "debian": {"name_zh": "Debian操作系统", "name_en": "OS Debian", "profile": "server"},
    "centos": {"name_zh": "CentOS操作系统", "name_en": "OS CentOS", "profile": "server"},
    "almalinux": {"name_zh": "AlmaLinux操作系统", "name_en": "OS AlmaLinux", "profile": "server"},
    "opensuse": {"name_zh": "OpenSUSE操作系统", "name_en": "OS OpenSUSE", "profile": "server"},
    "freebsd": {"name_zh": "FreeBSD操作系统", "name_en": "OS FreeBSD", "profile": "server"},
    "redhat": {"name_zh": "RedHat操作系统", "name_en": "OS RedHat", "profile": "server"},
    "rockylinux": {"name_zh": "Rocky Linux操作系统", "name_en": "OS Rocky Linux", "profile": "server"},
    "euleros": {"name_zh": "EulerOS操作系统", "name_en": "OS EulerOS", "profile": "server"},
    "fedora": {"name_zh": "Fedora操作系统", "name_en": "OS Fedora", "profile": "server"},
    "darwin": {"name_zh": "Darwin操作系统", "name_en": "OS Darwin", "profile": "desktop"},
    "macos": {"name_zh": "macOS操作系统", "name_en": "OS macOS", "profile": "desktop"},
    "windows": {"name_zh": "Windows操作系统", "name_en": "OS Windows", "profile": "windows"},
    "nvidia": {"name_zh": "NVIDIA GPU主机", "name_en": "NVIDIA GPU Host", "profile": "gpu"},
}

OS_TARGET_APPS: list[str] = list(OS_TEMPLATE_META.keys())

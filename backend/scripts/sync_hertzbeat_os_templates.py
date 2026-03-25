#!/usr/bin/env python3
"""
同步 HertzBeat 操作系统模板到本项目：
1) 默认保留本地模板（除非触发强制重建名单）
2) 本地缺失时从 define/app-*.yml 复制
3) 缺失源模板时按规则兜底（fedora <- linux）
4) 注入 OS 默认 alerts
5) Upsert 到 monitor_templates
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

from scripts.apply_os_default_alerts import POLICIES, _render_alerts, _upsert_alerts
from scripts.os_template_profiles import OS_TARGET_APPS


# 本次用户指定：统一按 Ubuntu 的单 bundle 方式改造的 OS 模板
BUNDLE_OS_APPS = {
    "linux",
    "ubuntu",
    "debian",
    "centos",
    "almalinux",
    "opensuse",
    "freebsd",
    "redhat",
    "rockylinux",
    "euleros",
    "fedora",
    "darwin",
}


def _parse_template_meta(content: str, fallback_app: str) -> tuple[str, str, str]:
    app_match = re.search(r"^app:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    app = (app_match.group(1).strip().lower() if app_match else fallback_app) or fallback_app

    category_match = re.search(r"^category:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    category = (category_match.group(1).strip().lower() if category_match else "os") or "os"

    name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*zh-CN:\s*([^\n]+)", content, flags=re.MULTILINE)
    if not name_match:
        name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*en-US:\s*([^\n]+)", content, flags=re.MULTILINE)
    name = (name_match.group(1).strip() if name_match else app) or app
    return app, name, category


def _derive_fedora_from_linux(src_dir: Path, dst: Path) -> bool:
    linux_src = src_dir / "app-linux.yml"
    if not linux_src.exists():
        return False
    raw = linux_src.read_text(encoding="utf-8")
    raw = re.sub(r"(?m)^app:\s*linux\s*$", "app: fedora", raw)
    raw = re.sub(r"(?m)^  zh-CN:\s*Linux\s*$", "  zh-CN: Fedora", raw)
    raw = re.sub(r"(?m)^  en-US:\s*Linux\s*$", "  en-US: Fedora", raw)
    raw = raw.replace("新建 Linux", "新建 Fedora")
    raw = raw.replace("New Linux", "New Fedora")
    raw = re.sub(r"(?m)(/help/)linux\b", r"\1fedora", raw)
    dst.write_text(raw, encoding="utf-8")
    return True


def _is_arco_slim_os_template(content: str) -> bool:
    raw = str(content or "")
    return ("- name: system_basic" in raw or "- name: load" in raw) and ("- name: basic" not in raw)


def _enhance_unix_interface(content: str) -> str:
    """统一补充 interface 的 ip/mac 字段，并让 interface script 输出 5 列。"""
    raw = str(content or "")
    if "- name: interface" not in raw:
        return raw

    metric_match = re.search(r"(?ms)^  - name: interface\n.*?(?=^  - name: |^alerts:|\Z)", raw)
    if not metric_match:
        return raw
    block = metric_match.group(0)

    if "field: ip_address" not in block:
        block = re.sub(
            r"(?m)^(\s*- field: receive_bytes\s*\n)",
            (
                "      - field: ip_address\n"
                "        type: 1\n"
                "        i18n:\n"
                "          zh-CN: IP地址\n"
                "          en-US: IP Address\n"
                "          ja-JP: IPアドレス\n"
                "      - field: mac_address\n"
                "        type: 1\n"
                "        i18n:\n"
                "          zh-CN: MAC地址\n"
                "          en-US: MAC Address\n"
                "          ja-JP: MACアドレス\n"
                r"\1"
            ),
            block,
            count=1,
        )

    script_line = (
        "      script: echo \"interface_name ip_address mac_address receive_bytes transmit_bytes\"; "
        "tail -n +3 /proc/net/dev 2>/dev/null | while read -r iface rest; do iface=${iface%:}; [ -z \"$iface\" ] && continue; "
        "set -- $rest; rx=$1; tx=$9; ip=$(ip -o -4 addr show dev \"$iface\" 2>/dev/null | awk '{print $4}' | head -n 1 | cut -d/ -f1); "
        "[ -z \"$ip\" ] && ip=$(ifconfig \"$iface\" 2>/dev/null | awk '/inet /{for(i=1;i<=NF;i++){if($i==\"inet\"){print $(i+1);exit} if(index($i,\"addr:\")==1){sub(\"addr:\",\"\",$i);print $i;exit}}}' | head -n 1); "
        "[ -z \"$ip\" ] && ip=-; mac=$(cat /sys/class/net/\"$iface\"/address 2>/dev/null | tr 'A-Z' 'a-z'); "
        "[ -z \"$mac\" ] && mac=$(ifconfig \"$iface\" 2>/dev/null | awk '/(ether|HWaddr)/{for(i=1;i<=NF;i++){if($i==\"ether\"||$i==\"HWaddr\"){print $(i+1);exit}}}' | tr 'A-Z' 'a-z' | head -n 1); "
        "[ -z \"$mac\" ] && mac=-; [ -z \"$rx\" ] && rx=0; [ -z \"$tx\" ] && tx=0; echo \"$iface $ip $mac $rx $tx\"; done"
    )

    block = re.sub(r"(?m)^\s{6}script:\s*.*$", script_line, block, count=1)
    return raw[: metric_match.start()] + block + raw[metric_match.end() :]


def _extract_script_from_metric_block(metric_block: str) -> str:
    block = str(metric_block or "")
    pipe_match = re.search(r"(?ms)^\s{6}script:\s*\|[^\n]*\n(?P<body>(?:\s{8}.*\n)*)", block)
    if pipe_match:
        body = pipe_match.group("body")
        lines = []
        for line in body.splitlines():
            if line.startswith("        "):
                lines.append(line[8:])
            else:
                lines.append(line)
        return "\n".join(lines).rstrip("\n")
    line_match = re.search(r"(?m)^\s{6}script:\s*(.*)$", block)
    if line_match:
        return line_match.group(1).strip()
    return ""


def _collect_ssh_metric_scripts(content: str) -> list[tuple[str, str]]:
    raw = str(content or "")
    out: list[tuple[str, str]] = []
    for mm in re.finditer(r"(?ms)^  - name: (?P<name>[A-Za-z0-9_]+)\n(?P<body>.*?)(?=^  - name: |^alerts:|\Z)", raw):
        name = mm.group("name").strip()
        body = mm.group("body")
        if not re.search(r"(?m)^\s{4}protocol:\s*ssh\s*$", body):
            continue
        script = _extract_script_from_metric_block(body)
        if script.strip():
            out.append((name, script))
    return out


def _build_bundle_script(metric_scripts: list[tuple[str, str]]) -> str:
    lines = ["set +e"]
    for metric_name, script in metric_scripts:
        lines.append("")
        lines.append(f'echo "__ARCO_SECTION_BEGIN__{metric_name}"')
        lines.extend(script.splitlines())
        lines.append(f'echo "__ARCO_SECTION_END__{metric_name}"')
    return "\n".join(lines)


def _render_bundle_param_block(bundle_script: str) -> str:
    lines = [
        "  - field: bundleScript",
        "    name:",
        "      zh-CN: 统一快照脚本",
        "      en-US: Bundle Snapshot Script",
        "      ja-JP: バンドルスナップショットスクリプト",
        "    type: textarea",
        "    required: true",
        "    hide: true",
        "    defaultValue: |-",
    ]
    for line in bundle_script.splitlines():
        lines.append("      " + line)
    return "\n".join(lines)


def _upsert_bundle_param(content: str, bundle_script: str) -> str:
    raw = str(content or "")
    bundle_block = _render_bundle_param_block(bundle_script)
    if "  - field: bundleScript" in raw:
        raw = re.sub(
            r"(?ms)^  - field: bundleScript\n.*?(?=^  - field: [A-Za-z0-9_]+\n)",
            bundle_block + "\n",
            raw,
            count=1,
        )
        return raw
    if "  - field: reuseConnection\n" in raw:
        return raw.replace("  - field: reuseConnection\n", bundle_block + "\n  - field: reuseConnection\n", 1)
    if "  - field: useProxy\n" in raw:
        return raw.replace("  - field: useProxy\n", bundle_block + "\n  - field: useProxy\n", 1)
    return raw


def _ensure_metric_bundle(content: str, metric_name: str) -> str:
    raw = str(content or "")
    metric_match = re.search(
        rf"(?ms)^  - name: {re.escape(metric_name)}\n.*?(?=^  - name: |^alerts:|\Z)",
        raw,
    )
    if not metric_match:
        return raw
    block = metric_match.group(0)

    if "bundleScript: ^_^bundleScript^_^" not in block or f"bundleSection: {metric_name}" not in block:
        injected = re.sub(
            r"(?m)^(\s*timeout:\s*[^\n]+\s*)$",
            (
                r"\1\n"
                "      bundleScript: ^_^bundleScript^_^\n"
                f"      bundleSection: {metric_name}"
            ),
            block,
            count=1,
        )
        if injected == block:
            injected = re.sub(
                r"(?m)^(\s*reuseConnection:\s*[^\n]+\s*)$",
                (
                    "      bundleScript: ^_^bundleScript^_^\n"
                    f"      bundleSection: {metric_name}\n"
                    r"\1"
                ),
                block,
                count=1,
            )
        block = injected

    # 移除旧 per-metric script（支持一行与块样式）
    block = re.sub(r"(?ms)^\s{6}script:\s*\|[^\n]*\n(?:\s{8,}.*\n)*", "", block)
    block = re.sub(r"(?m)^\s{6}script:\s*.*\n?", "", block)

    return raw[: metric_match.start()] + block + raw[metric_match.end() :]


def _ensure_os_bundle(content: str) -> str:
    raw = str(content or "")
    metric_scripts = _collect_ssh_metric_scripts(raw)
    if not metric_scripts:
        return raw
    bundle_script = _build_bundle_script(metric_scripts)
    raw = _upsert_bundle_param(raw, bundle_script)
    for metric_name, _ in metric_scripts:
        raw = _ensure_metric_bundle(raw, metric_name)
    return raw


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    src_dir = repo_root / "hertzbeat-master" / "hertzbeat-manager" / "src" / "main" / "resources" / "define"
    dst_dir = backend_dir / "templates"
    dst_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(backend_dir))
    from app import create_app
    from app.services.template_service import template_service

    preserved_local = []
    replaced_slim_local = []
    copied_from_source = []
    synthesized_fallback = []
    missing = []

    for app in OS_TARGET_APPS:
        src = src_dir / f"app-{app}.yml"
        dst = dst_dir / f"app-{app}.yml"
        has_local = dst.exists() and bool(dst.read_text(encoding="utf-8").strip())
        local_raw = dst.read_text(encoding="utf-8") if has_local else ""

        force_bundle_rebuild = app in BUNDLE_OS_APPS
        if force_bundle_rebuild and src.exists():
            shutil.copy2(src, dst)
            copied_from_source.append(app)
        elif force_bundle_rebuild and app == "fedora" and _derive_fedora_from_linux(src_dir, dst):
            synthesized_fallback.append(app)
        elif has_local and _is_arco_slim_os_template(local_raw) and src.exists():
            shutil.copy2(src, dst)
            replaced_slim_local.append(app)
            copied_from_source.append(app)
        elif has_local:
            preserved_local.append(app)
        elif src.exists():
            shutil.copy2(src, dst)
            copied_from_source.append(app)
        else:
            missing.append(str(src))
            if app == "fedora" and _derive_fedora_from_linux(src_dir, dst):
                synthesized_fallback.append(app)
            else:
                raise FileNotFoundError(f"source template missing and no fallback available: {src}")

        if app not in {"windows", "nvidia"}:
            raw = dst.read_text(encoding="utf-8")
            raw = _enhance_unix_interface(raw)
            if app in BUNDLE_OS_APPS:
                raw = _ensure_os_bundle(raw)
            dst.write_text(raw, encoding="utf-8")

        if app in POLICIES:
            raw = dst.read_text(encoding="utf-8")
            merged = _upsert_alerts(raw, _render_alerts(POLICIES[app]))
            dst.write_text(merged, encoding="utf-8")

    flask_app = create_app()
    upserted = []
    with flask_app.app_context():
        template_service.initialize()
        template_service.save_category("操作系统", "os", "desktop")
        for app in OS_TARGET_APPS:
            filepath = dst_dir / f"app-{app}.yml"
            content = filepath.read_text(encoding="utf-8")
            app_key, name, category = _parse_template_meta(content, app)
            template_service.save_template(app_key, name, category, content)
            upserted.append(app_key)

    print(f"[sync-os] preserved local templates: {len(preserved_local)} -> {', '.join(preserved_local)}")
    print(f"[sync-os] replaced slim local templates: {len(replaced_slim_local)} -> {', '.join(replaced_slim_local)}")
    print(f"[sync-os] source copied templates: {len(copied_from_source)} -> {', '.join(copied_from_source)}")
    print(f"[sync-os] rendered fallback templates: {len(synthesized_fallback)} -> {', '.join(synthesized_fallback)}")
    print(f"[sync-os] upserted templates: {len(upserted)} -> {', '.join(upserted)}")
    if missing:
        print("[sync-os] source template missing (rendered fallback used):")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

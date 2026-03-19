#!/usr/bin/env python3
"""
同步 HertzBeat 操作系统模板到本项目：
1) 优先复制 define/app-*.yml（若存在）
2) 使用 renderer 生成可落地模板覆盖（linux/windows/nvidia）
3) 注入 OS 默认 alerts
4) Upsert 到 monitor_templates
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

from scripts.apply_os_default_alerts import POLICIES, _render_alerts, _upsert_alerts
from scripts.os_template_profiles import OS_TARGET_APPS
from scripts.os_template_renderer import render_os_template


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


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    src_dir = repo_root / "hertzbeat-master" / "hertzbeat-manager" / "src" / "main" / "resources" / "define"
    dst_dir = backend_dir / "templates"
    dst_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(backend_dir))
    from app import create_app
    from app.services.template_service import template_service

    copied = []
    synthesized = []
    missing = []
    for app in OS_TARGET_APPS:
        src = src_dir / f"app-{app}.yml"
        dst = dst_dir / f"app-{app}.yml"
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(app)
        else:
            missing.append(str(src))
            dst.write_text("", encoding="utf-8")

        rendered = render_os_template(app)
        dst.write_text(rendered, encoding="utf-8")
        synthesized.append(app)

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

    print(f"[sync-os] source copied: {len(copied)} -> {', '.join(copied)}")
    print(f"[sync-os] rendered templates: {len(synthesized)} -> {', '.join(synthesized)}")
    print(f"[sync-os] upserted templates: {len(upserted)} -> {', '.join(upserted)}")
    if missing:
        print("[sync-os] source template missing (rendered fallback used):")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

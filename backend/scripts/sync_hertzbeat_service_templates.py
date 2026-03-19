#!/usr/bin/env python3
"""
同步 HertzBeat 应用服务模板到本项目：
1) 从 define 复制模板
2) 对缺失模板执行渲染兜底（IMAP）
3) 注入应用服务默认 alerts
4) upsert 到 monitor_templates
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

from scripts.apply_service_default_alerts import POLICIES, _render_alerts, _upsert_alerts
from scripts.service_template_profiles import ALL_SERVICE_APPS, RENDER_ONLY_APPS, SOURCE_APPS
from scripts.service_template_renderer import render_imap_template


def _parse_template_meta(content: str, fallback_app: str) -> tuple[str, str, str]:
    app_match = re.search(r"^app:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    app = (app_match.group(1).strip().lower() if app_match else fallback_app) or fallback_app

    category_match = re.search(r"^category:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    category = (category_match.group(1).strip().lower() if category_match else "service") or "service"

    name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*zh-CN:\s*([^\n]+)", content, flags=re.MULTILINE)
    if not name_match:
        name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*en-US:\s*([^\n]+)", content, flags=re.MULTILINE)
    name = (name_match.group(1).strip() if name_match else app) or app
    return app, name, category


def _render_missing_template(app: str) -> str:
    if app == "imap":
        return render_imap_template()
    raise ValueError(f"no renderer for app={app}")


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    src_dir = repo_root / "hertzbeat-master" / "hertzbeat-manager" / "src" / "main" / "resources" / "define"
    dst_dir = backend_dir / "templates"
    override_dir = backend_dir / "template_overrides"
    dst_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(backend_dir))
    from app import create_app
    from app.services.template_service import template_service

    copied = []
    rendered = []
    missing_source = []

    for app in SOURCE_APPS:
        src = src_dir / f"app-{app}.yml"
        dst = dst_dir / f"app-{app}.yml"
        if not src.exists():
            missing_source.append(str(src))
            continue
        shutil.copy2(src, dst)
        override = override_dir / f"app-{app}.yml"
        if override.exists():
            shutil.copy2(override, dst)
        if app in POLICIES:
            raw = dst.read_text(encoding="utf-8")
            merged = _upsert_alerts(raw, _render_alerts(POLICIES[app]))
            dst.write_text(merged, encoding="utf-8")
        copied.append((app, dst))

    for app in RENDER_ONLY_APPS:
        dst = dst_dir / f"app-{app}.yml"
        rendered_text = _render_missing_template(app)
        if app in POLICIES:
            rendered_text = _upsert_alerts(rendered_text, _render_alerts(POLICIES[app]))
        dst.write_text(rendered_text, encoding="utf-8")
        rendered.append((app, dst))

    flask_app = create_app()
    upserted = []
    with flask_app.app_context():
        template_service.initialize()
        template_service.save_category("应用服务", "service", "electrical-services")
        for fallback_app, filepath in [*copied, *rendered]:
            content = filepath.read_text(encoding="utf-8")
            app, name, category = _parse_template_meta(content, fallback_app)
            template_service.save_template(app, name, category, content)
            upserted.append(app)

    print(f"[sync-service] source copied: {len(copied)} -> {', '.join(app for app, _ in copied)}")
    print(f"[sync-service] rendered templates: {len(rendered)} -> {', '.join(app for app, _ in rendered)}")
    print(f"[sync-service] upserted templates: {len(upserted)} -> {', '.join(upserted)}")
    if missing_source:
        print("[sync-service] source template missing:")
        for item in missing_source:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
同步 HertzBeat 数据库类模板到本项目：
1) 复制 define/app-*.yml 到 backend/templates/
2) Upsert 到 monitor_templates 表，确保模板菜单可见

用法:
  cd backend
  PYTHONPATH=. python scripts/sync_hertzbeat_db_templates.py
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

from scripts.apply_db_default_alerts import POLICIES, _render_alerts, _upsert_alerts

TARGET_APPS = [
    "postgresql",
    "db2",
    "mariadb",
    "sqlserver",
    "kingbase",
    "greenplum",
    "tidb",
    "mongodb_atlas",
    "oceanbase",
    "vastbase",
    "oracle",
    "dm",
    "opengauss",
]


def _parse_template_meta(content: str, fallback_app: str) -> tuple[str, str, str]:
    app_match = re.search(r"^app:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    app = (app_match.group(1).strip().lower() if app_match else fallback_app) or fallback_app

    category_match = re.search(
        r"^category:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE
    )
    category = (category_match.group(1).strip().lower() if category_match else "db") or "db"

    name_match = re.search(
        r"^name:\s*\n(?:\s*#.*\n)*\s*zh-CN:\s*([^\n]+)",
        content,
        flags=re.MULTILINE,
    )
    if not name_match:
        name_match = re.search(
            r"^name:\s*\n(?:\s*#.*\n)*\s*en-US:\s*([^\n]+)",
            content,
            flags=re.MULTILINE,
        )
    name = (name_match.group(1).strip() if name_match else app) or app
    return app, name, category


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    src_dir = (
        repo_root
        / "hertzbeat-master"
        / "hertzbeat-manager"
        / "src"
        / "main"
        / "resources"
        / "define"
    )
    dst_dir = backend_dir / "templates"
    dst_dir.mkdir(parents=True, exist_ok=True)

    # 延迟导入，避免脚本在非 backend 目录运行时模块解析失败
    sys.path.insert(0, str(backend_dir))
    from app import create_app
    from app.services.template_service import template_service

    copied = []
    missing = []
    for app in TARGET_APPS:
        src = src_dir / f"app-{app}.yml"
        dst = dst_dir / f"app-{app}.yml"
        if not src.exists():
            missing.append(str(src))
            continue
        shutil.copy2(src, dst)
        if app in POLICIES:
            raw = dst.read_text(encoding="utf-8")
            merged = _upsert_alerts(raw, _render_alerts(POLICIES[app]))
            dst.write_text(merged, encoding="utf-8")
        copied.append((app, dst))

    flask_app = create_app()
    upserted = []
    with flask_app.app_context():
        template_service.initialize()
        for fallback_app, filepath in copied:
            content = filepath.read_text(encoding="utf-8")
            app, name, category = _parse_template_meta(content, fallback_app)
            template_service.save_template(app, name, category, content)
            upserted.append(app)

    print(f"[sync] copied files: {len(copied)}")
    print(f"[sync] upserted templates: {len(upserted)} -> {', '.join(upserted)}")
    if missing:
        print("[sync] missing source files:")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

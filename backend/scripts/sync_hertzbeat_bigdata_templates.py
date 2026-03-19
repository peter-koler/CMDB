#!/usr/bin/env python3
"""
同步 HertzBeat 大数据模板到本项目：
1) 复制 define/app-*.yml 到 backend/templates/
2) 统一分类为 bigdata
3) 注入默认 alerts
4) Upsert 到 monitor_templates，并确保分类 bigdata 存在
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

from scripts.apply_bigdata_default_alerts import POLICIES, _render_alerts, _upsert_alerts

TARGET_APPS = [
    "airflow",
    "hbase_master",
    "hbase_regionserver",
    "hdfs_datanode",
    "hdfs_namenode",
    "hugegraph",
    "hadoop",
    "hive",
    "iceberg",
    "clickhouse",
    "doris_be",
    "elasticsearch",
    "flink",
    "influxdb",
    "iotdb",
    "prestodb",
    "spark",
    "yarn",
]


def _parse_template_meta(content: str, fallback_app: str) -> tuple[str, str, str]:
    app_match = re.search(r"^app:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    app = (app_match.group(1).strip().lower() if app_match else fallback_app) or fallback_app
    name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*zh-CN:\s*([^\n]+)", content, flags=re.MULTILINE)
    if not name_match:
        name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*en-US:\s*([^\n]+)", content, flags=re.MULTILINE)
    name = (name_match.group(1).strip() if name_match else app) or app
    return app, name, "bigdata"


def _force_category_bigdata(content: str) -> str:
    return re.sub(r"^category:\s*[A-Za-z0-9_.-]+\s*$", "category: bigdata", content, flags=re.MULTILINE)


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
    missing = []
    for app in TARGET_APPS:
        src = src_dir / f"app-{app}.yml"
        dst = dst_dir / f"app-{app}.yml"
        if not src.exists():
            missing.append(str(src))
            continue
        shutil.copy2(src, dst)
        override = override_dir / f"app-{app}.yml"
        if override.exists():
            shutil.copy2(override, dst)

        raw = dst.read_text(encoding="utf-8")
        raw = _force_category_bigdata(raw)
        if app in POLICIES:
            raw = _upsert_alerts(raw, _render_alerts(POLICIES[app]))
        dst.write_text(raw, encoding="utf-8")
        copied.append((app, dst))

    flask_app = create_app()
    upserted = []
    with flask_app.app_context():
        template_service.initialize()
        template_service.save_category("大数据", "bigdata", "cluster")
        for fallback_app, filepath in copied:
            content = filepath.read_text(encoding="utf-8")
            app, name, category = _parse_template_meta(content, fallback_app)
            template_service.save_template(app, name, category, content)
            upserted.append(app)

    print(f"[sync-bigdata] copied files: {len(copied)}")
    print(f"[sync-bigdata] upserted templates: {len(upserted)} -> {', '.join(upserted)}")
    if missing:
        print("[sync-bigdata] missing source files:")
        for item in missing:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


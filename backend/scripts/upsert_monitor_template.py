#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_template_meta(content: str, fallback_app: str) -> tuple[str, str, str]:
    app_match = re.search(r"^app:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    app = (app_match.group(1).strip().lower() if app_match else fallback_app) or fallback_app

    category_match = re.search(r"^category:\s*([A-Za-z0-9_.-]+)\s*$", content, flags=re.MULTILINE)
    category = (category_match.group(1).strip().lower() if category_match else "service") or "service"

    name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*zh-CN:\s*([^\n]+)", content, flags=re.MULTILINE)
    if not name_match:
        name_match = re.search(r"^name:\s*\n(?:\s*#.*\n)*\s*en-US:\s*([^\n]+)", content, flags=re.MULTILINE)
    name = (name_match.group(1).strip() if name_match else app) or app
    return app, name, category


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert one or more monitor template YAML files into monitor_templates.")
    parser.add_argument("files", nargs="+", help="Template YAML file paths")
    args = parser.parse_args()

    from app import create_app
    from app.services.template_service import template_service

    app = create_app()
    updated: list[str] = []

    with app.app_context():
        template_service.initialize()
        for raw_path in args.files:
            path = Path(raw_path).resolve()
            if not path.exists():
                raise FileNotFoundError(f"template file not found: {path}")
            content = path.read_text(encoding="utf-8")
            fallback_app = path.stem.removeprefix("app-")
            app_name, name, category = parse_template_meta(content, fallback_app)
            template_service.save_template(app_name, name, category, content)
            updated.append(app_name)

    print(f"[upsert-template] updated: {', '.join(updated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

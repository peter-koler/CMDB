#!/usr/bin/env python3
"""
校验大数据模板迁移结果：
1) 模板文件存在
2) category 为 bigdata
3) 已注入 alerts 段
4) protocol 仅使用当前已支持集合（http/jdbc/jmx）
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


APPS = [
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

ALLOWED_PROTOCOLS = {"http", "jdbc", "jmx"}
PROTOCOL_PATTERN = re.compile(r"^\s*protocol:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)


def _check_template(path: Path) -> tuple[list[str], set[str]]:
    issues: list[str] = []
    protocols: set[str] = set()

    if not path.exists():
        return [f"missing file: {path.name}"], protocols

    content = path.read_text(encoding="utf-8")
    if "category: bigdata" not in content:
        issues.append("category != bigdata")
    if "\nalerts:\n" not in content and not content.lstrip().startswith("alerts:"):
        issues.append("alerts block missing")

    for match in PROTOCOL_PATTERN.finditer(content):
        protocols.add(match.group(1).strip().lower())
    unknown = sorted(protocols - ALLOWED_PROTOCOLS)
    if unknown:
        issues.append(f"unsupported protocol(s): {', '.join(unknown)}")

    return issues, protocols


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tpl_dir = root / "templates"

    failed = False
    print("[verify-bigdata] start")
    for app in APPS:
        file_path = tpl_dir / f"app-{app}.yml"
        issues, protocols = _check_template(file_path)
        if issues:
            failed = True
            print(f"[FAIL] {app}: {'; '.join(issues)}")
            continue
        print(f"[OK]   {app}: protocols={','.join(sorted(protocols)) or '-'}")

    if failed:
        print("[verify-bigdata] FAILED")
        return 1
    print("[verify-bigdata] PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

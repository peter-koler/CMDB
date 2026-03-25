#!/usr/bin/env python3
"""One-shot OS monitor diagnostics: DB + API + logs.

Usage:
  python3 backend/scripts/diagnose_os_monitor.py --monitor-id 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

DEFAULT_DB_URL = "postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db"
DEFAULT_MANAGER_API = "http://127.0.0.1:8080"
CORE_GROUPS = [
    "basic",
    "cpu",
    "memory",
    "disk",
    "interface",
    "disk_free",
    "top_cpu_process",
    "top_mem_process",
]


@dataclass
class GroupDef:
    name: str
    fields: list[str]
    parse_type: str


def normalize_pg_dsn(dsn: str) -> str:
    dsn = (dsn or "").strip()
    if dsn.startswith("postgresql+psycopg2://"):
        return "postgresql://" + dsn[len("postgresql+psycopg2://") :]
    if dsn.startswith("postgres+psycopg2://"):
        return "postgresql://" + dsn[len("postgres+psycopg2://") :]
    return dsn


def fetch_one(cur: Any, sql: str, args: tuple[Any, ...]) -> dict[str, Any] | None:
    cur.execute(sql, args)
    row = cur.fetchone()
    return dict(row) if row else None


def fetch_all(cur: Any, sql: str, args: tuple[Any, ...]) -> list[dict[str, Any]]:
    cur.execute(sql, args)
    return [dict(r) for r in cur.fetchall()]


def parse_template_groups(content: str) -> dict[str, GroupDef]:
    groups: dict[str, GroupDef] = {}
    in_metrics = False
    current: GroupDef | None = None
    in_fields = False

    for raw in (content or "").splitlines():
        line = raw.rstrip("\n")
        if not in_metrics:
            if re.match(r"^metrics:\s*$", line):
                in_metrics = True
            continue
        if re.match(r"^alerts:\s*$", line):
            break

        m_group = re.match(r"^  - name:\s*([A-Za-z0-9_]+)\s*$", line)
        if m_group:
            name = m_group.group(1)
            current = GroupDef(name=name, fields=[], parse_type="")
            groups[name] = current
            in_fields = False
            continue

        if current is None:
            continue

        if re.match(r"^    fields:\s*$", line):
            in_fields = True
            continue

        m_field = re.match(r"^      - field:\s*([A-Za-z0-9_]+)\s*$", line)
        if in_fields and m_field:
            current.fields.append(m_field.group(1))
            continue

        m_parse = re.match(r"^      parseType:\s*([A-Za-z0-9_]+)\s*$", line)
        if m_parse:
            current.parse_type = m_parse.group(1).strip().lower()
            continue

    return groups


def build_expected_names(groups: dict[str, GroupDef]) -> dict[str, list[str]]:
    expected: dict[str, list[str]] = {}
    for gname, gdef in groups.items():
        names: list[str] = []
        names.append(f"{gname}_success")
        names.append(f"{gname}_raw_latency")
        for field in gdef.fields:
            names.append(f"{gname}_{field}")
        is_multi = gdef.parse_type == "multirow" or gname in {
            "interface",
            "disk_free",
            "top_cpu_process",
            "top_mem_process",
            "top_memory_process",
        }
        if is_multi:
            for i in range(1, 11):
                for field in gdef.fields:
                    names.append(f"{gname}_row{i}_{field}")
                    names.append(f"row{i}_{field}")
        expected[gname] = sorted(set(names))
    return expected


def http_json(url: str, timeout: float = 3.0) -> tuple[dict[str, Any] | None, str | None]:
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
        return json.loads(payload), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def fetch_latest_api(
    manager_api: str,
    monitor_id: int,
    names: list[str],
    lookback_minutes: int,
    step_sec: int,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    now = datetime.now(timezone.utc)
    frm = int((now - timedelta(minutes=lookback_minutes)).timestamp())
    to = int(now.timestamp())
    items: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for idx, one in enumerate(chunked(names, 80), start=1):
        query = urllib.parse.urlencode(
            {
                "monitor_id": str(monitor_id),
                "from": str(frm),
                "to": str(to),
                "step": str(step_sec),
                "stale_seconds": str(step_sec * 3),
                "names": ",".join(one),
            }
        )
        url = f"{manager_api.rstrip('/')}/api/v1/metrics/latest?{query}"
        payload, err = http_json(url, timeout=5.0)
        if err:
            errors.append(f"chunk={idx} size={len(one)} err={err}")
            continue
        for item in (payload or {}).get("items", []):
            name = str(item.get("name") or "").strip()
            if name:
                items[name] = item
    return items, errors


def value_present(item: dict[str, Any] | None) -> bool:
    if not item:
        return False
    if item.get("value") is not None:
        return True
    text = item.get("text")
    return bool(isinstance(text, str) and text.strip())


def value_as_float(item: dict[str, Any] | None) -> float | None:
    if not item:
        return None
    v = item.get("value")
    if isinstance(v, (int, float)):
        return float(v)
    t = item.get("text")
    if isinstance(t, str):
        try:
            return float(t.strip())
        except ValueError:
            return None
    return None


def tail_lines(path: Path, line_count: int) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    return text.splitlines()[-line_count:]


def collect_log_hits(
    monitor_id: int,
    job_id: int | None,
    app: str,
    instance: str,
    line_count: int,
    max_hits: int,
) -> list[str]:
    roots = [Path("logs"), Path("manager-go/logs"), Path("collector-go/logs")]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.glob("*.log")):
            files.append(p)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    files = files[:12]

    id_patterns = [
        rf"\bmonitor[=: ]+{monitor_id}\b",
        rf"\bmonitor_id[=: ]+{monitor_id}\b",
        rf"/monitors/{monitor_id}\b",
        rf"\bjob-{monitor_id}-",
    ]
    if job_id:
        id_patterns.extend([rf"\bjob-{job_id}-"])
    if instance:
        host = instance.split(":")[0].strip()
        if host:
            id_patterns.append(re.escape(host))
    id_pattern = re.compile("(" + "|".join(id_patterns) + ")", re.IGNORECASE)
    err_pattern = re.compile(r"(error|failed|panic|timeout|ssh|parse|dispatch|compile|unavailable)", re.IGNORECASE)

    hits: list[str] = []
    for file in files:
        per_file = 0
        for line in tail_lines(file, line_count):
            if id_pattern.search(line) and (err_pattern.search(line) or app.lower() in line.lower() or "monitor" in line.lower()):
                hits.append(f"{file}: {line}")
                per_file += 1
                if len(hits) >= max_hits:
                    return hits
                if per_file >= 20:
                    break
    return hits


def summarize_group(
    gname: str,
    gdef: GroupDef,
    expected_names: list[str],
    api_items: dict[str, dict[str, Any]],
    db_by_group: dict[str, set[str]],
) -> tuple[str, str]:
    success_item = api_items.get(f"{gname}_success")
    success = value_as_float(success_item)
    present = [n for n in expected_names if value_present(api_items.get(n))]
    fresh = [n for n in present if not bool(api_items.get(n, {}).get("stale", True))]
    db_fields = db_by_group.get(gname, set())

    verdict = "OK"
    reason = ""
    if success is not None and success < 1:
        verdict = "FAIL"
        reason = f"success={success:g}"
    elif not present and not db_fields:
        verdict = "EMPTY"
        reason = "API和DB都无数据"
    elif success is not None and success >= 1 and not present:
        verdict = "MAPPING"
        reason = "success有值但字段为空，疑似解析/字段映射问题"
    elif present and not fresh:
        verdict = "STALE"
        reason = "有数据但全部陈旧"
    elif not present and db_fields:
        verdict = "API"
        reason = "DB有数据但API缺失，疑似VM查询名不匹配"
    else:
        reason = "数据正常"

    if gname == "interface":
        has_rx = any(value_present(api_items.get(n)) for n in [f"{gname}_receive_bytes", f"{gname}_row1_receive_bytes"])
        has_ip_mac = any(
            value_present(api_items.get(n))
            for n in [
                f"{gname}_ip_address",
                f"{gname}_mac_address",
                f"{gname}_row1_ip_address",
                f"{gname}_row1_mac_address",
                "row1_ip_address",
                "row1_mac_address",
            ]
        )
        if has_rx and not has_ip_mac:
            verdict = "MAPPING"
            reason = "网卡流量有值但IP/MAC为空，疑似脚本输出或字符串映射问题"

    if gname in {"memory", "disk_free"}:
        usage_keys = [f"{gname}_usage", f"{gname}_row1_usage", "row1_usage"]
        usage_ok = any(value_present(api_items.get(k)) for k in usage_keys)
        if not usage_ok:
            if gname == "memory" and any(value_present(api_items.get(k)) for k in [f"{gname}_total", f"{gname}_used"]):
                reason += "; usage 缺失，可检查计算表达式或前端格式化"
            if gname == "disk_free" and any(value_present(api_items.get(k)) for k in [f"{gname}_used", f"{gname}_available"]):
                reason += "; usage 缺失，可检查前端按 used/available 计算"

    visible_fields = sorted(db_fields)[:8]
    detail = (
        f"group={gname} parseType={gdef.parse_type or 'unknown'} "
        f"api_present={len(present)}/{len(expected_names)} api_fresh={len(fresh)} "
        f"db_fields={len(db_fields)} db_sample={visible_fields} reason={reason}"
    )
    return verdict, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose OS monitor data path (PG + API + logs).")
    parser.add_argument("--monitor-id", type=int, required=True, help="monitor id, e.g. 3")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL), help="PostgreSQL DSN")
    parser.add_argument("--manager-api", default=os.getenv("MANAGER_API", DEFAULT_MANAGER_API), help="manager-go API base URL")
    parser.add_argument("--lookback-minutes", type=int, default=30, help="lookback window for API/DB checks")
    parser.add_argument("--step", type=int, default=60, help="step seconds for /metrics/latest")
    parser.add_argument("--log-lines", type=int, default=400, help="tail N lines per log file")
    parser.add_argument("--max-log-hits", type=int, default=60, help="max matched log lines to print")
    args = parser.parse_args()

    dsn = normalize_pg_dsn(args.database_url)
    if not dsn:
        print("ERROR: missing --database-url or DATABASE_URL", file=sys.stderr)
        return 2

    now_utc = datetime.now(timezone.utc)
    since_ms = int((now_utc - timedelta(minutes=args.lookback_minutes)).timestamp() * 1000)

    monitor: dict[str, Any] | None = None
    params: list[dict[str, Any]] = []
    template: dict[str, Any] | None = None
    compile_logs: list[dict[str, Any]] = []
    db_rows: list[dict[str, Any]] = []
    db_scoped = True

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            monitor = fetch_one(
                cur,
                """
                SELECT id, job_id, app, name, instance, status, intervals, updated_at
                FROM monitors WHERE id = %s
                """,
                (args.monitor_id,),
            )
            if not monitor:
                print(f"ERROR: monitor id={args.monitor_id} not found")
                return 3

            params = fetch_all(
                cur,
                """
                SELECT field, param_value AS value
                FROM monitor_params
                WHERE monitor_id = %s
                ORDER BY field
                """,
                (args.monitor_id,),
            )
            template = fetch_one(
                cur,
                """
                SELECT id, app, version, is_hidden, updated_at, content
                FROM monitor_templates
                WHERE app = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (monitor["app"],),
            )
            compile_logs = fetch_all(
                cur,
                """
                SELECT stage, status, reason, created_at
                FROM monitor_compile_logs
                WHERE monitor_id = %s
                ORDER BY id DESC
                LIMIT 12
                """,
                (args.monitor_id,),
            )

            cands = [str(args.monitor_id), f"job-{args.monitor_id}-%"]
            if monitor.get("job_id"):
                cands.append(str(monitor["job_id"]))
                cands.append(f"job-{monitor['job_id']}-%")
            cands = list(dict.fromkeys(cands))

            cur.execute(
                """
                SELECT instance, metrics, metric, metric_type, max(timestamp) AS ts, count(*) AS n
                FROM metrics_history
                WHERE app = %s AND timestamp >= %s
                  AND (
                    instance = %s OR instance = %s
                    OR instance LIKE %s OR instance LIKE %s
                  )
                GROUP BY instance, metrics, metric, metric_type
                ORDER BY ts DESC
                LIMIT 3000
                """,
                (monitor["app"], since_ms, cands[0], cands[2] if len(cands) > 2 else cands[0], cands[1], cands[3] if len(cands) > 3 else cands[1]),
            )
            db_rows = [dict(r) for r in cur.fetchall()]
            if not db_rows:
                db_scoped = False
                cur.execute(
                    """
                    SELECT instance, metrics, metric, metric_type, max(timestamp) AS ts, count(*) AS n
                    FROM metrics_history
                    WHERE app = %s AND timestamp >= %s
                    GROUP BY instance, metrics, metric, metric_type
                    ORDER BY ts DESC
                    LIMIT 3000
                    """,
                    (monitor["app"], since_ms),
                )
                db_rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    template_content = str((template or {}).get("content") or "")
    groups = parse_template_groups(template_content)
    if not groups:
        groups = {k: GroupDef(name=k, fields=[], parse_type="") for k in CORE_GROUPS}
    expected_by_group = build_expected_names(groups)
    all_expected = sorted(set(n for arr in expected_by_group.values() for n in arr))

    health_payload, health_err = http_json(f"{args.manager_api.rstrip('/')}/api/v1/health", timeout=2.0)
    monitor_payload, monitor_err = http_json(
        f"{args.manager_api.rstrip('/')}/api/v1/monitors/{args.monitor_id}",
        timeout=3.0,
    )
    compile_payload, compile_err = http_json(
        f"{args.manager_api.rstrip('/')}/api/v1/monitors/{args.monitor_id}/compile-logs",
        timeout=3.0,
    )
    api_items, latest_errors = fetch_latest_api(
        manager_api=args.manager_api,
        monitor_id=args.monitor_id,
        names=all_expected,
        lookback_minutes=args.lookback_minutes,
        step_sec=args.step,
    )

    db_by_group: dict[str, set[str]] = {}
    for r in db_rows:
        g = str(r.get("metrics") or "").strip()
        m = str(r.get("metric") or "").strip()
        if not g or not m:
            continue
        db_by_group.setdefault(g, set()).add(m)

    print("=== Monitor Baseline ===")
    print(
        f"monitor_id={monitor['id']} job_id={monitor.get('job_id')} app={monitor['app']} "
        f"name={monitor['name']} instance={monitor['instance']} status={monitor['status']} intervals={monitor['intervals']}"
    )
    print(f"database_url={dsn}")
    print(f"manager_api={args.manager_api}")
    print(f"lookback_minutes={args.lookback_minutes}")
    print()

    print("=== Template ===")
    if template:
        print(
            f"template_id={template.get('id')} version={template.get('version')} "
            f"updated_at={template.get('updated_at')} is_hidden={template.get('is_hidden')}"
        )
    else:
        print("template=NOT_FOUND")
    print(f"groups_detected={sorted(groups.keys())}")
    print()

    print("=== Compile Logs ===")
    if compile_logs:
        for row in compile_logs[:8]:
            print(
                f"[DB] {row.get('created_at')} stage={row.get('stage')} "
                f"status={row.get('status')} reason={row.get('reason') or '-'}"
            )
    else:
        print("[DB] no compile logs")
    if compile_payload and isinstance(compile_payload.get("items"), list):
        print(f"[API] compile_logs_items={len(compile_payload.get('items', []))}")
    elif compile_err:
        print(f"[API] compile_logs_error={compile_err}")
    print()

    print("=== API Health ===")
    if health_err:
        print(f"health_error={health_err}")
    else:
        print(f"health={health_payload}")
    if monitor_err:
        print(f"monitor_api_error={monitor_err}")
    else:
        print(f"monitor_api_ok=1 monitor_api_keys={sorted(list(monitor_payload.keys()))[:10] if isinstance(monitor_payload, dict) else 'non_dict'}")
    if latest_errors:
        print("latest_api_errors:")
        for e in latest_errors[:3]:
            print(f"  - {e}")
    print(f"latest_items={len(api_items)} expected_names={len(all_expected)}")
    print()

    print("=== DB Metrics (metrics_history) ===")
    print(f"db_rows={len(db_rows)} scoped={'yes' if db_scoped else 'fallback_app_only'}")
    if db_rows:
        top_inst: dict[str, int] = {}
        for r in db_rows:
            inst = str(r.get("instance") or "")
            top_inst[inst] = top_inst.get(inst, 0) + 1
        top_instances = sorted(top_inst.items(), key=lambda x: x[1], reverse=True)[:8]
        print(f"instances={top_instances}")
    print()

    print("=== Group Diagnosis ===")
    group_verdicts: dict[str, str] = {}
    for gname in sorted(groups.keys()):
        gdef = groups[gname]
        verdict, detail = summarize_group(gname, gdef, expected_by_group[gname], api_items, db_by_group)
        group_verdicts[gname] = verdict
        print(f"[{verdict}] {detail}")
    print()

    print("=== Param Snapshot ===")
    sensitive = {"password", "privateKey", "privateKeyPassphrase", "proxyPassword", "proxyPrivateKey"}
    for row in params:
        field = str(row.get("field") or "")
        val = str(row.get("value") or "")
        if field in sensitive and val:
            val = "***"
        print(f"{field}={val}")
    print()

    print("=== Log Hits ===")
    hits = collect_log_hits(
        monitor_id=args.monitor_id,
        job_id=int(monitor["job_id"]) if monitor and monitor.get("job_id") else None,
        app=str(monitor["app"]),
        instance=str(monitor["instance"]),
        line_count=args.log_lines,
        max_hits=args.max_log_hits,
    )
    if not hits:
        print("no matched lines in scanned logs")
    else:
        for line in hits:
            print(line)

    print()
    print("=== Quick Verdict ===")
    all_groups_ok = bool(group_verdicts) and all(v == "OK" for v in group_verdicts.values())
    if health_err:
        print("manager-go API 不可达，先排查服务监听和网络。")
    elif api_items and all_groups_ok:
        if db_rows:
            print("采集正常：API 与分组检查均通过，且 DB 历史存在。")
        else:
            print("采集正常：API 与分组检查均通过；DB 历史为空通常表示当前主要走 VM 查询链路。")
    elif not api_items and not db_rows:
        print("API 与 DB 都没有近时段指标，优先排查 collector 执行/分发链路。")
    elif api_items and not db_rows:
        print("API有数据但DB历史为空，当前可能主要依赖 VM；若需DB历史请检查入库路径。")
    elif db_rows and not api_items:
        print("DB有数据但API latest为空，优先排查 metrics/latest 查询名与 monitor_id 标签。")
    else:
        print("已拿到 API/DB 数据，请按上方 Group Diagnosis 逐组修复缺失字段。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

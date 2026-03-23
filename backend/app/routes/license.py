from flask import Blueprint, jsonify, request
import json

from app.models.config import SystemConfig
from app.services.manager_api_service import manager_api_service, ManagerError

license_bp = Blueprint("license", __name__, url_prefix="/api/v1/license")


def _friendly_license_message(error_code: str, raw_message: str) -> str:
    msg = (raw_message or "").strip().lower()
    if error_code == "LICENSE_INVALID":
        if "expired" in msg:
            return "License 已过期，请联系管理员重新生成有效 License 后上传。"
        if "machine code mismatch" in msg:
            return "License 与当前机器不匹配，请使用当前机器码重新生成 License。"
        if "signature" in msg:
            return "License 签名校验失败，请确认文件来源并重新生成。"
        if "format" in msg or "malformed" in msg or "invalid" in msg:
            return "License 文件格式无效，请检查文件内容后重试。"
        return "License 校验失败，请确认文件是否正确并重新生成。"
    return raw_message or "请求失败"


@license_bp.route("/status", methods=["GET"])
def get_license_status():
    try:
        data = manager_api_service.request("GET", "/api/v1/license/status")
    except ManagerError as exc:
        return (
            jsonify(
                {
                    "code": exc.status,
                    "message": _friendly_license_message(exc.code, exc.message),
                    "data": {"error_code": exc.code},
                }
            ),
            exc.status,
        )
    return jsonify({"code": 200, "message": "success", "data": data})


@license_bp.route("/upload", methods=["POST"])
def upload_license():
    payload = request.get_json(silent=True) or {}
    license_content = str(payload.get("license") or payload.get("content") or "").strip()
    if not license_content:
        return jsonify({"code": 400, "message": "license 内容不能为空"}), 400

    try:
        data = manager_api_service.request(
            "POST",
            "/api/v1/license/upload",
            payload={"license": license_content},
        )
    except ManagerError as exc:
        return (
            jsonify(
                {
                    "code": exc.status,
                    "message": _friendly_license_message(exc.code, exc.message),
                    "data": {"error_code": exc.code},
                }
            ),
            exc.status,
        )
    try:
        claims = {
            "machine_code": str(data.get("machine_code") or "").strip(),
            "expire_time": str(data.get("expire_time") or "").strip(),
            "max_monitors": int(data.get("max_monitors") or 0),
        }
        if claims["machine_code"] and claims["expire_time"] and claims["max_monitors"] > 0:
            SystemConfig.set_value("license_claims_json", json.dumps(claims, ensure_ascii=False))
    except Exception:
        # 同步失败不影响上传成功；登录拦截会优先读取 manager-go 实时状态。
        pass
    return jsonify({"code": 200, "message": "success", "data": data})

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import current_app


@dataclass
class ManagerError(Exception):
    status: int
    code: str
    message: str


class ManagerAPIService:
    def __init__(self):
        self._state = "closed"  # closed | open | half_open
        self._failure_count = 0
        self._opened_at = 0.0
        self._transport = self._default_transport

    def _cfg(self, key: str, default: Any) -> Any:
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            return default

    def _base_url(self) -> str:
        return str(self._cfg("GO_MANAGER_URL", "http://127.0.0.1:8080")).rstrip("/")

    def _before_request(self) -> None:
        if self._state != "open":
            return
        recovery = int(self._cfg("GO_MANAGER_CB_RECOVERY_SECONDS", 30))
        if time.time() - self._opened_at >= recovery:
            self._state = "half_open"
            return
        raise ManagerError(status=503, code="UPSTREAM_UNAVAILABLE", message="Go Manager circuit open")

    def _on_success(self) -> None:
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = 0.0

    def _on_failure(self) -> None:
        self._failure_count += 1
        threshold = int(self._cfg("GO_MANAGER_CB_FAILURE_THRESHOLD", 3))
        if self._failure_count >= threshold:
            self._state = "open"
            self._opened_at = time.time()

    def _default_transport(
        self,
        method: str,
        url: str,
        data: Optional[bytes],
        headers: Dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]:
        req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
        auth_header: Optional[str] = None,
    ) -> Any:
        self._before_request()

        url = self._base_url() + path
        if params:
            q = urllib.parse.urlencode(params)
            url = f"{url}?{q}"

        timeout = float(self._cfg("GO_MANAGER_TIMEOUT_SECONDS", 3))
        max_retries = int(self._cfg("GO_MANAGER_MAX_RETRIES", 2))
        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header

        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        last_error: Optional[ManagerError] = None
        for attempt in range(max_retries + 1):
            try:
                status, raw = self._transport(method, url, body, headers, timeout)
                data = self._decode(raw)
                if status >= 400:
                    code = "UPSTREAM_ERROR"
                    message = "Go Manager error"
                    if isinstance(data, dict):
                        err = data.get("error", {})
                        if isinstance(err, dict):
                            code = err.get("code", code)
                            message = err.get("message", message)
                    raise ManagerError(status=status, code=code, message=message)
                self._on_success()
                return data
            except ManagerError as e:
                retriable = e.status >= 500
                last_error = e
                if not retriable or attempt == max_retries:
                    break
                time.sleep(0.05 * (attempt + 1))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                self._on_failure()
                last_error = ManagerError(status=503, code="UPSTREAM_UNAVAILABLE", message=str(e))
                if attempt == max_retries:
                    break
                time.sleep(0.05 * (attempt + 1))

        if last_error is None:
            last_error = ManagerError(status=500, code="INTERNAL_ERROR", message="unknown manager client error")
        if last_error.status >= 500:
            self._on_failure()
        raise last_error

    @staticmethod
    def _decode(raw: bytes) -> Any:
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {"raw": raw.decode("utf-8", errors="replace")}


manager_api_service = ManagerAPIService()

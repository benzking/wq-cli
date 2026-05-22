"""wq check — health + login status; wq status — auth-only."""
from cli.core import _req, _ok, _fail


def cmd_check(auto_recover=False):
    code_h, health = _req("GET", "/health")
    code_s, status = _req("GET", "/admin/status")

    result = {
        "service_healthy": code_h == 200 and health.get("status") == "healthy",
        "authenticated": status.get("authenticated", False),
        "is_expired": status.get("isExpired", True),
        "login_status_text": status.get("status", "未知"),
        "nickname": status.get("nickname", ""),
        "fakeid": status.get("fakeid", ""),
        "effective_route": status.get("effective_route", ""),
    }
    if auto_recover and not result["service_healthy"]:
        import subprocess
        try:
            subprocess.run(["bash", "/home/gly/wq-cli/start.sh"], timeout=30)
            code_h2, _ = _req("GET", "/health")
            result["auto_recovered"] = code_h2 == 200
            result["service_healthy"] = code_h2 == 200
        except Exception as e:
            result["auto_recover_error"] = str(e)

    result["ok"] = result["service_healthy"] and result["authenticated"] and not result["is_expired"]
    _ok(result)


def cmd_status():
    code, status = _req("GET", "/admin/status")
    if code != 200:
        _fail(f"Failed to get status: HTTP {code}")
    _ok(status)

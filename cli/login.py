"""wq login — guide user to browser-based QR code login."""
import sys
from cli.core import _req


def cmd_login():
    code, status = _req("GET", "/admin/status")
    print("Login page: http://localhost:5000/login.html")
    if code == 200:
        is_expired = status.get("isExpired", False)
        authenticated = status.get("authenticated", False)
        if not authenticated:
            print("\nStatus: NOT LOGGED IN — please scan QR code on the page above.")
        elif is_expired:
            print("\nStatus: LOGIN EXPIRED — please re-scan QR code on the page above.")
        else:
            nickname = status.get("nickname", "(unknown)")
            expire_ts = status.get("expireTime", 0)
            if expire_ts > 1e12:
                expire_ts = expire_ts / 1000
            from datetime import datetime, timezone, timedelta
            TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
            expire_str = datetime.fromtimestamp(expire_ts, TZ).strftime("%Y-%m-%d %H:%M") if expire_ts else "unknown"
            print(f"\nStatus: LOGGED IN as {nickname}, expires at {expire_str}")
    else:
        print(f"\nWARNING: Service unreachable (HTTP {code}). Start it first: bash /home/gly/wq-cli/start.sh")
    sys.exit(0)

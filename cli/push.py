"""wq push-report / md-push — generate article push reports."""
import time
from datetime import datetime, timezone, timedelta
from cli.core import _db_conn, _req, _ok, _fail

TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def cmd_push_report(hours=24):
    conn = _db_conn()
    if not conn:
        _fail("Database not found. Check service is running at wq-cli data directory.")

    cutoff = int(time.time()) - hours * 3600
    rows = conn.execute(
        """SELECT a.id, a.fakeid, s.nickname, a.title, a.link, a.digest,
                  a.publish_time
           FROM articles a
           LEFT JOIN subscriptions s ON a.fakeid = s.fakeid
           WHERE a.publish_time >= :cutoff
           ORDER BY s.nickname, a.publish_time DESC
           LIMIT 200""",
        {"cutoff": cutoff},
    ).fetchall()
    conn.close()

    articles = []
    for r in rows:
        pub = r["publish_time"]
        articles.append({
            "id": r["id"],
            "nickname": r["nickname"] or "",
            "title": r["title"],
            "link": r["link"],
            "digest": (r["digest"] or "")[:300],
            "publish_time_str": datetime.fromtimestamp(pub, TZ).strftime("%Y-%m-%d %H:%M") if pub else "",
        })

    _, status = _req("GET", "/admin/status")
    login_info = {
        "authenticated": status.get("authenticated", False),
        "is_expired": status.get("isExpired", True),
        "status_text": status.get("status", ""),
    }

    _ok({
        "period_hours": hours,
        "end_time": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "start_time": datetime.fromtimestamp(cutoff, TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "article_count": len(articles),
        "articles": articles,
        "login": login_info,
    })


def cmd_md_push(hours=24):
    conn = _db_conn()
    if not conn:
        print("Database not found")
        import sys as _sys
        _sys.exit(1)

    cutoff = int(time.time()) - hours * 3600
    rows = conn.execute(
        """SELECT a.id, a.fakeid, s.nickname, a.title, a.link, a.digest,
                  a.publish_time
           FROM articles a
           LEFT JOIN subscriptions s ON a.fakeid = s.fakeid
           WHERE a.publish_time >= :cutoff
           ORDER BY a.publish_time DESC""",
        {"cutoff": cutoff},
    ).fetchall()
    conn.close()

    _, status = _req("GET", "/admin/status")

    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"wq 公众号文章推送 — {now_str}", ""]

    if not rows:
        lines.append(f"最近 {hours} 小时无新增文章。")
    else:
        by_account = {}
        for r in rows:
            name = r["nickname"] or r["fakeid"][:8]
            by_account.setdefault(name, []).append(r)

        for name, arts in sorted(by_account.items()):
            lines.append(f"**【{name}】** — {len(arts)} 篇")
            for a in arts:
                pub = a["publish_time"]
                ts = datetime.fromtimestamp(pub, TZ).strftime("%m-%d %H:%M") if pub else ""
                digest = (a["digest"] or "")[:120]
                lines.append(f"• {a['title']}  _{ts}_")
                lines.append(f"  {a['link']}")
                if digest:
                    lines.append(f"  > {digest}")
            lines.append("")

    lines.append("---")
    authed = status.get("authenticated", False)
    s_text = status.get("status", "未知")
    is_expired = status.get("isExpired", True)
    lines.append(f"**登录状态**: {'OK' if authed else 'EXPIRED'}")
    lines.append(f"Status: {s_text}")
    if not authed or is_expired:
        lines.append("")
        lines.append("Login expired, please visit http://localhost:5000/login.html to re-scan QR code.")

    print("\n".join(lines))
    import sys as _sys
    _sys.exit(0)

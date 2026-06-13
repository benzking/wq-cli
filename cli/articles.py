"""wq articles — query cached articles via SQLite with API fallback."""
import time
from datetime import datetime, timezone, timedelta
from cli.core import _db_conn, _req, _ok, _fail

TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def cmd_articles(fakeid=None, hours=None, keyword=None, limit=20, fmt="json"):
    conn = _db_conn()
    if conn is not None:
        _articles_from_db(conn, fakeid, hours, keyword, limit, fmt)
    else:
        _articles_from_api(fakeid, hours, keyword, limit, fmt)


def _articles_from_db(conn, fakeid, hours, keyword, limit, fmt):
    conditions = ["1=1"]
    params = {}
    if fakeid:
        conditions.append("a.fakeid = :fakeid")
        params["fakeid"] = fakeid
    if keyword:
        conditions.append("a.title LIKE :kw")
        params["kw"] = f"%{keyword}%"
    if hours is not None:
        cutoff = int(time.time()) - int(hours) * 3600
        conditions.append("a.publish_time >= :cutoff")
        params["cutoff"] = cutoff

    sql = f"""
        SELECT a.id, a.fakeid, s.nickname, a.title, a.link, a.author,
               a.digest, a.publish_time, a.fetched_at
        FROM articles a
        LEFT JOIN subscriptions s ON a.fakeid = s.fakeid
        WHERE {' AND '.join(conditions)}
        ORDER BY a.publish_time DESC
        LIMIT :limit
    """
    params["limit"] = limit
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    articles = [_row_to_dict(r) for r in rows]
    if fmt == "table":
        _articles_table(articles)
    _ok(articles)


def _articles_from_api(fakeid, hours, keyword, limit, fmt):
    params = []
    if fakeid:
        params.append(f"fakeid={fakeid}")
    if keyword:
        import urllib.parse
        params.append(f"keyword={urllib.parse.quote(keyword)}")
    params.append(f"count={limit}")
    qs = "&".join(params)
    code, d = _req("GET", f"/public/articles?{qs}")
    if code != 200 or not d.get("success"):
        _fail(d.get("error", f"API fallback failed: HTTP {code}"))
    data = d.get("data", {})
    articles = data.get("articles", []) if isinstance(data, dict) else data
    if fmt == "table":
        _articles_table(articles)
    _ok(articles)


def _row_to_dict(r):
    pub = r["publish_time"]
    return {
        "id": r["id"],
        "fakeid": r["fakeid"],
        "nickname": r["nickname"] or "",
        "title": r["title"],
        "link": r["link"],
        "author": r["author"] or "",
        "digest": (r["digest"] or "")[:200],
        "publish_time": pub,
        "publish_time_str": datetime.fromtimestamp(pub, TZ).strftime("%Y-%m-%d %H:%M") if pub else "",
    }


def _articles_table(articles):
    from cli.core import _format_table
    rows = [[a.get("nickname", ""), a["title"], a.get("publish_time_str", ""),
             (a.get("digest", "") or "")[:60]] for a in articles]
    print(_format_table(rows, ["Account", "Title", "Time", "Digest"]))
    import sys
    sys.exit(0)

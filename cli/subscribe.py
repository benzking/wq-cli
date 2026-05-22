"""wq subscribe / unsubscribe / subscriptions / poll — RSS subscription management."""
from cli.core import _req, _ok, _fail


def cmd_subscribe(fakeid, nickname=""):
    code, d = _req("POST", "/rss/subscribe", body={"fakeid": fakeid, "nickname": nickname})
    if code != 200:
        _fail(f"Subscribe failed: HTTP {code}")
    _ok({"message": d.get("message", "Subscribed"), "fakeid": fakeid})


def cmd_unsubscribe(fakeid):
    code, d = _req("DELETE", f"/rss/subscribe/{fakeid}")
    if code != 200:
        _fail(f"Unsubscribe failed: HTTP {code}")
    _ok({"message": d.get("message", "Unsubscribed"), "fakeid": fakeid})


def cmd_subscriptions(fmt="json"):
    code, d = _req("GET", "/rss/subscriptions")
    if code != 200:
        _fail(f"List subscriptions failed: HTTP {code}")
    subs = d.get("data", [])
    if fmt == "table":
        from cli.core import _format_table
        rows = [[s.get("nickname", ""), s["fakeid"], s.get("article_count", 0),
                 s.get("rss_url", "")] for s in subs]
        print(_format_table(rows, ["Nickname", "FakeID", "Articles", "RSS URL"]))
        import sys
        sys.exit(0)
    _ok(subs)


def cmd_poll():
    code, d = _req("POST", "/rss/poll")
    if code != 200:
        _fail(f"Poll failed: HTTP {code}")
    _ok(d.get("data", {"message": "Poll triggered"}))

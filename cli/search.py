"""wq search — search WeChat accounts; wq info — account details."""
import urllib.parse
from cli.core import _req, _ok, _fail


def cmd_search(query, fmt="json"):
    encoded = urllib.parse.quote(query)
    code, d = _req("GET", f"/public/searchbiz?query={encoded}")
    if code != 200:
        _fail(d.get("error", f"HTTP {code}"))
    if not d.get("success"):
        _fail(d.get("error", "Search failed"))
    accounts = d["data"]["list"]
    if not accounts:
        _fail("No matching accounts found")
    if fmt == "table":
        _ok_as_table(accounts)
    _ok(accounts)


def cmd_info(fakeid):
    code, d = _req("GET", f"/public/accountinfo?fakeid={fakeid}")
    if code != 200:
        _fail(d.get("error", f"HTTP {code}"))
    _ok(d.get("data", d))


def _ok_as_table(accounts):
    from cli.core import _format_table
    rows = [[a.get("nickname", ""), a["fakeid"], a.get("alias", ""),
             (a.get("round_head_img", "") or "")[:50] + "..."]
            for a in accounts]
    print(_format_table(rows, ["Nickname", "FakeID", "Alias", "HeadImg"]))
    import sys
    sys.exit(0)

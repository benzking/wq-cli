"""wq-cli CLI — WeChat Article Query command line interface.

Usage:
  wq check [--auto-recover]
  wq status
  wq search <query> [--format=json|table]
  wq info <fakeid>
  wq subscribe <fakeid> [--nickname=<name>]
  wq unsubscribe <fakeid>
  wq subscriptions [--format=json|table]
  wq poll
  wq articles [--hours=N] [--keyword=K] [--fakeid=F] [--limit=N] [--format=json|table]
  wq fetch <url> [--format=json|md|mhtml] [--outdir=PATH]
  wq push-report [--hours=N]
  wq md-push [--hours=N]
  wq login
  wq cron-setup
  wq version
"""
import argparse
import sys

VERSION = "0.1.0"


def main():
    parser = argparse.ArgumentParser(
        prog="wq",
        description="WeChat Article Query CLI — Agent interface for wq-cli service",
    )
    sub = parser.add_subparsers(dest="command", title="commands")

    # check
    p_check = sub.add_parser("check", help="Health + login status check")
    p_check.add_argument("--auto-recover", action="store_true", help="Try auto-restart on failure")

    # status
    sub.add_parser("status", help="Auth status only (JSON)")

    # search
    p_search = sub.add_parser("search", help="Search WeChat accounts")
    p_search.add_argument("query", nargs="+", help="Search keyword")
    p_search.add_argument("--format", default="json", choices=["json", "table"])

    # info
    p_info = sub.add_parser("info", help="Account detail")
    p_info.add_argument("fakeid", help="Account FakeID")

    # subscribe
    p_sub = sub.add_parser("subscribe", help="Add RSS subscription")
    p_sub.add_argument("fakeid", help="Account FakeID")
    p_sub.add_argument("--nickname", default="", help="Account nickname")
    p_sub.add_argument("--alias", default="", help="Account wechat ID (微信号)")
    p_sub.add_argument("--head-img", default="", help="Account head image URL")

    # unsubscribe
    p_unsub = sub.add_parser("unsubscribe", help="Remove subscription")
    p_unsub.add_argument("fakeid", help="Account FakeID")

    # subscriptions
    p_subs = sub.add_parser("subscriptions", help="List subscriptions")
    p_subs.add_argument("--format", default="json", choices=["json", "table"])

    # poll
    sub.add_parser("poll", help="Trigger RSS poll")

    # articles
    p_arts = sub.add_parser("articles", help="Query cached articles")
    p_arts.add_argument("--hours", type=int, default=None)
    p_arts.add_argument("--keyword", default=None)
    p_arts.add_argument("--fakeid", default=None)
    p_arts.add_argument("--limit", type=int, default=20)
    p_arts.add_argument("--format", default="json", choices=["json", "table"])

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch article full content")
    p_fetch.add_argument("url", help="WeChat article URL")
    p_fetch.add_argument("--format", default="json", choices=["json", "md", "mhtml"])
    p_fetch.add_argument("--outdir", default=".", help="Output directory (for md/mhtml)")

    # push-report
    p_pr = sub.add_parser("push-report", help="Push report JSON")
    p_pr.add_argument("--hours", type=int, default=24)

    # md-push
    p_mp = sub.add_parser("md-push", help="Push report Markdown")
    p_mp.add_argument("--hours", type=int, default=24)

    # login
    sub.add_parser("login", help="Show login page URL")

    # cron-setup
    sub.add_parser("cron-setup", help="Print cron registration guide")

    # version
    sub.add_parser("version", help="Show version")

    # parse_known_args for OpenCLI compatibility
    args, _ = parser.parse_known_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "cron-setup":
        _cmd_cron_setup()
        return

    if args.command == "version":
        print(f"wq-cli v{VERSION}")
        return

    if args.command == "login":
        _cmd_login()
        return

    # All other commands need service
    from cli.core import _ensure_service
    if args.command != "check":
        _ensure_service()

    _dispatch(args)


def _dispatch(args):
    cmd = args.command
    if cmd == "check":
        from cli.health import cmd_check
        cmd_check(auto_recover=getattr(args, 'auto_recover', False))
    elif cmd == "status":
        from cli.health import cmd_status
        cmd_status()
    elif cmd == "search":
        from cli.search import cmd_search
        cmd_search(" ".join(args.query), fmt=getattr(args, 'format', 'json'))
    elif cmd == "info":
        from cli.search import cmd_info
        cmd_info(args.fakeid)
    elif cmd == "subscribe":
        from cli.subscribe import cmd_subscribe
        cmd_subscribe(args.fakeid, args.nickname, alias=args.alias, head_img=args.head_img)
    elif cmd == "unsubscribe":
        from cli.subscribe import cmd_unsubscribe
        cmd_unsubscribe(args.fakeid)
    elif cmd == "subscriptions":
        from cli.subscribe import cmd_subscriptions
        cmd_subscriptions(fmt=getattr(args, 'format', 'json'))
    elif cmd == "poll":
        from cli.subscribe import cmd_poll
        cmd_poll()
    elif cmd == "articles":
        from cli.articles import cmd_articles
        cmd_articles(
            fakeid=args.fakeid, hours=args.hours,
            keyword=args.keyword, limit=args.limit,
            fmt=getattr(args, 'format', 'json'),
        )
    elif cmd == "fetch":
        from cli.fetch import cmd_fetch
        cmd_fetch(args.url, fmt=args.format, outdir=args.outdir)
    elif cmd == "push-report":
        from cli.push import cmd_push_report
        cmd_push_report(hours=args.hours)
    elif cmd == "md-push":
        from cli.push import cmd_md_push
        cmd_md_push(hours=args.hours)


def _cmd_cron_setup():
    venv_wq = "/home/gly/wq-cli/venv/bin/python -m cli"
    print(f"""\
## Hermes cron

### Daily 09:00 inspection
cronjob action=create \\
  name="wechat-inspection" \\
  schedule="0 9 * * *" \\
  script=cd /home/gly/wq-cli && {venv_wq} check \\
  no_agent=true \\
  deliver=origin

### Daily 18:00 push
cronjob action=create \\
  name="wechat-daily-push" \\
  schedule="0 18 * * *" \\
  script=cd /home/gly/wq-cli && {venv_wq} md-push --hours=24 \\
  no_agent=true \\
  deliver=origin

### Verify
cronjob action=list

> venv python: /home/gly/wq-cli/venv/bin/python
> entry point: python -m cli
> wq wrapper: /home/gly/wq-cli/wq.sh
""")


def _cmd_login():
    print("""\
Login page: http://localhost:5000/login.html

Please open this URL in a browser and scan the QR code with WeChat.
After login, credentials are valid for ~4 days.
Check status with: wq check
""")

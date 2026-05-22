"""wq-cli core — HTTP, DB fallback, output, image download. stdlib only."""
import concurrent.futures
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request

API = os.environ.get("WECHAT_API", "http://localhost:5000/api")
SERVICE_DIR = os.environ.get("WECHAT_SERVICE_DIR", "/home/gly/wq-cli")
DB_PATH = os.path.join(SERVICE_DIR, "data", "rss.db")

IMAGE_CDN_DOMAINS = frozenset({
    "mmbiz.qpic.cn",
    "mmbiz.qlogo.cn",
    "mmecoa.qpic.cn",
    "mp.weixin.qq.com",
})

IMAGE_MAGIC = {
    b'\xff\xd8\xff': 'jpg',
    b'\x89PNG':    'png',
    b'GIF8':       'gif',
    b'RIFF':       'webp',
    b'<?xml':      'svg',
    b'<svg':       'svg',
}

VERSION = "0.1.0"


def _req(method, path, body=None):
    """HTTP request via urllib (stdlib). Returns (status_code, dict)."""
    url = f"{API}{path}"
    data = None
    headers = {"Accept": "application/json", "User-Agent": f"wq-cli/{VERSION} (Agent)"}
    if method == "POST" and body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else "{}"
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"error": raw[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


def _db_conn():
    """Four-level DB access fallback. Returns sqlite3.Connection or None."""
    if not os.path.isfile(DB_PATH):
        return None
    db_dir = os.path.dirname(DB_PATH)

    # Level 1: direct read/write
    if os.access(db_dir, os.W_OK) and os.access(DB_PATH, os.R_OK):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    # Level 2: read-only + memory temp store
    if os.access(DB_PATH, os.R_OK):
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.row_factory = sqlite3.Row
        return conn

    # Level 3: copy to /tmp
    try:
        h = hashlib.sha256(DB_PATH.encode()).hexdigest()[:12]
        tmp = os.path.join(tempfile.gettempdir(), f"wechat_rss_{h}.db")
        shutil.copy2(DB_PATH, tmp)
        os.chmod(tmp, 0o600)
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        return conn
    except (PermissionError, OSError):
        return None


def _ok(data=None):
    """Print JSON success payload and exit 0."""
    print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
    sys.exit(0)


def _fail(msg, exit_code=1):
    """Print JSON error payload and exit with given code."""
    print(json.dumps({"ok": False, "error": str(msg)}, ensure_ascii=False))
    sys.exit(exit_code)


def _ensure_service():
    """Check service health, _fail if unreachable."""
    code, d = _req("GET", "/health")
    if code != 200 or d.get("status") != "healthy":
        _fail(f"Service unreachable ({code}). Start: bash /home/gly/wq-cli/start.sh")


def _format_table(rows, columns, format_spec="simple"):
    """Render rows as table. Uses tabulate if available, else ASCII fallback."""
    try:
        from tabulate import tabulate
        return tabulate(rows, headers=columns, tablefmt=format_spec)
    except ImportError:
        return _ascii_table(rows, columns)


def _ascii_table(rows, columns):
    """Minimal ASCII table when tabulate is not installed."""
    if not rows:
        return "(empty)"
    col_widths = [len(c) for c in columns]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header = "|" + "|".join(f" {columns[i]:<{col_widths[i]}} " for i in range(len(columns))) + "|"
    lines = [sep, header, sep]
    for row in rows:
        lines.append("|" + "|".join(f" {str(row[i]):<{col_widths[i]}} " for i in range(len(row))) + "|")
    lines.append(sep)
    return "\n".join(lines)


def _validate_image_bytes(data):
    """Check magic bytes to confirm data is an image."""
    for magic, _ext in IMAGE_MAGIC.items():
        if data[:len(magic)] == magic:
            return True
    return False


def _download_images(image_urls, outdir):
    """Download images to outdir. Returns {url: local_path} mapping.

    Raises ValueError for non-whitelisted domains.
    """
    from urllib.parse import urlparse

    os.makedirs(outdir, exist_ok=True)
    concurrency = int(os.environ.get("WQ_IMAGE_CONCURRENCY", "4"))

    # Validate domains first
    for url in image_urls:
        domain = urlparse(url).netloc.split(":")[0]
        if domain not in IMAGE_CDN_DOMAINS:
            raise ValueError(f"Image domain not allowed: {domain} ({url})")

    def _download_one(url):
        domain = urlparse(url).netloc.split(":")[0]
        ext = ".jpg"
        for suffix in ['.png', '.gif', '.webp', '.svg', '.jpeg', '.jpg']:
            if suffix in url.split('?')[0].lower():
                ext = suffix
                break
        h = hashlib.sha256(url.encode()).hexdigest()[:12]
        fname = f"{h}{ext}"
        fpath = os.path.join(outdir, fname)
        if os.path.exists(fpath):
            return url, fpath
        req = urllib.request.Request(url, headers={"User-Agent": f"wq-cli/{VERSION}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not _validate_image_bytes(data):
            raise ValueError(f"Downloaded file is not a valid image: {url}")
        with open(fpath, 'wb') as f:
            f.write(data)
        os.chmod(fpath, 0o600)
        return url, fpath

    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(_download_one, u): u for u in image_urls}
        for fut in concurrent.futures.as_completed(futures):
            url, local_path = fut.result()
            result[url] = local_path
    return result

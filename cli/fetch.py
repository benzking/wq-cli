"""wq fetch — fetch article full content with json/md/mhtml output."""
import base64
import os
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from cli.core import _req, _ok, _fail, _download_images

TZ = timezone(timedelta(hours=8), "Asia/Shanghai")

_WECHAT_BASE_CSS = """\
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
       "Hiragino Sans GB", "Microsoft YaHei", sans-serif; font-size: 17px;
       line-height: 1.6; color: #333; max-width: 677px; margin: 0 auto;
       padding: 20px; }
img { max-width: 100%; height: auto; }
p { margin: 0 0 1em; }
h1, h2, h3 { margin: 1.2em 0 0.6em; }
blockquote { border-left: 3px solid #ddd; padding-left: 1em; color: #666; margin: 1em 0; }
pre { background: #f5f5f5; padding: 1em; overflow-x: auto; border-radius: 4px; }
code { background: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; }
"""


def cmd_fetch(url, fmt="json", outdir="."):
    code, d = _req("POST", "/article", body={"url": url})
    if code != 200:
        _fail(f"Fetch failed: HTTP {code}")
    if not d.get("success"):
        _fail(d.get("error", "Fetch failed"))

    article = d["data"]
    if fmt == "json":
        _ok(article)
    elif fmt == "md":
        _ok(_fetch_md(article, outdir))
    elif fmt == "mhtml":
        _ok(_fetch_mhtml(article, outdir))


def _fetch_md(article, outdir):
    title = article.get("title", "untitled")
    content = article.get("content", "")
    images = article.get("images", [])

    outpath = os.path.abspath(outdir)
    if not os.access(outpath, os.W_OK):
        _fail(f"Output directory not writable: {outpath}")

    img_dir = os.path.join(outpath, "images")
    img_map = {}
    if images:
        img_map = _download_images(images, img_dir)

    md_body = _html_to_md(content)

    for url, local_path in img_map.items():
        rel_path = os.path.relpath(local_path, outpath)
        md_body = md_body.replace(url, rel_path)

    author = article.get("author", "")
    pub_ts = article.get("publish_time", 0)
    pub_str = datetime.fromtimestamp(pub_ts, TZ).strftime("%Y-%m-%d %H:%M:%S") if pub_ts else ""

    lines = [f"# {title}", ""]
    if author:
        lines.append(f"**作者**: {author}")
    if pub_str:
        lines.append(f"**发布时间**: {pub_str}")
    lines.append("")
    lines.append(md_body)

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
    md_path = os.path.join(outpath, f"{safe_title}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    return {"md_path": md_path, "image_dir": img_dir}


def _fetch_mhtml(article, outdir):
    title = article.get("title", "untitled")
    content = article.get("content", "")
    images = article.get("images", [])

    outpath = os.path.abspath(outdir)
    if not os.access(outpath, os.W_OK):
        _fail(f"Output directory not writable: {outpath}")

    img_dir = os.path.join(outpath, "images")
    img_map = {}
    if images:
        img_map = _download_images(images, img_dir)

    boundary = f"----wq-mhtml-{uuid.uuid4().hex[:16]}"

    style_blocks = []
    for m in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE):
        style_blocks.append(m.group(1))

    combined_css = "\n".join(style_blocks) + "\n" + _WECHAT_BASE_CSS

    html_body = content
    cid_map = {}
    for i, (url, local_path) in enumerate(img_map.items()):
        cid = f"image-{i:03d}"
        cid_map[cid] = (url, local_path)
        html_body = html_body.replace(url, f"cid:{cid}")

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_escape_html(title)}</title>
  <base href="https://mp.weixin.qq.com/">
  <style>{combined_css}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    html_part = MIMEText(html_doc, "html", "utf-8")

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)[:80]
    mhtml_path = os.path.join(outpath, f"{safe_title}.mhtml")

    with open(mhtml_path, 'w', encoding='utf-8') as f:
        f.write(f"From: <saved by wq-cli>\r\n")
        f.write(f"Subject: {title}\r\n")
        f.write(f"Date: {datetime.now(TZ).strftime('%a, %d %b %Y %H:%M:%S +0800')}\r\n")
        f.write(f"MIME-Version: 1.0\r\n")
        f.write(f"Content-Type: multipart/related; boundary=\"{boundary}\"; type=\"text/html\"\r\n")
        f.write("\r\n")
        f.write(f"--{boundary}\r\n")
        f.write("Content-Type: text/html; charset=utf-8\r\n")
        f.write("Content-Transfer-Encoding: quoted-printable\r\n")
        f.write("\r\n")
        f.write(html_doc)
        f.write("\r\n")

        for cid, (url, local_path) in cid_map.items():
            with open(local_path, 'rb') as img_file:
                img_data = img_file.read()
            ext = os.path.splitext(local_path)[1].lower()
            mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                        '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'}
            mime_type = mime_map.get(ext, 'image/jpeg')
            encoded = base64.b64encode(img_data).decode('ascii')

            f.write(f"--{boundary}\r\n")
            f.write(f"Content-Type: {mime_type}\r\n")
            f.write("Content-Transfer-Encoding: base64\r\n")
            f.write(f"Content-ID: <{cid}>\r\n")
            f.write("\r\n")
            for i in range(0, len(encoded), 76):
                f.write(encoded[i:i+76] + "\r\n")
            f.write("\r\n")

        f.write(f"--{boundary}--\r\n")

    return {"mhtml_path": mhtml_path}


def _html_to_md(html):
    try:
        import html2text
        h = html2text.HTML2Text()
        h.body_width = 0
        h.ignore_links = False
        h.ignore_images = False
        return h.handle(html)
    except ImportError:
        text = re.sub(r'<br\s*/?\s*>', '\n', html, flags=re.IGNORECASE)
        text = re.sub(r'</(?:p|div|section|h[1-6]|tr|li|blockquote)>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def _escape_html(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

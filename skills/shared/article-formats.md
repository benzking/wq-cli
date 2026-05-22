# Article Output Formats

## JSON (default)

```bash
wq fetch <url>
```

Returns structured article data: `title`, `content` (raw HTML), `plain_content`, `author`, `publish_time`, `images[]`.
Same format as `POST /api/article` response. Best for Agent processing.

## Markdown (`--format=md`)

```bash
wq fetch <url> --format=md --outdir=./output
```

1. Converts WeChat HTML to Markdown (html2text optional, falls back to basic strip)
2. Downloads all images to `--outdir/images/`
3. Replaces image URLs with local relative paths
4. Output: `<outdir>/<title>.md` + `<outdir>/images/`

Images are saved with `sha256(url)[:12]` filenames, preserving original extensions.
Already downloaded images are skipped (idempotent).

## MHTML (`--format=mhtml`)

```bash
wq fetch <url> --format=mhtml --outdir=./output
```

1. Downloads all images locally
2. Converts images to base64 data URIs
3. Inlines CSS from original `<style>` blocks + WeChat baseline styles
4. Assembles MIME multipart/related document with `cid:` image references
5. Output: `<outdir>/<title>.mhtml` — single file, fully offline readable

MHTML structure follows RFC 2557:
- `<base href="https://mp.weixin.qq.com/">` for relative links
- `<img src="cid:image-NNN">` for inline images
- Each image as a separate MIME part with `Content-ID` header

## Image Download Constraints

- Only WeChat CDN domains allowed: `mmbiz.qpic.cn`, `mmbiz.qlogo.cn`, `mmecoa.qpic.cn`, `mp.weixin.qq.com`
- Concurrent downloads: `WQ_IMAGE_CONCURRENCY` (default 4)
- Magic byte validation: JPEG/PNG/GIF/WebP/SVG
- File permissions: `0o600`

# Troubleshooting

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | — |
| 1 | General error | Read the `error` field in JSON output |
| 2 | Auth expired | Call `wq login`, open URL in browser, re-scan QR |

## Common Errors

### "Service unreachable"
```bash
cd /home/gly/wq-cli && bash start.sh && sleep 3 && wq check
```

### "Not logged in" / "Auth expired"
```bash
wq login
# → Open http://localhost:5000/login.html in browser
# → Scan QR code with WeChat (via the logged-in Official Account admin)
# → Verify with: wq check
```

### "Rate limited"
Wait 30–60 seconds before retrying. The backend has built-in rate limiting.

### "Verification required"
WeChat is showing a CAPTCHA. Open the article URL in a real browser, complete the verification,
then wait 30 minutes before retrying.

### "No matching accounts found"
Try a shorter or different keyword. WeChat search is fuzzy-match on account names.

### "Database not found"
This happens when the CLI user lacks read permission on `data/rss.db`:
```bash
# Fix: add current user to wechat-api group
sudo usermod -aG wechat-api $(whoami)
# Then re-login or run: newgrp wechat-api
```
The CLI falls back to HTTP API (Level 4) automatically for `wq articles`.

## Output Format Notes

- **`md-push`** outputs pure Markdown, NOT JSON. This is intentional — for direct cron delivery.
- All other commands output `{"ok": true/false, "data/error": ...}`.
- `--format=table` prints ASCII table to stdout (tabulate optional).

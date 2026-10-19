# watch

A tiny uptime check. Every 5 minutes a GitHub Actions job requests a health URL and sends a Telegram message when it fails twice in a row, every 30 minutes while it stays down, and once when it recovers.

The URL, bot token and chat id are repository secrets (`HEALTH_URL`, `TG_TOKEN`, `TG_CHAT`). The job log prints only `ok` or `down`.

# Bunk Budget notifier

Runs entirely on GitHub Actions (daily at 23:05 IST). No laptop or
Claude app needs to be open.

It spawns the official `@newtonschool/newton-mcp` server over stdio,
pulls your current semester's attendance (lecture + lab combined per
subject), and pushes a summary notification to your phone via
[ntfy.sh](https://ntfy.sh) — install the ntfy Android app and
subscribe to the topic stored in this repo's `NTFY_TOPIC` secret.

Trigger a run manually any time from the Actions tab ("Run workflow").

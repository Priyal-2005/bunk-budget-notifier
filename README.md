# Bunk Budget notifier

Pulls your current semester's data from Newton School and sends a
Telegram message with:

- Overall attendance %, plus each subject's lecture+lab combined %
- Assignment completion % (with a nudge if it's at or below 75%)
- On the morning run only: any assignments/contests due in the next
  24 hours

## Current status: not fully automatable for free

This was designed to run entirely on GitHub Actions, no device
needed. In practice, Newton's API blocks requests from GitHub's
shared runner IPs with a 403 — confirmed on **both** the macOS pool
(running the official `@newtonschool/newton-mcp` binary, `notify.py`)
and the Ubuntu pool (a from-scratch pure-HTTP client, `notify_http.py`,
built by capturing and verifying the official tool's real traffic —
see its docstring). Both get blocked instantly, with completely
different request fingerprints, which points to a network-level block
on datacenter/CI IP ranges rather than anything specific to one tool
or runner. Other free CI providers are likely to hit the same wall
for the same reason.

`.github/workflows/notify.yml` is kept for **manual testing only**
(`workflow_dispatch`) in case that ever changes — it is not scheduled
to run automatically. The reliable path right now is a scheduled task
running inside Claude (not tied to a flagged IP range), which needs
the Claude app open around trigger time (or opened at some point that
day — it catches up on next launch).

If you have an always-on machine with a non-datacenter IP (e.g. a
home server, a Raspberry Pi), running `notify_http.py` there on a
real cron job would sidestep this entirely — no Claude dependency.

## Setup (for your own account)

1. **Use this template** to create your own repo (top of this page,
   "Use this template" → "Create a new repository"). Keep it private.

2. **Get your Newton token.** On any machine with Node installed:
   ```bash
   npx -y @newtonschool/newton-mcp@latest login
   ```
   Approve the device-code prompt in your browser. This saves a
   token to `~/.newton-mcp/credentials.json`.

3. **Create a Telegram bot.** Message [@BotFather](https://t.me/BotFather)
   on Telegram, send `/newbot`, and save the token it gives you.
   Then send your new bot any message (e.g. "hi") so it knows your
   chat ID — fetch it with:
   ```bash
   curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
   ```
   and grab the `chat.id` field from the response.

4. **Set repo secrets** (Settings → Secrets and variables → Actions,
   or via `gh secret set <NAME>`):
   - `NEWTON_CREDENTIALS_JSON` — contents of `~/.newton-mcp/credentials.json`
   - `TELEGRAM_BOT_TOKEN` — your bot's token
   - `TELEGRAM_CHAT_ID` — your chat ID from step 3

5. **Test it**: Actions tab → "Bunk Budget notify" → "Run workflow".
   If your network isn't in a blocked range, this alone might just
   work — worth trying before assuming you need the Claude fallback.

6. **`notify_http.py`** hardcodes the current semester's course/subject
   hashes (`COURSE_HASH`, `SUBJECT_PAIRS` near the top) — update these
   each semester using `list_courses` via Claude or the MCP server.

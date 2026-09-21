# Bunk Budget notifier

Pulls your current semester's data from Newton School and sends an
[ntfy](https://ntfy.sh) notification with:

- Overall attendance %, plus each subject's lecture+lab combined %
- Assignment completion % (with a nudge if it's at or below 75%)
- On the morning run only: any assignments/contests due in the next
  24 hours

## Recommended setup: your phone, via Termux (fully independent)

The most reliable free option is running `notify_http.py` on a real
cron job **on your own phone**, using [Termux](https://f-droid.org/en/packages/com.termux/)
(install from F-Droid, not Play Store). Your phone has a mobile/
residential IP, not a datacenter one, so it isn't subject to the
GitHub Actions issue below — and it doesn't depend on Claude, a
laptop, or any subscription.

```bash
# In Termux:
pkg update -y && pkg upgrade -y
pkg install -y python git nodejs cronie termux-services termux-api

# Get your own Newton token (opens a browser approval link)
npx -y @newtonschool/newton-mcp@latest login

git clone <this-repo-url>
cd bunk-budget-notifier

# Pick your own private ntfy topic (anyone who knows it can read your
# notifications) and subscribe to it in the ntfy app first
cat > ~/.bunk-budget-env << 'EOF'
export NTFY_TOPIC="<your-own-random-topic-name>"
EOF

sv-enable crond
crontab -e
```
Add:
```
0 8 * * * . ~/.bunk-budget-env && cd ~/bunk-budget-notifier && SLOT=morning CHECK_DEADLINES=true python3 notify_http.py >> ~/bunk-budget.log 2>&1
0 23 * * * . ~/.bunk-budget-env && cd ~/bunk-budget-notifier && SLOT=evening python3 notify_http.py >> ~/bunk-budget.log 2>&1
```

Then go to **Settings → Apps → Termux → Battery** and set it to
**Unrestricted** — otherwise Android may silently kill the cron jobs
in the background.

Test it anytime with:
```bash
. ~/.bunk-budget-env && cd ~/bunk-budget-notifier && SLOT=test CHECK_DEADLINES=true python3 notify_http.py
```

## GitHub Actions: known not to work for free right now

`.github/workflows/notify.yml` exists but its automatic schedule is
**disabled**. Newton's API blocks requests from GitHub's shared
runner IPs with a 403 — confirmed on both the macOS pool (running the
official `@newtonschool/newton-mcp` binary, `notify.py`) and the
Ubuntu pool (`notify_http.py`, a from-scratch client built by
capturing and verifying the official tool's real traffic — see its
docstring, not guessed). Both get blocked instantly with completely
different request fingerprints, pointing to a network-level block on
datacenter/CI IP ranges generally, not one tool or runner. Other free
CI providers are likely to hit the same wall.

You can still trigger it manually (Actions tab → "Bunk Budget notify"
→ "Run workflow") to check if that's ever changed — worth trying once
before assuming you need Termux or a Claude-based fallback.

## Setup, step by step

1. **Use this template** to create your own repo (top of this page,
   "Use this template" → "Create a new repository"). Public or
   private both work — no secrets ever live in the code itself, only
   in your own GitHub Actions secrets / local env files, which never
   get committed.

2. **Get your Newton token.** On any machine with Node installed:
   ```bash
   npx -y @newtonschool/newton-mcp@latest login
   ```
   Approve the device-code prompt in your browser. This saves a
   token to `~/.newton-mcp/credentials.json`.

3. **Pick an ntfy topic** — install the [ntfy app](https://ntfy.sh)
   (iOS or Android) and subscribe to a topic name only you know (a
   random string works well — anyone who knows the name can read
   notifications sent to it).

4. **Run it** — either via Termux on your phone (see above,
   recommended), or via GitHub Actions manually: set repo secrets
   `NEWTON_CREDENTIALS_JSON` (contents of `~/.newton-mcp/credentials.json`)
   and `NTFY_TOPIC`, then Actions tab → "Bunk Budget notify" → "Run workflow".

5. **`notify_http.py`** hardcodes the current semester's course/subject
   hashes (`COURSE_HASH`, `SUBJECT_PAIRS` near the top) — update these
   each semester. Ask Claude (with the Newton MCP server connected) to
   call `list_courses` and give you the new values.

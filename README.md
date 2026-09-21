# Bunk Budget notifier

Pulls your current semester's data from Newton School and sends a
Telegram message with:

- Overall attendance %, plus each subject's lecture+lab combined %
- Assignment completion % (with a nudge if it's at or below 75%)
- On the morning run only: any assignments/contests due in the next
  24 hours

Fires daily at 8:00am and 11:00pm IST.

## Setup for your own account

All paths require the same initial setup:

### 1. Get your Newton token
On any machine with Node installed (Mac, Linux, or even Termux on Android):
```bash
npx -y @newtonschool/newton-mcp@latest login
```
Approve the device-code prompt in your browser with *your own* Newton account. 
Saves a token to `~/.newton-mcp/credentials.json`.

### 2. Create a Telegram bot
Message [@BotFather](https://t.me/BotFather) on Telegram:
- Send `/newbot`
- Save the bot token it gives you
- Send your new bot any message (e.g. "hi")
- Get your chat ID with:
```bash
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
```
Look for `"id"` in the response — that's your chat ID.

### 3. Pick your setup path

---

## Android (Termux) — Fully independent ⭐ Recommended

No Claude Pro needed, no Mac needed, fully automatic.

**Install:**
1. Download **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) 
   (not Play Store — that version is outdated)
2. Open Termux and run:
```bash
pkg update -y && pkg upgrade -y
pkg install -y python git nodejs cronie termux-services termux-api
```

**Setup:**
3. Get your Newton token (see step 1 above) and copy it to the phone
4. Clone the repo:
```bash
git clone https://github.com/Priyal-2005/bunk-budget-notifier.git
cd bunk-budget-notifier
```

5. Create your environment file:
```bash
cat > ~/.bunk-budget-env << 'ENVEOF'
export TELEGRAM_BOT_TOKEN="<your-bot-token>"
export TELEGRAM_CHAT_ID="<your-chat-id>"
ENVEOF
```

6. Set up cron (this runs the script automatically at 8am/11pm):
```bash
sv-enable crond
crontab -e
```
Add these two lines:
```
0 8 * * * . ~/.bunk-budget-env && cd ~/bunk-budget-notifier && SLOT=morning CHECK_DEADLINES=true python3 notify_http.py >> ~/bunk-budget.log 2>&1
0 23 * * * . ~/.bunk-budget-env && cd ~/bunk-budget-notifier && SLOT=evening python3 notify_http.py >> ~/bunk-budget.log 2>&1
```
Save with `Ctrl+X`, `Y`, `Enter`.

7. **Important:** Go to **Settings → Apps → Termux → Battery** and set to 
   **Unrestricted** (not "Optimized") — otherwise Android may kill the cron jobs.

8. Test it:
```bash
. ~/.bunk-budget-env && python3 notify_http.py
```
Should get a Telegram message immediately with your attendance data.

---

## iOS — Using Claude scheduled tasks (requires Claude Pro)

No Termux equivalent exists for iOS.

1. **Use this template** to create your own repo (top of the page,
   "Use this template" → "Create a new repository").
2. Get your Newton token (step 1 above).
3. In Claude Code, open this repo and create two scheduled tasks:
   - Morning: 8:00 AM IST, sends morning check + deadline reminders
   - Evening: 11:00 PM IST, sends evening check
   
   Both send via Telegram using your bot token and chat ID.
4. Keep the Claude app open around trigger time, or open it anytime that day 
   (tasks catch up on next launch).

**Trade-off:** Needs Claude Pro. Without it, the scheduled tasks won't run.

---

## Mac / Linux server — Full automation (like Android)

Same as the Android Termux setup, just install on your Mac/Linux:
```bash
# macOS (using Homebrew)
brew install python3 nodejs git

# Then follow the Termux setup steps (clone repo, environment file, crontab, etc.)
```

Cron runs 24/7 on your machine, so notifications are fully automatic. No Claude needed.

---

## GitHub Actions — Manual testing only (not automatic)

`.github/workflows/notify.yml` exists but is **not scheduled** — Newton's API blocks 
requests from GitHub's datacenter IPs. You can still manually trigger it (Actions tab 
→ "Bunk Budget notify" → "Run workflow") if you want to test from a CI environment, 
but it's not reliable.

---

## Notes

- **Course/subject hashes** in `notify_http.py` are hardcoded for the current semester 
  (`COURSE_HASH`, `SUBJECT_PAIRS` near the top). Update these each semester by asking 
  Claude to call `mcp__newton__list_courses`.
- Each person gets their own Telegram bot and Newton token — they're never shared 
  across users.
- The repo is public; no secrets ever get committed, only environment variables on 
  each device.

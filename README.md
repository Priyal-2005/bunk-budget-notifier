# Bunk Budget notifier

Runs entirely on GitHub Actions — no laptop, phone app, or Claude
needs to be open. It spawns the official `@newtonschool/newton-mcp`
server over stdio, pulls your current semester's data from Newton
School, and sends you a Telegram message with:

- Overall attendance %, plus each subject's lecture+lab combined %
- Assignment completion % (with a nudge if it's at or below 75%)
- On the morning run only: any assignments/contests due in the next
  24 hours

Fires daily at 8:00am and 11:00pm IST (`.github/workflows/notify.yml`
— edit the cron lines to change the schedule; both are in UTC).

## Setup (for your own account)

1. **Use this template** to create your own repo (top of this page,
   "Use this template" → "Create a new repository"). Keep it private.

2. **Get your Newton token.** On any Mac/Linux machine with Node
   installed:
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

That's it — it'll run on schedule from then on, independent of any
device you own.

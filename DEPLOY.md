# Deploying the clinic bot

This repo runs on Render's free tier as a webhook service - Telegram pushes
every message straight to it, so replies are instant, with no one relaying
messages by hand.

Claude (the assistant that built this) drove the GitHub repo creation and
the Render web service setup directly. The only two things Claude will never
touch are your bot token and the final webhook URL that contains it - those
stay entirely in your hands, by design.

## Your two remaining steps
1. In the Render dashboard, under this service's "Environment" tab, add:
   - Key: TELEGRAM_BOT_TOKEN
   - Value: your bot's token (from @BotFather -> /mybots -> your bot -> API Token)
2. Once the service is live at its Render URL, open this in your browser
   (fill in your own token and URL):
   https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<YOUR_RENDER_URL>/webhook
   You should see {"ok":true,"result":true,...}

Then message @call_jimmy_bot on Telegram - it replies on its own from here on.

## Known limitations of this MVP
- Cold start: Render's free tier sleeps after 15 minutes idle; the first
  message after a quiet period takes roughly 30-50 seconds to wake up.
  Every message after that is instant.
- Storage: appointments are stored in a JSON file on Render's disk - fine
  for testing, but swap for a real database (Render Postgres, Supabase, etc)
  before relying on it for real bookings.
- Payment link and prescription are simulated (sandbox-style fake data), as
  discussed - a real payment gateway and a real doctor's prescription source
  are separate, later integrations.

Sources checked for the free-tier claims above:
- https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026
- https://snapdeploy.dev/blog/host-python-web-app-free-2026-guide

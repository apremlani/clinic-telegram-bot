# Deploying the clinic bot -- always-on, no more manual relaying

This makes the bot respond instantly on its own, 24/7. It uses Render's free
tier (no credit card, confirmed as of 2026 -- see sources at the bottom).
Your bot token stays only in Render's own dashboard -- never paste it in
chat with Claude.

## 1. Put the code on GitHub (5 min)
1. Go to github.com and sign up free if you don't have an account.
2. Click "New repository", name it e.g. `clinic-telegram-bot`, keep it Private or
   Public (either works), click Create.
3. On the new repo page, click "Add file" -> "Upload files", and drag in every
   file from the `tronix_bot` folder you were sent (engine.py, main.py,
   requirements.txt, render.yaml, DESIGN.md -- the data/ folder can stay out,
   it'll be created automatically). Commit.

## 2. Deploy on Render (5 min)
1. Go to render.com, sign up free (you can sign up with your GitHub account --
   no card needed).
2. Click "New +" -> "Web Service" -> connect the GitHub repo you just made.
3. Render should auto-detect the `render.yaml` and pre-fill everything. If it
   asks manually instead, set:
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Under "Environment", add a variable:
   - Key: `TELEGRAM_BOT_TOKEN`
   - Value: your bot's token (get it again anytime from @BotFather -> /mybots ->
     your bot -> API Token, if you don't have it handy)
5. Click "Create Web Service". Wait for the build to finish -- Render gives you
   a live URL like `https://clinic-telegram-bot-xxxx.onrender.com`.

## 3. Point Telegram at it (1 min)
Open this URL in your browser (fill in your own token and your Render URL):

```
https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<YOUR_RENDER_URL>/webhook
```

You should see `{"ok":true,"result":true,...}`. That's it -- Telegram will now
push every message straight to your bot the instant it arrives.

## 4. Test it
Message @call_jimmy_bot on Telegram. It should reply on its own, instantly,
with no one relaying anything.

## 5. Make bookings survive restarts (recommended -- 5 min)
Render's free tier wipes its local disk on every restart, which also wipes
the `data/db.json` file the bot used at first -- so without this step, the
bot "forgets" bookings/prescriptions/reminders whenever it restarts (e.g.
after 15 minutes idle). Fix it with a free Postgres database (a proper
database service, unlike a plain file -- doesn't get wiped):

1. Go to supabase.com, sign up free (no credit card needed), and create a
   new project (pick any name/region/password for the project -- the
   password here is Supabase's own project password, separate from your
   bot token).
2. In your Supabase project, go to Project Settings -> Database ->
   Connection string, and copy the "URI" connection string (starts with
   `postgresql://...`). Fill in the database password you set in step 1
   wherever the string shows `[YOUR-PASSWORD]`.
3. In Render, open your bot's service -> Environment tab -> Add Environment
   Variable:
   - Key: `DATABASE_URL`
   - Value: the connection string you copied (paste it directly here --
     never share it in chat with Claude or anyone else)
4. Save. Render will automatically restart the bot picking up the new
   variable. From then on, all bookings/prescriptions/reminders are stored
   in this database and survive restarts and redeploys.

If `DATABASE_URL` is never set, the bot keeps working exactly as before,
using the local JSON file (fine for quick testing, not for real use).

## Known limitations of this MVP (be aware, not blockers for testing)
- **Cold start**: Render's free tier sleeps after 15 minutes idle; the first
  message after a quiet period takes ~30-50 seconds to wake up. Every message
  after that is instant. (Source: render.com's own 2026 free-tier writeup.)
- **Payment link and prescription are simulated** (sandbox-style fake data),
  as discussed -- wiring a real payment gateway and a real doctor's
  prescription source are separate, later steps.

Sources checked for the free-tier claims above:
- https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026
- https://snapdeploy.dev/blog/host-python-web-app-free-2026-guide
- https://www.itpathsolutions.com/supabase-free-tier-limits
- https://freetier.co/directory/products/supabase

# Clinic WhatsApp/Telegram Assistant - v1 Design (channel: Telegram for MVP)

## States (per chat_id)
- IDLE - default, listens for commands or free text
- BOOK_WHO - who is this appointment for (self / family member)
- BOOK_NAME - patient's name (if booking for someone else)
- BOOK_REASON - reason for visit (light intake, non-diagnostic)
- BOOK_TIME - preferred date/time
- BOOK_CONFIRM - confirm before saving

## Data model (JSON store, data/db.json)
- patients: [{id, chat_id, name, relation_to_requester}]
- appointments: [{id, chat_id, patient_id, reason, preferred_time, status, urgent, created_at}]
- prescriptions: [{id, appointment_id, medicines: [{name, dose, duration_days}], created_at}]
- payments: [{id, appointment_id, amount_inr, link, status}]
- reminder_log: [{id, appointment_id, kind, scheduled_for, sent}]

## Commands
- /start, /help - menu
- /book - start booking flow (supports booking for self or a family member)
- /myappointments - list bookings for this chat
- /prescription - show a (simulated) digital prescription for the latest completed appointment + auto-derived medicine reminders
- /pay - generate a sandbox payment link for the latest appointment
- /reminders - show what reminders would fire and when (demo of the reminder engine's rules, since real 24/7 delivery needs a persistent deployment)
- /cancel - abort the current flow

## Safety-by-design rules
1. The bot never gives medical advice or a diagnosis - reason-for-visit capture is descriptive only, passed to the doctor, not interpreted.
2. Urgent-keyword detection (chest pain, can't breathe, unconscious, severe bleeding, "emergency") triggers a clear "please call emergency services / clinic directly" response + logs a severity-tagged alert - it never tries to triage medically itself.
3. Language: basic Devanagari-script detection to reply in Hindi when the user writes in Hindi, else English.

## What's real vs simulated in this MVP
- Real: the Telegram bot, the conversation engine, the booking/appointment data, urgent-keyword logging, language detection.
- Simulated (clearly labeled to the user): payment gateway (sandbox-style fake link, no real gateway account yet), prescription source (sample data, not a live doctor's EMR), timed reminder delivery (shown as "would fire at X" rather than actually firing, since always-on scheduling needs a persistent server - see DEPLOY.md).

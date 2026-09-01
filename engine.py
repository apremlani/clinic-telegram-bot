"""
Clinic Assistant conversation engine (channel-agnostic).
Feed it (chat_id, user_display_name, text) -> get back a reply string.
All state is persisted to data/db.json so the engine can be called once
per incoming message (works for both a live polling loop and a webhook).

This file has NO Telegram-specific code in it on purpose: the same engine
can sit behind Telegram, WhatsApp, or a web widget later without changes.
"""
import json
import os
import re
import uuid
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "db.json")

URGENT_KEYWORDS = [
    "chest pain", "can't breathe", "cant breathe", "unconscious", "severe bleeding",
    "emergency", "urgent", "not breathing", "seizure", "collapsed", "बेहोश", "सांस नहीं",
]

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

MEDICINE_SAMPLE = [
    {"name": "Paracetamol 500mg", "dose": "1 tablet twice a day", "duration_days": 3},
    {"name": "Cetirizine 10mg", "dose": "1 tablet at night", "duration_days": 5},
]


def _now():
    return datetime.utcnow().isoformat()


def _empty_db():
    return {"patients": [], "appointments": [], "prescriptions": [], "payments": [], "sessions": {}}


def load_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        db = _empty_db()
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def is_hindi(text: str) -> bool:
    return bool(DEVANAGARI_RE.search(text or ""))


def detect_urgent(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in URGENT_KEYWORDS)


def _session(db, chat_id):
    s = db["sessions"].setdefault(str(chat_id), {"state": "IDLE", "draft": {}})
    return s


def _reset_session(db, chat_id):
    db["sessions"][str(chat_id)] = {"state": "IDLE", "draft": {}}


def _latest_appointment(db, chat_id):
    apps = [a for a in db["appointments"] if a["chat_id"] == str(chat_id)]
    return apps[-1] if apps else None


HELP_EN = (
    "Here's what I can do:\n"
    "/book - book a clinic appointment (for yourself or a family member)\n"
    "/myappointments - see your bookings\n"
    "/prescription - view your latest digital prescription (demo data)\n"
    "/pay - get a payment link for your visit (sandbox/test link)\n"
    "/reminders - preview the reminders this booking would trigger\n"
    "/cancel - stop whatever we were doing\n\n"
    "If this is a medical emergency, please call your local emergency number or the "
    "clinic directly - I only handle bookings and logistics, never medical advice."
)

HELP_HI = (
    "मैं यह कर सकता हूँ:\n"
    "/book - क्लिनिक अपॉइंटमेंट बुक करें (अपने लिए या परिवार के किसी सदस्य के लिए)\n"
    "/myappointments - अपनी बुकिंग देखें\n"
    "/prescription - नवीनतम पर्ची देखें (डेमो डेटा)\n"
    "/pay - भुगतान लिंक पाएं (सैंडबॉक्स/टेस्ट लिंक)\n"
    "/reminders - इस बुकिंग से जुड़े रिमाइंडर देखें\n"
    "/cancel - मौजूदा प्रक्रिया रोकें\n\n"
    "अगर यह मेडिकल इमरजेंसी है, तो कृपया तुरंत इमरजेंसी नंबर या क्लिनिक को कॉल करें - मैं सिर्फ "
    "बुकिंग और लॉजिस्टिक्स संभालता हूँ, मेडिकल सलाह नहीं देता।"
)


def handle_message(chat_id, user_display_name, text) -> str:
    db = load_db()
    session = _session(db, chat_id)
    hindi = is_hindi(text)
    text_stripped = (text or "").strip()
    lower = text_stripped.lower()

    if detect_urgent(text_stripped) and session["state"] == "IDLE":
        appt = _latest_appointment(db, chat_id)
        alert = {
            "id": str(uuid.uuid4())[:8],
            "chat_id": str(chat_id),
            "text": text_stripped,
            "severity": "high",
            "appointment_id": appt["id"] if appt else None,
            "created_at": _now(),
        }
        db.setdefault("urgent_alerts", []).append(alert)
        save_db(db)
        if hindi:
            return (
                "⚠️ यह गंभीर लग रहा है। कृपया तुरंत 112 (इमरजेंसी) या अपने नज़दीकी अस्पताल को कॉल करें।\n"
                f"मैंने क्लिनिक को एक तत्काल अलर्ट भेज दिया है (अलर्ट #{alert['id']})। "
                "मैं डॉक्टर नहीं हूँ, इसलिए मैं सलाह नहीं दे सकता - कृपया अभी मदद लें।"
            )
        return (
            "⚠️ This sounds urgent. Please call your local emergency number (112 in India) or go to "
            "the nearest hospital right now.\n"
            f"I've also logged an urgent alert for the clinic (alert #{alert['id']}). "
            "I'm not a doctor and can't advise - please get help immediately."
        )

    if lower in ("/start", "start", "hi", "hello", "hey", "namaste", "नमस्ते"):
        _reset_session(db, chat_id)
        save_db(db)
        greeting_hi = f"नमस्ते {user_display_name}! मैं Tronix क्लिनिक असिस्टेंट हूँ।\n\n" + HELP_HI
        greeting_en = f"Hi {user_display_name}! I'm your clinic assistant.\n\n" + HELP_EN
        return greeting_hi if hindi else greeting_en

    if lower in ("/help", "help"):
        return HELP_HI if hindi else HELP_EN

    if lower in ("/cancel", "cancel"):
        _reset_session(db, chat_id)
        save_db(db)
        return "रद्द किया गया। /book टाइप करके फिर से शुरू करें।" if hindi else "Cancelled. Type /book to start again."

    if lower in ("/book", "book", "book appointment"):
        session["state"] = "BOOK_WHO"
        session["draft"] = {}
        save_db(db)
        return (
            "किसके लिए बुकिंग है? खुद के लिए लिखें 'self', या रिश्ता बताएं जैसे 'father', 'mother', 'daughter'।"
            if hindi else
            "Who is this appointment for? Type 'self', or a relation like 'father', 'mother', 'daughter'."
        )

    if lower in ("/myappointments", "myappointments", "my appointments"):
        apps = [a for a in db["appointments"] if a["chat_id"] == str(chat_id)]
        if not apps:
            return "अभी कोई बुकिंग नहीं है। /book टाइप करें।" if hindi else "No appointments yet. Type /book to make one."
        lines = []
        for a in apps[-5:]:
            patient = next((p for p in db["patients"] if p["id"] == a["patient_id"]), None)
            pname = patient["name"] if patient else "?"
            lines.append(f"#{a['id']} - {pname} - {a['preferred_time']} - {a['reason']} - status: {a['status']}")
        header = "आपकी हाल की बुकिंग:\n" if hindi else "Your recent appointments:\n"
        return header + "\n".join(lines)

    if lower in ("/prescription", "prescription"):
        appt = _latest_appointment(db, chat_id)
        if not appt:
            return "कोई अपॉइंटमेंट नहीं मिली। पहले /book करें।" if hindi else "No appointment found yet. Book one first with /book."
        existing = next((p for p in db["prescriptions"] if p["appointment_id"] == appt["id"]), None)
        if not existing:
            existing = {
                "id": str(uuid.uuid4())[:8],
                "appointment_id": appt["id"],
                "medicines": MEDICINE_SAMPLE,
                "created_at": _now(),
            }
            db["prescriptions"].append(existing)
            save_db(db)
        lines = [f"- {m['name']}: {m['dose']}, for {m['duration_days']} days" for m in existing["medicines"]]
        reminders = [f"  reminder every day until day {m['duration_days']} for {m['name']}" for m in existing["medicines"]]
        header = "📄 डिजिटल पर्ची (डेमो डेटा):\n" if hindi else "📄 Digital prescription (demo data - not a real doctor's prescription):\n"
        rem_header = "\n\nइनसे स्वतः दवा रिमाइंडर बनेंगे:\n" if hindi else "\n\nAuto-generated medicine reminders from this:\n"
        return header + "\n".join(lines) + rem_header + "\n".join(reminders)

    if lower in ("/pay", "pay"):
        appt = _latest_appointment(db, chat_id)
        if not appt:
            return "कोई अपॉइंटमेंट नहीं मिली।" if hindi else "No appointment found yet. Book one first with /book."
        existing = next((p for p in db["payments"] if p["appointment_id"] == appt["id"]), None)
        if not existing:
            existing = {
                "id": str(uuid.uuid4())[:8],
                "appointment_id": appt["id"],
                "amount_inr": 500,
                "link": f"https://sandbox.pay.example/tronix-demo/{uuid.uuid4().hex[:10]}",
                "status": "pending",
            }
            db["payments"].append(existing)
            save_db(db)
        note_hi = "\n\n(यह एक सैंडबॉक्स/डेमो लिंक है - असली भुगतान गेटवे अभी कॉन्फ़िगर नहीं है।)"
        note_en = "\n\n(This is a sandbox/demo link - a real payment gateway isn't wired up yet.)"
        body = f"💳 ₹{existing['amount_inr']} - {existing['link']}"
        return body + (note_hi if hindi else note_en)

    if lower in ("/reminders", "reminders"):
        appt = _latest_appointment(db, chat_id)
        if not appt:
            return "कोई अपॉइंटमेंट नहीं मिली।" if hindi else "No appointment found yet. Book one first with /book."
        plan = [
            "24h before the visit: appointment reminder",
            "2h before the visit: final reminder",
            "Same evening after the visit: follow-up check-in",
            "Daily while medicines are active: medicine reminder (see /prescription)",
        ]
        header = "🔔 इस बुकिंग के लिए रिमाइंडर योजना (डेमो - अभी असल में शेड्यूल नहीं हो रहे):\n" if hindi else \
                 "🔔 Reminder plan for this booking (preview - not actually scheduled yet in this demo):\n"
        return header + "\n".join(f"- {p}" for p in plan)

    state = session["state"]
    draft = session["draft"]

    if state == "BOOK_WHO":
        draft["relation"] = text_stripped or "self"
        session["state"] = "BOOK_NAME"
        save_db(db)
        if draft["relation"].lower() == "self":
            draft["name"] = user_display_name
            session["state"] = "BOOK_REASON"
            save_db(db)
            return "विज़िट की वजह क्या है? (सिर्फ बताएं, यह डॉक्टर के लिए है)" if hindi else \
                   "What's the reason for the visit? (Just describe it - this goes to the doctor, not for diagnosis.)"
        return "उनका नाम क्या है?" if hindi else "What's their name?"

    if state == "BOOK_NAME":
        draft["name"] = text_stripped
        session["state"] = "BOOK_REASON"
        save_db(db)
        return "विज़िट की वजह क्या है?" if hindi else "What's the reason for the visit?"

    if state == "BOOK_REASON":
        draft["reason"] = text_stripped
        session["state"] = "BOOK_TIME"
        save_db(db)
        return "कौन सा दिन/समय पसंद करेंगे?" if hindi else "What day/time would you prefer?"

    if state == "BOOK_TIME":
        draft["preferred_time"] = text_stripped
        session["state"] = "BOOK_CONFIRM"
        save_db(db)
        summary = (
            f"Patient: {draft['name']} ({draft['relation']})\n"
            f"Reason: {draft['reason']}\n"
            f"Preferred time: {draft['preferred_time']}\n\n"
        )
        return summary + ("पुष्टि करने के लिए 'yes' लिखें, बदलने के लिए 'no'।" if hindi else "Type 'yes' to confirm, or 'no' to start over.")

    if state == "BOOK_CONFIRM":
        if lower in ("yes", "y", "हाँ", "haan", "ha"):
            patient_id = str(uuid.uuid4())[:8]
            db["patients"].append({
                "id": patient_id, "chat_id": str(chat_id),
                "name": draft["name"], "relation_to_requester": draft["relation"],
            })
            appt_id = str(uuid.uuid4())[:8]
            db["appointments"].append({
                "id": appt_id, "chat_id": str(chat_id), "patient_id": patient_id,
                "reason": draft["reason"], "preferred_time": draft["preferred_time"],
                "status": "booked", "urgent": False, "created_at": _now(),
            })
            _reset_session(db, chat_id)
            save_db(db)
            done_hi = f"✅ बुकिंग पक्की! अपॉइंटमेंट #{appt_id}। रिमाइंडर देखने के लिए /reminders टाइप करें।"
            done_en = f"✅ Booked! Appointment #{appt_id}. Type /reminders to see what reminders this triggers."
            return done_hi if hindi else done_en
        _reset_session(db, chat_id)
        save_db(db)
        return "ठीक है, रद्द किया। फिर से /book करें।" if hindi else "Okay, cancelled. Type /book to try again."

    return HELP_HI if hindi else ("I didn't quite get that. " + HELP_EN)

import os
import json
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886").strip()
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def configured():
    return bool(
        TWILIO_ACCOUNT_SID
        and TWILIO_AUTH_TOKEN
        and TWILIO_WHATSAPP_FROM
        and TWILIO_WHATSAPP_TO
    )

def twilio_client():
    if not configured():
        raise RuntimeError("Twilio environment variables are incomplete.")
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.get("/")
def index():
    return render_template(
        "index.html",
        configured=configured(),
        whatsapp_from=TWILIO_WHATSAPP_FROM,
        whatsapp_to=TWILIO_WHATSAPP_TO,
        public_base_url=PUBLIC_BASE_URL,
    )

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "hosen-whatsapp-test",
        "twilio_configured": configured(),
        "timestamp": utc_now(),
    })

@app.post("/api/send-test")
def send_test():
    if not configured():
        return jsonify({
            "ok": False,
            "error": "Twilio environment variables are incomplete."
        }), 500

    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()

    if not body:
        body = (
            "🚨 HOSEN TEST\n\n"
            "This is a WhatsApp test from the HOSEN test server.\n"
            "Unit: TS-001\n"
            "Status: TEST\n"
            "Server: Railway\n"
            f"Time: {utc_now()}"
        )

    kwargs = {
        "from_": f"whatsapp:{TWILIO_WHATSAPP_FROM}",
        "to": f"whatsapp:{TWILIO_WHATSAPP_TO}",
        "body": body,
    }

    # Optional delivery-status callback.
    if PUBLIC_BASE_URL:
        kwargs["status_callback"] = f"{PUBLIC_BASE_URL}/twilio/status"

    try:
        message = twilio_client().messages.create(**kwargs)

        return jsonify({
            "ok": True,
            "sid": message.sid,
            "status": message.status,
            "to": message.to,
            "from": message.from_,
            "date_created": (
                message.date_created.isoformat()
                if message.date_created else None
            ),
        })

    except TwilioRestException as e:

    app.logger.exception("Twilio API error")

    return jsonify({
        "ok": False,
        "type": "TwilioRestException",
        "status": getattr(e, "status", None),
        "code": getattr(e, "code", None),
        "message": getattr(e, "msg", str(e)),
        "details": str(e),
    }), 502

    except Exception as e:
        app.logger.exception("Unexpected send error")
        return jsonify({
            "ok": False,
            "type": type(e).__name__,
            "message": str(e),
        }), 500

@app.post("/twilio/status")
def twilio_status():
    # Twilio posts form-encoded status data here.
    data = request.form.to_dict(flat=True)

    app.logger.info(
        "TWILIO STATUS: %s",
        json.dumps(data, ensure_ascii=False)
    )

    return ("", 204)

@app.post("/twilio/incoming")
def twilio_incoming():
    # Useful later if we want to test inbound WhatsApp.
    data = request.form.to_dict(flat=True)

    app.logger.info(
        "TWILIO INCOMING: %s",
        json.dumps(data, ensure_ascii=False)
    )

    return ("", 204)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

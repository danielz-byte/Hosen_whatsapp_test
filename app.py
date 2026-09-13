import os
import json
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


app = Flask(__name__)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

# For Twilio WhatsApp Sandbox use:
# +14155238886
TWILIO_WHATSAPP_FROM = os.getenv(
    "TWILIO_WHATSAPP_FROM",
    "+14155238886"
).strip()

TWILIO_WHATSAPP_TO = os.getenv(
    "TWILIO_WHATSAPP_TO",
    ""
).strip()

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    ""
).strip().rstrip("/")


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def twilio_configured():
    return bool(
        TWILIO_ACCOUNT_SID
        and TWILIO_AUTH_TOKEN
        and TWILIO_WHATSAPP_FROM
        and TWILIO_WHATSAPP_TO
    )


def get_twilio_client():
    if not twilio_configured():
        raise RuntimeError(
            "Twilio environment variables are incomplete."
        )

    return Client(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def index():
    return render_template(
        "index.html",
        configured=twilio_configured(),
        whatsapp_from=TWILIO_WHATSAPP_FROM,
        whatsapp_to=TWILIO_WHATSAPP_TO,
        public_base_url=PUBLIC_BASE_URL
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "hosen-whatsapp-test",
        "twilio_configured": twilio_configured(),
        "whatsapp_from": TWILIO_WHATSAPP_FROM,
        "whatsapp_to": TWILIO_WHATSAPP_TO,
        "public_base_url": PUBLIC_BASE_URL,
        "timestamp": utc_now()
    })


# ============================================================
# SEND TEST WHATSAPP
# ============================================================

@app.post("/api/send-test")
def send_test():

    if not twilio_configured():
        return jsonify({
            "ok": False,
            "type": "ConfigurationError",
            "message": "Twilio environment variables are incomplete."
        }), 500

    payload = request.get_json(silent=True) or {}

    body = str(payload.get("body") or "").strip()

    if not body:
        body = (
            "🚨 HOSEN TEST\n\n"
            "זוהי הודעת בדיקה ממערכת חוסן.\n"
            "Unit: TS-001\n"
            "Status: TEST\n"
            "Server: Railway\n"
            f"Time: {utc_now()}"
        )

    try:

        client = get_twilio_client()

        message_params = {
            "from_": f"whatsapp:{TWILIO_WHATSAPP_FROM}",
            "to": f"whatsapp:{TWILIO_WHATSAPP_TO}",
            "body": body
        }

        # Optional Twilio delivery status callback
        if PUBLIC_BASE_URL:
            message_params["status_callback"] = (
                f"{PUBLIC_BASE_URL}/twilio/status"
            )

        message = client.messages.create(
            **message_params
        )

        return jsonify({
            "ok": True,
            "sid": message.sid,
            "status": message.status,
            "to": message.to,
            "from": message.from_,
            "date_created": (
                message.date_created.isoformat()
                if message.date_created
                else None
            ),
            "message": "WhatsApp message accepted by Twilio."
        }), 200

    except TwilioRestException as e:

        app.logger.exception(
            "Twilio API error"
        )

        return jsonify({
            "ok": False,
            "type": "TwilioRestException",
            "status": getattr(e, "status", None),
            "code": getattr(e, "code", None),
            "message": getattr(e, "msg", str(e)),
            "details": str(e)
        }), 502

    except Exception as e:

        app.logger.exception(
            "Unexpected error while sending WhatsApp"
        )

        return jsonify({
            "ok": False,
            "type": type(e).__name__,
            "message": str(e)
        }), 500


# ============================================================
# TWILIO STATUS CALLBACK
# ============================================================

@app.post("/twilio/status")
def twilio_status():

    data = request.form.to_dict(
        flat=True
    )

    app.logger.info(
        "TWILIO STATUS: %s",
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    return "", 204


# ============================================================
# TWILIO INCOMING MESSAGE WEBHOOK
# ============================================================

@app.post("/twilio/incoming")
def twilio_incoming():

    data = request.form.to_dict(
        flat=True
    )

    app.logger.info(
        "TWILIO INCOMING: %s",
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    return "", 204


# ============================================================
# OPTIONAL DEBUG ROUTE
# ============================================================

@app.get("/debug/config")
def debug_config():
    return jsonify({
        "twilio_account_sid_set": bool(
            TWILIO_ACCOUNT_SID
        ),
        "twilio_auth_token_set": bool(
            TWILIO_AUTH_TOKEN
        ),
        "whatsapp_from": TWILIO_WHATSAPP_FROM,
        "whatsapp_to": TWILIO_WHATSAPP_TO,
        "public_base_url": PUBLIC_BASE_URL
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
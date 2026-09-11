# HOSEN WhatsApp Test

Standalone Flask service for testing Twilio WhatsApp from Railway.

## Environment variables

- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_WHATSAPP_FROM
- TWILIO_WHATSAPP_TO
- PUBLIC_BASE_URL

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

## Production

Start command:

```bash
gunicorn app:app
```

Endpoints:

- GET /
- GET /health
- POST /api/send-test
- POST /twilio/status
- POST /twilio/incoming

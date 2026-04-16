"""
Alert Service
Sends notifications via email (SendGrid), SMS (Twilio), and webhooks.
"""
from __future__ import annotations
import httpx
import structlog
from config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()


async def send_email_alert(incident: dict):
    if not settings.sendgrid_api_key:
        log.warning("SendGrid not configured, skipping email alert")
        return

    subject = f"[{incident['severity'].upper()}] Anti-India Campaign Detected — Score {incident['threat_score']}"
    body = f"""
Threat Score: {incident['threat_score']}/100
Severity: {incident['severity']}
Source: {incident['source']}
URL: {incident.get('url', 'N/A')}
Categories: {', '.join(incident.get('categories', []))}
Language: {incident.get('language', 'unknown')}
Bot Probability: {incident.get('bot_probability', 0):.0%}
Coordinated: {incident.get('is_coordinated', False)}

Content preview:
{str(incident.get('text', ''))[:500]}

Recommended action: {incident['recommended_action']}
"""
    payload = {
        "personalizations": [{"to": [{"email": settings.alert_email_to}]}],
        "from": {"email": settings.alert_email_from},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            log.info("Email alert sent", status=resp.status_code)
    except Exception as e:
        log.error("Email alert failed", error=str(e))


async def send_sms_alert(incident: dict):
    if not settings.twilio_account_sid:
        return
    msg = (
        f"[ALERT] Anti-India threat detected!\n"
        f"Score: {incident['threat_score']}/100 ({incident['severity']})\n"
        f"Source: {incident['source']}\n"
        f"Action: {incident['recommended_action']}"
    )
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
                data={"From": settings.twilio_from_number, "To": settings.alert_sms_to, "Body": msg},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=10,
            )
            resp.raise_for_status()
            log.info("SMS alert sent")
    except Exception as e:
        log.error("SMS alert failed", error=str(e))


async def send_webhook_alert(incident: dict):
    if not settings.alert_webhook_url:
        return
    payload = {
        "text": f":warning: *Anti-India Threat Detected* — Score `{incident['threat_score']}/100` ({incident['severity']})",
        "attachments": [{
            "color": "#E24B4A" if incident["severity"] in ("high", "critical") else "#EF9F27",
            "fields": [
                {"title": "Source", "value": incident["source"], "short": True},
                {"title": "Action", "value": incident["recommended_action"], "short": True},
                {"title": "Categories", "value": ", ".join(incident.get("categories", [])), "short": False},
                {"title": "URL", "value": incident.get("url", "N/A"), "short": False},
            ],
        }],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.alert_webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            log.info("Webhook alert sent")
    except Exception as e:
        log.error("Webhook alert failed", error=str(e))


async def dispatch_alerts(incident: dict):
    """Send all configured alerts for high/critical incidents."""
    severity = incident.get("severity", "low")
    if severity in ("high", "critical"):
        await send_email_alert(incident)
        await send_webhook_alert(incident)
    if severity == "critical":
        await send_sms_alert(incident)

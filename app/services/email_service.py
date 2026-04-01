import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def _send(to_email: str, subject: str, html: str) -> bool:
    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP not configured — email skipped (to=%s)", to_email)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.from_email
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_tls,
        )
        return True
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return False


async def send_quote_link(
    to_email: str,
    client_name: str,
    quote_number: str,
    public_url: str,
) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto;color:#1a1a1a">
      <h2>Quote {quote_number}</h2>
      <p>Dear {client_name},</p>
      <p>Your quote is ready for review.</p>
      <a href="{public_url}"
         style="display:inline-block;background:#185FA5;color:#fff;padding:12px 28px;
                border-radius:6px;text-decoration:none;font-weight:600">
        View &amp; Respond to Quote
      </a>
      <p style="margin-top:24px;font-size:12px;color:#666">No login required.</p>
    </div>
    """
    return await _send(to_email, f"Quote {quote_number} — Ready for Review", html)


async def send_client_response_notification(
    to_email: str,
    sales_name: str,
    quote_number: str,
    action: str,
    comment: str,
    public_url: str,
) -> bool:
    labels = {
        "approved": ("Approved ✓", "#15803d"),
        "rejected": ("Rejected ✗", "#dc2626"),
        "changes_requested": ("Changes Requested ↪", "#b45309"),
    }
    label, color = labels.get(action, (action, "#1a1a1a"))
    comment_block = f"<p><strong>Client comment:</strong> {comment}</p>" if comment else ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto;color:#1a1a1a">
      <h2>Client Response — {quote_number}</h2>
      <p>Hi {sales_name},</p>
      <p>Your client responded to quote <strong>{quote_number}</strong>:</p>
      <p style="font-size:22px;font-weight:700;color:{color};margin:20px 0">{label}</p>
      {comment_block}
      <a href="{public_url}"
         style="display:inline-block;background:#185FA5;color:#fff;padding:12px 28px;
                border-radius:6px;text-decoration:none;font-weight:600">
        Open Quote
      </a>
    </div>
    """
    return await _send(to_email, f"[{label}] Client responded to {quote_number}", html)

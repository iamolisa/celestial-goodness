"""
email_service.py — Celestial Goodness Email Sequences
======================================================
Handles all three automated emails using SendGrid:

  Email 1 — Immediate booking confirmation
  Email 2 — 24-hour pre-session reminder
  Email 3 — 24-hour post-session integration

Scheduled jobs are registered via APScheduler on app startup.
"""

import os
import logging
from datetime import datetime, timedelta

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Read at module load — but _send() also re-reads SENDGRID_API_KEY at call time
# so that the value is always fresh even if .env loaded after this module.
FROM_EMAIL         = os.environ.get("SENDGRID_FROM_EMAIL", "")
FROM_NAME          = os.environ.get("SENDGRID_FROM_NAME", "Heather — Celestial Goodness")
SITE_URL           = os.environ.get("SITE_URL", "http://127.0.0.1:5000")

# ─────────────────────────────────────────────────────────────────────────────
# Scheduler — persists jobs to SQLite so reminders survive server restarts
# ─────────────────────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url="sqlite:///instance/celestial.db")
    },
    job_defaults={"misfire_grace_time": 3600},   # fire up to 1hr late if server was down
    timezone="UTC",
)


def start_scheduler():
    """Call once on app startup."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def stop_scheduler():
    """Call on app teardown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)


# ─────────────────────────────────────────────────────────────────────────────
# Core send helper
# ─────────────────────────────────────────────────────────────────────────────

def _send(to_email: str, to_name: str, subject: str, html_body: str) -> bool:
    """Send a single email via SendGrid. Returns True on success."""
    # Always read fresh so .env loaded after module import still works
    api_key    = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", FROM_EMAIL)
    from_name  = os.environ.get("SENDGRID_FROM_NAME", FROM_NAME)

    if not api_key:
        logger.warning("SENDGRID_API_KEY not set — email NOT sent to %s", to_email)
        return False
    if not from_email:
        logger.warning("SENDGRID_FROM_EMAIL not set — email NOT sent to %s", to_email)
        return False
    try:
        message = Mail(
            from_email  = (from_email, from_name),
            to_emails   = To(to_email, to_name),
            subject     = subject,
            html_content= html_body,
        )
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logger.info("✅ Email sent to %s | subject: %s | status %s", to_email, subject, response.status_code)
        return response.status_code in (200, 202)
    except Exception as e:
        logger.error("❌ SendGrid error sending to %s: %s", to_email, e)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Shared HTML wrapper — keeps all emails on-brand
# ─────────────────────────────────────────────────────────────────────────────

def _wrap(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Celestial Goodness</title>
</head>
<body style="margin:0;padding:0;background:#0e0f1a;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0e0f1a;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td align="center" style="padding:32px 40px 24px;
              background:linear-gradient(180deg,#1a1030,#0e0f1a);
              border-radius:12px 12px 0 0;
              border:1px solid #202440;border-bottom:none;">
            <p style="margin:0 0 6px;font-size:28px;color:#c9922a;letter-spacing:.1em;">✦</p>
            <h1 style="margin:0;font-family:'Georgia',serif;font-size:22px;
                color:#e8e2d5;font-weight:normal;letter-spacing:.05em;">
              Celestial Goodness
            </h1>
            <p style="margin:4px 0 0;font-family:Arial,sans-serif;font-size:11px;
                color:#727ab8;letter-spacing:.2em;text-transform:uppercase;">
              Astrology &amp; Tarot
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px 40px;background:#13162b;
              border-left:1px solid #202440;border-right:1px solid #202440;">
            {content}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td align="center" style="padding:20px 40px 32px;background:#0e0f1a;
              border-radius:0 0 12px 12px;
              border:1px solid #202440;border-top:1px solid #202440;">
            <p style="margin:0 0 6px;font-family:Arial,sans-serif;font-size:11px;
                color:#727ab8;text-align:center;">
              © Celestial Goodness Astrology &amp; Tarot · Heather Wiggins
            </p>
            <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;color:#727ab8;text-align:center;">
              <a href="{SITE_URL}" style="color:#c9922a;text-decoration:none;">
                celestialgoodnessastrology.com
              </a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Email 1 — Immediate Booking Confirmation
# ─────────────────────────────────────────────────────────────────────────────

def send_booking_confirmation(booking: dict) -> bool:
    """
    Sent immediately when a booking is confirmed.
    booking dict keys: client_name, email, service_name, date, time,
                       zoom_link, requires_birth_info, birth_date,
                       birth_time, birth_location, id
    """
    name         = booking.get("client_name", "Beautiful Soul")
    service      = booking.get("service_name", "your session")
    date_str     = booking.get("date", "")
    time_str     = booking.get("time", "")
    zoom_link    = booking.get("zoom_link", "")
    booking_id   = booking.get("id", "")
    needs_birth  = booking.get("requires_birth_info", False)

    # Format date nicely e.g. "Friday, March 21, 2026"
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        pretty_date = d.strftime("%A, %B %-d, %Y")
    except Exception:
        pretty_date = date_str

    # Format time e.g. "10:00 AM"
    try:
        t = datetime.strptime(time_str, "%H:%M")
        pretty_time = t.strftime("%-I:%M %p")
    except Exception:
        pretty_time = time_str

    zoom_block = ""
    if zoom_link:
        zoom_block = f"""
        <tr><td style="padding:6px 0;">
          <span style="font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">Zoom Link:</span><br>
          <a href="{zoom_link}" style="color:#c9922a;font-family:Arial,sans-serif;font-size:13px;">
            {zoom_link}
          </a>
        </td></tr>"""
    else:
        zoom_block = """
        <tr><td style="padding:6px 0;">
          <span style="font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">Zoom Link:</span><br>
          <span style="font-family:Arial,sans-serif;font-size:13px;color:#e8e2d5;">
            Your Zoom link will be sent by Heather prior to your session.
          </span>
        </td></tr>"""

    birth_block = ""
    if needs_birth:
        has_birth = booking.get("birth_date") or booking.get("birth_time") or booking.get("birth_location")
        if has_birth:
            birth_block = f"""
            <p style="margin:20px 0 8px;font-family:Arial,sans-serif;font-size:13px;
                color:#c9922a;font-weight:bold;text-transform:uppercase;letter-spacing:.1em;">
              Birth Information Received
            </p>
            <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;color:#727ab8;line-height:1.6;">
              Date: {booking.get('birth_date','—')} &nbsp;·&nbsp;
              Time: {booking.get('birth_time','—')} &nbsp;·&nbsp;
              Location: {booking.get('birth_location','—')}
            </p>"""
        else:
            birth_block = """
            <div style="margin:20px 0;padding:16px;background:rgba(201,146,42,.08);
                border:1px solid rgba(201,146,42,.2);border-radius:8px;">
              <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;
                  color:#c9922a;line-height:1.6;">
                ⚠️ <strong>Birth Information Needed:</strong> Your session includes astrology.
                Please ensure your <strong>birth date, exact birth time, and birth location</strong>
                are submitted accurately before we meet. If your exact birth time is unknown,
                we can use an Aries Rising chart with your birth date and location.
              </p>
            </div>"""

    content = f"""
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:15px;color:#e8e2d5;">
      Dear {name},
    </p>
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;color:#727ab8;line-height:1.8;">
      Your session has been confirmed. I am honored to hold this most sacred space for you.
    </p>

    <!-- Session Details Box -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;
        background:rgba(19,22,43,.8);border:1px solid #202440;border-radius:8px;">
      <tr><td style="padding:20px 24px;">
        <p style="margin:0 0 14px;font-family:Arial,sans-serif;font-size:11px;
            color:#c9922a;text-transform:uppercase;letter-spacing:.2em;">
          Session Details
        </p>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="padding:6px 0;border-bottom:1px solid #202440;">
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">Booking ID:</span><br>
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#e8e2d5;font-weight:bold;">{booking_id}</span>
          </td></tr>
          <tr><td style="padding:6px 0;border-bottom:1px solid #202440;">
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">Session:</span><br>
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#e8e2d5;">{service}</span>
          </td></tr>
          <tr><td style="padding:6px 0;border-bottom:1px solid #202440;">
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">Date:</span><br>
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#e8e2d5;">{pretty_date}</span>
          </td></tr>
          <tr><td style="padding:6px 0;border-bottom:1px solid #202440;">
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">Time:</span><br>
            <span style="font-family:Arial,sans-serif;font-size:13px;color:#e8e2d5;">{pretty_time} (your local time)</span>
          </td></tr>
          {zoom_block}
        </table>
      </td></tr>
    </table>

    {birth_block}

    <p style="margin:20px 0 8px;font-family:Arial,sans-serif;font-size:14px;color:#e8e2d5;line-height:1.8;">
      Before we meet, I invite you to reflect on what feels most alive in your life right now.
      Is there a question you want clarity on? A decision weighing on you? A transition that is unfolding?
    </p>
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;color:#727ab8;line-height:1.8;">
      Please arrive on time and in a quiet space where you can be fully present.
    </p>

    <!-- CTA Button -->
    <table cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr><td style="background:linear-gradient(135deg,#c9922a,#c06420,#d4ac55);
          border-radius:6px;padding:12px 28px;text-align:center;">
        <a href="{SITE_URL}/booking/success?id={booking_id}"
           style="color:#0e0f1a;font-family:Arial,sans-serif;font-size:14px;
           font-weight:bold;text-decoration:none;letter-spacing:.05em;">
          View Your Booking ✦
        </a>
      </td></tr>
    </table>

    <p style="margin:24px 0 4px;font-family:Georgia,serif;font-size:13px;
        color:#727ab8;font-style:italic;">
      With loving intention and wisdom,
    </p>
    <p style="margin:0;font-family:Georgia,serif;font-size:14px;color:#c9922a;">
      Heather aka Celestial Goodness
    </p>"""

    subject = f"Your {service} is Confirmed ✦"
    return _send(booking["email"], name, subject, _wrap(content))


# ─────────────────────────────────────────────────────────────────────────────
# Email 2 — 24-Hour Pre-Session Reminder
# ─────────────────────────────────────────────────────────────────────────────

def send_reminder_email(booking: dict) -> bool:
    """Sent 24 hours before the session."""
    name     = booking.get("client_name", "Beautiful Soul")
    service  = booking.get("service_name", "your session")
    date_str = booking.get("date", "")
    time_str = booking.get("time", "")
    zoom_link = booking.get("zoom_link", "")

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        pretty_date = d.strftime("%A, %B %-d, %Y")
    except Exception:
        pretty_date = date_str

    try:
        t = datetime.strptime(time_str, "%H:%M")
        pretty_time = t.strftime("%-I:%M %p")
    except Exception:
        pretty_time = time_str

    zoom_row = f"""
      <p style="margin:12px 0 0;font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">
        Zoom Link:&nbsp;
        <a href="{zoom_link}" style="color:#c9922a;">{zoom_link}</a>
      </p>""" if zoom_link else ""

    content = f"""
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:15px;color:#e8e2d5;">
      Dear {name},
    </p>
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;color:#727ab8;line-height:1.8;">
      Our session is <strong style="color:#e8e2d5;">tomorrow</strong>, and I am looking forward
      to sharing in this sacred space with you.
    </p>

    <!-- Session reminder box -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;
        background:rgba(19,22,43,.8);border:1px solid #202440;border-radius:8px;">
      <tr><td style="padding:20px 24px;">
        <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:11px;
            color:#c9922a;text-transform:uppercase;letter-spacing:.2em;">Tomorrow's Session</p>
        <p style="margin:0;font-family:Arial,sans-serif;font-size:15px;color:#e8e2d5;font-weight:bold;">
          {service}
        </p>
        <p style="margin:6px 0 0;font-family:Arial,sans-serif;font-size:13px;color:#727ab8;">
          {pretty_date} at {pretty_time}
        </p>
        {zoom_row}
      </td></tr>
    </table>

    <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:14px;
        color:#e8e2d5;line-height:1.8;">
      Take a few moments today to ground yourself. You may wish to journal briefly about
      what you most want clarity around.
    </p>

    <!-- Preparation tips -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;
        background:rgba(110,77,153,.08);border:1px solid rgba(110,77,153,.2);border-radius:8px;">
      <tr><td style="padding:20px 24px;">
        <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:11px;
            color:#9b7abf;text-transform:uppercase;letter-spacing:.2em;">
          How to Prepare
        </p>
        <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          📓 &nbsp;Bring a <strong style="color:#e8e2d5;">notebook</strong> to capture insights
        </p>
        <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          🎙️ &nbsp;You are free to <strong style="color:#e8e2d5;">record the session</strong>
          so you can play back any useful parts later
        </p>
        <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          🤫 &nbsp;Find a <strong style="color:#e8e2d5;">quiet, private space</strong>
          where you can be fully present
        </p>
        <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          ⏰ &nbsp;Please <strong style="color:#e8e2d5;">arrive on time</strong>
        </p>
      </td></tr>
    </table>

    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;
        color:#727ab8;line-height:1.8;font-style:italic;">
      Come open. Come curious. Come honest.
      You already hold so much more wisdom than you know!
    </p>

    <p style="margin:24px 0 4px;font-family:Georgia,serif;font-size:13px;
        color:#727ab8;font-style:italic;">Warmly,</p>
    <p style="margin:0;font-family:Georgia,serif;font-size:14px;color:#c9922a;">
      Heather aka Celestial Goodness
    </p>"""

    subject = f"Preparing for Your Session Tomorrow ✦"
    return _send(booking["email"], name, subject, _wrap(content))


# ─────────────────────────────────────────────────────────────────────────────
# Email 3 — 24-Hour Post-Session Integration
# ─────────────────────────────────────────────────────────────────────────────

def send_integration_email(booking: dict) -> bool:
    """Sent 24 hours after the session."""
    name    = booking.get("client_name", "Beautiful Soul")
    service = booking.get("service_name", "your session")

    content = f"""
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:15px;color:#e8e2d5;">
      Dear {name},
    </p>
    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;color:#727ab8;line-height:1.8;">
      Thank you for allowing me to witness and guide your journey during
      your <strong style="color:#e8e2d5;">{service}</strong>.
    </p>

    <!-- Integration guidance -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;
        background:rgba(19,22,43,.8);border:1px solid #202440;border-radius:8px;">
      <tr><td style="padding:20px 24px;">
        <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:11px;
            color:#c9922a;text-transform:uppercase;letter-spacing:.2em;">
          Integration & Reflection
        </p>
        <p style="margin:0 0 10px;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          🌙 &nbsp;Over the next few days, <strong style="color:#e8e2d5;">pay attention to
          subtle confirmations</strong> and also to your dreams.
        </p>
        <p style="margin:0 0 10px;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          💫 &nbsp;<strong style="color:#e8e2d5;">Notice how your body responds</strong>
          to the decisions we discussed.
        </p>
        <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          🌱 &nbsp;Trust yourself that you are capable of making
          <strong style="color:#e8e2d5;">wise decisions</strong> for your life.
        </p>
      </td></tr>
    </table>

    <p style="margin:0 0 20px;font-family:Arial,sans-serif;font-size:14px;
        color:#727ab8;line-height:1.8;">
      Integration is where transformation happens, and you have planted the seeds of awareness.
      Let us see what blooms!
    </p>

    <!-- Testimonial CTA -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;
        background:rgba(110,77,153,.08);border:1px solid rgba(110,77,153,.2);border-radius:8px;">
      <tr><td style="padding:20px 24px;text-align:center;">
        <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:13px;
            color:#727ab8;line-height:1.7;">
          If you found value in your session, I would be honored if you shared a testimonial.
        </p>
        <a href="{SITE_URL}/testimonials"
           style="display:inline-block;margin-top:8px;padding:10px 24px;
           background:linear-gradient(135deg,#c9922a,#c06420,#d4ac55);
           border-radius:6px;color:#0e0f1a;font-family:Arial,sans-serif;
           font-size:13px;font-weight:bold;text-decoration:none;">
          Leave a Testimonial ✦
        </a>
      </td></tr>
    </table>

    <!-- Mantra -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;
        background:rgba(201,146,42,.06);border-left:3px solid #c9922a;border-radius:0 8px 8px 0;">
      <tr><td style="padding:16px 20px;">
        <p style="margin:0;font-family:Georgia,serif;font-size:14px;
            color:#c9922a;font-style:italic;line-height:1.8;text-align:center;">
          "I trust my timing, I trust my path.<br>
          I trust that what is meant for me cannot miss me."
        </p>
        <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:11px;
            color:#727ab8;text-align:center;">
          Repeat as frequently as you need.
        </p>
      </td></tr>
    </table>

    <p style="margin:0 0 4px;font-family:Georgia,serif;font-size:13px;
        color:#727ab8;font-style:italic;">
      With divine love and respect,
    </p>
    <p style="margin:0;font-family:Georgia,serif;font-size:14px;color:#c9922a;">
      Heather
    </p>"""

    subject = "Integration & Reflection — Your Celestial Session ✦"
    return _send(booking["email"], name, subject, _wrap(content))


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler helpers — called from app.py
# ─────────────────────────────────────────────────────────────────────────────

def schedule_booking_emails(booking: dict):
    """
    Schedule Email 2 (24hr before) and Email 3 (24hr after) for a booking.
    Email 1 is sent immediately by the calling code — not scheduled.
    """
    try:
        session_dt = datetime.strptime(
            f"{booking['date']} {booking['time']}", "%Y-%m-%d %H:%M"
        )
    except Exception as e:
        logger.error("Could not parse session datetime: %s", e)
        return

    booking_id = booking["id"]

    # Email 2 — 24 hours before the session
    remind_at = session_dt - timedelta(hours=24)
    if remind_at > datetime.utcnow():
        scheduler.add_job(
            func        = send_reminder_email,
            trigger     = "date",
            run_date    = remind_at,
            args        = [booking],
            id          = f"remind_{booking_id}",
            replace_existing = True,
        )
        logger.info("Reminder scheduled for %s at %s", booking_id, remind_at)

    # Email 3 — 24 hours after the session
    integrate_at = session_dt + timedelta(hours=24)
    scheduler.add_job(
        func        = send_integration_email,
        trigger     = "date",
        run_date    = integrate_at,
        args        = [booking],
        id          = f"integrate_{booking_id}",
        replace_existing = True,
    )
    logger.info("Integration email scheduled for %s at %s", booking_id, integrate_at)


def cancel_booking_emails(booking_id: str):
    """Remove scheduled emails when a booking is deleted or rescheduled."""
    for prefix in ("remind_", "integrate_"):
        job_id = f"{prefix}{booking_id}"
        try:
            scheduler.remove_job(job_id)
            logger.info("Removed scheduled job %s", job_id)
        except Exception:
            pass  # job may not exist yet — that's fine

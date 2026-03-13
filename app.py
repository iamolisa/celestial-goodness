from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid
import os
import re
from dotenv import load_dotenv
load_dotenv()

from email_service import (
    start_scheduler, stop_scheduler,
    send_booking_confirmation,
    schedule_booking_emails,
    cancel_booking_emails,
)

app = Flask(__name__)
app.secret_key = "celestial-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///celestial.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# Start background email scheduler
# ─────────────────────────────────────────────
import atexit
start_scheduler()
atexit.register(stop_scheduler)

# ─────────────────────────────────────────────
# Available booking time slots
# ─────────────────────────────────────────────
AVAILABLE_SLOTS = [
    "09:00", "10:00", "11:00", "12:00",
    "13:00", "14:00", "15:00", "16:00", "17:00",
]
AVAILABLE_DAYS = [0, 1, 2, 3, 4]  # Mon–Fri (0=Mon, 6=Sun)

ADMIN_EMAIL    = "admin@celestialgoodnessastrology.com"
ADMIN_PASSWORD = "admin123"


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class Service(db.Model):
    __tablename__ = "services"

    id                  = db.Column(db.String(10),  primary_key=True)
    title               = db.Column(db.String(200), nullable=False)
    description         = db.Column(db.Text,        nullable=False)
    duration            = db.Column(db.String(50),  nullable=False)
    price               = db.Column(db.Float,       nullable=False)
    icon                = db.Column(db.String(10),  nullable=False)
    category            = db.Column(db.String(50),  nullable=False)
    requires_birth_info = db.Column(db.Boolean,     default=False)

    bookings = db.relationship("Booking", backref="service_rel", lazy=True)

    def to_dict(self):
        return {
            "id":                  self.id,
            "title":               self.title,
            "description":         self.description,
            "duration":            self.duration,
            "price":               self.price,
            "icon":                self.icon,
            "category":            self.category,
            "requires_birth_info": self.requires_birth_info,
        }


class Booking(db.Model):
    __tablename__ = "bookings"

    id             = db.Column(db.String(20),  primary_key=True)
    client_name    = db.Column(db.String(120), nullable=False)
    email          = db.Column(db.String(120), nullable=False)
    service_id     = db.Column(db.String(10),  db.ForeignKey("services.id"), nullable=False)
    service_name   = db.Column(db.String(200), nullable=False)
    price          = db.Column(db.Float,       nullable=False, default=0.0)
    date           = db.Column(db.String(20),  nullable=False)
    time           = db.Column(db.String(10),  nullable=False)
    format         = db.Column(db.String(20),  default="zoom")
    notes          = db.Column(db.Text,        default="")
    birth_date     = db.Column(db.String(20),  default="")
    birth_time     = db.Column(db.String(10),  default="")
    birth_location = db.Column(db.String(200), default="")
    payment_status    = db.Column(db.String(20),  default="pending")
    status            = db.Column(db.String(20),  default="upcoming")
    zoom_link         = db.Column(db.String(500), default="")
    reschedule_count  = db.Column(db.Integer,     default=0)
    created_at        = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":            self.id,
            "clientName":    self.client_name,
            "email":         self.email,
            "serviceId":     self.service_id,
            "serviceName":   self.service_name,
            "price":         self.price,
            "date":          self.date,
            "time":          self.time,
            "format":        self.format,
            "notes":         self.notes,
            "birthDate":     self.birth_date,
            "birthTime":     self.birth_time,
            "birthLocation": self.birth_location,
            "paymentStatus": self.payment_status,
            "status":        self.status,
            "zoomLink":      self.zoom_link or "",
            "rescheduleCount": self.reschedule_count or 0,
            "createdAt":     self.created_at.isoformat() + "Z",
        }


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id         = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    name       = db.Column(db.String(120), nullable=False)
    text       = db.Column(db.Text,        nullable=False)
    rating     = db.Column(db.Integer,     nullable=False, default=5)
    service    = db.Column(db.String(200), default="")
    approved   = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "text":      self.text,
            "rating":    self.rating,
            "service":   self.service,
            "approved":  self.approved,
            "createdAt": self.created_at.isoformat() + "Z",
        }


class Subscriber(db.Model):
    __tablename__ = "subscribers"

    id         = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":        self.id,
            "email":     self.email,
            "createdAt": self.created_at.isoformat() + "Z",
        }


class Contact(db.Model):
    __tablename__ = "contacts"

    id         = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(120), nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    read       = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":        self.id,
            "name":      self.name,
            "email":     self.email,
            "message":   self.message,
            "read":      self.read,
            "createdAt": self.created_at.isoformat() + "Z",
        }


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id         = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    title      = db.Column(db.String(300), nullable=False)
    category   = db.Column(db.String(100), default="")
    excerpt    = db.Column(db.Text,        default="")
    body       = db.Column(db.Text,        nullable=False)
    published  = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id":        self.id,
            "title":     self.title,
            "category":  self.category,
            "excerpt":   self.excerpt,
            "body":      self.body,
            "published": self.published,
            "createdAt": self.created_at.isoformat() + "Z",
            "updatedAt": self.updated_at.isoformat() + "Z",
        }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_admin():
    return session.get("admin") is True

def valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

def _next_booking_id():
    """Generate the next sequential booking ID in the format CG-YYYY-NNN.
    Finds the highest existing number for the current year and increments it.
    """
    year   = datetime.utcnow().year
    prefix = f"CG-{year}-"
    existing = Booking.query.filter(Booking.id.like(f"{prefix}%")).all()
    max_num  = 0
    for b in existing:
        try:
            num = int(b.id.replace(prefix, ""))
            if num > max_num:
                max_num = num
        except ValueError:
            pass
    return f"{prefix}{str(max_num + 1).zfill(3)}"

def slot_is_taken(date, time, exclude_id=None):
    """Return True if date+time slot already has an upcoming booking."""
    q = Booking.query.filter_by(date=date, time=time, status="upcoming")
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return q.first() is not None

def date_is_in_past(date_str):
    """Return True if the supplied YYYY-MM-DD date is strictly before today."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return d < datetime.utcnow().date()
    except ValueError:
        return True   # treat unparseable dates as invalid


# ─────────────────────────────────────────────
# Seed
# ─────────────────────────────────────────────

def seed_services():
    if Service.query.count():
        return
    rows = [
        Service(id="1a", title="The Celestial Oracle Session — Quick Pull",
                description="A focused tarot/oracle pull for when you need swift clarity on a specific question or situation. Direct, intuitive, and illuminating.",
                duration="15 min", price=33.33, icon="✨", category="oracle", requires_birth_info=False),
        Service(id="1b", title="The Celestial Oracle Session",
                description="A deeper tarot/oracle reading to explore the energies surrounding your question with greater nuance and insight.",
                duration="30 min", price=44.44, icon="✨", category="oracle", requires_birth_info=False),
        Service(id="1c", title="The Celestial Oracle Session — Extended",
                description="An expansive tarot/oracle reading for those seeking thorough guidance across multiple areas of life or a complex situation.",
                duration="45 min", price=77.77, icon="✨", category="oracle", requires_birth_info=False),
        Service(id="1d", title="The Celestial Oracle Session — Year Long Reading Forecast",
                description="A comprehensive year-ahead tarot/oracle forecast exploring the themes, cycles, and opportunities unfolding over the next 12 months.",
                duration="Year Forecast", price=111.00, icon="✨", category="oracle", requires_birth_info=False),
        Service(id="2",  title="The Celestial Blueprint Consultation",
                description="A detailed natal chart reading that reveals the sacred architecture of who you are — your temperament, life purpose, karmic lessons, and the cycles shaping your journey.",
                duration="60 min", price=155.50, icon="🌙", category="astrology", requires_birth_info=True),
        Service(id="3",  title="The Celestial Sovereignty Session",
                description="An integrative session combining astrology and tarot for a powerful, layered reading that speaks to both your cosmic blueprint and your present-moment energy.",
                duration="90 min", price=222.00, icon="🔮", category="astrology", requires_birth_info=True),
        Service(id="4",  title="The Divine Union Celestial Consultation Session",
                description="A relationship compatibility reading using astrology and tarot to explore the dynamics, strengths, and growth edges between two people.",
                duration="75 min", price=188.80, icon="💫", category="astrology", requires_birth_info=True),
        Service(id="5",  title="The Celestial Visionary Alignment Session",
                description="A strategic spiritual session combining astrology and tarot — an astrological and tarot SWOT analysis ideal for creatives and entrepreneurs.",
                duration="60 min", price=155.50, icon="⭐", category="astrology", requires_birth_info=True),
    ]
    db.session.add_all(rows)

    bookings = [
        Booking(id="CG-2026-001", client_name="Sample Client",   email="sample@example.com",
                service_id="2",  service_name="The Celestial Blueprint Consultation",
                price=155.50, date="2026-03-10", time="10:00", payment_status="paid", status="upcoming",
                created_at=datetime(2026, 3, 1, 10, 30)),
        Booking(id="CG-2026-002", client_name="Sample Client 2", email="sample2@example.com",
                service_id="3",  service_name="The Celestial Sovereignty Session",
                price=222.00, date="2026-03-12", time="14:00", payment_status="paid", status="upcoming",
                created_at=datetime(2026, 3, 2, 8, 15)),
        Booking(id="CG-2026-003", client_name="Sample Client 3", email="sample3@example.com",
                service_id="1c", service_name="The Celestial Oracle Session — Extended",
                price=77.77, date="2026-03-05", time="11:00", payment_status="paid", status="completed",
                created_at=datetime(2026, 2, 28, 16, 45)),
    ]
    db.session.add_all(bookings)
    db.session.commit()


# ─────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    services     = Service.query.limit(3).all()
    testimonials = Testimonial.query.filter_by(approved=True).order_by(Testimonial.created_at.desc()).limit(3).all()
    return render_template("index.html",
                           services=[s.to_dict() for s in services],
                           testimonials=[t.to_dict() for t in testimonials])

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/services")
def services():
    return render_template("services.html", services=[s.to_dict() for s in Service.query.all()])

@app.route("/booking")
def booking():
    service_id = request.args.get("service", "")
    return render_template("booking.html",
                           services=[s.to_dict() for s in Service.query.all()],
                           preselected=service_id)

@app.route("/booking/success")
def booking_success():
    booking_id = request.args.get("id", "")
    booking = Booking.query.get(booking_id) if booking_id else None
    if not booking:
        return redirect(url_for("booking"))
    return render_template("success.html", booking=booking.to_dict())

@app.route("/testimonials")
def testimonials():
    approved = Testimonial.query.filter_by(approved=True).order_by(Testimonial.created_at.desc()).all()
    return render_template("testimonials.html", testimonials=[t.to_dict() for t in approved])

@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/ethics")
def ethics():
    return render_template("ethics.html")


@app.route("/blog")
def blog():
    """
    Fetch recent posts from Heather's WordPress blog at celestialgoodness.com
    via its RSS feed. Falls back to an empty list if the feed is unreachable.
    """
    import urllib.request
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    BLOG_URL  = "https://celestialgoodness.com"
    FEED_URL  = f"{BLOG_URL}/feed/"
    posts     = []
    feed_error = False

    try:
        req = urllib.request.Request(
            FEED_URL,
            headers={"User-Agent": "CelestialGoodnessBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read()

        root = ET.fromstring(raw)
        ns   = {"content": "http://purl.org/rss/1.0/modules/content/",
                "dc":      "http://purl.org/dc/elements/1.1/"}

        for item in root.findall(".//item")[:9]:   # latest 9 posts
            title    = item.findtext("title", "").strip()
            link     = item.findtext("link",  "").strip()
            pub_date = item.findtext("pubDate", "")
            excerpt  = item.findtext("description", "").strip()
            category = item.findtext("category", "").strip()

            # Strip HTML tags from excerpt
            import re as _re
            excerpt = _re.sub(r"<[^>]+>", "", excerpt)[:200].strip()
            if len(excerpt) == 200:
                excerpt += "…"

            # Format date nicely
            try:
                dt        = parsedate_to_datetime(pub_date)
                pretty_dt = dt.strftime("%B %-d, %Y")
            except Exception:
                pretty_dt = pub_date[:16]

            posts.append({
                "title":    title,
                "link":     link,
                "date":     pretty_dt,
                "excerpt":  excerpt,
                "category": category,
            })

    except Exception as e:
        feed_error = True
        app.logger.warning("Could not fetch blog feed: %s", e)

    return render_template("blog.html",
                           posts=posts,
                           blog_url="https://celestialgoodness.com",
                           feed_error=feed_error)



def admin_login():
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")

@app.route("/success")
def success_fallback():
    return redirect(url_for("index"))


# ─────────────────────────────────────────────
# Booking API  (2-step: preview → confirm)
# ─────────────────────────────────────────────

@app.route("/api/booking/preview", methods=["POST"])
def booking_preview():
    """
    Step 1 — validate and return a summary.
    Nothing is written to the database yet.
    """
    data = request.get_json() or {}
    required = ["name", "email", "serviceId", "date", "time"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "Please fill in all required fields."}), 400

    if not valid_email(data["email"]):
        return jsonify({"error": "Please enter a valid email address."}), 400

    if date_is_in_past(data["date"]):
        return jsonify({"error": "Please choose a date in the future."}), 400

    service = db.session.get(Service, data["serviceId"])
    if not service:
        return jsonify({"error": "Invalid service selected."}), 400

    if slot_is_taken(data["date"], data["time"]):
        return jsonify({
            "error": "That date and time is already booked. Please choose a different slot."
        }), 409

    # Birth-info validation for astrology sessions
    if service.requires_birth_info and not data.get("birthDate"):
        return jsonify({
            "error": "A date of birth is required for this session type."
        }), 400

    summary = {
        "serviceId":     service.id,
        "serviceName":   service.title,
        "duration":      service.duration,
        "price":         service.price,
        "requiresBirth": service.requires_birth_info,
        "name":          data["name"].strip(),
        "email":         data["email"].strip(),
        "date":          data["date"],
        "time":          data["time"],
        "format":        data.get("format", "zoom"),
        "notes":         data.get("notes", "").strip(),
        "birthDate":     data.get("birthDate", ""),
        "birthTime":     data.get("birthTime", ""),
        "birthLocation": data.get("birthLocation", ""),
    }
    return jsonify({"success": True, "summary": summary}), 200


@app.route("/api/booking/confirm", methods=["POST"])
def booking_confirm():
    """
    Step 2 — the client has reviewed and clicked Confirm.
    Run validation once more (slot may have gone in the meantime),
    then persist to the database.
    """
    data = request.get_json() or {}
    required = ["name", "email", "serviceId", "date", "time"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "Missing required fields."}), 400

    service = db.session.get(Service, data["serviceId"])
    if not service:
        return jsonify({"error": "Invalid service."}), 400

    if date_is_in_past(data["date"]):
        return jsonify({"error": "That date is no longer valid."}), 400

    if slot_is_taken(data["date"], data["time"]):
        return jsonify({
            "error": "Sorry — that slot was just taken. Please go back and choose another time."
        }), 409

    booking = Booking(
        id             = _next_booking_id(),
        client_name    = data["name"].strip(),
        email          = data["email"].strip(),
        service_id     = service.id,
        service_name   = service.title,
        price          = service.price,
        date           = data["date"],
        time           = data["time"],
        format         = data.get("format", "zoom"),
        notes          = data.get("notes", "").strip(),
        birth_date     = data.get("birthDate", ""),
        birth_time     = data.get("birthTime", ""),
        birth_location = data.get("birthLocation", ""),
        payment_status = "pending",
        status         = "upcoming",
    )
    db.session.add(booking)
    db.session.commit()

    # ── Email sequences ──────────────────────────────
    # email_service expects snake_case keys (not camelCase from to_dict())
    svc = db.session.get(Service, booking.service_id)
    booking_dict = {
        "id":                  booking.id,
        "client_name":         booking.client_name,
        "email":               booking.email,
        "service_name":        booking.service_name,
        "date":                booking.date,
        "time":                booking.time,
        "zoom_link":           booking.zoom_link or "",
        "requires_birth_info": svc.requires_birth_info if svc else False,
        "birth_date":          booking.birth_date,
        "birth_time":          booking.birth_time,
        "birth_location":      booking.birth_location,
    }
    # Email 1 — send immediately
    send_booking_confirmation(booking_dict)
    # Emails 2 & 3 — schedule for 24hr before/after
    schedule_booking_emails(booking_dict)

    return jsonify({"success": True, "bookingId": booking.id}), 201


# ─────────────────────────────────────────────
# Testimonials API (public)
# ─────────────────────────────────────────────

@app.route("/api/testimonial", methods=["POST"])
def submit_testimonial():
    data = request.get_json() or {}
    name   = data.get("name", "").strip()
    text   = data.get("text", "").strip()
    rating = int(data.get("rating", 0))
    service = data.get("service", "").strip()

    if not name or not text:
        return jsonify({"error": "Name and testimonial text are required."}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "Please provide a star rating (1–5)."}), 400

    t = Testimonial(name=name, text=text, rating=rating, service=service, approved=False)
    db.session.add(t)
    db.session.commit()
    return jsonify({"success": True}), 201


# ─────────────────────────────────────────────
# Newsletter API (public)
# ─────────────────────────────────────────────

@app.route("/api/newsletter", methods=["POST"])
def newsletter():
    import urllib.request as _urllib
    import json as _json

    data  = request.get_json() or {}
    email = data.get("email", "").strip()

    if not email or not valid_email(email):
        return jsonify({"error": "A valid email address is required."}), 400

    # Save to local DB (always, as backup)
    if not Subscriber.query.filter_by(email=email).first():
        db.session.add(Subscriber(email=email))
        db.session.commit()

    # Sync to ConvertKit
    ck_api_key = os.environ.get("CONVERTKIT_API_KEY", "")
    ck_form_id = os.environ.get("CONVERTKIT_FORM_ID", "")

    if ck_api_key and ck_form_id:
        try:
            payload = _json.dumps({
                "api_key": ck_api_key,
                "email":   email,
            }).encode("utf-8")
            ck_req = _urllib.Request(
                f"https://api.convertkit.com/v3/forms/{ck_form_id}/subscribe",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with _urllib.urlopen(ck_req, timeout=6) as resp:
                ck_resp = _json.loads(resp.read())
                app.logger.info("ConvertKit sync: %s", ck_resp.get("subscription", {}).get("state", "unknown"))
        except Exception as e:
            # Don't fail the request if ConvertKit is down — local DB is the backup
            app.logger.warning("ConvertKit sync failed: %s", e)

    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────
# Contact API (public)
# ─────────────────────────────────────────────

@app.route("/api/contact", methods=["POST"])
def contact_submit():
    data = request.get_json() or {}
    name    = data.get("name", "").strip()
    email   = data.get("email", "").strip()
    message = data.get("message", "").strip()
    if not name or not email or not message:
        return jsonify({"error": "All fields are required."}), 400
    if not valid_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    db.session.add(Contact(name=name, email=email, message=message))
    db.session.commit()
    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────
# Admin — Auth
# ─────────────────────────────────────────────

@app.route("/api/admin/login", methods=["POST"])
def admin_login_api():
    data = request.get_json() or {}
    if data.get("email") == ADMIN_EMAIL and data.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success": True}), 200
    return jsonify({"error": "Invalid credentials."}), 401

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"success": True}), 200


@app.route("/api/admin/test-email")
def test_email():
    """Quick diagnostic — visit this URL while logged in to send a test email."""
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    api_key    = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "")
    result = send_booking_confirmation({
        "id":            "TEST-001",
        "client_name":   "Heather (Test)",
        "email":         from_email or "aguakaolisa2004@gmail.com",
        "service_name":  "Test Session",
        "date":          "2026-12-01",
        "time":          "10:00",
        "zoom_link":     "https://zoom.us/test",
        "requires_birth_info": False,
    })
    return jsonify({
        "sent": result,
        "api_key_set": bool(api_key),
        "from_email":  from_email,
        "message":     "Check your inbox and the PyCharm console for logs."
    })


# ─────────────────────────────────────────────
# Admin — Stats
# ─────────────────────────────────────────────

@app.route("/api/admin/stats")
def admin_stats():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    bookings   = Booking.query.all()
    paid       = [b for b in bookings if b.payment_status == "paid"]
    total_rev  = sum(b.price for b in paid)

    return jsonify({
        "totalBookings":      len(bookings),
        "upcomingBookings":   sum(1 for b in bookings if b.status == "upcoming"),
        "completedSessions":  sum(1 for b in bookings if b.status == "completed"),
        "totalRevenue":       round(total_rev, 2),
        "pendingTestimonials": Testimonial.query.filter_by(approved=False).count(),
        "totalSubscribers":   Subscriber.query.count(),
        "unreadContacts":     Contact.query.filter_by(read=False).count(),
    }), 200


# Admin — Bookings

@app.route("/api/admin/bookings")
def get_bookings():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bookings]), 200

@app.route("/api/admin/bookings/<booking_id>/complete", methods=["PATCH"])
def complete_booking(booking_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    b = db.session.get(Booking, booking_id)
    if not b:
        return jsonify({"error": "Not found"}), 404
    b.status = "completed"
    db.session.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/bookings/<booking_id>/payment", methods=["PATCH"])
def update_payment(booking_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    b = db.session.get(Booking, booking_id)
    if not b:
        return jsonify({"error": "Not found"}), 404
    status = (request.get_json() or {}).get("status")
    if status not in ("paid", "pending", "failed"):
        return jsonify({"error": "Invalid payment status"}), 400
    b.payment_status = status
    db.session.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/bookings/<booking_id>", methods=["DELETE"])
def delete_booking(booking_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    b = db.session.get(Booking, booking_id)
    if not b:
        return jsonify({"error": "Not found"}), 404
    # Cancel any scheduled reminder/integration emails before deleting
    cancel_booking_emails(b.id)
    db.session.delete(b)
    db.session.commit()
    return jsonify({"success": True}), 200


@app.route("/api/admin/bookings/<booking_id>/reschedule", methods=["PATCH"])
def reschedule_booking(booking_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    b = db.session.get(Booking, booking_id)
    if not b:
        return jsonify({"error": "Not found"}), 404
    if b.reschedule_count >= 1:
        return jsonify({"error": "This booking has already been rescheduled once. No further reschedules are permitted per policy."}), 400
    data = request.get_json()
    new_date = data.get("date", "").strip()
    new_time = data.get("time", "").strip()
    if not new_date or not new_time:
        return jsonify({"error": "New date and time are required."}), 400
    if date_is_in_past(new_date):
        return jsonify({"error": "New date cannot be in the past."}), 400
    if slot_is_taken(new_date, new_time, exclude_id=booking_id):
        return jsonify({"error": "That slot is already taken. Please choose a different time."}), 409
    b.date             = new_date
    b.time             = new_time
    b.reschedule_count = (b.reschedule_count or 0) + 1
    db.session.commit()
    return jsonify({"success": True, "rescheduleCount": b.reschedule_count}), 200


@app.route("/api/admin/bookings/<booking_id>/zoom", methods=["PATCH"])
def set_zoom_link(booking_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    b = db.session.get(Booking, booking_id)
    if not b:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    b.zoom_link = data.get("zoomLink", "").strip()
    db.session.commit()
    # Re-send confirmation email so client receives their Zoom link
    if b.zoom_link:
        svc = db.session.get(Service, b.service_id)
        booking_for_email = {
            "id":                  b.id,
            "client_name":         b.client_name,
            "email":               b.email,
            "service_name":        b.service_name,
            "date":                b.date,
            "time":                b.time,
            "zoom_link":           b.zoom_link,
            "requires_birth_info": svc.requires_birth_info if svc else False,
            "birth_date":          b.birth_date,
            "birth_time":          b.birth_time,
            "birth_location":      b.birth_location,
        }
        # Email 1 — resend confirmation with the Zoom link now included
        send_booking_confirmation(booking_for_email)
        # Reschedule Email 2 reminder so it also carries the Zoom link
        # (the original scheduled job had empty zoom_link baked in)
        schedule_booking_emails(booking_for_email)
    return jsonify({"success": True}), 200


@app.route("/api/booking/slots")
def get_available_slots():
    """Return only genuinely available time slots for a given date.

    A slot is excluded (not returned at all) when:
      1. It has already been booked by another booking (status=upcoming).
      2. It falls within 1 hour AFTER another booked slot (buffer time).
      3. It is in the past (for today's date, current hour and earlier are gone).
      4. The date is a weekend (Mon–Fri only).

    Optional query param `exclude` — a booking ID whose slot should be
    ignored when computing conflicts.  Used by the reschedule flow so the
    booking being moved does not block its own current slot.
    """
    date_str   = request.args.get("date", "")
    exclude_id = request.args.get("exclude", None)   # booking ID to ignore

    if not date_str:
        return jsonify({"error": "date parameter required"}), 400
    try:
        chosen = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    today = datetime.utcnow().date()
    if chosen < today:
        return jsonify({"slots": [], "message": "Please choose a future date."}), 200

    # Block weekends
    if chosen.weekday() not in AVAILABLE_DAYS:
        return jsonify({"slots": [], "message": "Sessions are available Monday–Friday only."}), 200

    # Collect booked hours — exclude the booking being rescheduled so its
    # current slot doesn't pollute the available-slot calculation
    query = Booking.query.filter_by(date=date_str, status="upcoming")
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    booked_hours = {int(b.time.split(":")[0]) for b in query.all()}

    # Current hour threshold — for today, slots at or before now are gone
    now_hour = datetime.utcnow().hour if chosen == today else -1

    available_slots = []
    for slot in AVAILABLE_SLOTS:
        slot_hour = int(slot.split(":")[0])

        # Skip past slots (today only)
        if slot_hour <= now_hour:
            continue

        # Skip the booked slot itself
        if slot_hour in booked_hours:
            continue

        # Skip the 1-hour buffer after any booked slot
        # e.g. if 10:00 is booked, 11:00 is also blocked
        if any(slot_hour == booked_h + 1 for booked_h in booked_hours):
            continue

        available_slots.append({"time": slot})

    return jsonify({"slots": available_slots}), 200


# ─────────────────────────────────────────────
# Admin — Testimonials
# ─────────────────────────────────────────────

@app.route("/api/admin/testimonials")
def admin_get_testimonials():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    items = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return jsonify([t.to_dict() for t in items]), 200

@app.route("/api/admin/testimonials/<int:tid>/approve", methods=["PATCH"])
def toggle_testimonial(tid):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    t = db.session.get(Testimonial, tid)
    if not t:
        return jsonify({"error": "Not found"}), 404
    t.approved = not t.approved
    db.session.commit()
    return jsonify({"success": True, "approved": t.approved}), 200

@app.route("/api/admin/testimonials/<int:tid>", methods=["DELETE"])
def delete_testimonial(tid):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    t = db.session.get(Testimonial, tid)
    if not t:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────
# Admin — Contacts
# ─────────────────────────────────────────────

@app.route("/api/admin/contacts")
def admin_get_contacts():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    # Mark all as read when fetched by admin
    Contact.query.filter_by(read=False).update({"read": True})
    db.session.commit()
    items = Contact.query.order_by(Contact.created_at.desc()).all()
    return jsonify([c.to_dict() for c in items]), 200

@app.route("/api/admin/contacts/<int:cid>", methods=["DELETE"])
def delete_contact(cid):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    c = db.session.get(Contact, cid)
    if not c:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────
# Admin — Subscribers
# ─────────────────────────────────────────────

@app.route("/api/admin/subscribers")
def admin_get_subscribers():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    items = Subscriber.query.order_by(Subscriber.created_at.desc()).all()
    return jsonify([s.to_dict() for s in items]), 200


# ─────────────────────────────────────────────
# Admin — Blog
# ─────────────────────────────────────────────

@app.route("/api/admin/blog")
def admin_get_blog():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posts]), 200

@app.route("/api/admin/blog", methods=["POST"])
def admin_create_post():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    if not data.get("title") or not data.get("body"):
        return jsonify({"error": "Title and body are required."}), 400
    post = BlogPost(
        title     = data["title"].strip(),
        category  = data.get("category", "").strip(),
        excerpt   = data.get("excerpt", "").strip(),
        body      = data["body"].strip(),
        published = bool(data.get("published", False)),
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"success": True, "id": post.id}), 201

@app.route("/api/admin/blog/<int:pid>", methods=["PATCH"])
def admin_update_post(pid):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    post = db.session.get(BlogPost, pid)
    if not post:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "title"     in data: post.title     = data["title"].strip()
    if "category"  in data: post.category  = data["category"].strip()
    if "excerpt"   in data: post.excerpt   = data["excerpt"].strip()
    if "body"      in data: post.body      = data["body"].strip()
    if "published" in data: post.published = bool(data["published"])
    post.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True}), 200

@app.route("/api/admin/blog/<int:pid>", methods=["DELETE"])
def admin_delete_post(pid):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    post = db.session.get(BlogPost, pid)
    if not post:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(post)
    db.session.commit()
    return jsonify({"success": True}), 200


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def check_and_migrate():
    """
    Detect schema drift and rebuild the SQLite DB if any expected column is missing.
    Safe for development — use Alembic in production.
    """
    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    tables    = set(inspector.get_table_names())

    expected = {
        "contacts":    {"id","name","email","message","read","created_at"},
        "bookings":    {"id","client_name","email","service_id","service_name","price",
                        "date","time","format","notes","birth_date","birth_time",
                        "birth_location","payment_status","status","zoom_link","reschedule_count","created_at"},
        "testimonials":{"id","name","text","rating","service","approved","created_at"},
        "blog_posts":  {"id","title","category","excerpt","body","published",
                        "created_at","updated_at"},
        "services":    {"id","title","description","duration","price","icon",
                        "category","requires_birth_info"},
        "subscribers": {"id","email","created_at"},
    }

    needs_reset = False
    for table, cols in expected.items():
        if table not in tables:
            print(f"[migrate] Table '{table}' missing — will rebuild.")
            needs_reset = True
            break
        live_cols = {c["name"] for c in inspector.get_columns(table)}
        missing   = cols - live_cols
        if missing:
            print(f"[migrate] '{table}' missing columns {missing} — will rebuild.")
            needs_reset = True
            break

    if needs_reset:
        print("[migrate] Rebuilding database with current schema...")
        db.drop_all()
        db.create_all()
        seed_services()
        print("[migrate] Database rebuilt and seeded successfully.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()        # create any brand-new tables
        check_and_migrate()    # detect & fix schema drift (missing columns etc.)
        seed_services()        # seed only if tables are empty
    app.run(debug=True, port=5000)


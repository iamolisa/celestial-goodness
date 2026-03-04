# Celestial Goodness Astrology & Tarot — Flask + Tailwind CSS

A full-stack spiritual booking website converted from React/TypeScript to
plain HTML + Tailwind CSS + JavaScript frontend with a Python Flask backend.

## Project Structure

```
celestial-grace/
├── app.py                  # Flask application (routes + API)
├── requirements.txt
└── templates/
    ├── base.html           # Shared layout (navbar, footer, toast)
    ├── index.html          # Home page
    ├── about.html          # About page
    ├── services.html       # All services
    ├── booking.html        # Booking form
    ├── success.html        # Booking confirmation
    ├── contact.html        # Contact form
    ├── admin_login.html    # Admin login
    └── admin_dashboard.html# Admin dashboard (bookings management)
```

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the development server
python app.py
```

Then open http://localhost:5000 in your browser.

## Admin Access

- URL: http://localhost:5000/admin
- Email: admin@celestialgoodnessastrology.com
- Password: admin123

## API Endpoints

| Method | Endpoint                                  | Description              |
|--------|-------------------------------------------|--------------------------|
| POST   | /api/booking                              | Create a new booking     |
| POST   | /api/newsletter                           | Subscribe to newsletter  |
| POST   | /api/contact                              | Submit contact form      |
| POST   | /api/admin/login                          | Admin login              |
| POST   | /api/admin/logout                         | Admin logout             |
| GET    | /api/admin/bookings                       | List all bookings        |
| PATCH  | /api/admin/bookings/<id>/complete         | Mark booking completed   |
| DELETE | /api/admin/bookings/<id>                  | Delete a booking         |

## Production Notes

- Replace the in-memory `BOOKINGS` / `SUBSCRIBERS` lists with a real database (SQLite, PostgreSQL, etc.)
- Set a strong `app.secret_key` via environment variable
- Use a proper authentication library (Flask-Login) for admin auth
- Add CSRF protection (Flask-WTF)

"""
Run this script once to completely wipe and rebuild the database:

    python reset_db.py

Use this whenever:
  - You see "no such column" errors
  - The dashboard gets stuck on Loading...
  - You've pulled new code that added/changed model columns
"""
from app import app, db, seed_services

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating tables with current schema...")
    db.create_all()
    print("Seeding services and sample data...")
    seed_services()
    print("\nDone! Database has been reset and seeded.")
    print("You can now run: python app.py")

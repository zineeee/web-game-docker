# Arcade Hub — Mini Game Portal

A Flask mini-game website with user accounts, personal score history, and a leaderboard. Built as a learning project using Python, Flask, SQLite, Jinja templates, and Docker.

## Features

- Responsive homepage and shared visual design.
- User registration and login with hashed passwords.
- Session-based authentication and CSRF protection for forms.
- Number guessing game with server-side validation and score calculation.
- Mini golf round with five shots and saved results.
- Personal dashboard with recent games, total games, best score, and total points.
- Public leaderboard and feedback form.
- SQLite schema initialization at application startup.
- Docker deployment support with Gunicorn.

## Tech stack

- Python 3
- Flask
- Flask-WTF (CSRF protection)
- SQLite
- Jinja2 templates
- HTML/CSS
- Docker + Gunicorn

## Run locally

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate it:
   - Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set a strong secret key before running. Example for a local PowerShell session:
   ```powershell
   $env:SECRET_KEY = "replace-with-a-long-random-secret"
   ```
5. Start the app:
   ```bash
   python app.py
   ```
6. Open http://127.0.0.1:5000

The application creates its tables automatically in the SQLite database at `DATABASE_PATH`, or `game.db` if that variable is not set.

## Docker

Build and run:

```bash
docker build -t arcade-hub .
docker run --rm -p 5000:5000 -e SECRET_KEY="replace-with-a-long-random-secret" arcade-hub
```

Then open http://127.0.0.1:5000.

## Deployment notes

Set these environment variables in your hosting provider:

- `SECRET_KEY`: a long, random secret value. Do not commit the real value to Git.
- `SESSION_COOKIE_SECURE=true`: enable secure session cookies when the site is served over HTTPS.
- `DATABASE_PATH=/data/game.db`: optional; use only when a persistent volume is mounted at `/data`.

**Important:** SQLite data is not durable on most container platforms unless a persistent volume is mounted and configured. If using a volume at `/data`, set `DATABASE_PATH=/data/game.db`. The app creates a new database schema there, so migrate any old scores you want to preserve. Back up the old database before making deployment changes.

## Current scope / next improvements

- Email verification and password reset are not implemented.
- Rate limiting and account lockout should be added before a high-traffic public launch.
- The current mini-games are simple demonstrations; their score rules can be expanded.
- Leaderboard scores from different games currently share one list, so their scoring scales are not directly comparable.
- SQLite is suitable for a small demo. A production multi-user service may benefit from PostgreSQL.

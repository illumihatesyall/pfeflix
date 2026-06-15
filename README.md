# PFEFLIX 🎬

AI-powered movie & series recommendation platform built with Django.

## Stack
- **Backend:** Django 4.2 + PostgreSQL (Neon)
- **ML:** Scikit-learn — Hybrid CBF (TF-IDF + cosine similarity) + CF (TruncatedSVD)
- **Frontend:** Custom HTML/CSS/JS dark cinematic UI
- **Deployment:** Render + Neon DB

## Local Setup

```bash
# 1. Clone & install
git clone https://github.com/illumihatesyall/pfeflix.git
cd pfeflix
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in your .env values

# 3. Run migrations
python manage.py migrate

# 4. Import dataset
python import_csv.py

# 5. Start server
python manage.py runserver
```

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for dev, `False` for prod |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://your-app.onrender.com` |
| `TMDB_API_KEY` | TMDB JWT Bearer token for movie posters |
| `SECURE_SSL_REDIRECT` | `True` in production |
| `SESSION_COOKIE_SECURE` | `True` in production |
| `CSRF_COOKIE_SECURE` | `True` in production |

## Features
- 🤖 Hybrid AI recommendation engine (CBF + CF blend)
- 🎭 Search by actor or director
- ⭐ Star rating system with AJAX
- 🎬 Title detail pages with similar content
- 👥 Community — browse other users' profiles & taste match %
- 🧠 Mood-based AI chatbot questionnaire
- 🖼️ TMDB poster integration with lazy loading

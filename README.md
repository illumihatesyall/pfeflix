# PFEFLIX 🎬

AI-powered movie & series recommendation platform built with Django.

## Stack
- **Backend:** Django 4.x + PostgreSQL (Neon)
- **ML:** Scikit-learn (TF-IDF + cosine similarity), Surprise (SVD)
- **Frontend:** Custom HTML/CSS/JS dark UI
- **Deployment:** Railway + Neon DB

## Local setup

```bash
# 1. Clone & install
git clone https://github.com/YOUR_USERNAME/pfeflix.git
cd pfeflix
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in your .env values

# 3. Run migrations
python manage.py migrate

# 4. Import dataset
python manage.py shell -c "exec(open('import_csv.py').read())"

# 5. Start server
python manage.py runserver
```

## Environment variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for dev, `False` for prod |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |

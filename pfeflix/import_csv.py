import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PFE.settings')
django.setup()

from core.models import Content

df = pd.read_csv('all_platforms_combined.csv')
df = df.where(pd.notnull(df), None)

Content.objects.all().delete()
print(f"Importing {len(df)} records...")

batch = []
for _, row in df.iterrows():
    try:
        duration = row.get('duration_minutes')
        duration = int(duration) if duration and str(duration).strip().isdigit() else None
        year = row.get('release_year')
        year = int(year) if year and str(year).strip().isdigit() else None

        batch.append(Content(
            title=str(row['title'])[:300],
            platform=str(row['platform'])[:50],
            type=str(row['type'])[:20],
            genres=str(row['genres']) if row['genres'] else '',
            release_year=year,
            rating=str(row['rating'])[:20] if row['rating'] else '',
            duration_minutes=duration,
            director=str(row['director'])[:300] if row['director'] else '',
        ))
    except Exception as e:
        print(f"  Skip row: {e}")

Content.objects.bulk_create(batch, batch_size=500)
print(f"Done. {Content.objects.count()} records imported.")

import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PFE.settings')
django.setup()

from core.models import Content

df = pd.read_csv('all_platforms_combined.csv')

for _, row in df.iterrows():
    Content.objects.create(
        title=row['title'],
        platform=row['platform'],
        type=row['type'],
        genres=row['genres'],
        release_year=row['release_year']
    )

print("Import completed successfully")
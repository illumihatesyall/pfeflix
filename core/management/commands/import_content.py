from django.core.management.base import BaseCommand
import os
import pandas as pd
from core.models import Content


class Command(BaseCommand):
    help = 'Import content from CSV file'

    def handle(self, *args, **options):
        csv_path = os.path.join(os.path.dirname(__file__), '../../../all_platforms_combined.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.WARNING(f'CSV file not found at {csv_path}'))
            return

        try:
            df = pd.read_csv(csv_path)
            df = df.where(pd.notnull(df), None)

            # Check if data already exists
            existing_count = Content.objects.count()
            if existing_count > 0:
                self.stdout.write(self.style.SUCCESS(f'Content table already has {existing_count} records. Skipping import.'))
                return

            self.stdout.write(f'Importing {len(df)} records...')

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
                        cast=str(row['cast']) if row.get('cast') else '',
                        description=str(row['description']) if row.get('description') else '',
                    ))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Skip row: {e}'))

            Content.objects.bulk_create(batch, batch_size=500)
            self.stdout.write(self.style.SUCCESS(f'Done. {Content.objects.count()} records imported.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing CSV: {str(e)}'))

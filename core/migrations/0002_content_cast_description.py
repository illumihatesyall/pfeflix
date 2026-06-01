from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='cast',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='content',
            name='description',
            field=models.TextField(blank=True),
        ),
        # Also add missing fields from models.py that weren't in original migration
        migrations.AddField(
            model_name='content',
            name='rating',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='content',
            name='duration_minutes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='content',
            name='director',
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='genres',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='content_type',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='duration',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='platform',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='max_rating',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together={('user', 'title')},
        ),
    ]

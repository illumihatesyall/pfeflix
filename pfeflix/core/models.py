from django.db import models
from django.contrib.auth.models import User


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    genres = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=20, blank=True)
    duration = models.CharField(max_length=20, blank=True)
    platform = models.CharField(max_length=50, blank=True)
    max_rating = models.CharField(max_length=20, blank=True)


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    score = models.FloatField()

    class Meta:
        unique_together = ('user', 'title')


class Content(models.Model):
    title = models.CharField(max_length=300)
    platform = models.CharField(max_length=50)
    type = models.CharField(max_length=20)
    genres = models.TextField()
    release_year = models.IntegerField(null=True, blank=True)
    rating = models.CharField(max_length=20, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    director = models.CharField(max_length=300, blank=True)

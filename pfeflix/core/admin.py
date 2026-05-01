from django.contrib import admin
from .models import Content, Rating, UserPreference

admin.site.register(Content)
admin.site.register(Rating)
admin.site.register(UserPreference)
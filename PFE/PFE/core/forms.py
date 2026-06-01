from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserPreference

class PreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ['genres', 'content_type', 'duration', 'platform', 'max_rating']

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
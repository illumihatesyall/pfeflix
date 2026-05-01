from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserPreference

GENRE_CHOICES = [
    ('Action', 'Action'),
    ('Adventure', 'Adventure'),
    ('Animation', 'Animation'),
    ('Anime', 'Anime'),
    ('Biographical', 'Biographical'),
    ('Comedies', 'Comedy'),
    ('Crime', 'Crime'),
    ('Documentaries', 'Documentary'),
    ('Drama', 'Drama'),
    ('Family', 'Family'),
    ('Fantasy', 'Fantasy'),
    ('Historical', 'Historical'),
    ('Horror', 'Horror'),
    ('International', 'International'),
    ('Music', 'Music'),
    ('Mystery', 'Mystery'),
    ('Romance', 'Romance'),
    ('Sci-Fi', 'Sci-Fi'),
    ('Sports', 'Sports'),
    ('Thriller', 'Thriller'),
]

PLATFORM_CHOICES = [
    ('', 'Any Platform'),
    ('Netflix', 'Netflix'),
    ('Amazon Prime', 'Amazon Prime'),
    ('Disney+', 'Disney+'),
    ('Hulu', 'Hulu'),
]

CONTENT_TYPE_CHOICES = [
    ('', 'Movies & TV Shows'),
    ('Movie', 'Movies only'),
    ('TV Show', 'TV Shows only'),
]

RATING_CHOICES = [
    ('', 'Any Rating'),
    ('Kids', 'Kids'),
    ('General', 'General'),
    ('PG', 'PG'),
    ('Teen', 'Teen'),
    ('Adult', 'Adult'),
]


class PreferenceForm(forms.ModelForm):
    genres = forms.MultipleChoiceField(
        choices=GENRE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Favorite Genres"
    )
    platform = forms.ChoiceField(
        choices=PLATFORM_CHOICES,
        required=False,
        label="Preferred Platform"
    )
    content_type = forms.ChoiceField(
        choices=CONTENT_TYPE_CHOICES,
        required=False,
        label="Content Type"
    )
    max_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        required=False,
        label="Max Rating"
    )

    class Meta:
        model = UserPreference
        fields = ['genres', 'content_type', 'platform', 'max_rating']
        exclude = ['duration']

    def clean_genres(self):
        return ','.join(self.cleaned_data.get('genres', []))


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import PreferenceForm, RegisterForm


def home(request):
    return render(request, 'home.html')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('questionnaire')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@login_required
def questionnaire(request):
    from .models import UserPreference
    # Pre-fill if preferences already exist
    try:
        existing = UserPreference.objects.get(user=request.user)
    except UserPreference.DoesNotExist:
        existing = None

    if request.method == 'POST':
        form = PreferenceForm(request.POST, instance=existing)
        if form.is_valid():
            pref = form.save(commit=False)
            pref.user = request.user
            # duration field not in new form, give a default
            if not pref.duration:
                pref.duration = ''
            pref.save()
            return redirect('recommendations')
    else:
        # Pre-populate genres as list for MultipleChoiceField
        initial = {}
        if existing:
            initial['genres'] = existing.genres.split(',') if existing.genres else []
        form = PreferenceForm(instance=existing, initial=initial)

    return render(request, 'questionnaire.html', {'form': form})


@login_required
def recommendations(request):
    from .models import Content, UserPreference, Rating

    try:
        pref = UserPreference.objects.get(user=request.user)
    except UserPreference.DoesNotExist:
        pref = None

    qs = Content.objects.all()

    if pref:
        # Filter by platform
        if pref.platform:
            qs = qs.filter(platform=pref.platform)

        # Filter by content type
        if pref.content_type:
            qs = qs.filter(type=pref.content_type)

        # Filter by rating
        rating_order = ['Kids', 'General', 'PG', 'Teen', 'Adult', 'Unrated']
        if pref.max_rating and pref.max_rating in rating_order:
            allowed = rating_order[:rating_order.index(pref.max_rating) + 1]
            qs = qs.filter(rating__in=allowed)

        # Score by genre match (Python-level scoring)
        user_genres = [g.strip().lower() for g in pref.genres.split(',') if g.strip()]

        if user_genres:
            content_list = list(qs[:500])
            def score(item):
                item_genres = item.genres.lower()
                return sum(1 for g in user_genres if g in item_genres)
            content_list.sort(key=score, reverse=True)
            content_list = content_list[:60]
        else:
            content_list = list(qs[:60])
    else:
        content_list = list(qs[:60])

    # Get titles the user already rated
    rated_titles = set(
        Rating.objects.filter(user=request.user).values_list('title', flat=True)
    )

    # Get user's ratings as a dict
    user_ratings = dict(
        Rating.objects.filter(user=request.user).values_list('title', 'score')
    )

    for item in content_list:
        item.user_rating = user_ratings.get(item.title)
        item.rated = item.title in rated_titles

    return render(request, 'recommendations.html', {
        'movies': content_list,
        'pref': pref,
    })


@login_required
def rate_movie(request, title):
    from .models import Rating
    if request.method == 'POST':
        score = request.POST.get('score', 5)
        try:
            score = float(score)
        except (ValueError, TypeError):
            score = 5.0

        Rating.objects.update_or_create(
            user=request.user,
            title=title,
            defaults={'score': score}
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'score': score})

    return redirect('recommendations')


def logout_user(request):
    logout(request)
    return redirect('home')

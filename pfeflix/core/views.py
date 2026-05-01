from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
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
    try:
        existing = UserPreference.objects.get(user=request.user)
    except UserPreference.DoesNotExist:
        existing = None

    if request.method == 'POST':
        form = PreferenceForm(request.POST, instance=existing)
        if form.is_valid():
            pref = form.save(commit=False)
            pref.user = request.user
            if not pref.duration:
                pref.duration = ''
            pref.save()
            return redirect('recommendations')
    else:
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

    # --- Search query (searches full DB) ---
    search_q = request.GET.get('q', '').strip()
    content_type_filter = request.GET.get('type', '')
    page_num = request.GET.get('page', 1)

    qs = Content.objects.all()

    if search_q:
        # Full DB search
        qs = qs.filter(
            Q(title__icontains=search_q) |
            Q(genres__icontains=search_q) |
            Q(director__icontains=search_q)
        )
    elif pref:
        # Apply preference filters
        if pref.platform:
            qs = qs.filter(platform=pref.platform)
        if pref.content_type:
            qs = qs.filter(type=pref.content_type)

        rating_order = ['Kids', 'General', 'PG', 'Teen', 'Adult', 'Unrated']
        if pref.max_rating and pref.max_rating in rating_order:
            allowed = rating_order[:rating_order.index(pref.max_rating) + 1]
            qs = qs.filter(rating__in=allowed)

        # Genre scoring — score top 500, sort, then paginate all results
        user_genres = [g.strip().lower() for g in pref.genres.split(',') if g.strip()]
        if user_genres:
            content_list = list(qs[:800])
            def score(item):
                item_genres = item.genres.lower()
                return sum(1 for g in user_genres if g in item_genres)
            content_list.sort(key=score, reverse=True)
            # Convert back — we'll paginate the full scored list
            from django.db.models import Case, When, IntegerField
            qs = content_list  # use list directly for pagination below
        else:
            qs = qs.order_by('-release_year')

    # Apply type filter chip
    if content_type_filter and not search_q:
        if isinstance(qs, list):
            qs = [c for c in qs if c.type == content_type_filter]
        else:
            qs = qs.filter(type=content_type_filter)

    # Paginate — 24 per page
    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(page_num)
    content_list = list(page_obj)

    # Annotate with user ratings
    rated_titles = set(
        Rating.objects.filter(user=request.user).values_list('title', flat=True)
    )
    user_ratings = dict(
        Rating.objects.filter(user=request.user).values_list('title', 'score')
    )
    for item in content_list:
        item.user_rating = user_ratings.get(item.title)
        item.rated = item.title in rated_titles

    return render(request, 'recommendations.html', {
        'movies': content_list,
        'pref': pref,
        'page_obj': page_obj,
        'search_q': search_q,
        'content_type_filter': content_type_filter,
        'total_count': paginator.count,
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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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

    qs = Content.objects.all()

    if pref:
        if pref.platform:
            qs = qs.filter(platform=pref.platform)
        if pref.content_type:
            qs = qs.filter(type=pref.content_type)

        rating_order = ['Kids', 'General', 'PG', 'Teen', 'Adult', 'Unrated']
        if pref.max_rating and pref.max_rating in rating_order:
            allowed = rating_order[:rating_order.index(pref.max_rating) + 1]
            qs = qs.filter(rating__in=allowed)

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


@login_required
def search_people(request):
    """Search content by actor or director name."""
    from .models import Content

    query = request.GET.get('q', '').strip()
    results = []
    search_type = None  # 'actor' | 'director' | 'both'
    error_message = None

    try:
        if query:
            actor_qs    = Content.objects.filter(cast__icontains=query)
            director_qs = Content.objects.filter(director__icontains=query)

            actor_ids    = set(actor_qs.values_list('id', flat=True))
            director_ids = set(director_qs.values_list('id', flat=True))

            if actor_ids and director_ids:
                search_type = 'both'
            elif actor_ids:
                search_type = 'actor'
            elif director_ids:
                search_type = 'director'

            # Combine: director results first, then actor-only results
            combined_ids = list(director_ids) + [i for i in actor_ids if i not in director_ids]
            if combined_ids:
                # Preserve order using Python instead of huge SQL CASE statement
                content_dict = {item.id: item for item in Content.objects.filter(id__in=combined_ids)}
                results = [content_dict[pk] for pk in combined_ids if pk in content_dict][:60]
    except Exception as e:
        error_message = f"Search error: {str(e)}"
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Search people error")

    return render(request, 'search_people.html', {
        'query':       query,
        'results':     results,
        'search_type': search_type,
        'count':       len(results),
        'error_message': error_message,
    })


def logout_user(request):
    logout(request)
    return redirect('home')


@login_required
def title_detail(request, pk):
    """Full detail page for a single movie or TV show."""
    from .models import Content, Rating

    content = get_object_or_404(Content, pk=pk)

    # User's rating for this title
    try:
        user_rating = Rating.objects.get(user=request.user, title=content.title)
        user_score = int(user_rating.score)
    except Rating.DoesNotExist:
        user_score = None

    # Handle rating POST from this page
    if request.method == 'POST':
        score = request.POST.get('score')
        if score:
            try:
                score = float(score)
                Rating.objects.update_or_create(
                    user=request.user,
                    title=content.title,
                    defaults={'score': score}
                )
                user_score = int(score)
            except (ValueError, TypeError):
                pass

    # Similar titles: same genres, exclude this one
    similar = []
    if content.genres:
        main_genres = [g.strip().lower() for g in content.genres.split(',') if g.strip()]
        if main_genres:
            candidates = Content.objects.filter(
                type=content.type
            ).exclude(pk=content.pk)[:300]

            def sim_score(item):
                ig = item.genres.lower()
                return sum(1 for g in main_genres if g in ig)

            scored = sorted(candidates, key=sim_score, reverse=True)
            similar = [s for s in scored if sim_score(s) > 0][:8]

    # Parse cast into a list for nicer display
    cast_list = [c.strip() for c in content.cast.split(',') if c.strip()] if content.cast else []

    return render(request, 'title_detail.html', {
        'content':    content,
        'user_score': user_score,
        'similar':    similar,
        'cast_list':  cast_list,
    })
import json
import secrets
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import TaskForm
from .models import Task

PROVIDER_URLS = {
    'netflix': 'https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&sort_by=popularity.desc&with_watch_providers=8&watch_region=US&with_watch_monetization_types=flatrate',
    'amazon': 'https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&sort_by=popularity.desc&with_watch_providers=9-10&watch_region=US&with_watch_monetization_types=flatrate',
    'apple': 'https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&sort_by=popularity.desc&with_watch_providers=350&watch_region=US&with_watch_monetization_types=flatrate',
}


@login_required
def index(request):
    tasks = Task.objects.filter(user=request.user).order_by("-priority", "-created")
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
        return redirect("/")

    context = {"tasks": tasks, "form": form, "version": settings.VERSION}
    return render(request, "tasks/list.html", context)


@login_required
def updateTask(request, pk):
    task = Task.objects.get(id=pk, user=request.user)
    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("/")

    context = {"form": form}
    return render(request, "tasks/update_task.html", context)


@login_required
def deleteTask(request, pk):
    item = Task.objects.get(id=pk, user=request.user)

    if request.method == "POST":
        item.delete()
        return redirect("/")

    context = {"item": item}
    return render(request, "tasks/delete.html", context)


@login_required
def add_watchlist(request, provider):
    if request.method != "POST" or provider not in PROVIDER_URLS:
        return redirect("/")

    base_url = PROVIDER_URLS[provider]
    added = 0
    page = 1

    while added < 10:
        url = f"{base_url}&page={page}&api_key={settings.TMDB_API_KEY}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        for show in data.get("results", []):
            if added >= 10:
                break
            tmdb_id = show["id"]
            provider_label = {'netflix': 'Netflix', 'amazon': 'Amazon Prime', 'apple': 'Apple TV'}[provider]
            if not Task.objects.filter(user=request.user, tmdb_id=tmdb_id).exists():
                Task.objects.create(
                    title=f"{show['name']} ({provider_label})",
                    tmdb_id=tmdb_id,
                    user=request.user,
                )
                added += 1

        if page >= data.get("total_pages", 1):
            break
        page += 1

    return redirect("/")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    form = UserCreationForm()
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    return render(request, "tasks/register.html", {"form": form})



def fc_authorize(request):
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    request.session['fc_state'] = state
    request.session['fc_nonce'] = nonce
    request.session.save()

    params = urllib.parse.urlencode({
        'response_type': 'code',
        'client_id': settings.FC_CLIENT_ID,
        'redirect_uri': settings.FC_CALLBACK_URL,
        'scope': settings.FC_SCOPES,
        'state': state,
        'nonce': nonce,
        'acr_values': 'eidas1',
    })
    return redirect(f"{settings.FC_BASE_URL}/api/v1/authorize?{params}")


def fc_callback(request):
    from django.http import HttpResponse
    code = request.GET.get('code')

    if not code:
        return HttpResponse(f"Error: no code. GET params: {request.GET}", status=400)

    try:
        # Exchange code for tokens
        token_data = urllib.parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.FC_CALLBACK_URL,
            'client_id': settings.FC_CLIENT_ID,
            'client_secret': settings.FC_CLIENT_SECRET,
        }).encode()

        token_req = urllib.request.Request(
            f"{settings.FC_BASE_URL}/api/v1/token",
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        with urllib.request.urlopen(token_req) as resp:
            tokens = json.loads(resp.read().decode())

        access_token = tokens['access_token']
        id_token = tokens['id_token']
        request.session['fc_id_token'] = id_token

        # Get user info
        userinfo_req = urllib.request.Request(
            f"{settings.FC_BASE_URL}/api/v1/userinfo",
            headers={'Authorization': f'Bearer {access_token}'},
        )
        with urllib.request.urlopen(userinfo_req) as resp:
            userinfo = json.loads(resp.read().decode())

        # Find or create user based on FC sub
        fc_sub = userinfo['sub']
        email = userinfo.get('email', '')
        given_name = userinfo.get('given_name', '')
        family_name = userinfo.get('family_name', '')
        username = f"fc_{fc_sub[:20]}"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': given_name,
                'last_name': family_name,
            },
        )
        if not created:
            user.email = email
            user.first_name = given_name
            user.last_name = family_name
            user.save()

        login(request, user)
        return redirect('/')

    except Exception as e:
        return HttpResponse(f"Error during FC callback: {e}", status=500)


def fc_logout(request):
    id_token = request.session.get('fc_id_token', '')
    state = secrets.token_urlsafe(32)

    from django.contrib.auth import logout
    logout(request)

    if id_token:
        params = urllib.parse.urlencode({
            'id_token_hint': id_token,
            'state': state,
            'post_logout_redirect_uri': settings.FC_LOGOUT_CALLBACK_URL,
        })
        return redirect(f"{settings.FC_BASE_URL}/api/v1/logout?{params}")

    return redirect('login')


def fc_logout_callback(request):
    return redirect('login')

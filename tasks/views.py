import json
import urllib.request
from django.conf import settings
from django.shortcuts import redirect, render

from .forms import TaskForm
from .models import Task

PROVIDER_URLS = {
    'netflix': 'https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&sort_by=popularity.desc&with_watch_providers=8&watch_region=US&with_watch_monetization_types=flatrate',
    'amazon': 'https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&sort_by=popularity.desc&with_watch_providers=9-10&watch_region=US&with_watch_monetization_types=flatrate',
    'apple': 'https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&sort_by=popularity.desc&with_watch_providers=350&watch_region=US&with_watch_monetization_types=flatrate',
}


def index(request):
    tasks = Task.objects.order_by("-priority", "-created")
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            # Adds to the database if valid
            form.save()
        return redirect("/")

    context = {"tasks": tasks, "form": form, "version": settings.VERSION}
    return render(request, "tasks/list.html", context)


def updateTask(request, pk):
    task = Task.objects.get(id=pk)
    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("/")

    context = {"form": form}
    return render(request, "tasks/update_task.html", context)


def deleteTask(request, pk):
    item = Task.objects.get(id=pk)

    if request.method == "POST":
        item.delete()
        return redirect("/")

    context = {"item": item}
    return render(request, "tasks/delete.html", context)


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
            if not Task.objects.filter(tmdb_id=tmdb_id).exists():
                Task.objects.create(
                    title=f"{show['name']} ({provider_label})",
                    tmdb_id=tmdb_id,
                )
                added += 1

        if page >= data.get("total_pages", 1):
            break
        page += 1

    return redirect("/")

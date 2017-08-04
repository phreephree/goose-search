from django.shortcuts import render
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseForbidden
from search.models import SearchPreset
from search.forms import SearchForm
from ratelimit.decorators import ratelimit
from search.views import utils
import geopy
import overpass
import logging
import json

def home(request):
    """
        The main page of Goose. Shows the search form, validate it
        and redirect to "results" if it's correct.
    """
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            form.clean()
            user_latitude = form.cleaned_data["user_latitude"]
            user_longitude = form.cleaned_data["user_longitude"]
            calculated_address = form.cleaned_data["calculated_address"]
            request.session["search_form"] = {
                "user_latitude": user_latitude,
                "user_longitude": user_longitude,
                "user_address": calculated_address,
                "radius": form.cleaned_data["radius"],
                "search_preset_id": form.cleaned_data["search_preset"].id,
                "no_private": form.cleaned_data["no_private"],
            }
            return redirect("results")
    else:
        form = SearchForm()
    return render(request, "search/geo.html", locals())

@ratelimit(key='ip', rate="3/m")
def results(request):
    """
        The page where the results are displayed. Initially empty,
        filled with Ajax and the "geo_get_results" view.
    """
    if request.session.get("search_form") is None:
        return redirect("home")
    was_limited = getattr(request, 'limited', False)
    search_preset_id = request.session["search_form"]["search_preset_id"]
    search_preset = SearchPreset.objects.get(id=search_preset_id)
    user_latitude = request.session["search_form"]["user_latitude"]
    user_longitude = request.session["search_form"]["user_longitude"]
    user_address = request.session["search_form"]["user_address"]
    radius = request.session["search_form"]["radius"]
    no_private = request.session["search_form"]["no_private"]
    search_description = '"{}" dans un rayon de {} mètres.'.format(search_preset.name, radius)
    if no_private is True:
        search_description += " Exclusion des résultats à accès privé."
    else:
        search_description += " Inclusion des résultats à accès privé."
    return render(request, "search/geo_results.html", {
        "user_coords": (user_latitude, user_longitude),
        "user_address": user_address,
        "radius": radius,
        "search_preset_id": search_preset_id,
        "no_private": no_private,
        "was_limited": was_limited,
        "search_description": search_description
        }
    )

@csrf_exempt
def get_results(request):
    """
        Used by Ajax to get the results.
    """
    if not request.is_ajax():
        return HttpResponseForbidden("This URL if for Ajax only.")
    search_preset_id = request.POST["search_preset_id"]
    search_preset = SearchPreset.objects.get(id=search_preset_id)
    radius = request.POST["radius"]
    user_latitude = float(request.POST["user_latitude"])
    user_longitude = float(request.POST["user_longitude"])
    no_private = request.POST["no_private"]
    if no_private == "true":
        no_private = True
    else:
        no_private = False
    rendered_results = []
    status = "error"
    err_msg = ""
    debug_msg = ""
    tags_filter = ""
    try:
        results = utils.get_results(
            search_preset, (user_latitude, user_longitude), radius,
            no_private
        )
        for result in results:
            tags_count = utils.get_all_tags(results)
            tags_filter = utils.render_tag_filter(tags_count, len(results))
            rendered_results.append("<li>" + result.render() + "</li>")
        status = "ok"
    except geopy.exc.GeopyError as e:
        err_msg = "Une erreur s'est produite lors de l'acquisition de vos coordonnées. Vous pouvez essayer de recharger la page dans quelques instants."
        debug_msg = str(e)
    except overpass.OverpassError as e:
        err_msg = "Une erreur s'est produite lors de la requête vers les serveurs d'OpenStreetMap. Vous pouvez essayer de recharger la page dans quelques instants."
        debug_msg = str(e)
    except Exception as e:
        err_msg = "Une erreur non prise en charge s'est produite."
        debug_msg = str(e)
    # Logs the request to make statistics.
    # Doesn't logs if the request comes from an authenticated user,
    # as it is probably an admin.
    if not request.user.is_authenticated():
        logger = logging.getLogger("statistics")
        logger.info(
            "search:{id}:{radius}:{lat}:{lon}".format(
                id=search_preset_id,
                radius=radius,
                # Rounds the stored coordinates for privacy's sake.
                lat=round(user_latitude),
                lon=round(user_longitude)
            )
        )
    return HttpResponse(json.dumps({
            "status": status, "content": rendered_results, "err_msg": err_msg,
            "debug_msg": debug_msg, "filters": tags_filter
        }),
        content_type="application/json"
    )

def about(request):
    """
        The about page, providing some informations about the site itself.
    """
    # Logs the request to make statistics.
    logger = logging.getLogger("statistics")
    logger.info("about_page")
    return render(request, "search/about.html")
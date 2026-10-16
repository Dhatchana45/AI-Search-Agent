import os
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

TV_CATEGORIES = {"TV Serials", "Web Series"}


def get_tmdb_session():
    """Create a session with retries for temporary network failures."""
    session = requests.Session()

    retries = Retry(
        total=2,
        connect=2,
        read=0,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def _auth(params: dict) -> dict:
    """
    TMDB has two credentials: the short v3 API key (query parameter) and the
    long v4 "Read Access Token" (Bearer header). Support both.
    """
    headers = {}
    if TMDB_API_KEY and len(TMDB_API_KEY) > 60:
        headers["Authorization"] = f"Bearer {TMDB_API_KEY}"
    else:
        params["api_key"] = TMDB_API_KEY
    return headers


def search_media(query, media_type="multi", max_results=10):
    """Search TMDB for movies, TV shows, or both."""
    if not TMDB_API_KEY:
        return {"success": False, "error": "TMDB_API_KEY is missing from .env", "results": []}

    query = (query or "").strip()
    if not query:
        return {"success": True, "results": []}

    endpoints = {
        "movie": "/search/movie",
        "tv": "/search/tv",
        "multi": "/search/multi",
    }
    if media_type not in endpoints:
        media_type = "multi"

    url = TMDB_BASE_URL + endpoints[media_type]
    params = {
        "query": query,
        "language": "en-US",
        "page": 1,
        "include_adult": "false",  # requests would send Python's False as "False"
    }

    try:
        headers = _auth(params)
        response = get_tmdb_session().get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()

        data = response.json()
        results = []

        for item in data.get("results", [])[:max_results]:
            item_type = item.get("media_type", media_type)

            # /search/multi can also return other types; only keep known ones.
            if item_type not in {"movie", "tv", "person"}:
                continue

            if item_type == "person":
                title = item.get("name", "")
            else:
                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("original_title")
                    or item.get("original_name")
                    or ""
                )

            if item_type == "movie":
                category = "Movies"
            elif item_type == "tv":
                category = "TV Serials"
            else:
                category = "People / Celebrities"

            # TMDB genre 16 = Animation. Japanese-language animation = anime.
            if item_type in {"movie", "tv"} and 16 in (item.get("genre_ids") or []):
                category = (
                    "Anime / Manga"
                    if item.get("original_language") == "ja"
                    else "Cartoons / Animation"
                )

            item_id = item.get("id")
            poster_path = item.get("poster_path") or item.get("profile_path")
            overview = item.get("overview") or ""
            if item_type == "person" and not overview:
                known_for = [
                    k.get("title") or k.get("name")
                    for k in (item.get("known_for") or [])
                    if (k.get("title") or k.get("name"))
                ]
                if known_for:
                    overview = "Known for: " + ", ".join(known_for)

            results.append({
                "title": title,
                "name": title,
                "overview": overview,
                "release_date": item.get("release_date") or item.get("first_air_date") or "",
                "media_type": item_type,
                "category": category,
                "source": "tmdb",
                "provider": "tmdb",
                "url": f"https://www.themoviedb.org/{item_type}/{item_id}" if item_id else "https://www.themoviedb.org/",
                "id": item_id,
                "poster_path": poster_path,
                "poster_url": f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None,
                "vote_average": item.get("vote_average"),
                # rag/documents.py reads "rating"; keep both names available.
                "rating": item.get("vote_average"),
            })

        return {"success": True, "results": results}

    except requests.RequestException as error:
        return {"success": False, "error": f"TMDB request failed: {error}", "results": []}
    except ValueError as error:
        return {"success": False, "error": f"Invalid JSON from TMDB: {error}", "results": []}


def _media_type_for(categories):
    """
    FIX: the old code searched /search/movie for TV Serials and Web Series.
    Choose the right TMDB endpoint from the categories that were merged into
    this search.
    """
    cats = set(categories or ["Movies"])
    wants_movie = "Movies" in cats
    wants_tv = bool(cats & TV_CATEGORIES)

    if wants_movie and not wants_tv and cats <= {"Movies"}:
        return "movie"
    if wants_tv and not wants_movie and cats <= TV_CATEGORIES:
        return "tv"
    return "multi"


def process_media_searches(searches, max_results_per_query=10):
    """Process searches created by query_search.py."""
    all_results = []
    errors = []
    done = set()

    for item in searches:
        if item.get("provider") != "tmdb":
            continue

        query = (item.get("search_query") or "").strip()
        if not query:
            continue

        categories = item.get("categories") or [item.get("category", "Movies")]
        media_type = _media_type_for(categories)

        if (query, media_type) in done:
            continue
        done.add((query, media_type))

        result = search_media(query, media_type=media_type, max_results=max_results_per_query)

        if not result["success"]:
            errors.append({"query": query, "error": result["error"]})
            continue

        for media in result["results"]:
            media["search_query"] = query
            media["query"] = query
            all_results.append(media)

    return {"results": all_results, "errors": errors}
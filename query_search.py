import re

from service.category_service import classify_query


# News goes to GNews, which matches keywords, so it gets the plain query.
CATEGORY_QUERIES = {
    "News": "{query}",
    "Politics / Government": "{query} government politics public affairs",
    "Sports": "{query} sports news results",
    "Weather": "{query} weather forecast rainfall updates",
    "Technology / Products": "{query} technology products devices",
    "Programming / Software Dev": "{query} programming tutorial documentation",
    "Business / Company": "{query} company business financial news",
    "Finance / Crypto": "{query} finance market price today",
    "Fruit / Agriculture": "{query} fruit agriculture cultivation nutrition",
    "Movies": "{query}",
    "TV Serials": "{query}",
    "Web Series": "{query}",
    "Cartoons / Animation": "{query}",
    "Anime / Manga": "{query}",
    "Entertainment / Cinema": "{query} entertainment cinema reviews",
    "Music / Songs": "{query} song music",
    "Books / Literature": "{query} book author summary",
    "Video Games": "{query} video game",
    "People / Celebrities": "{query} biography profile career",
    "Education": "{query} education courses learning",
    "Jobs / Careers": "{query} jobs careers openings",
    "Science": "{query} science research discoveries",
    "Space / Astronomy": "{query} space astronomy",
    "Mathematics": "{query} mathematics explained",
    "Health": "{query} health medical information",
    "Travel / Places": "{query} location travel guide",
    "Geography / Countries": "{query} geography facts",
    "Food": "{query} food recipes ingredients",
    "Environment": "{query} environment climate conservation",
    "Animals / Pets": "{query} animal facts care",
    "Crime": "{query} crime investigation reports",
    "Law / Legal": "{query} law legal explained",
    "Automobiles": "{query} car bike price review",
    "Transport / Railways": "{query} transport railway timings",
    "Fashion / Beauty": "{query} fashion beauty",
    "Shopping / Deals": "{query} price buy offers",
    "Real Estate": "{query} real estate property",
    "Religion / Spirituality": "{query} religion spirituality",
    "Festivals / Events": "{query} festival event date",
    "History": "{query} history facts",
    "Art / Culture": "{query} art culture",
    "Languages": "{query} language meaning",
    "Social Media": "{query} social media",
    "Kids / Parenting": "{query} kids parenting",
    "Relationships / Lifestyle": "{query} lifestyle advice",
    "Home / DIY": "{query} home DIY guide",
    "General Web": "{query}",
}

# Categories answered by TMDB (movies / TV / animation).
TMDB_CATEGORIES = {
    "Movies", "TV Serials", "Web Series",
    "Cartoons / Animation", "Anime / Manga",
}

# Whole-word hints only. The old substring check matched "cast" inside
# "forecast"/"broadcast" and wrongly forced a Movies search.
MOVIE_HINT_PATTERN = re.compile(
    r"\b(movie|movies|film|films|cinema|trailer|soundtrack|"
    r"box office|ott release|cast of|cast and crew)\b",
    re.IGNORECASE,
)


def _provider_for(category: str) -> str:
    if category == "News":
        return "gnews"
    if category in TMDB_CATEGORIES:
        return "tmdb"
    return "tavily"


def build_category_queries(query: str, categories: list[str]) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    searches = []
    by_key = {}

    for category in categories:
        template = CATEGORY_QUERIES.get(category, "{query}")
        search_query = template.format(query=query)
        provider = _provider_for(category)

        # Movies / TV Serials / Web Series all use the same plain query on
        # TMDB. Merge them into ONE search instead of calling TMDB 3 times.
        key = (provider, search_query)
        if key in by_key:
            by_key[key]["categories"].append(category)
            continue

        entry = {
            "category": category,
            "categories": [category],
            "search_query": search_query,
            "provider": provider,
        }
        by_key[key] = entry
        searches.append(entry)

    return searches


def prepare_search(query: str) -> dict:
    query = query.strip()

    if not query:
        return {
            "original_query": query,
            "categories": [],
            "search_intent": "empty",
            "searches": [],
        }

    classification = classify_query(query)
    categories = list(classification.get("categories", []))

    # Explicit movie-related searches should always include TMDB.
    if MOVIE_HINT_PATTERN.search(query) and "Movies" not in categories:
        categories.insert(0, "Movies")

    searches = build_category_queries(query, categories)

    prepared = {
        "original_query": query,
        "categories": categories,
        "search_intent": classification.get("search_intent", "general"),
        "searches": searches,
    }
    if classification.get("classification_warning"):
        prepared["classification_warning"] = classification["classification_warning"]

    return prepared
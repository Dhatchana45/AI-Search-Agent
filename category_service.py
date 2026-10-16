
import json
import re

from google import genai
from google.genai.errors import ServerError
from google.genai import types
from dotenv import load_dotenv

from config import GEMINI_API_KEY, LLM_MODEL

load_dotenv()


CATEGORIES = [
    "News",
    "Politics / Government",
    "Sports",
    "Weather",
    "Technology / Products",
    "Business / Company",
    "Fruit / Agriculture",
    "Movies",
    "TV Serials",
    "Web Series",
    "Entertainment / Cinema",
    "People / Celebrities",
    "Education",
    "Science",
    "Health",
    "Travel / Places",
    "Food",
    "Environment",
    "Crime",
    "General Web"
]


def normalize_query(query: str) -> str:
    """Clean and normalize the user's search query."""
    query = (query or "").strip()
    return re.sub(r"\s+", " ", query)


def fallback_categories(query: str) -> list[str]:
    """
    Classify queries locally using keyword rules.
    No Gemini API requests or quota consumption.
    """

    q = normalize_query(query).lower()

    if not q:
        return ["General Web"]

    categories = []

    rules = {
        "Weather": [
            "weather", "rainfall", "rain", "raining",
            "cyclone", "flood", "temperature", "monsoon",
            "forecast", "humidity", "storm", "drought"
        ],
        "Politics / Government": [
            "chief minister", "prime minister",
            "government", "election", "minister",
            "politician", "parliament", "president",
            "mla", "mp ", "politics", "cm gave",
            "cm announces", "policy"
        ],
        "Sports": [
            "cricket", "cricketer", "football",
            "tennis", "chess", "ipl", "olympics",
            "badminton", "basketball", "hockey",
            "world cup", "match score", "sports",
            "formula 1", "f1 racing"
        ],
        "Technology / Products": [
            "iphone", "ipad", "apple watch",
            "smartphone", "laptop", "mobile phone",
            "software", "artificial intelligence",
            "machine learning", "robotics",
            "gadget", "processor", "graphics card",
            "samsung galaxy", "product review",
            "product launch", "tech news"
        ],
        "Business / Company": [
            "company shares", "stock market",
            "company earnings", "business news",
            "startup", "share price", "sensex",
            "nifty", "quarterly results",
            "revenue", "profit", "ipo", "finance"
        ],
        "Movies": [
            "movie", "movies", "film", "films",
            "cinema", "box office", "movie review",
            "film review", "movie cast", "film cast",
            "movie trailer", "film trailer",
            "movie release", "film release",
            "actor in", "actress in"
        ],
        "TV Serials": [
            "tv serial", "television serial",
            "soap opera", "serial episode",
            "daily serial", "tv show"
        ],
        "Web Series": [
            "web series", "streaming series",
            "web show", "series episode",
            "series season", "ott series"
        ],
        "Entertainment / Cinema": [
            "entertainment", "celebrity news",
            "film industry", "cinema news",
            "award ceremony", "music release",
            "dance performance", "dancer",
            "singer", "concert", "album release"
        ],
        "People / Celebrities": [
            "biography", "biography of",
            "personal life", "age of",
            "career of", "net worth",
            "profile of", "who is"
        ],
        "Fruit / Agriculture": [
            "fruit", "apple fruit", "farming",
            "crop", "harvest", "agriculture",
            "cultivation", "farmer", "fertilizer",
            "irrigation", "soil health", "pesticide"
        ],
        "Education": [
            "education", "school admission",
            "college admission", "university",
            "exam results", "syllabus",
            "scholarship", "online course",
            "tutorial", "learning", "student"
        ],
        "Science": [
            "science", "scientific research",
            "physics", "chemistry", "biology",
            "space research", "astronomy",
            "discovery", "experiment"
        ],
        "Health": [
            "health", "symptoms", "disease",
            "treatment", "nutrition", "hospital",
            "medicine", "medical", "doctor",
            "fitness", "mental health"
        ],
        "Travel / Places": [
            "travel", "tourism", "tourist places",
            "places to visit", "hotel", "flight",
            "destination", "travel guide",
            "near me", "things to do"
        ],
        "Food": [
            "food", "recipe", "recipes", "cooking",
            "ingredients", "restaurant", "cuisine",
            "breakfast", "lunch recipe", "dinner recipe",
            "dessert", "baking", "chef", "apple pie"
        ],
        "Environment": [
            "environment", "climate change",
            "global warming", "pollution",
            "deforestation", "conservation",
            "biodiversity", "renewable energy",
            "carbon emissions"
        ],
        "Crime": [
            "crime", "criminal", "murder",
            "theft", "robbery", "police investigation",
            "arrested", "court case", "fraud"
        ],
        "News": [
            "latest news", "breaking news",
            "today news", "news update",
            "latest updates", "current affairs"
        ]
    }

    # Match longer phrases first to reduce ambiguous matches.
    for category, keywords in rules.items():
        if any(keyword in q for keyword in keywords):
            categories.append(category)

    # Handle "Apple" as an ambiguous query.
    # Add likely meanings without assuming a single intent.
    if re.search(r"\bapple\b", q):
        if not any(
            category in categories
            for category in [
                "Technology / Products",
                "Fruit / Agriculture",
                "Food"
            ]
        ):
            categories.extend([
                "Technology / Products",
                "Fruit / Agriculture"
            ])

    # Recognize explicit movie and series search intent.
    if re.search(
        r"\b(movie|movies|film|films|cinema|"
        r"trailer|box office|movie review|film review)\b",
        q
    ):
        categories.append("Movies")

    if re.search(
        r"\b(web series|streaming series|ott series)\b",
        q
    ):
        categories.append("Web Series")

    if not categories:
        categories = ["General Web"]

    return list(dict.fromkeys(categories))


def classify_query(query: str) -> dict:
    """
    Classify a query using Gemini when configured, with local keyword rules
    as a fallback when no Gemini API key is available or Gemini is unavailable.

    Returns:
        {
            "query": "...",
            "categories": [...],
            "search_intent": "..."
        }
    """

    query = normalize_query(query)

    if not query:
        return {
            "query": "",
            "categories": [],
            "search_intent": "empty"
        }

    if GEMINI_API_KEY:
        prompt = f"""
Classify the user's search query by its meaning, not only by matching
keywords. Recognize named people, products, places, works of fiction,
and other entities when they identify the query's topic.

Return JSON only in this format:
{{"categories": ["Movies"]}}

Choose one or more categories only from this list:
{json.dumps(CATEGORIES, ensure_ascii=False)}

Use "General Web" only when the query does not clearly fit another category.
Do not invent details or return categories outside the provided list.

User query: {query}
"""
        try:
            with genai.Client(api_key=GEMINI_API_KEY) as client:
                response = client.models.generate_content(
                    model=LLM_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
        except ServerError as exc:
            if exc.code != 503:
                raise
            return {
                "query": query,
                "categories": fallback_categories(query),
                "search_intent": "local_keyword_fallback",
                "classification_warning": (
                    "Gemini is temporarily unavailable (503); "
                    "using local keyword classification."
                ),
            }
        if not response.text:
            raise RuntimeError("Gemini returned an empty category response.")

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned an invalid category response."
            ) from exc

        raw_categories = result.get("categories") if isinstance(result, dict) else None
        if not isinstance(raw_categories, list):
            raise RuntimeError(
                "Gemini category response must contain a categories list."
            )
        categories = list(dict.fromkeys(
            category for category in raw_categories
            if isinstance(category, str) and category in CATEGORIES
        ))
        if not categories:
            raise RuntimeError(
                "Gemini did not return any recognized search categories."
            )
        search_intent = "ai_query_classification"
    else:
        categories = fallback_categories(query)
        search_intent = "local_keyword_search"

    return {
        "query": query,
        "categories": categories,
        "search_intent": search_intent
    }


if __name__ == "__main__":
    test_queries = [
        "Apple",
        "iPhone 17 launch",
        "Vikram",
        "Vikram movie",
        "Stranger Things web series",
        "CM gave award to Vetrimaaran",
        "Today's rainfall in Tamil Nadu",
        "latest cricket news",
        "apple pie recipe",
        "laptop price",
        "climate change"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print(classify_query(query))

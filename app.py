import os
import json
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from service.query_search import prepare_search
from service.news_search import process_news_searches
from service.web_search import process_web_searches
from service.media_search import process_media_searches
from rag.documents import (
    news_to_documents,
    web_to_documents,
    media_to_documents,
)

load_dotenv()

st.set_page_config(
    page_title="AI-Powered Universal Search",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 AI-Powered Universal Search")
st.write(
    "Search a topic, person, event, or question. AI identifies relevant "
    "categories and searches news, the web, and movie/TV sources."
)


# Optional RAG integration. If vector-store dependencies or configuration
# are unavailable, search still works and the app displays a warning.
try:
    from rag.vector_stores import add_documents, search_similar_documents
    RAG_AVAILABLE = True
    RAG_IMPORT_ERROR = None
except Exception as exc:
    RAG_AVAILABLE = False
    RAG_IMPORT_ERROR = str(exc)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def get_result_items(result, possible_keys):
    """Extract a list of result items from a service response safely."""
    if isinstance(result, list):
        return result
    if not isinstance(result, dict):
        return []
    for key in possible_keys:
        value = result.get(key)
        if isinstance(value, list):
            return value
    # Some service versions return individual result dictionaries directly.
    if any(key in result for key in ("title", "name", "url", "link", "overview")):
        return [result]
    return []


def service_error(result):
    if isinstance(result, dict) and not result.get("success", True):
        return result.get("error") or "The provider reported an unsuccessful search."
    return None


def infer_content_category(item, fallback="General Web"):
    """Infer a result's category from its own title and content, not its search query."""
    title = str(
        item.get("title") or item.get("name") or item.get("original_title")
        or item.get("original_name") or ""
    )
    description = str(
        item.get("description") or item.get("overview") or item.get("content")
        or item.get("snippet") or item.get("text") or ""
    )
    text = f"{title} {description}".lower()

    # More specific content types should be checked before broad categories.
    rules = [
        ("Food", ["recipe", "recipes", "ingredients", "cooking", "cookbook", "bake", "baking", "food network", "chef", "apple pie", "nutrition"]),
        ("Dance", ["dance", "dancing", "choreography", "choreographer", "dance video", "dance performance"]),
        ("Web Series", ["web series", "streaming series", "season episode", "netflix series", "prime video series"]),
        ("TV Serials", ["tv serial", "television serial", "soap opera", "serial episode"]),
        ("Movies", ["movie", "movies", "film", "films", "movie review", "film review", "box office", "movie trailer", "film trailer", "cinema release", "cinematic universe", "feature film"]),
        ("Entertainment / Cinema", ["entertainment", "celebrity", "red carpet", "award show", "music video", "concert", "actor", "actress"]),
        ("Technology / Products", ["product review", "product launch", "smartphone", "iphone", "laptop", "gadget", "device", "specifications", "unboxing", "technology"]),
        ("Fruit / Agriculture", ["fruit", "apple fruit", "farming", "agriculture", "crop", "harvest", "cultivation"]),
        ("Sports", ["cricket", "football", "basketball", "tennis", "chess", "match highlights", "tournament", "olympics"]),
        ("Weather", ["weather forecast", "rainfall", "cyclone", "flood warning", "temperature forecast", "monsoon"]),
        ("Politics / Government", ["government", "election", "prime minister", "chief minister", "parliament", "political party", "minister"]),
        ("Business / Company", ["company earnings", "stock market", "business news", "quarterly results", "market share", "revenue"]),
        ("Education", ["course", "tutorial", "lesson", "education", "how to learn", "lecture"]),
        ("Health", ["medical", "health", "symptom", "treatment", "hospital", "disease"]),
        ("Science", ["scientific research", "research study", "experiment", "discovery", "space mission"]),
        ("Travel / Places", ["travel guide", "tourism", "destination", "things to do", "travel vlog"]),
        ("Environment", ["climate change", "environment", "conservation", "wildlife", "pollution"]),
        ("Crime", ["police investigation", "court case", "arrested", "crime", "murder investigation"]),
    ]
    for category_name, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category_name
    return fallback if fallback and fallback != "General Web" else "General Web"


def add_category(items, category, provider):
    """Tag each result according to its own content, retaining search category as fallback."""
    tagged = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["category"] = infer_content_category(row, fallback=category)
        row["provider"] = provider
        tagged.append(row)
    return tagged


def display_result(item, index):
    """Render a normalized search result from any provider."""
    title = (
        item.get("title")
        or item.get("name")
        or item.get("original_title")
        or item.get("original_name")
        or "Untitled result"
    )
    description = (
        item.get("description")
        or item.get("overview")
        or item.get("content")
        or item.get("snippet")
        or item.get("text")
        or ""
    )
    url = item.get("url") or item.get("link") or item.get("web_url")
    category = item.get("category", "General Web")
    provider = item.get("provider", "Search")

    with st.container(border=True):
        st.markdown(f"### {index}. {title}")
        st.caption(f"Category: {category} · Source: {provider}")
        if description:
            st.write(str(description))

        source = item.get("source")
        if isinstance(source, dict):
            source = source.get("name")
        if source:
            st.caption(f"Publisher/source: {source}")

        published = item.get("publishedAt") or item.get("published_at") or item.get("release_date")
        if published:
            st.caption(f"Date: {published}")

        if url:
            st.markdown(f"[Open result]({url})")
        elif item.get("id") is not None:
            st.caption(f"Provider item ID: {item.get('id')}")


def run_provider_searches(searches):
    """Run each provider only for the searches routed to that provider."""
    news_searches = [s for s in searches if s.get("provider") == "gnews"]
    web_searches = [s for s in searches if s.get("provider") == "tavily"]
    media_searches = [s for s in searches if s.get("provider") == "tmdb"]

    raw_responses = {"news": [], "web": [], "media": []}
    errors = []

    if news_searches:
        try:
            response = process_news_searches(news_searches)
            raw_responses["news"] = response if isinstance(response, list) else [response]
        except Exception as exc:
            errors.append(f"GNews search failed: {exc}")

    if web_searches:
        try:
            response = process_web_searches(web_searches)
            raw_responses["web"] = response if isinstance(response, list) else [response]
        except Exception as exc:
            errors.append(f"Tavily web search failed: {exc}")

    if media_searches:
        try:
            response = process_media_searches(media_searches)
            raw_responses["media"] = response if isinstance(response, list) else [response]
        except Exception as exc:
            errors.append(f"TMDB media search failed: {exc}")

    news_items = []
    for response in raw_responses["news"]:
        error = service_error(response)
        if error:
            errors.append(f"GNews: {error}")
        items = get_result_items(response, ["articles", "results", "data"])
        category = response.get("category", "News") if isinstance(response, dict) else "News"
        news_items.extend(add_category(items, category, "GNews"))

    web_items = []
    for response in raw_responses["web"]:
        error = service_error(response)
        if error:
            errors.append(f"Tavily: {error}")
        items = get_result_items(response, ["results", "items", "data"])
        category = response.get("category", "General Web") if isinstance(response, dict) else "General Web"
        web_items.extend(add_category(items, category, "Tavily"))

    media_items = []
    for response in raw_responses["media"]:
        error = service_error(response)
        if error:
            errors.append(f"TMDB: {error}")
        items = get_result_items(response, ["results", "items", "data"])
        category = response.get("category", "Movies / TV") if isinstance(response, dict) else "Movies / TV"
        media_items.extend(add_category(items, category, "TMDB"))

    return news_items, web_items, media_items, errors


def deduplicate_results(items):
    """Remove duplicates by URL or provider ID while preserving order."""
    output = []
    seen = set()
    for item in items:
        key = item.get("url") or item.get("link")
        if not key:
            key = f"{item.get('provider')}:{item.get('id')}:{item.get('title') or item.get('name')}"
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


# ---------------------------------------------------------------------
# Search form
# ---------------------------------------------------------------------
with st.form("universal_search_form"):
    query = st.text_input(
        "What would you like to search?",
        placeholder=(
            "Examples: Today's rainfall in Tamil Nadu, Virat Kohli, "
            "Apple iPhone, Stranger Things, artificial intelligence"
        ),
    )
    use_rag = st.checkbox(
        "Save retrieved results to the local RAG knowledge base (if configured)",
        value=False,
    )
    submitted = st.form_submit_button(
        "Search with AI",
        type="primary",
        use_container_width=True,
    )


if submitted:
    query = query.strip()
    if not query:
        st.warning("Please enter a search query.")
    else:
        try:
            with st.spinner("AI is classifying your query and searching relevant sources..."):
                prepared = prepare_search(query)
                categories = prepared.get("categories", [])
                searches = prepared.get("searches", [])
                classification_warning = prepared.get("classification_warning")

                # Always try TMDB for the original query as well. Short names such
                # as "Vikram" can be ambiguous, and query classification may not
                # include Movies even when a matching film exists.
                if not any(item.get("provider") == "tmdb" for item in searches):
                    searches.append({
                        "category": "Movies",
                        "search_query": query,
                        "provider": "tmdb",
                    })

                news_items, web_items, media_items, errors = run_provider_searches(searches)

            st.subheader("Search understanding")
            col1, col2 = st.columns(2)
            col1.metric("Detected categories", len(categories))
            col2.metric("Prepared searches", len(searches))
            if categories:
                st.write("**Categories:** " + " · ".join(categories))
            st.caption(f"Search intent: {prepared.get('search_intent', 'general_search')}")
            if classification_warning:
                st.warning(classification_warning)

            with st.expander("Search plan", expanded=False):
                st.json(searches)

            if errors:
                with st.expander("Search warnings", expanded=True):
                    for error in errors:
                        st.warning(error)

            all_results = deduplicate_results(news_items + web_items + media_items)
            st.subheader(f"Search results ({len(all_results)})")

            if not all_results:
                st.info(
                    "No results were returned. Check your API keys, provider limits, "
                    "internet connection, and service response formats."
                )
            else:
                provider_counts = {
                    "News": len(news_items),
                    "Web": len(web_items),
                    "Movies / TV": len(media_items),
                }
                metric_cols = st.columns(3)
                for col, (label, count) in zip(metric_cols, provider_counts.items()):
                    col.metric(label, count)

                available_categories = sorted({
                    str(item.get("category", "General Web")) for item in all_results
                })
                selected_category = st.selectbox(
                    "Filter results by category",
                    ["All categories"] + available_categories,
                )
                selected_provider = st.selectbox(
                    "Filter results by source",
                    ["All sources", "GNews", "Tavily", "TMDB"],
                )
                filtered = [
                    item for item in all_results
                    if (selected_category == "All categories" or item.get("category") == selected_category)
                    and (selected_provider == "All sources" or item.get("provider") == selected_provider)
                ]
                st.caption(f"Showing {len(filtered)} of {len(all_results)} results.")

                for index, item in enumerate(filtered, start=1):
                    display_result(item, index)

                if use_rag:
                    if not RAG_AVAILABLE:
                        st.warning(
                            "RAG is not available because the vector-store module could not be imported. "
                            f"Details: {RAG_IMPORT_ERROR}"
                        )
                    else:
                        try:
                            with st.spinner("Preparing and saving results to the RAG knowledge base..."):
                                documents = (
                                    news_to_documents(news_items)
                                    + web_to_documents(web_items)
                                    + media_to_documents(media_items)
                                )
                                if documents:
                                    add_documents(documents)
                                    st.success(f"Saved {len(documents)} document(s) to the RAG knowledge base.")
                                else:
                                    st.info("There were no documents to save.")
                        except Exception as exc:
                            st.warning(f"Could not save results to RAG: {exc}")

        except Exception as exc:
            st.error(f"Search failed: {exc}")
            st.caption(
                "Check your API keys, Gemini model availability, provider service code, "
                "internet connection, and installed requirements."
            )


# ---------------------------------------------------------------------
# Optional semantic retrieval from existing RAG knowledge base
# ---------------------------------------------------------------------
st.divider()
st.subheader("🧠 Search saved knowledge (RAG)")
st.caption("Search previously saved documents using semantic similarity.")
with st.form("rag_search_form"):
    rag_query = st.text_input("Search the local knowledge base", key="rag_query")
    rag_k = st.slider("Number of similar documents", min_value=1, max_value=10, value=5)
    rag_submitted = st.form_submit_button("Search knowledge base")

if rag_submitted:
    if not rag_query.strip():
        st.warning("Enter a question or topic to search the knowledge base.")
    elif not RAG_AVAILABLE:
        st.warning(f"RAG is not available: {RAG_IMPORT_ERROR}")
    else:
        try:
            with st.spinner("Searching saved documents..."):
                similar = search_similar_documents(rag_query.strip(), k=rag_k)
            if not similar:
                st.info("No similar documents were found in the knowledge base.")
            else:
                for index, doc in enumerate(similar, start=1):
                    # Accommodate either LangChain Document objects or dict results.
                    if isinstance(doc, dict):
                        content = doc.get("page_content") or doc.get("content") or str(doc)
                        metadata = doc.get("metadata", {})
                    else:
                        content = getattr(doc, "page_content", str(doc))
                        metadata = getattr(doc, "metadata", {}) or {}
                    with st.container(border=True):
                        st.markdown(f"### Match {index}")
                        if metadata:
                            st.caption(json.dumps(metadata, ensure_ascii=False, default=str))
                        st.write(content)
        except Exception as exc:
            st.error(f"RAG search failed: {exc}")

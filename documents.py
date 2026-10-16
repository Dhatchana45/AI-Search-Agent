from typing import Any


def _text(value: Any) -> str:
    """APIs sometimes return None instead of ''. .get(k, '').strip() crashes on None."""
    return str(value or "").strip()


def create_document(
    title: str,
    content: str,
    source: str = "",
    url: str = "",
    category: str = "General",
    metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a standardized document from retrieved information."""

    document_metadata = metadata.copy() if metadata else {}

    document_metadata.update({
        "title": title,
        "source": source,
        "url": url,
        "category": category,
    })

    return {
        "page_content": f"{title}\n\n{content}".strip(),
        "metadata": document_metadata,
    }


def news_to_documents(
    articles: list[dict[str, Any]],
    category: str = "News"
) -> list[dict[str, Any]]:
    """Convert GNews articles into standardized documents."""

    documents = []

    for article in articles:
        title = _text(article.get("title"))
        description = _text(article.get("description"))
        content = _text(article.get("content"))

        combined_content = "\n\n".join(p for p in [description, content] if p)

        if not title and not combined_content:
            continue

        documents.append(
            create_document(
                title=title or "Untitled news article",
                content=combined_content,
                source=_text(article.get("source")) or "GNews",
                url=_text(article.get("url")),
                # FIX: use the result's own category (the old code always
                # stored "News"), so category filters in RAG work properly.
                category=article.get("category") or category,
                metadata={
                    "provider": article.get("provider", "gnews"),
                    "published_at": article.get("published_at", ""),
                    "image": article.get("image", ""),
                    "query": article.get("query", ""),
                },
            )
        )

    return documents


def web_to_documents(
    results: list[dict[str, Any]],
    category: str = "Web"
) -> list[dict[str, Any]]:
    """Convert Tavily web results into standardized documents."""

    documents = []

    for result in results:
        title = _text(result.get("title"))
        content = _text(result.get("content"))

        if not title and not content:
            continue

        documents.append(
            create_document(
                title=title or "Untitled web result",
                content=content,
                source=result.get("provider", "tavily"),
                url=_text(result.get("url")),
                category=result.get("category") or category,
                metadata={
                    "provider": result.get("provider", "tavily"),
                    "score": result.get("score", 0),
                    "published_date": result.get("published_date"),
                    "query": result.get("query", ""),
                },
            )
        )

    return documents


def media_to_documents(
    results: list[dict[str, Any]],
    category: str = "Entertainment"
) -> list[dict[str, Any]]:
    """Convert TMDB movie, TV and person results into standardized documents."""

    documents = []

    for result in results:
        title = _text(result.get("title") or result.get("name"))
        overview = _text(result.get("overview"))

        if not title and not overview:
            continue

        release_date = _text(result.get("release_date"))
        # FIX: media_search used to emit "vote_average" while this function
        # read "rating", so ratings were silently dropped.
        rating = result.get("rating", result.get("vote_average"))

        poster_url = result.get("poster_url")
        if not poster_url and result.get("poster_path"):
            poster_url = f"https://image.tmdb.org/t/p/w500{result['poster_path']}"

        content_parts = []
        if overview:
            content_parts.append(overview)
        if release_date:
            content_parts.append(f"Release date: {release_date}")
        if rating is not None:
            content_parts.append(f"Rating: {rating}")

        documents.append(
            create_document(
                title=title or "Untitled media result",
                content="\n".join(content_parts),
                source="TMDB",
                url=_text(result.get("url")),
                category=result.get("category") or category,
                metadata={
                    "provider": result.get("provider", "tmdb"),
                    "media_type": result.get("media_type", ""),
                    "rating": rating,
                    "release_date": release_date,
                    "poster_url": poster_url,
                    "query": result.get("query") or result.get("search_query", ""),
                },
            )
        )

    return documents


def combine_documents(
    news: list[dict[str, Any]] | None = None,
    web: list[dict[str, Any]] | None = None,
    media: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Convert and combine results from all search services."""

    documents = []
    documents.extend(news_to_documents(news or []))
    documents.extend(web_to_documents(web or []))
    documents.extend(media_to_documents(media or []))
    return documents
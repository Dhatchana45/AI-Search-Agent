import hashlib
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "chroma_db"

COLLECTION_NAME = "ai_search_documents"
EMBEDDING_MODEL = "models/gemini-embedding-001"


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Initialize Gemini embeddings.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. "
            "Add it to your .env file."
        )

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key
    )


def get_vector_store() -> Chroma:
    """
    Create or load the persistent Chroma vector store.
    """

    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(VECTOR_STORE_DIR)
    )


def _clean_metadata(
    metadata: dict[str, Any] | None
) -> dict[str, Any]:
    """
    Keep metadata compatible with Chroma.
    """

    cleaned = {}

    for key, value in (metadata or {}).items():
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            cleaned[str(key)] = value
        else:
            cleaned[str(key)] = str(value)

    return cleaned


def prepare_documents(
    documents: list[dict[str, Any]]
) -> list[Document]:
    """
    Convert dictionaries from rag/documents.py
    into LangChain Document objects.
    """

    prepared = []

    for item in documents:
        if not isinstance(item, dict):
            continue

        content = str(item.get("page_content", "")).strip()

        if not content:
            continue

        metadata = _clean_metadata(item.get("metadata"))

        prepared.append(
            Document(
                page_content=content,
                metadata=metadata
            )
        )

    return prepared


def _document_id(document: Document) -> str:
    """Stable ID from URL + content, so saving the same result twice updates
    it instead of storing a duplicate."""
    base = f"{document.metadata.get('url', '')}|{document.page_content}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def add_documents(
    documents: list[dict[str, Any]]
) -> int:
    """
    Embed and save documents into Chroma.
    Returns the number of unique documents saved.
    """

    prepared = prepare_documents(documents)

    if not prepared:
        return 0

    # De-duplicate inside this batch (Chroma rejects repeated IDs in one call).
    unique: dict[str, Document] = {}
    for document in prepared:
        unique[_document_id(document)] = document

    vector_store = get_vector_store()
    vector_store.add_documents(
        list(unique.values()),
        ids=list(unique.keys())
    )

    return len(unique)


def search_similar_documents(
    query: str,
    k: int = 5,
    category: str | None = None
) -> list[dict[str, Any]]:
    """
    Retrieve documents semantically similar to a query.

    Optionally filter results by category.
    """

    if not query or not query.strip():
        return []

    vector_store = get_vector_store()

    search_kwargs: dict[str, Any] = {
        "k": max(1, min(k, 20))
    }

    if category:
        search_kwargs["filter"] = {
            "category": category
        }

    matches = vector_store.similarity_search(
        query=query.strip(),
        **search_kwargs
    )

    results = []

    for document in matches:
        results.append({
            "page_content": document.page_content,
            "metadata": document.metadata
        })

    return results


def delete_collection() -> None:
    """
    Delete the local collection and its stored documents.

    WARNING: This removes all documents in this collection.
    """

    vector_store = get_vector_store()
    vector_store.delete_collection()
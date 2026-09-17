from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document

from aftermath.config import settings
from aftermath.data_loader import load_knowledge_corpus
from aftermath.embedding import documents_from_texts
from aftermath.llm import get_embeddings


_store: Chroma | None = None


def get_vector_store() -> Chroma:
    global _store

    if _store is None:
        _store = Chroma(
            collection_name="aftermath",
            embedding_function=get_embeddings(),
            persist_directory=str(settings.chroma_dir),
        )

    return _store


def index_documents(docs: list[Document]) -> int:
    if not docs:
        return 0

    store = get_vector_store()
    store.add_documents(docs)

    return len(docs)


def clear_user_uploads(user_id: str) -> int:
    """
    Delete uploaded document chunks belonging to a specific user.

    The source filter also catches uploads created before user_id
    metadata was added, such as the original demo test upload.
    """

    store = get_vector_store()

    result = store.get(
        where={
            "$and": [
                {"kind": "user_upload"},
                {
                    "$or": [
                        {"user_id": user_id},
                        {"source": f"upload-{user_id}.txt"},
                    ]
                },
            ]
        }
    )

    ids = result.get("ids", [])

    if ids:
        store.delete(ids=ids)

    return len(ids)


def ensure_knowledge_indexed() -> int:
    store = get_vector_store()

    existing = store.get()

    if existing and existing.get("ids"):
        return len(existing["ids"])

    pairs = load_knowledge_corpus()

    docs = documents_from_texts(
        pairs,
        kind="knowledge",
    )

    return index_documents(docs)
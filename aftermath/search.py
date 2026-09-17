from __future__ import annotations

from aftermath.config import settings
from aftermath.schemas import RetrievedChunk
from aftermath.vector_store import get_vector_store


def retrieve(
    query: str,
    k: int | None = None,
    user_id: str | None = None,
) -> list[RetrievedChunk]:
    """
    Search the built-in knowledge base and, when a user_id is provided,
    that user's uploaded documents.

    User-uploaded documents are isolated by user_id so one user's
    uploads cannot be retrieved for another user.
    """

    store = get_vector_store()
    k = k or settings.retrieve_k

    results = []

    # Always search the built-in knowledge base.
    knowledge_pairs = store.similarity_search_with_relevance_scores(
        query,
        k=k,
        filter={"kind": "knowledge"},
    )

    results.extend(knowledge_pairs)

    # Only search user-uploaded documents when we know the user.
    if user_id:
        user_pairs = store.similarity_search_with_relevance_scores(
            query,
            k=k,
            filter={
                "$and": [
                    {"kind": "user_upload"},
                    {"user_id": user_id},
                ]
            },
        )

        results.extend(user_pairs)

    # Keep only relevant results.
    filtered = [
        (doc, score)
        for doc, score in results
        if score >= settings.similarity_threshold
    ]

    # Highest relevance first.
    filtered.sort(
        key=lambda pair: float(pair[1]),
        reverse=True,
    )

    # Remove duplicate chunks if the same chunk somehow appears twice.
    seen = set()
    chunks: list[RetrievedChunk] = []

    for doc, score in filtered:
        source = str(
            doc.metadata.get(
                "source",
                "unknown",
            )
        )

        text = doc.page_content

        key = (
            source,
            text,
        )

        if key in seen:
            continue

        seen.add(key)

        chunks.append(
            RetrievedChunk(
                source=source,
                score=round(float(score), 3),
                preview=text[:300],
                text=text,
            )
        )

        if len(chunks) >= k:
            break

    return chunks
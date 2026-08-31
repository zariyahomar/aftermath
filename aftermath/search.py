from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

from aftermath.config import settings
from aftermath.llm import get_llm
from aftermath.schemas import RetrievedChunk
from aftermath.vector_store import get_vector_store


def retrieve(query: str, k: int | None = None) -> list[RetrievedChunk]:
    store = get_vector_store()
    k = k or settings.retrieve_k
    pairs = store.similarity_search_with_relevance_scores(query, k=k)
    chunks: list[RetrievedChunk] = []
    for doc, score in pairs:
        if score < settings.similarity_threshold:
            continue
        text = doc.page_content
        chunks.append(
            RetrievedChunk(
                source=str(doc.metadata.get("source", "unknown")),
                score=round(float(score), 3),
                preview=text[:300],
                text=text,
            )
        )
    return chunks


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No retrieved context above the similarity threshold."
    parts = []
    for c in chunks:
        parts.append(f"[{c.source} | score={c.score}]\n{c.text}")
    return "\n\n".join(parts)


def build_rag_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer using only the retrieved context. Cite source filenames. "
                "If context is missing, say you do not know. No new borrowing advice.\n\n{context}",
            ),
            ("human", "{question}"),
        ]
    )

    def retrieve_text(question: str) -> str:
        return _format_chunks(retrieve(question))

    return (
        RunnableParallel(
            {
                "context": retrieve_text,
                "question": RunnablePassthrough(),
            }
        )
        | prompt
        | get_llm(temperature=0.1)
        | StrOutputParser()
    )

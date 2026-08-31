from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from aftermath.config import settings


def split_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def documents_from_texts(pairs: list[tuple[str, str]], *, kind: str) -> list[Document]:
    docs: list[Document] = []
    for source, text in pairs:
        docs.append(
            Document(
                page_content=text,
                metadata={"source": source, "kind": kind},
            )
        )
    return split_documents(docs)

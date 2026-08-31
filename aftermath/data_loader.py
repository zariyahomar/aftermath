from pathlib import Path

from pypdf import PdfReader

from aftermath.config import settings


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"[page {i}]\n{text}")
    return "\n\n".join(pages)


def load_path(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return load_pdf(path)
    return load_text_file(path)


def load_knowledge_corpus() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    for path in sorted(settings.knowledge_dir.glob("*")):
        if path.suffix.lower() in {".md", ".txt", ".pdf"}:
            docs.append((path.name, load_path(path)))
    return docs

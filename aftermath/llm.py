from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from aftermath.config import settings


def get_llm(*, temperature: float = 0.2) -> ChatOpenAI:
    kwargs: dict = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key or "missing",
        "temperature": temperature,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def get_embeddings() -> OpenAIEmbeddings:
    kwargs: dict = {"api_key": settings.openai_api_key or "missing"}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAIEmbeddings(**kwargs)

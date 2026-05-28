from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


def create_llm(model: str | None = None) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model or settings.default_model,
        google_api_key=settings.google_api_key,
        max_output_tokens=4096,
        streaming=True,
    )

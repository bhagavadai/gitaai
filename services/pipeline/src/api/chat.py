"""Chat endpoint: retrieve relevant verses and generate answer with Claude."""

from __future__ import annotations

from typing import AsyncGenerator

import anthropic
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import settings
from ..retrieval.vector_search import search_verses

router = APIRouter()


def get_client():
    """Create the appropriate Anthropic client based on config."""
    if settings.llm_provider == "bedrock":
        kwargs = {"aws_region": settings.aws_region}
        if settings.aws_access_key_id:
            kwargs["aws_access_key"] = settings.aws_access_key_id
            kwargs["aws_secret_key"] = settings.aws_secret_access_key
        return anthropic.AnthropicBedrock(**kwargs)
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are GitaAI, a wise and knowledgeable guide to the Bhagavad Gita and Vedic philosophy.

Your role:
- Answer questions grounded in the Bhagavad Gita verses provided as context
- Always cite specific verses using the format [BG X.Y] (e.g., [BG 2.47])
- Include the Sanskrit transliteration when quoting a verse
- Explain concepts in clear, accessible language while preserving depth
- When the context doesn't contain enough information, say so honestly
- Present multiple perspectives when they exist
- Be respectful of the sacred nature of these texts

Guidelines:
- Start with a direct answer, then support it with verses
- Keep responses focused and well-structured
- Use the verse translations provided — do not make up or paraphrase verses
- If a question is outside the scope of the provided verses, acknowledge the limitation
"""


class ChatRequest(BaseModel):
    message: str
    n_verses: int = 5


class VerseContext(BaseModel):
    verse_id: str
    chapter_number: int
    verse_number: int
    sanskrit: str
    transliteration: str
    translation: str
    translator: str
    chapter_name: str


class ChatResponse(BaseModel):
    answer: str
    verses: list[VerseContext]


def format_context(verses: list[dict]) -> str:
    """Format retrieved verses into context for the LLM prompt."""
    parts = []
    for v in verses:
        parts.append(
            f"[BG {v['chapter_number']}.{v['verse_number']}] "
            f"(Chapter: {v['chapter_name']})\n"
            f"Sanskrit: {v['sanskrit']}\n"
            f"Transliteration: {v['transliteration']}\n"
            f"Translation ({v['translator']}): {v['translation']}"
        )
    return "\n\n---\n\n".join(parts)


async def generate_stream(message: str, verses: list[dict]) -> AsyncGenerator[str, None]:
    """Stream the LLM response."""
    client = get_client()

    context = format_context(verses)
    user_message = (
        f"Here are relevant Bhagavad Gita verses:\n\n{context}\n\n"
        f"---\n\nUser question: {message}"
    )

    with client.messages.stream(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        temperature=settings.temperature,
    ) as stream:
        for text in stream.text_stream:
            yield text


@router.post("/chat")
async def chat(request: ChatRequest):
    """Retrieve relevant verses and stream a Claude-generated answer."""
    verses = search_verses(request.message, n_results=request.n_verses)

    async def stream_response():
        # First, send the verses as JSON on the first line
        import json
        yield json.dumps({"verses": [VerseContext(**v).model_dump() for v in verses]}) + "\n"

        # Then stream the answer text
        async for chunk in generate_stream(request.message, verses):
            yield chunk

    return StreamingResponse(stream_response(), media_type="text/plain")


@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """Non-streaming version for testing."""
    verses = search_verses(request.message, n_results=request.n_verses)

    client = get_client()

    context = format_context(verses)
    user_message = (
        f"Here are relevant Bhagavad Gita verses:\n\n{context}\n\n"
        f"---\n\nUser question: {request.message}"
    )

    response = client.messages.create(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        temperature=settings.temperature,
    )

    return ChatResponse(
        answer=response.content[0].text,
        verses=[VerseContext(**v) for v in verses],
    )

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

SYSTEM_PROMPT = """You are GitaAI — a warm, wise companion who helps people find guidance in the Bhagavad Gita.

How to respond:
- Talk like a thoughtful friend, not a professor. Be natural, warm, and human.
- Give practical, heartfelt advice that connects the Gita's wisdom to the person's real life.
- Write in flowing paragraphs, not bullet points or headers. Keep it conversational.
- Use simple, accessible language. Avoid jargon unless explaining a concept.
- Be concise — aim for 3-5 short paragraphs. Don't over-explain.
- DO NOT include verse citations, numbers, or references inline in your answer. The UI shows verses separately — your job is just the wisdom, naturally expressed.
- DO NOT use markdown formatting (no ##, no **, no bullet lists). Just plain, warm text.
- You may weave in a short Sanskrit phrase naturally (like "nishkama karma" or "sthitaprajna") if it enriches the answer, but don't force it.
- If the provided verses don't fully address the question, share what wisdom you can and be honest about limitations.
- Never fabricate or invent verses.
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

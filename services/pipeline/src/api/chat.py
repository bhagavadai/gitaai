"""Chat endpoint: retrieve relevant verses and stream LLM answer."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

import anthropic
import openai
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import settings
from ..graph.traversal import get_concept_context
from ..retrieval.vector_search import search_verses

logger = logging.getLogger(__name__)
router = APIRouter()

_OPENAI_PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "groq_api_key"),
    "google": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "google_api_key",
    ),
    "openrouter": ("https://openrouter.ai/api/v1", "openrouter_api_key"),
}


def _get_openai_client():
    """Create OpenAI-compatible client for Groq, Google, or OpenRouter."""
    provider = settings.llm_provider
    base_url, key_attr = _OPENAI_PROVIDERS[provider]
    return openai.OpenAI(
        base_url=base_url,
        api_key=getattr(settings, key_attr),
    )


def _get_anthropic_client():
    """Create Anthropic client (direct or Bedrock)."""
    if settings.llm_provider == "bedrock":
        kwargs = {"aws_region": settings.aws_region}
        if settings.aws_access_key_id:
            kwargs["aws_access_key"] = settings.aws_access_key_id
            kwargs["aws_secret_key"] = settings.aws_secret_access_key
        return anthropic.AnthropicBedrock(**kwargs)
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


SYSTEM_PROMPT_EN = (
    "You are GitaAI — a warm, wise companion who helps people "
    "find guidance in the Bhagavad Gita.\n\n"
    "How to respond:\n"
    "- Talk like a thoughtful friend, not a professor. "
    "Be natural, warm, and human.\n"
    "- Give practical, heartfelt advice that connects the Gita's "
    "wisdom to the person's real life.\n"
    "- Write in flowing paragraphs, not bullet points or headers. "
    "Keep it conversational.\n"
    "- Use simple, accessible language. Avoid jargon unless "
    "explaining a concept.\n"
    "- Be concise — aim for 3-5 short paragraphs. Don't over-explain.\n"
    "- DO NOT include verse citations, numbers, or references inline "
    "in your answer. The UI shows verses separately — your job is "
    "just the wisdom, naturally expressed.\n"
    "- DO NOT use markdown formatting (no ##, no **, no bullet lists). "
    "Just plain, warm text.\n"
    "- You may weave in a short Sanskrit phrase naturally "
    '(like "nishkama karma" or "sthitaprajna") if it enriches '
    "the answer, but don't force it.\n"
    "- If the provided verses don't fully address the question, "
    "share what wisdom you can and be honest about limitations.\n"
    "- Never fabricate or invent verses."
)

SYSTEM_PROMPT_HI = (
    "तुम GitaAI हो — एक गर्मजोशी भरा, बुद्धिमान साथी "
    "जो लोगों को भगवद्गीता में मार्गदर्शन खोजने में मदद करता है।\n\n"
    "कैसे जवाब दें:\n"
    "- एक सोच-समझकर बोलने वाले दोस्त की तरह बात करो, "
    "किसी प्रोफेसर की तरह नहीं। स्वाभाविक, गर्मजोशी भरा और मानवीय रहो।\n"
    "- व्यावहारिक, दिल से सलाह दो "
    "जो गीता की बुद्धि को व्यक्ति के असल जीवन से जोड़े।\n"
    "- बहती हुई भाषा में लिखो, बुलेट पॉइंट्स या हेडिंग्स नहीं। "
    "बातचीत जैसा रखो।\n"
    "- सरल, सुलभ हिंदी का प्रयोग करो। "
    "जहाँ जरूरी हो वहाँ संस्कृत शब्द स्वाभाविक रूप से इस्तेमाल करो।\n"
    "- संक्षिप्त रहो — 3-5 छोटे पैराग्राफ। ज्यादा विस्तार मत करो।\n"
    "- जवाब में श्लोक संख्या या संदर्भ मत डालो। "
    "UI अलग से श्लोक दिखाता है — "
    "तुम्हारा काम सिर्फ ज्ञान देना है, स्वाभाविक रूप से।\n"
    "- Markdown formatting मत करो "
    "(no ##, no **, no bullet lists)। सादा, गर्मजोशी भरा text।\n"
    "- श्लोक गढ़ो या बनाओ मत।"
)


class ChatRequest(BaseModel):
    message: str
    language: str = "auto"  # "en", "hi", or "auto" (detect from message)
    n_verses: int = 5


class VerseContext(BaseModel):
    verse_id: str
    chapter_number: int
    verse_number: int
    sanskrit: str
    transliteration: str
    translation: str
    translator: str
    translation_hindi: str = ""
    translator_hindi: str = ""
    chapter_name: str


class ChatResponse(BaseModel):
    answer: str
    verses: list[VerseContext]
    language: str


def detect_language(text: str) -> str:
    """Simple detection: if text contains Devanagari characters, it's Hindi."""
    for char in text:
        if "\u0900" <= char <= "\u097f":
            return "hi"
    return "en"


def format_context(verses: list[dict], language: str) -> str:
    """Format retrieved verses into context for the LLM prompt."""
    parts = []
    for v in verses:
        translation = v["translation"]
        translator = v["translator"]
        if language == "hi" and v.get("translation_hindi"):
            translation = v["translation_hindi"]
            translator = v.get("translator_hindi", translator)

        parts.append(
            f"[BG {v['chapter_number']}.{v['verse_number']}] "
            f"(Chapter: {v['chapter_name']})\n"
            f"Sanskrit: {v['sanskrit']}\n"
            f"Transliteration: {v['transliteration']}\n"
            f"Translation ({translator}): {translation}"
        )
    return "\n\n---\n\n".join(parts)


def get_system_prompt(language: str) -> str:
    if language == "hi":
        return SYSTEM_PROMPT_HI
    return SYSTEM_PROMPT_EN


def _build_user_message(
    message: str, verses: list[dict], language: str, graph_context: str = ""
) -> str:
    """Build the full user message with verse context."""
    context = format_context(verses, language)
    parts = [f"Here are relevant Bhagavad Gita verses:\n\n{context}"]
    if graph_context:
        parts.append(f"Knowledge graph context:\n\n{graph_context}")
    parts.append(f"User question: {message}")
    return "\n\n---\n\n".join(parts)


async def _stream_openai_compat(user_message: str, language: str) -> AsyncGenerator[str, None]:
    """Stream via OpenAI-compatible API (Groq, Google, OpenRouter)."""
    client = _get_openai_client()
    stream = client.chat.completions.create(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        messages=[
            {"role": "system", "content": get_system_prompt(language)},
            {"role": "user", "content": user_message},
        ],
        temperature=settings.temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def _stream_anthropic(user_message: str, language: str) -> AsyncGenerator[str, None]:
    """Stream via Anthropic (direct or Bedrock)."""
    client = _get_anthropic_client()
    with client.messages.stream(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        system=get_system_prompt(language),
        messages=[{"role": "user", "content": user_message}],
        temperature=settings.temperature,
    ) as stream:
        for text in stream.text_stream:
            yield text


async def generate_stream(
    message: str, verses: list[dict], language: str, graph_context: str = ""
) -> AsyncGenerator[str, None]:
    """Stream the LLM response using the configured provider."""
    user_message = _build_user_message(message, verses, language, graph_context)

    if settings.llm_provider in _OPENAI_PROVIDERS:
        async for text in _stream_openai_compat(user_message, language):
            yield text
    else:
        async for text in _stream_anthropic(user_message, language):
            yield text


class ConceptInfo(BaseModel):
    id: str
    name: str
    sanskrit_term: str
    category: str
    description: str
    description_hindi: str = ""


@router.post("/chat")
async def chat(request: ChatRequest):
    """Retrieve relevant verses via hybrid search (vector + graph) and stream answer."""
    language = request.language
    if language == "auto":
        language = detect_language(request.message)

    # Vector search
    verses = search_verses(request.message, n_results=request.n_verses)

    # Graph context (concepts, relationships, key verses) — graceful fallback
    try:
        graph_result = get_concept_context(request.message)
    except Exception:
        graph_result = {}
    graph_context = graph_result.get("graph_context", "")

    # Boost retrieval with graph-suggested key verses not already in vector results
    vector_ids = {v["verse_id"] for v in verses}
    for gv in graph_result.get("key_verses", []):
        if gv["verse_id"] not in vector_ids:
            # Search for this specific verse to get full metadata
            from_vector = search_verses(gv["verse_id"], n_results=1)
            if from_vector:
                verses.append(from_vector[0])
                vector_ids.add(gv["verse_id"])
            if len(verses) >= request.n_verses + 3:
                break

    # Build concept list for frontend
    matched_concepts = [
        ConceptInfo(**c).model_dump() for c in graph_result.get("matched_concepts", [])
    ]
    related_concepts = []
    seen_ids = {c["id"] for c in matched_concepts}
    for rc in graph_result.get("related_concepts", []):
        if rc["id"] not in seen_ids:
            seen_ids.add(rc["id"])
            related_concepts.append(ConceptInfo(**rc).model_dump())

    async def stream_response():
        verse_data = [VerseContext(**v).model_dump() for v in verses]
        yield (
            json.dumps(
                {
                    "verses": verse_data,
                    "language": language,
                    "concepts": matched_concepts,
                    "related_concepts": related_concepts,
                }
            )
            + "\n"
        )

        async for chunk in generate_stream(request.message, verses, language, graph_context):
            yield chunk

    return StreamingResponse(stream_response(), media_type="text/plain")


@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """Non-streaming version for testing."""
    language = request.language
    if language == "auto":
        language = detect_language(request.message)

    verses = search_verses(request.message, n_results=request.n_verses)
    try:
        graph_result = get_concept_context(request.message)
    except Exception:
        graph_result = {}
    graph_context = graph_result.get("graph_context", "")

    user_message = _build_user_message(request.message, verses, language, graph_context)

    if settings.llm_provider in _OPENAI_PROVIDERS:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=settings.model_name,
            max_tokens=settings.max_tokens,
            messages=[
                {"role": "system", "content": get_system_prompt(language)},
                {"role": "user", "content": user_message},
            ],
            temperature=settings.temperature,
        )
        answer = response.choices[0].message.content
    else:
        client = _get_anthropic_client()
        response = client.messages.create(
            model=settings.model_name,
            max_tokens=settings.max_tokens,
            system=get_system_prompt(language),
            messages=[{"role": "user", "content": user_message}],
            temperature=settings.temperature,
        )
        answer = response.content[0].text

    return ChatResponse(
        answer=answer,
        verses=[VerseContext(**v) for v in verses],
        language=language,
    )

"""Resilient Multi-Provider LLM Factory with automatic fallback across 100% free models."""

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from whisperer.config import settings

logger = logging.getLogger("whisperer.agents.llm_factory")


def get_resilient_llm(temperature: float = 0.5) -> BaseChatModel:
    """Create a resilient, zero-cost LLM chain with automatic fallback across free models.
    
    Tier 1: Google Gemini 2.5 Flash (Primary Key)
    Tier 2: Google Gemini 2.5 Flash (Backup Key)
    Tier 3: OpenRouter Free Model (nvidia/nemotron-3.5-lightning:free)
    """
    models = []

    # Tier 1: Primary Google Gemini
    if settings.GOOGLE_API_KEY:
        try:
            gemini_primary = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=temperature,
                max_retries=1,
            )
            models.append(gemini_primary)
        except Exception as e:
            logger.warning("Could not initialize primary Google Gemini LLM: %s", e)

    # Tier 2: Backup Google Gemini Key
    if settings.GOOGLE_API_KEY_BACKUP and settings.GOOGLE_API_KEY_BACKUP != settings.GOOGLE_API_KEY:
        try:
            gemini_backup = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY_BACKUP,
                temperature=temperature,
                max_retries=1,
            )
            models.append(gemini_backup)
        except Exception as e:
            logger.warning("Could not initialize backup Google Gemini LLM: %s", e)

    # Tier 3: OpenRouter Free Model
    if settings.OPENROUTER_API_KEY:
        try:
            openrouter_free = ChatOpenAI(
                model=settings.OPENROUTER_MODEL,
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_retries=1,
            )
            models.append(openrouter_free)
        except Exception as e:
            logger.warning("Could not initialize OpenRouter free LLM: %s", e)

    if not models:
        raise ValueError("No LLM API keys found. Set GOOGLE_API_KEY or OPENROUTER_API_KEY in .env")

    # If multiple free tiers available, chain with LangChain's native with_fallbacks()
    if len(models) > 1:
        primary = models[0]
        fallbacks = models[1:]
        logger.info(
            "Configured resilient free LLM chain: Primary=%s with %d fallback tier(s)",
            type(primary).__name__,
            len(fallbacks),
        )
        return primary.with_fallbacks(fallbacks)

    return models[0]

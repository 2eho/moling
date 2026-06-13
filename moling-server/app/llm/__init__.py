"""
墨灵 (Moling) — LLM Integration Package.

Provides a unified asynchronous LLM client (OpenAI-compatible) and
a prompt template library organised by generation scenario.
"""

from app.llm.client import LLMClient, llm_client
from app.llm.prompts import PromptLibrary

__all__ = [
    "LLMClient",
    "llm_client",
    "PromptLibrary",
]

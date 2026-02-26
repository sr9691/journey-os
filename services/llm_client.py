# =============================================================================
# LLM Client Wrappers
# =============================================================================
#
# Provides async wrappers for LLM API calls used by CIS agents.
#
# Phase 3: ClaudeClient for intent analysis via Anthropic API.
# Phase 5: GeminiClient for email generation via Google Generative AI API.
#
# All clients use httpx directly (no SDK dependencies) and provide
# structured responses via complete_json() or plain text via complete_text().
# =============================================================================

import json
import logging
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Raised when an LLM API call fails."""

    def __init__(self, message: str, provider: str = "unknown"):
        self.provider = provider
        super().__init__(message)


# =============================================================================
# Claude Client (Anthropic Messages API)
# =============================================================================

class ClaudeClient:
    """Async wrapper for the Anthropic Messages API.

    Uses httpx directly (no SDK dependency) for a minimal footprint.
    Provides complete_json() for structured JSON responses.
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self.max_tokens = max_tokens or settings.anthropic_max_tokens
        self.timeout = timeout or settings.api_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ClaudeClient":
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION,
                "content-type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "ClaudeClient must be used as async context manager: "
                "async with ClaudeClient() as claude:"
            )
        return self._client

    async def complete_json(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Send a message and parse the response as JSON.

        Args:
            system: System prompt instructing Claude's behavior.
            user_message: The user message containing data to analyze.
            temperature: Sampling temperature (low = more deterministic).

        Returns:
            Parsed JSON dict from Claude's response.

        Raises:
            LLMClientError: If the API call fails or response isn't valid JSON.
        """

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [
                {"role": "user", "content": user_message},
            ],
        }

        try:
            response = await self.client.post(self.API_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract text from the first content block
            content_blocks = data.get("content", [])
            if not content_blocks:
                raise LLMClientError("Empty response from Claude", provider="anthropic")

            text = content_blocks[0].get("text", "")

            # Parse JSON from the response \u2014 handle markdown code fences
            json_text = _extract_json(text)
            result = json.loads(json_text)

            logger.info(
                "Claude API call successful",
                extra={
                    "model": data.get("model"),
                    "input_tokens": data.get("usage", {}).get("input_tokens"),
                    "output_tokens": data.get("usage", {}).get("output_tokens"),
                },
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Claude API HTTP error: {e.response.status_code}")
            raise LLMClientError(
                f"Claude API returned {e.response.status_code}: {e.response.text[:200]}",
                provider="anthropic",
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Claude API request failed: {e}")
            raise LLMClientError(
                f"Claude API request failed: {e}",
                provider="anthropic",
            ) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            raise LLMClientError(
                f"Claude response was not valid JSON: {e}",
                provider="anthropic",
            ) from e


# =============================================================================
# Gemini Client (Google Generative AI API)
# =============================================================================

class GeminiClient:
    """Async wrapper for the Google Gemini API.

    Uses httpx directly (no SDK dependency) for a minimal footprint.
    Provides complete_text() for plain-text email generation and
    complete_json() for structured JSON responses.
    """

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.max_tokens = max_tokens or settings.gemini_max_tokens
        self.timeout = timeout or settings.api_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GeminiClient":
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"content-type": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "GeminiClient must be used as async context manager: "
                "async with GeminiClient() as gemini:"
            )
        return self._client

    async def complete_text(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.7,
    ) -> str:
        """Send a message and return the response as plain text.

        Args:
            system: System instruction guiding Gemini's behavior.
            user_message: The user message containing data/instructions.
            temperature: Sampling temperature (higher = more creative).

        Returns:
            Plain text response from Gemini.

        Raises:
            LLMClientError: If the API call fails.
        """

        url = f"{self.API_URL}/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}],
                },
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract text from first candidate
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMClientError("Empty response from Gemini", provider="gemini")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise LLMClientError("No content parts in Gemini response", provider="gemini")

            text = parts[0].get("text", "")

            logger.info(
                "Gemini API call successful",
                extra={
                    "model": self.model,
                    "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount"),
                    "output_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount"),
                },
            )

            return text

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API HTTP error: {e.response.status_code}")
            raise LLMClientError(
                f"Gemini API returned {e.response.status_code}: {e.response.text[:200]}",
                provider="gemini",
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Gemini API request failed: {e}")
            raise LLMClientError(
                f"Gemini API request failed: {e}",
                provider="gemini",
            ) from e

    async def complete_json(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Send a message and parse the response as JSON.

        Returns:
            Parsed JSON dict from Gemini's response.

        Raises:
            LLMClientError: If the API call fails or response isn't valid JSON.
        """
        text = await self.complete_text(system, user_message, temperature)

        try:
            json_text = _extract_json(text)
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            raise LLMClientError(
                f"Gemini response was not valid JSON: {e}",
                provider="gemini",
            ) from e


# =============================================================================
# Helpers
# =============================================================================

def _extract_json(text: str) -> str:
    """Extract JSON from a response that may be wrapped in markdown code fences."""
    text = text.strip()

    # Strip ```json ... ``` fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()

    return text

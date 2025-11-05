"""LLM connector using LiteLLM for unified API access."""

import time
from dataclasses import dataclass
from typing import List, Optional

import litellm

from config.settings import is_provider_enabled


@dataclass
class LLMResponse:
    """Response from LLM call."""

    text: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    error: Optional[str] = None
    original_model: Optional[str] = None  # If fallback was used
    fallback_reason: Optional[str] = None  # Why fallback was triggered


class LLMConnector:
    """Unified LLM connector using LiteLLM."""

    def __init__(self, retry_count: int = 1):
        self.retry_count = retry_count
        # Disable LiteLLM logging
        litellm.suppress_debug_info = True

    def _extract_provider(self, model: str) -> str:
        """
        Extract provider name from model string.

        Maps LiteLLM model prefixes to canonical provider names.
        Example: "gemini/gemini-2.5-pro" → "google"
        """
        prefix = model.split("/")[0] if "/" in model else "unknown"

        # Map LiteLLM prefixes to canonical provider names
        provider_map = {
            "gemini": "google",  # gemini/* models use GOOGLE_API_KEY
        }

        return provider_map.get(prefix, prefix)

    def _try_model(
        self,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: int,
        start_time: float,
    ) -> tuple[Optional[LLMResponse], Optional[str]]:
        """
        Try calling a specific model.

        Returns:
            Tuple of (LLMResponse if successful, error_reason if failed)
        """
        provider = self._extract_provider(model)

        # Check if provider is enabled
        if not is_provider_enabled(provider):
            return None, f"Missing API key for provider '{provider}'"

        # Try calling the model
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                duration_ms = (time.perf_counter() - start_time) * 1000

                # Extract text
                text = response.choices[0].message.content

                # Check for empty/filtered content
                if text is None or (isinstance(text, str) and not text.strip()):
                    # Check finish_reason for filtering
                    finish_reason = response.choices[0].finish_reason if hasattr(response.choices[0], 'finish_reason') else None

                    if finish_reason in ['content_filter', 'safety']:
                        return None, f"Content filtered by provider (reason: {finish_reason})"
                    elif completion_tokens := (response.usage.completion_tokens if response.usage else 0):
                        # Model generated tokens but returned empty content - unusual
                        return None, f"Empty response despite {completion_tokens} completion tokens (possible content filter)"
                    else:
                        return None, "Empty response from model"

                # Extract usage
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                total_tokens = usage.total_tokens if usage else 0

                return (
                    LLMResponse(
                        text=text,
                        model=model,
                        provider=provider,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        duration_ms=duration_ms,
                    ),
                    None,
                )

            except Exception as e:
                error_str = str(e).lower()
                last_error = str(e)

                # Check if error is due to missing API key or auth
                if any(
                    keyword in error_str
                    for keyword in ["api key", "authentication", "unauthorized", "auth"]
                ):
                    # Provider unavailable - don't retry
                    return None, f"Authentication failed for provider '{provider}'"

                # Other errors - retry
                if attempt < self.retry_count:
                    time.sleep(1)
                    continue

        # All retries failed
        return None, f"Model call failed after {self.retry_count + 1} attempts: {last_error}"

    def call(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        fallback_order: Optional[List[str]] = None,
    ) -> LLMResponse:
        """
        Call LLM with retry logic and fallback support.

        Args:
            model: Model identifier (e.g., "openai/gpt-4o-mini")
            system: System prompt
            user: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            fallback_order: List of fallback models to try if primary fails

        Returns:
            LLMResponse with text and metadata
        """
        start_time = time.perf_counter()
        original_model = model

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        # Build list of models to try (primary + fallbacks)
        models_to_try = [model]
        if fallback_order:
            models_to_try.extend(fallback_order)

        first_error = None  # Track primary model error
        last_error = None   # Track most recent error
        for idx, current_model in enumerate(models_to_try):
            # Try this model
            result, error_reason = self._try_model(
                model=current_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                start_time=start_time,
            )

            if result:
                # Success! Add fallback metadata if we used a fallback
                if idx > 0:
                    result.original_model = original_model
                    # Use the error from the PRIMARY model (idx == 0)
                    result.fallback_reason = first_error or "Primary model unavailable"
                return result

            # This model failed, track reason
            error = error_reason or f"Model '{current_model}' failed"
            last_error = error

            # Save the first error (primary model failure reason)
            if idx == 0:
                first_error = error

        # All models exhausted - return error
        duration_ms = (time.perf_counter() - start_time) * 1000
        provider = self._extract_provider(original_model)

        return LLMResponse(
            text="",
            model=original_model,
            provider=provider,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=duration_ms,
            error=f"All models failed. Last error: {last_error}",
        )

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
        """Extract provider name from model string."""
        return model.split("/")[0] if "/" in model else "unknown"

    def _try_model(
        self,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: int,
        start_time: float,
    ) -> Optional[LLMResponse]:
        """
        Try calling a specific model.

        Returns:
            LLMResponse if successful, None if provider unavailable
        """
        provider = self._extract_provider(model)

        # Check if provider is enabled
        if not is_provider_enabled(provider):
            return None

        # Try calling the model
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

                # Extract usage
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                total_tokens = usage.total_tokens if usage else 0

                return LLMResponse(
                    text=text,
                    model=model,
                    provider=provider,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                error_str = str(e).lower()
                # Check if error is due to missing API key or auth
                if any(
                    keyword in error_str
                    for keyword in ["api key", "authentication", "unauthorized", "auth"]
                ):
                    # Provider unavailable - don't retry
                    return None

                # Other errors - retry
                if attempt < self.retry_count:
                    time.sleep(1)
                    continue

        # All retries failed
        return None

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

        last_error = None
        for idx, current_model in enumerate(models_to_try):
            provider = self._extract_provider(current_model)

            # Try this model
            result = self._try_model(
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
                    result.fallback_reason = f"Provider '{self._extract_provider(original_model)}' unavailable"
                return result

            # This model failed, track reason
            if not is_provider_enabled(provider):
                last_error = f"Provider '{provider}' disabled or missing API key"
            else:
                last_error = f"Model '{current_model}' failed"

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

"""LLM connector using LiteLLM for unified API access."""
import time
from dataclasses import dataclass
from typing import Optional

import litellm


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


class LLMConnector:
    """Unified LLM connector using LiteLLM."""

    def __init__(self, retry_count: int = 1):
        self.retry_count = retry_count
        # Disable LiteLLM logging
        litellm.suppress_debug_info = True

    def call(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """
        Call LLM with retry logic.

        Args:
            model: Model identifier (e.g., "openai/gpt-4o-mini")
            system: System prompt
            user: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with text and metadata
        """
        start_time = time.perf_counter()
        last_error = None

        for attempt in range(self.retry_count + 1):
            try:
                response = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
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

                # Extract provider from model string
                provider = model.split("/")[0] if "/" in model else "unknown"

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
                last_error = str(e)
                if attempt < self.retry_count:
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    # Final attempt failed
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    provider = model.split("/")[0] if "/" in model else "unknown"

                    return LLMResponse(
                        text="",
                        model=model,
                        provider=provider,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        duration_ms=duration_ms,
                        error=last_error,
                    )

        # Should never reach here
        return LLMResponse(
            text="",
            model=model,
            provider="unknown",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=0,
            error="Unknown error",
        )

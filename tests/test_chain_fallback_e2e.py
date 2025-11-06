"""End-to-end tests for chain execution with fallback."""

import os
from unittest.mock import MagicMock, patch


from core.agent_runtime import AgentRuntime


class TestChainFallbackE2E:
    """Test end-to-end chain execution with provider fallback."""

    @patch("core.llm_connector.litellm.completion")
    @patch("core.llm_connector.is_provider_enabled")
    def test_chain_completes_with_anthropic_disabled(
        self, mock_enabled, mock_completion
    ):
        """Test full chain execution when Anthropic is disabled."""

        # Setup: Anthropic disabled, OpenAI and Google enabled
        def provider_check(provider):
            return provider in ["openai", "google"]

        mock_enabled.side_effect = provider_check

        # Mock LiteLLM responses for different stages
        def completion_side_effect(*args, **kwargs):
            model = kwargs.get("model")
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]

            if "gpt-4o" in model:
                mock_response.choices[0].message.content = "Builder output (OpenAI)"
            elif "gemini" in model:
                mock_response.choices[0].message.content = "Critic output (Google)"
            else:
                mock_response.choices[0].message.content = "Generic output"

            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            return mock_response

        mock_completion.side_effect = completion_side_effect

        # Execute chain
        runtime = AgentRuntime()
        results = runtime.chain(
            prompt="Test chain with Anthropic disabled",
            stages=["builder", "critic", "closer"],
        )

        # Assert: Chain completed successfully
        # v0.9.0+: builder → individual critics → multi-critic consensus → closer (4 results)
        assert len(results) == 4
        assert all(r.error is None for r in results)

        # Assert: Fallbacks were used (builder uses Anthropic by default)
        builder_result = results[0]
        assert builder_result.agent == "builder"
        # Builder should have fallen back from Anthropic to OpenAI
        assert "openai" in builder_result.model or "gpt" in builder_result.model

    @patch("core.llm_connector.litellm.completion")
    @patch("core.llm_connector.is_provider_enabled")
    def test_single_agent_with_fallback(self, mock_enabled, mock_completion):
        """Test single agent execution with fallback."""

        # Setup: Anthropic disabled, OpenAI enabled
        def provider_check(provider):
            return provider == "openai"

        mock_enabled.side_effect = provider_check

        # Mock successful OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenAI fallback response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_completion.return_value = mock_response

        # Execute single agent (builder defaults to Anthropic)
        runtime = AgentRuntime()
        result = runtime.run(agent="builder", prompt="Test prompt")

        # Assert: Execution succeeded with fallback
        assert result.error is None
        assert "openai" in result.provider.lower()
        assert result.original_model is not None  # Fallback was used
        assert "anthropic" in result.original_model

    @patch("core.llm_connector.litellm.completion")
    @patch("core.llm_connector.is_provider_enabled")
    def test_auto_routing_with_fallback(self, mock_enabled, mock_completion):
        """Test auto-routing when router provider is disabled."""

        # Setup: OpenAI disabled initially, Google enabled
        call_count = [0]

        def provider_check(provider):
            call_count[0] += 1
            # First call (router) - OpenAI disabled, falls back to Google
            # Second call (builder) - All enabled
            if call_count[0] <= 2:
                return provider == "google"
            return True

        mock_enabled.side_effect = provider_check

        # Mock responses
        def completion_side_effect(*args, **kwargs):
            messages = kwargs.get("messages", [])
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]

            # Router call - returns agent name
            if any("routing agent" in str(m).lower() for m in messages):
                mock_response.choices[0].message.content = "builder"
            else:
                # Builder call
                mock_response.choices[0].message.content = "Builder response"

            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            return mock_response

        mock_completion.side_effect = completion_side_effect

        # Execute with auto routing
        runtime = AgentRuntime()
        result = runtime.run(agent="auto", prompt="Create a function")

        # Assert: Auto-routing succeeded
        assert result.error is None
        assert result.agent == "builder"

    @patch("core.llm_connector.is_provider_enabled")
    def test_all_providers_fail_returns_error(self, mock_enabled):
        """Test graceful error when all providers unavailable."""

        # Setup: All providers disabled
        mock_enabled.return_value = False

        # Execute
        runtime = AgentRuntime()
        result = runtime.run(agent="builder", prompt="Test prompt")

        # Assert: Error returned, system doesn't crash
        assert result.error is not None
        assert "failed" in result.error.lower()

    @patch.dict(
        os.environ,
        {
            "DISABLE_ANTHROPIC": "1",
            "OPENAI_API_KEY": "sk-test",
            "GOOGLE_API_KEY": "test",
        },
        clear=False,
    )
    @patch("core.llm_connector.litellm.completion")
    def test_feature_flag_integration(self, mock_completion):
        """Test DISABLE_ANTHROPIC flag in full runtime."""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback success"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_completion.return_value = mock_response

        # Execute (should fallback from Anthropic)
        runtime = AgentRuntime()
        result = runtime.run(agent="builder", prompt="Test")

        # Assert: Anthropic not used
        assert "anthropic" not in result.provider.lower()
        assert result.error is None

    @patch("core.llm_connector.litellm.completion")
    @patch("core.llm_connector.is_provider_enabled")
    def test_override_model_skips_fallback(self, mock_enabled, mock_completion):
        """Test model override bypasses fallback logic."""

        # Setup: Anthropic disabled
        mock_enabled.side_effect = lambda p: p == "google"

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Override response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_completion.return_value = mock_response

        # Execute with override (Google model)
        runtime = AgentRuntime()
        result = runtime.run(
            agent="builder",
            prompt="Test",
            override_model="gemini/gemini-2.5-pro",
        )

        # Assert: Override used, no fallback metadata
        assert result.model == "gemini/gemini-2.5-pro"
        assert result.original_model is None  # No fallback used

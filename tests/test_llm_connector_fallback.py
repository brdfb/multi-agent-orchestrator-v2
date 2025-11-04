"""Test LLMConnector fallback logic."""

import os
from unittest.mock import MagicMock, patch


from core.llm_connector import LLMConnector


class TestLLMConnectorFallback:
    """Test fallback functionality in LLMConnector."""

    def setup_method(self):
        """Setup test environment."""
        self.connector = LLMConnector(retry_count=0)

    @patch("core.llm_connector.is_provider_enabled")
    @patch("core.llm_connector.litellm.completion")
    def test_primary_model_success_no_fallback(self, mock_completion, mock_enabled):
        """Test primary model succeeds, no fallback needed."""
        # Setup: All providers enabled
        mock_enabled.return_value = True

        # Mock successful LiteLLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_completion.return_value = mock_response

        # Call with no fallback
        result = self.connector.call(
            model="openai/gpt-4o-mini",
            system="Test system",
            user="Test user",
        )

        # Assert: Primary model used, no fallback
        assert result.model == "openai/gpt-4o-mini"
        assert result.text == "Test response"
        assert result.original_model is None
        assert result.fallback_reason is None
        assert result.error is None

    @patch("core.llm_connector.is_provider_enabled")
    @patch("core.llm_connector.litellm.completion")
    def test_primary_disabled_fallback_succeeds(self, mock_completion, mock_enabled):
        """Test primary provider disabled, fallback succeeds."""

        # Setup: Anthropic disabled, OpenAI enabled
        def provider_check(provider):
            return provider == "openai"

        mock_enabled.side_effect = provider_check

        # Mock successful LiteLLM response for fallback
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_completion.return_value = mock_response

        # Call with fallback
        result = self.connector.call(
            model="anthropic/claude-3-5-sonnet-20241022",
            system="Test system",
            user="Test user",
            fallback_order=["openai/gpt-4o-mini"],
        )

        # Assert: Fallback model used
        assert result.model == "openai/gpt-4o-mini"
        assert result.text == "Fallback response"
        assert result.original_model == "anthropic/claude-3-5-sonnet-20241022"
        assert "anthropic" in result.fallback_reason.lower()
        assert result.error is None

    @patch("core.llm_connector.is_provider_enabled")
    def test_all_providers_disabled_returns_error(self, mock_enabled):
        """Test all providers disabled, return error."""
        # Setup: All providers disabled
        mock_enabled.return_value = False

        # Call with fallback
        result = self.connector.call(
            model="anthropic/claude-3-5-sonnet-20241022",
            system="Test system",
            user="Test user",
            fallback_order=["openai/gpt-4o-mini", "google/gemini-1.5-pro"],
        )

        # Assert: Error returned
        assert result.text == ""
        assert result.error is not None
        assert "failed" in result.error.lower()

    @patch("core.llm_connector.is_provider_enabled")
    @patch("core.llm_connector.litellm.completion")
    def test_primary_auth_error_triggers_fallback(self, mock_completion, mock_enabled):
        """Test API key error triggers fallback."""

        # Setup: All providers enabled
        mock_enabled.return_value = True

        # Mock: First call fails with auth error, second succeeds
        def completion_side_effect(*args, **kwargs):
            model = kwargs.get("model")
            if "anthropic" in model:
                raise Exception("Authentication failed - invalid api key")
            else:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Fallback response"
                mock_response.usage.prompt_tokens = 10
                mock_response.usage.completion_tokens = 20
                mock_response.usage.total_tokens = 30
                return mock_response

        mock_completion.side_effect = completion_side_effect

        # Call with fallback
        result = self.connector.call(
            model="anthropic/claude-3-5-sonnet-20241022",
            system="Test system",
            user="Test user",
            fallback_order=["openai/gpt-4o-mini"],
        )

        # Assert: Fallback used due to auth error
        assert result.model == "openai/gpt-4o-mini"
        assert result.text == "Fallback response"
        assert result.original_model == "anthropic/claude-3-5-sonnet-20241022"

    @patch("core.llm_connector.is_provider_enabled")
    @patch("core.llm_connector.litellm.completion")
    def test_fallback_chain_exhaustion(self, mock_completion, mock_enabled):
        """Test all models in fallback chain fail."""
        # Setup: All providers enabled
        mock_enabled.return_value = True

        # Mock: All calls fail with non-auth errors (e.g., rate limit)
        mock_completion.side_effect = Exception("Rate limit exceeded")

        # Call with multiple fallbacks
        result = self.connector.call(
            model="anthropic/claude-3-5-sonnet-20241022",
            system="Test system",
            user="Test user",
            fallback_order=["openai/gpt-4o-mini", "google/gemini-1.5-pro"],
        )

        # Assert: Error after all fallbacks exhausted
        assert result.text == ""
        assert result.error is not None

    @patch.dict(os.environ, {"DISABLE_ANTHROPIC": "1"}, clear=False)
    def test_feature_flag_disables_provider(self):
        """Test DISABLE_ANTHROPIC environment variable."""
        from config.settings import is_provider_enabled

        # Assert: Anthropic is disabled
        assert not is_provider_enabled("anthropic")

    @patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "sk-test", "GOOGLE_API_KEY": "test"},
        clear=True,
    )
    def test_available_providers_without_anthropic(self):
        """Test get_available_providers when Anthropic key missing."""
        from config.settings import get_available_providers

        available = get_available_providers()

        # Assert: Only OpenAI and Google available
        assert "openai" in available
        assert "google" in available
        assert "anthropic" not in available

"""Test agent_runner.py CLI script."""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Lazy imports to avoid dependency issues during test collection
# Functions will be imported inside test functions when needed


class TestPathValidation:
    """Test path validation functions."""

    def test_validate_path_basic_allows_normal_file(self, tmp_path):
        """Test that normal files are allowed."""
        from scripts.agent_runner import validate_path_basic
        
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")
        
        result = validate_path_basic(str(test_file))
        assert result == test_file.resolve()

    def test_validate_path_basic_blocks_env_file(self, tmp_path):
        """Test that .env files are blocked."""
        from scripts.agent_runner import validate_path_basic
        
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=test")
        
        with pytest.raises(SystemExit) as exc_info:
            validate_path_basic(str(env_file))
        assert exc_info.value.code == 1

    def test_validate_path_basic_blocks_git_directory(self, tmp_path):
        """Test that .git directories are blocked."""
        from scripts.agent_runner import validate_path_basic
        
        git_file = tmp_path / ".git" / "config"
        git_file.parent.mkdir()
        git_file.write_text("[core]")
        
        with pytest.raises(SystemExit) as exc_info:
            validate_path_basic(str(git_file))
        assert exc_info.value.code == 1

    def test_validate_path_basic_blocks_ssh_files(self, tmp_path):
        """Test that SSH files are blocked."""
        from scripts.agent_runner import validate_path_basic
        
        ssh_file = tmp_path / "id_rsa"
        ssh_file.write_text("private key")
        
        with pytest.raises(SystemExit) as exc_info:
            validate_path_basic(str(ssh_file))
        assert exc_info.value.code == 1

    def test_validate_path_basic_blocks_credentials(self, tmp_path):
        """Test that credential files are blocked."""
        from scripts.agent_runner import validate_path_basic
        
        cred_file = tmp_path / "credentials.json"
        cred_file.write_text('{"key": "value"}')
        
        with pytest.raises(SystemExit) as exc_info:
            validate_path_basic(str(cred_file))
        assert exc_info.value.code == 1

    def test_validate_path_basic_warns_outside_cwd(self, tmp_path, capsys):
        """Test that files outside CWD are warned but allowed."""
        from scripts.agent_runner import validate_path_basic
        
        # Create file in temp directory (outside CWD)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("# Test")
            temp_file = Path(f.name)
        
        try:
            result = validate_path_basic(str(temp_file))
            assert result == temp_file.resolve()
            
            # Check warning was printed
            captured = capsys.readouterr()
            assert "Reading outside project" in captured.out or "outside" in captured.out.lower()
        finally:
            temp_file.unlink()


class TestFileReading:
    """Test file reading functions."""

    def test_read_file_with_validation_success(self, tmp_path):
        """Test successful file read."""
        from scripts.agent_runner import read_file_with_validation
        
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test content")
        
        content = read_file_with_validation(str(test_file))
        assert content == "# Test content"

    def test_read_file_with_validation_not_found(self, tmp_path):
        """Test file not found error."""
        from scripts.agent_runner import read_file_with_validation
        
        missing_file = tmp_path / "missing.md"
        
        with pytest.raises(SystemExit) as exc_info:
            read_file_with_validation(str(missing_file))
        assert exc_info.value.code == 1

    def test_read_file_with_validation_directory(self, tmp_path):
        """Test that directories are rejected."""
        from scripts.agent_runner import read_file_with_validation
        
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        with pytest.raises(SystemExit) as exc_info:
            read_file_with_validation(str(test_dir))
        assert exc_info.value.code == 1

    def test_read_file_with_validation_size_limit(self, tmp_path):
        """Test file size limit (10MB)."""
        from scripts.agent_runner import read_file_with_validation
        
        # Create file larger than 10MB
        large_file = tmp_path / "large.txt"
        # Write 11MB of data
        with open(large_file, 'wb') as f:
            f.write(b'x' * (11 * 1024 * 1024))
        
        with pytest.raises(SystemExit) as exc_info:
            read_file_with_validation(str(large_file))
        assert exc_info.value.code == 1

    def test_read_file_with_validation_utf8_encoding(self, tmp_path):
        """Test UTF-8 encoding handling."""
        from scripts.agent_runner import read_file_with_validation
        
        test_file = tmp_path / "test.txt"
        # Write UTF-8 content
        test_file.write_text("Test: 测试 🚀", encoding='utf-8')
        
        content = read_file_with_validation(str(test_file))
        assert "测试" in content
        assert "🚀" in content


class TestCostEstimation:
    """Test cost estimation functions."""

    def test_estimate_input_cost_with_tiktoken(self):
        """Test cost estimation with tiktoken."""
        from scripts.agent_runner import estimate_input_cost
        
        text = "This is a test prompt with some content."
        tokens, cost = estimate_input_cost(text, "gpt-4o")
        
        assert tokens > 0
        assert cost > 0
        # Rough check: cost should be proportional to tokens
        assert cost < 0.01  # Should be very small for short text

    def test_estimate_input_cost_fallback(self, monkeypatch):
        """Test cost estimation fallback when tiktoken not available."""
        from scripts.agent_runner import estimate_input_cost
        
        # Mock tiktoken import failure
        import sys
        original_import = __import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'tiktoken':
                raise ImportError("tiktoken not available")
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr('builtins.__import__', mock_import)
        
        text = "Test"
        tokens, cost = estimate_input_cost(text, "gpt-4o")
        
        # Fallback uses len(text) // 4
        assert tokens == len(text) // 4
        assert cost > 0


class TestErrorHandling:
    """Test error handling and solution display."""

    def test_show_error_with_solution_api_key(self, capsys):
        """Test API key error solution."""
        from scripts.agent_runner import show_error_with_solution
        
        show_error_with_solution("Missing API key")
        captured = capsys.readouterr()
        assert "Solution" in captured.out
        assert ".env" in captured.out
        assert "ANTHROPIC_API_KEY" in captured.out

    def test_show_error_with_solution_model_not_found(self, capsys):
        """Test model not found error solution."""
        from scripts.agent_runner import show_error_with_solution
        
        show_error_with_solution("Model not found")
        captured = capsys.readouterr()
        assert "Solution" in captured.out
        assert "claude-sonnet-4-5" in captured.out or "gpt-4o" in captured.out

    def test_show_error_with_solution_rate_limit(self, capsys):
        """Test rate limit error solution."""
        from scripts.agent_runner import show_error_with_solution
        
        show_error_with_solution("Rate limit exceeded (429)")
        captured = capsys.readouterr()
        assert "Solution" in captured.out
        assert "30-60 seconds" in captured.out

    def test_show_error_with_solution_network(self, capsys):
        """Test network error solution."""
        from scripts.agent_runner import show_error_with_solution
        
        show_error_with_solution("Network connection failed")
        captured = capsys.readouterr()
        assert "Solution" in captured.out
        assert "internet connection" in captured.out.lower()

    def test_show_error_with_solution_timeout(self, capsys):
        """Test timeout error solution."""
        from scripts.agent_runner import show_error_with_solution
        
        show_error_with_solution("Request timeout")
        captured = capsys.readouterr()
        assert "Solution" in captured.out
        assert "simplifying" in captured.out.lower() or "complex" in captured.out.lower()

    def test_show_error_with_solution_generic(self, capsys):
        """Test generic error solution."""
        from scripts.agent_runner import show_error_with_solution
        
        show_error_with_solution("Unknown error occurred")
        captured = capsys.readouterr()
        assert "Need Help" in captured.out or "Troubleshooting" in captured.out


class TestCLIIntegration:
    """Test CLI integration with mocked AgentRuntime."""

    @patch('scripts.agent_runner.AgentRuntime')
    @patch('scripts.agent_runner.get_session_manager')
    def test_cli_with_file_input(self, mock_session, mock_runtime_class, tmp_path, capsys):
        """Test CLI with --file flag."""
        # Create test file
        test_file = tmp_path / "prompt.md"
        test_file.write_text("Create a REST API")
        
        # Mock runtime
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        # Mock session manager
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        # Mock result
        from core.agent_runtime import RunResult
        mock_result = RunResult(
            agent="builder",
            model="anthropic/claude-sonnet-4-5",
            provider="anthropic",
            prompt="Create a REST API",
            response="Here's a REST API...",
            duration_ms=1000.0,
            prompt_tokens=10,
            completion_tokens=50,
            total_tokens=60,
            timestamp="2024-01-01T00:00:00",
            log_file="test.json",
        )
        mock_runtime.run.return_value = mock_result
        
        # Import and run main
        from scripts.agent_runner import main
        import sys
        
        # Set argv for test
        original_argv = sys.argv
        try:
            sys.argv = ['agent_runner.py', 'builder', '--file', str(test_file)]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify runtime.run was called with correct prompt
        mock_runtime.run.assert_called_once()
        call_args = mock_runtime.run.call_args
        assert call_args[1]['agent'] == 'builder'
        assert 'Create a REST API' in call_args[1]['prompt']

    @patch('scripts.agent_runner.AgentRuntime')
    @patch('scripts.agent_runner.get_session_manager')
    def test_cli_with_save_to(self, mock_session, mock_runtime_class, tmp_path):
        """Test CLI with --save-to flag."""
        # Create test file
        test_file = tmp_path / "prompt.md"
        test_file.write_text("Test prompt")
        output_file = tmp_path / "output.md"
        
        # Mock runtime
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        # Mock session manager
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        # Mock result
        from core.agent_runtime import RunResult
        mock_result = RunResult(
            agent="builder",
            model="anthropic/claude-sonnet-4-5",
            provider="anthropic",
            prompt="Test prompt",
            response="Test response",
            duration_ms=1000.0,
            prompt_tokens=10,
            completion_tokens=50,
            total_tokens=60,
            timestamp="2024-01-01T00:00:00",
            log_file="test.json",
        )
        mock_runtime.run.return_value = mock_result
        
        # Import and run main
        from scripts.agent_runner import main
        import sys
        
        # Set argv for test
        original_argv = sys.argv
        try:
            sys.argv = ['agent_runner.py', 'builder', 'Test prompt', '--save-to', str(output_file)]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify file was saved
        assert output_file.exists()
        assert "Test response" in output_file.read_text()

    @patch('scripts.agent_runner.AgentRuntime')
    @patch('scripts.agent_runner.get_session_manager')
    @patch('scripts.agent_runner.is_provider_enabled')
    def test_cli_with_model_override(self, mock_provider_enabled, mock_session, mock_runtime_class):
        """Test CLI with --model flag."""
        # Mock provider as enabled
        mock_provider_enabled.return_value = True
        
        # Mock runtime
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        # Mock session manager
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        # Mock result
        from core.agent_runtime import RunResult
        mock_result = RunResult(
            agent="builder",
            model="openai/gpt-4o",
            provider="openai",
            prompt="Test",
            response="Response",
            duration_ms=1000.0,
            prompt_tokens=10,
            completion_tokens=50,
            total_tokens=60,
            timestamp="2024-01-01T00:00:00",
            log_file="test.json",
        )
        mock_runtime.run.return_value = mock_result
        
        # Import and run main
        from scripts.agent_runner import main
        import sys
        
        # Set argv for test
        original_argv = sys.argv
        try:
            sys.argv = ['agent_runner.py', 'builder', 'Test', '--model', 'openai/gpt-4o']
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify model override was passed
        assert mock_runtime.run.called, "run() should have been called"
        call_args = mock_runtime.run.call_args
        # call_args is a tuple: (args, kwargs) or MockCall object
        if call_args:
            # Try to get kwargs
            if hasattr(call_args, 'kwargs'):
                kwargs = call_args.kwargs
            elif isinstance(call_args, tuple) and len(call_args) > 1:
                kwargs = call_args[1]
            else:
                kwargs = {}
            assert kwargs.get('override_model') == 'openai/gpt-4o', f"Expected override_model='openai/gpt-4o', got {kwargs.get('override_model')}"

    @patch('scripts.agent_runner.AgentRuntime')
    @patch('scripts.agent_runner.get_session_manager')
    def test_cli_with_max_usd_guardrail(self, mock_session, mock_runtime_class, capsys):
        """Test CLI with --max-usd guardrail."""
        # Mock runtime (should not be called if guardrail triggers)
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        # Mock session manager
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        # Import and run main
        from scripts.agent_runner import main
        import sys
        
        # Set argv for test with large prompt that exceeds cost
        original_argv = sys.argv
        try:
            # Create a large prompt (will have high token count)
            large_prompt = "Test " * 10000  # ~5000 tokens
            sys.argv = ['agent_runner.py', 'builder', large_prompt, '--max-usd', '0.01']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        # Verify runtime.run was NOT called (guardrail triggered)
        mock_runtime.run.assert_not_called()
        
        # Verify error message
        captured = capsys.readouterr()
        assert "exceeds budget" in captured.out.lower() or "exceeds limit" in captured.out.lower()

    @patch('scripts.agent_runner.AgentRuntime')
    @patch('scripts.agent_runner.get_session_manager')
    def test_cli_with_max_input_tokens_guardrail(self, mock_session, mock_runtime_class, capsys):
        """Test CLI with --max-input-tokens guardrail."""
        # Mock runtime (should not be called if guardrail triggers)
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        # Mock session manager
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        # Import and run main
        from scripts.agent_runner import main
        import sys
        
        # Set argv for test with large prompt
        original_argv = sys.argv
        try:
            large_prompt = "Test " * 1000  # ~500 tokens
            sys.argv = ['agent_runner.py', 'builder', large_prompt, '--max-input-tokens', '100']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        # Verify runtime.run was NOT called
        mock_runtime.run.assert_not_called()
        
        # Verify error message
        captured = capsys.readouterr()
        assert "exceeds limit" in captured.out.lower()

    @patch('scripts.agent_runner.AgentRuntime')
    @patch('scripts.agent_runner.get_session_manager')
    def test_cli_with_force_bypass(self, mock_session, mock_runtime_class, capsys):
        """Test CLI with --force flag bypasses guardrails."""
        # Mock runtime
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        # Mock session manager
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        # Mock result
        from core.agent_runtime import RunResult
        mock_result = RunResult(
            agent="builder",
            model="anthropic/claude-sonnet-4-5",
            provider="anthropic",
            prompt="Test",
            response="Response",
            duration_ms=1000.0,
            prompt_tokens=10,
            completion_tokens=50,
            total_tokens=60,
            timestamp="2024-01-01T00:00:00",
            log_file="test.json",
        )
        mock_runtime.run.return_value = mock_result
        
        # Import and run main
        from scripts.agent_runner import main
        import sys
        
        # Set argv for test with --force
        original_argv = sys.argv
        try:
            large_prompt = "Test " * 1000
            sys.argv = ['agent_runner.py', 'builder', large_prompt, '--max-input-tokens', '100', '--force']
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify runtime.run WAS called (force bypassed guardrail)
        mock_runtime.run.assert_called_once()
        
        # Verify warning was printed
        captured = capsys.readouterr()
        assert "FORCE" in captured.out or "Bypassing" in captured.out


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_prompt_error(self, capsys):
        """Test that empty prompt is rejected."""
        from scripts.agent_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['agent_runner.py', 'builder', '']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        captured = capsys.readouterr()
        # Error message can be "empty" or "must provide either prompt or --file"
        assert "empty" in captured.out.lower() or "must provide" in captured.out.lower() or "prompt" in captured.out.lower()

    def test_missing_prompt_and_file_error(self, capsys):
        """Test that missing both prompt and --file is rejected."""
        from scripts.agent_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['agent_runner.py', 'builder']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        captured = capsys.readouterr()
        assert "prompt" in captured.out.lower() or "file" in captured.out.lower()

    def test_invalid_agent_error(self, capsys):
        """Test that invalid agent is rejected."""
        from scripts.agent_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['agent_runner.py', 'invalid_agent', 'Test']
            main()
        except SystemExit as e:
            assert e.code == 2  # argparse error
        finally:
            sys.argv = original_argv


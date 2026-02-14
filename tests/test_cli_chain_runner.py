"""Test chain_runner.py CLI script."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Lazy imports to avoid dependency issues during test collection


class TestChainRunnerFileIO:
    """Test file I/O in chain runner."""

    def test_chain_runner_reads_file(self, tmp_path):
        """Test that chain runner reads file correctly."""
        from scripts.chain_runner import read_file_with_validation
        
        test_file = tmp_path / "design.md"
        test_file.write_text("# Design Document\n\nCreate a REST API")
        
        content = read_file_with_validation(str(test_file))
        assert "Design Document" in content
        assert "REST API" in content

    def test_chain_runner_saves_output(self, tmp_path):
        """Test that chain runner saves output to file."""
        output_file = tmp_path / "output.md"
        
        # Mock the chain execution
        from core.agent_runtime import RunResult
        
        mock_results = [
            RunResult(
                agent="builder",
                model="test/model",
                provider="test",
                prompt="test",
                response="builder response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test1.json",
            ),
            RunResult(
                agent="critic",
                model="test/model",
                provider="test",
                prompt="test",
                response="critic response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test2.json",
            ),
            RunResult(
                agent="closer",
                model="test/model",
                provider="test",
                prompt="test",
                response="closer response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test3.json",
            ),
        ]
        
        # Test save functionality directly
        from scripts.chain_runner import main
        import sys
        
        with patch('scripts.chain_runner.AgentRuntime') as mock_runtime_class, \
             patch('scripts.chain_runner.get_session_manager') as mock_session:
            
            mock_runtime = MagicMock()
            mock_runtime_class.return_value = mock_runtime
            mock_runtime.chain.return_value = mock_results
            
            mock_session_manager = MagicMock()
            mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
            mock_session.return_value = mock_session_manager
            
            original_argv = sys.argv
            try:
                sys.argv = ['chain_runner.py', 'Test prompt', '--save-to', str(output_file)]
                main()
            except SystemExit:
                pass
            finally:
                sys.argv = original_argv
        
        # Verify file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "Chain Execution Report" in content
        assert "builder response" in content
        assert "critic response" in content
        assert "closer response" in content


class TestChainRunnerCostGuardrails:
    """Test cost guardrails in chain runner."""

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    def test_chain_runner_max_usd_guardrail(self, mock_session, mock_runtime_class, capsys):
        """Test that chain runner respects --max-usd guardrail."""
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            # Large prompt that will exceed cost
            large_prompt = "Test " * 10000
            sys.argv = ['chain_runner.py', large_prompt, '--max-usd', '0.01']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        # Verify chain was NOT called
        mock_runtime.chain.assert_not_called()
        
        # Verify error message
        captured = capsys.readouterr()
        assert "exceeds budget" in captured.out.lower() or "exceeds limit" in captured.out.lower()

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    def test_chain_runner_force_bypass(self, mock_session, mock_runtime_class):
        """Test that --force bypasses guardrails in chain runner."""
        from core.agent_runtime import RunResult
        
        mock_results = [
            RunResult(
                agent="builder",
                model="test/model",
                provider="test",
                prompt="test",
                response="response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test.json",
            ),
        ]
        
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        mock_runtime.chain.return_value = mock_results
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            large_prompt = "Test " * 1000
            sys.argv = ['chain_runner.py', large_prompt, '--max-input-tokens', '100', '--force']
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify chain WAS called (force bypassed)
        mock_runtime.chain.assert_called_once()


class TestChainRunnerCustomStages:
    """Test custom stage specification."""

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    def test_chain_runner_custom_stages(self, mock_session, mock_runtime_class):
        """Test that custom stages are used."""
        from core.agent_runtime import RunResult
        
        mock_results = [
            RunResult(
                agent="builder",
                model="test/model",
                provider="test",
                prompt="test",
                response="response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test.json",
            ),
            RunResult(
                agent="critic",
                model="test/model",
                provider="test",
                prompt="test",
                response="response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test.json",
            ),
        ]
        
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        mock_runtime.chain.return_value = mock_results
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['chain_runner.py', 'Test', 'builder', 'critic']
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify chain was called with custom stages
        call_args = mock_runtime.chain.call_args
        assert call_args[1]['stages'] == ['builder', 'critic']

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    def test_chain_runner_invalid_stage_error(self, mock_session, mock_runtime_class, capsys):
        """Test that invalid stage names are rejected."""
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['chain_runner.py', 'Test', 'invalid_agent']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        # Verify chain was NOT called
        mock_runtime.chain.assert_not_called()
        
        # Verify error message
        captured = capsys.readouterr()
        assert "invalid" in captured.out.lower() or "Invalid agent" in captured.out


class TestChainRunnerInteractiveMode:
    """Test interactive mode."""

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    @patch('builtins.input')
    def test_chain_runner_interactive_mode(self, mock_input, mock_session, mock_runtime_class):
        """Test interactive mode when no args provided."""
        from core.agent_runtime import RunResult
        
        mock_input.return_value = "Test prompt"
        
        mock_results = [
            RunResult(
                agent="builder",
                model="test/model",
                provider="test",
                prompt="Test prompt",
                response="response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test.json",
            ),
        ]
        
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        mock_runtime.chain.return_value = mock_results
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['chain_runner.py']  # No args = interactive
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify input was called
        mock_input.assert_called_once()
        
        # Verify chain was called with input prompt
        call_args = mock_runtime.chain.call_args
        assert call_args[1]['prompt'] == "Test prompt"

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    @patch('builtins.input')
    def test_chain_runner_interactive_empty_prompt(self, mock_input, mock_session, mock_runtime_class, capsys):
        """Test that empty prompt in interactive mode is rejected."""
        mock_input.return_value = ""  # Empty prompt
        
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['chain_runner.py']
            main()
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.argv = original_argv
        
        # Verify chain was NOT called
        mock_runtime.chain.assert_not_called()
        
        # Verify error message
        captured = capsys.readouterr()
        assert "empty" in captured.out.lower()


class TestChainRunnerModelOverride:
    """Test model override in chain runner."""

    @patch('scripts.chain_runner.AgentRuntime')
    @patch('scripts.chain_runner.get_session_manager')
    @patch('scripts.chain_runner.is_provider_enabled')
    def test_chain_runner_model_override(self, mock_provider_enabled, mock_session, mock_runtime_class):
        """Test that model override is passed to chain."""
        from core.agent_runtime import RunResult
        
        # Mock provider as enabled
        mock_provider_enabled.return_value = True
        
        mock_results = [
            RunResult(
                agent="builder",
                model="openai/gpt-4o",
                provider="openai",
                prompt="test",
                response="response",
                duration_ms=100.0,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                timestamp="2024-01-01T00:00:00",
                log_file="test.json",
            ),
        ]
        
        mock_runtime = MagicMock()
        mock_runtime_class.return_value = mock_runtime
        mock_runtime.chain.return_value = mock_results
        
        mock_session_manager = MagicMock()
        mock_session_manager.get_or_create_session.return_value = "cli-12345-test"
        mock_session.return_value = mock_session_manager
        
        from scripts.chain_runner import main
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['chain_runner.py', 'Test', '--model', 'openai/gpt-4o']
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify model override was passed
        assert mock_runtime.chain.called, "chain() should have been called"
        call_args = mock_runtime.chain.call_args
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


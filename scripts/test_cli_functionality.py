#!/usr/bin/env python3
"""
CLI Functionality Test Script
Tests what actually works in the WSL environment without making real API calls.
"""
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

class CLITester:
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.base_dir = Path(__file__).parent.parent
        
    def test(self, name: str, test_func):
        """Run a test and record results."""
        print(f"\n{BLUE}Testing: {name}{RESET}")
        try:
            result, message = test_func()
            self.results.append((name, result, message))
            if result:
                print(f"{GREEN}✓ PASSED{RESET}: {message}")
            else:
                print(f"{RED}✗ FAILED{RESET}: {message}")
        except Exception as e:
            self.results.append((name, False, f"Exception: {str(e)}"))
            print(f"{RED}✗ ERROR{RESET}: {str(e)}")
    
    def run_command(self, cmd: List[str], check_output: bool = True) -> Tuple[bool, str]:
        """Run a command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip() or "Command executed successfully"
            else:
                return False, result.stderr.strip() or result.stdout.strip() or f"Exit code: {result.returncode}"
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def test_help_commands(self):
        """Test that help commands work."""
        tests = [
            ("agent_runner --help", ["python", "scripts/agent_runner.py", "--help"]),
            ("chain_runner --help", ["python", "scripts/chain_runner.py", "--help"]),
        ]
        
        for name, cmd in tests:
            self.test(f"Help: {name}", lambda c=cmd: self.run_command(c))
    
    def test_argument_parsing(self):
        """Test argument parsing without making API calls."""
        # Test missing required arguments
        self.test(
            "agent_runner: missing prompt",
            lambda: self.run_command(["python", "scripts/agent_runner.py", "builder"])
        )
        
        self.test(
            "chain_runner: missing prompt",
            lambda: self.run_command(["python", "scripts/chain_runner.py"])
        )
        
        # Test invalid agent
        self.test(
            "agent_runner: invalid agent",
            lambda: self.run_command(["python", "scripts/agent_runner.py", "invalid", "test"])
        )
    
    def test_file_operations(self):
        """Test file reading/writing operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Create test files
            test_file = tmp_path / "test_prompt.md"
            test_file.write_text("# Test Prompt\n\nThis is a test prompt.")
            
            blocked_file = tmp_path / ".env"
            blocked_file.write_text("SECRET=value")
            
            # Test reading valid file
            self.test(
                "agent_runner: read from file",
                lambda: self.run_command([
                    "python", "scripts/agent_runner.py", "builder",
                    "--file", str(test_file)
                ])
            )
            
            # Test blocked file
            self.test(
                "agent_runner: block .env file",
                lambda: self.run_command([
                    "python", "scripts/agent_runner.py", "builder",
                    "--file", str(blocked_file)
                ])
            )
            
            # Test save-to (will fail at API call, but should create file structure)
            output_file = tmp_path / "output.md"
            self.test(
                "agent_runner: --save-to argument",
                lambda: self.run_command([
                    "python", "scripts/agent_runner.py", "builder", "test",
                    "--save-to", str(output_file)
                ])
            )
    
    def test_cost_guardrails(self):
        """Test cost guardrails (should fail before API call)."""
        # Test max-input-tokens
        large_prompt = "test " * 1000  # ~500 tokens
        self.test(
            "agent_runner: max-input-tokens guardrail",
            lambda: self.run_command([
                "python", "scripts/agent_runner.py", "builder", large_prompt,
                "--max-input-tokens", "100"
            ])
        )
        
        # Test max-usd
        self.test(
            "agent_runner: max-usd guardrail",
            lambda: self.run_command([
                "python", "scripts/agent_runner.py", "builder", large_prompt,
                "--max-usd", "0.001"
            ])
        )
    
    def test_model_override(self):
        """Test model override argument parsing."""
        # This will fail at provider check or API call, but should parse correctly
        self.test(
            "agent_runner: --model argument parsing",
            lambda: self.run_command([
                "python", "scripts/agent_runner.py", "builder", "test",
                "--model", "openai/gpt-4o"
            ])
        )
        
        self.test(
            "chain_runner: --model argument parsing",
            lambda: self.run_command([
                "python", "scripts/chain_runner.py", "test",
                "--model", "openai/gpt-4o"
            ])
        )
    
    def test_chain_runner_features(self):
        """Test chain runner specific features."""
        # Test custom stages
        self.test(
            "chain_runner: custom stages",
            lambda: self.run_command([
                "python", "scripts/chain_runner.py", "test",
                "builder", "critic"
            ])
        )
        
        # Test invalid stage
        self.test(
            "chain_runner: invalid stage",
            lambda: self.run_command([
                "python", "scripts/chain_runner.py", "test",
                "invalid_stage"
            ])
        )
    
    def test_script_imports(self):
        """Test that scripts can be imported without errors."""
        self.test(
            "Import: agent_runner",
            lambda: self.run_command([
                "python", "-c", "import sys; sys.path.insert(0, '.'); from scripts.agent_runner import main; print('Import successful')"
            ])
        )
        
        self.test(
            "Import: chain_runner",
            lambda: self.run_command([
                "python", "-c", "import sys; sys.path.insert(0, '.'); from scripts.chain_runner import main; print('Import successful')"
            ])
        )
    
    def test_environment_check(self):
        """Check environment setup."""
        # Check Python version
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True
        )
        self.test(
            "Environment: Python available",
            lambda: (result.returncode == 0, result.stdout.strip())
        )
        
        # Check if venv is activated
        import sys
        venv_active = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        self.test(
            "Environment: Virtual environment",
            lambda: (venv_active, "Venv active" if venv_active else "Venv not active")
        )
        
        # Check required modules
        modules = ['rich', 'litellm', 'fastapi']
        for module in modules:
            try:
                __import__(module)
                self.test(
                    f"Environment: {module} module",
                    lambda m=module: (True, f"{m} is installed")
                )
            except ImportError:
                self.test(
                    f"Environment: {module} module",
                    lambda m=module: (False, f"{m} is NOT installed")
                )
    
    def test_configuration(self):
        """Test configuration loading."""
        self.test(
            "Config: Load settings",
            lambda: self.run_command([
                "python", "-c",
                "import sys; sys.path.insert(0, '.'); from config.settings import get_env_source, get_available_providers; print(f'Env: {get_env_source()}, Providers: {get_available_providers()}')"
            ])
        )
    
    def run_all_tests(self):
        """Run all test suites."""
        print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
        print(f"{BOLD}{BLUE}CLI Functionality Test Suite{RESET}")
        print(f"{BOLD}{BLUE}{'='*80}{RESET}")
        
        print(f"\n{YELLOW}Note: These tests check CLI functionality without making real API calls.{RESET}")
        print(f"{YELLOW}Tests that would make API calls will fail at the API call stage, which is expected.{RESET}\n")
        
        self.test_environment_check()
        self.test_script_imports()
        self.test_configuration()
        self.test_help_commands()
        self.test_argument_parsing()
        self.test_file_operations()
        self.test_cost_guardrails()
        self.test_model_override()
        self.test_chain_runner_features()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
        print(f"{BOLD}Test Summary{RESET}")
        print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
        
        passed = sum(1 for _, result, _ in self.results if result)
        failed = len(self.results) - passed
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}")
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
        
        if failed > 0:
            print(f"{RED}Failed Tests:{RESET}")
            for name, result, message in self.results:
                if not result:
                    print(f"  - {name}: {message}")
        
        print(f"\n{BOLD}Interpretation:{RESET}")
        print(f"- Tests that fail at 'API call' stage are {GREEN}EXPECTED{RESET} (we're not making real calls)")
        print(f"- Tests that fail at 'parsing' or 'validation' stage indicate {RED}REAL ISSUES{RESET}")
        print(f"- All environment and import tests should {GREEN}PASS{RESET}")


if __name__ == "__main__":
    tester = CLITester()
    tester.run_all_tests()


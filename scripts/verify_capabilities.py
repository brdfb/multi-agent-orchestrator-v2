#!/usr/bin/env python3
"""
Capability Verification Script

Bu script, APPLICATION_CAPABILITIES.md dosyasında belirtilen özelliklerin
gerçekten kodda implement edilip edilmediğini kontrol eder.

Kullanım:
    python scripts/verify_capabilities.py
    python scripts/verify_capabilities.py --verbose
    python scripts/verify_capabilities.py --json
"""

import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class CapabilityCheck:
    """Bir özellik kontrolü sonucu."""
    name: str
    status: str  # "pass", "fail", "warning", "not_found"
    details: str
    evidence: List[str] = None  # Kod referansları, test dosyaları vb.


class CapabilityVerifier:
    """Özellik doğrulama motoru."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks: List[CapabilityCheck] = []
        self.base_path = Path(__file__).parent.parent

    def check_file_exists(self, file_path: str) -> bool:
        """Dosyanın var olup olmadığını kontrol et."""
        return (self.base_path / file_path).exists()

    def check_class_exists(self, module_path: str, class_name: str) -> bool:
        """Bir modülde sınıfın var olup olmadığını kontrol et."""
        try:
            spec = importlib.util.spec_from_file_location(
                "module", self.base_path / module_path
            )
            if spec is None:
                return False
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return hasattr(module, class_name)
        except Exception:
            return False

    def check_method_exists(self, module_path: str, class_name: str, method_name: str) -> bool:
        """Bir sınıfta metodun var olup olmadığını kontrol et."""
        try:
            spec = importlib.util.spec_from_file_location(
                "module", self.base_path / module_path
            )
            if spec is None:
                return False
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls = getattr(module, class_name, None)
            if cls is None:
                return False
            return hasattr(cls, method_name) and callable(getattr(cls, method_name))
        except Exception:
            return False

    def grep_in_file(self, file_path: str, pattern: str) -> bool:
        """Dosyada pattern araması yap."""
        try:
            content = (self.base_path / file_path).read_text(encoding='utf-8')
            return pattern.lower() in content.lower()
        except Exception:
            return False

    def find_test_files(self, pattern: str) -> List[str]:
        """Test dosyalarında pattern araması yap."""
        test_dir = self.base_path / "tests"
        if not test_dir.exists():
            return []
        
        found = []
        for test_file in test_dir.glob("test_*.py"):
            if self.grep_in_file(f"tests/{test_file.name}", pattern):
                found.append(f"tests/{test_file.name}")
        return found

    def verify_multi_agent_orchestration(self):
        """1. Multi-Agent Orchestration özelliklerini kontrol et."""
        checks = [
            ("AgentRuntime class", "core/agent_runtime.py", "AgentRuntime"),
            ("Builder agent config", "config/agents.yaml", "builder:"),
            ("Critic agent config", "config/agents.yaml", "critic:"),
            ("Closer agent config", "config/agents.yaml", "closer:"),
            ("Router agent config", "config/agents.yaml", "router:"),
            ("run() method", "core/agent_runtime.py", "AgentRuntime", "run"),
            ("chain() method", "core/agent_runtime.py", "AgentRuntime", "chain"),
            ("route() method", "core/agent_runtime.py", "AgentRuntime", "route"),
        ]

        for name, file_path, *args in checks:
            if len(args) == 1:
                # String pattern check
                exists = self.grep_in_file(file_path, args[0])
            elif len(args) == 2:
                # Class + method check - use grep for reliability
                method_pattern = f"def {args[1]}("
                exists = self.grep_in_file(file_path, method_pattern)
            else:
                # Class check
                exists = self.check_class_exists(file_path, args[0])

            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Multi-Agent: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_memory_system(self):
        """2. Persistent Memory System özelliklerini kontrol et."""
        checks = [
            ("MemoryEngine class", "core/memory_engine.py", "MemoryEngine"),
            ("SQLiteBackend class", "core/memory_backend.py", "SQLiteBackend"),
            ("EmbeddingEngine", "core/embedding_engine.py", "EmbeddingEngine"),
            ("store_conversation()", "core/memory_engine.py", "MemoryEngine", "store_conversation"),
            ("get_context_for_prompt()", "core/memory_engine.py", "MemoryEngine", "get_context_for_prompt"),
            ("Memory config", "config/memory.yaml", "memory:"),
            ("Semantic search", "core/memory_engine.py", "semantic"),
        ]

        for name, file_path, *args in checks:
            if len(args) == 1:
                exists = self.grep_in_file(file_path, args[0])
            elif len(args) == 2:
                # Method check - use grep for reliability
                method_pattern = f"def {args[1]}("
                exists = self.grep_in_file(file_path, method_pattern)
            else:
                exists = self.check_class_exists(file_path, args[0])

            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Memory: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_cost_optimization(self):
        """3. Cost Optimization özelliklerini kontrol et."""
        checks = [
            ("Semantic compression", "core/agent_runtime.py", "_compress_semantic"),
            ("Compression config", "config/agents.yaml", "compression:"),
            ("Dynamic critic selection", "core/agent_runtime.py", "_select_relevant_critics"),
            ("Dynamic selection config", "config/agents.yaml", "dynamic_selection:"),
            ("Cost tracking", "core/logging_utils.py", "estimated_cost"),
        ]

        for name, file_path, *args in checks:
            if len(args) == 1:
                exists = self.grep_in_file(file_path, args[0])
            else:
                exists = self.check_method_exists(file_path, "AgentRuntime", args[0]) if file_path == "core/agent_runtime.py" else self.grep_in_file(file_path, args[0])

            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Cost Optimization: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_fallback_system(self):
        """4. Intelligent Fallback özelliklerini kontrol et."""
        checks = [
            ("LLMConnector class", "core/llm_connector.py", "LLMConnector"),
            ("Fallback logic", "core/llm_connector.py", "fallback"),
            ("Fallback order config", "config/agents.yaml", "fallback_order:"),
            ("Provider status", "config/settings.py", "get_provider_status"),
        ]

        for name, file_path, *args in checks:
            if len(args) == 1:
                exists = self.grep_in_file(file_path, args[0])
            else:
                exists = self.check_method_exists(file_path, "LLMConnector", args[0]) if "llm_connector" in file_path else self.grep_in_file(file_path, args[0])

            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Fallback: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_interfaces(self):
        """5. Üç farklı arayüzü kontrol et."""
        # CLI
        cli_checks = [
            ("CLI agent runner", "scripts/agent_runner.py", ""),
            ("CLI chain runner", "scripts/chain_runner.py", ""),
            ("CLI memory tools", "scripts/memory_cli.py", ""),
            ("CLI stats tools", "scripts/stats_cli.py", ""),
        ]

        for name, file_path, _ in cli_checks:
            exists = self.check_file_exists(file_path)
            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"CLI: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

        # API
        api_checks = [
            ("FastAPI server", "api/server.py", ""),
            ("/ask endpoint", "api/server.py", "/ask"),
            ("/chain endpoint", "api/server.py", "/chain"),
            ("/health endpoint", "api/server.py", "/health"),
        ]

        for name, file_path, pattern in api_checks:
            exists = self.grep_in_file(file_path, pattern) if pattern else self.check_file_exists(file_path)
            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"API: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

        # Web UI
        ui_checks = [
            ("Web UI template", "ui/templates/index.html", ""),
            ("HTMX usage", "ui/templates/index.html", "htmx"),
        ]

        for name, file_path, pattern in ui_checks:
            exists = self.grep_in_file(file_path, pattern) if pattern else self.check_file_exists(file_path)
            status = "pass" if exists else "warning" if not exists and self.check_file_exists(file_path) else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Web UI: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_observability(self):
        """6. Observability özelliklerini kontrol et."""
        checks = [
            ("JSON logging", "core/logging_utils.py", "write_json"),
            ("Metrics aggregation", "core/logging_utils.py", "get_metrics"),
            ("Cost tracking", "core/logging_utils.py", "estimated_cost"),
            ("Health monitoring", "api/server.py", "/health"),
        ]

        for name, file_path, pattern in checks:
            exists = self.grep_in_file(file_path, pattern)
            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Observability: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_advanced_features(self):
        """7. Advanced Features özelliklerini kontrol et."""
        checks = [
            ("Multi-critic consensus", "core/agent_runtime.py", "_run_multi_critic"),
            ("Multi-critic config", "config/agents.yaml", "multi_critic:"),
            ("Automatic refinement", "core/agent_runtime.py", "refinement"),
            ("Refinement config", "config/agents.yaml", "refinement:"),
            ("Session tracking", "core/session_manager.py", "SessionManager"),
        ]

        for name, file_path, *args in checks:
            if len(args) == 1:
                exists = self.grep_in_file(file_path, args[0])
            elif len(args) == 2:
                exists = self.check_method_exists(file_path, args[0], args[1]) if file_path == "core/agent_runtime.py" else self.grep_in_file(file_path, args[0])
            else:
                exists = self.check_class_exists(file_path, args[0])

            status = "pass" if exists else "fail"
            self.checks.append(CapabilityCheck(
                name=f"Advanced: {name}",
                status=status,
                details=f"File: {file_path}",
                evidence=[file_path] if exists else []
            ))

    def verify_tests(self):
        """8. Test coverage kontrolü."""
        test_files = [
            "test_runtime.py",
            "test_memory_engine.py",
            "test_chain.py",
            "test_api.py",
            "test_llm_connector_fallback.py",
        ]

        for test_file in test_files:
            exists = self.check_file_exists(f"tests/{test_file}")
            status = "pass" if exists else "warning"
            self.checks.append(CapabilityCheck(
                name=f"Tests: {test_file}",
                status=status,
                details=f"Test file: tests/{test_file}",
                evidence=[f"tests/{test_file}"] if exists else []
            ))

    def run_all_checks(self):
        """Tüm kontrolleri çalıştır."""
        # Skip print for JSON mode
        pass
        
        self.verify_multi_agent_orchestration()
        self.verify_memory_system()
        self.verify_cost_optimization()
        self.verify_fallback_system()
        self.verify_interfaces()
        self.verify_observability()
        self.verify_advanced_features()
        self.verify_tests()

    def print_results(self, json_output: bool = False):
        """Sonuçları yazdır."""
        if json_output:
            result = {
                "total": len(self.checks),
                "pass": sum(1 for c in self.checks if c.status == "pass"),
                "fail": sum(1 for c in self.checks if c.status == "fail"),
                "warning": sum(1 for c in self.checks if c.status == "warning"),
                "checks": [asdict(c) for c in self.checks]
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # Group by category
        categories = {}
        for check in self.checks:
            category = check.name.split(":")[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(check)

        # Print summary
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.status == "pass")
        failed = sum(1 for c in self.checks if c.status == "fail")
        warnings = sum(1 for c in self.checks if c.status == "warning")

        try:
            print("\n" + "="*70)
            print("OZET")
            print("="*70)
            print(f"Toplam Kontrol: {total}")
            print(f"[OK] Gecti: {passed} ({passed/total*100:.1f}%)")
            print(f"[FAIL] Basarisiz: {failed} ({failed/total*100:.1f}%)")
            print(f"[WARN] Uyari: {warnings} ({warnings/total*100:.1f}%)")
            print("="*70 + "\n")
        except UnicodeEncodeError:
            # Fallback for Windows console
            print("\n" + "="*70)
            print("OZET")
            print("="*70)
            print(f"Toplam Kontrol: {total}")
            print(f"[OK] Gecti: {passed} ({passed/total*100:.1f}%)")
            print(f"[FAIL] Basarisiz: {failed} ({failed/total*100:.1f}%)")
            print(f"[WARN] Uyari: {warnings} ({warnings/total*100:.1f}%)")
            print("="*70 + "\n")

        # Print by category
        for category, checks in categories.items():
            try:
                print(f"\n[{category}]")
            except UnicodeEncodeError:
                print(f"\n[{category}]")
            print("-" * 70)
            for check in checks:
                try:
                    icon = "[OK]" if check.status == "pass" else "[FAIL]" if check.status == "fail" else "[WARN]"
                    print(f"{icon} {check.name}")
                except UnicodeEncodeError:
                    icon = "[OK]" if check.status == "pass" else "[FAIL]" if check.status == "fail" else "[WARN]"
                    print(f"{icon} {check.name}")
                if self.verbose and check.details:
                    print(f"   {check.details}")
                if self.verbose and check.evidence:
                    print(f"   Evidence: {', '.join(check.evidence)}")

        # Print failures
        failures = [c for c in self.checks if c.status == "fail"]
        if failures:
            print("\n" + "="*70)
            print("[FAIL] BASARISIZ KONTROLLER (Dikkat Gerektirir)")
            print("="*70)
            for check in failures:
                print(f"\n• {check.name}")
                print(f"  {check.details}")
                if check.evidence:
                    print(f"  Beklenen: {', '.join(check.evidence)}")


def main():
    """Ana fonksiyon."""
    import argparse
    parser = argparse.ArgumentParser(
        description="APPLICATION_CAPABILITIES.md özelliklerini doğrula"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Detaylı çıktı")
    parser.add_argument("--json", "-j", action="store_true", help="JSON çıktı")
    args = parser.parse_args()

    verifier = CapabilityVerifier(verbose=args.verbose)
    verifier.run_all_checks()
    verifier.print_results(json_output=args.json)

    # Exit code
    failures = sum(1 for c in verifier.checks if c.status == "fail")
    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()


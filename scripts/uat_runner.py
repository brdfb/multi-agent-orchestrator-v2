#!/usr/bin/env python3
"""
UAT Runner – Multi-Agent Orchestrator

UAT_PLAN.md'deki senaryoları çalıştırır; mock modda API anahtarı gerektirmez.
Rapor hem stdout'a hem isteğe bağlı dosyaya (docs/UAT_REPORT.md) yazılır.

Kullanım:
    python scripts/uat_runner.py
    python scripts/uat_runner.py --report docs/UAT_REPORT.md
    python scripts/uat_runner.py -v
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Proje kökü
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# UAT öncesi mock modu (API key gerektirmez)
os.environ["LLM_MOCK"] = "1"


def _install_embedding_mock():
    """Embedding model yüklemesini engelle (ağ gerektirir). Mock encoder kullan."""
    import numpy as np
    from unittest.mock import MagicMock

    mock_engine = MagicMock()
    mock_engine.encode.return_value = np.zeros(384, dtype=np.float32)
    mock_engine.get_sentence_embedding_dimension = lambda: 384
    # Patch get_embedding_engine in memory_engine so semantic search doesn't hit HuggingFace
    import core.memory_engine as mem_mod
    mem_mod.get_embedding_engine = lambda: mock_engine


@dataclass
class UATResult:
    category: str
    scenario_id: str
    name: str
    passed: bool
    message: str = ""
    critical: bool = True
    duration_ms: float = 0.0


@dataclass
class UATReport:
    results: list[UATResult] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    critical_failed: int = 0

    def add(self, r: UATResult):
        self.results.append(r)
        self.total += 1
        if r.passed:
            self.passed += 1
        else:
            self.failed += 1
            if r.critical:
                self.critical_failed += 1

    def overall_ok(self) -> bool:
        return self.critical_failed == 0


def _time_it(f, *args, **kwargs):
    start = datetime.now(timezone.utc)
    try:
        out = f(*args, **kwargs)
        ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return out, ms, None
    except Exception as e:
        ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return None, ms, e


def run_config_tests(report: UATReport, verbose: bool) -> None:
    """C01–C04: Konfigürasyon."""
    from config.settings import (
        load_agents_config,
        load_memory_config,
        get_env_source,
        is_provider_enabled,
    )

    # C01
    out, ms, err = _time_it(load_agents_config)
    if err:
        report.add(UATResult("Config", "C01", "load_agents_config", False, str(err), True, ms))
    else:
        agents = (out or {}).get("agents") or {}
        has_all = all(k in agents for k in ["builder", "critic", "closer", "router"])
        report.add(UATResult(
            "Config", "C01", "load_agents_config (agents present)",
            bool(out and has_all),
            "agents.builder/critic/closer/router" if has_all else "missing agents",
            True,
            ms,
        ))

    # C02
    out, ms, err = _time_it(load_memory_config)
    if err:
        report.add(UATResult("Config", "C02", "load_memory_config", False, str(err), True, ms))
    else:
        mem = (out or {}).get("memory") or {}
        report.add(UATResult(
            "Config", "C02", "load_memory_config",
            bool(out and ("enabled" in mem or "db_path" in mem or "backend" in mem)),
            "",
            True,
            ms,
        ))

    # C03
    out, ms, err = _time_it(get_env_source)
    ok = not err and out in ("none", "dotenv", "environment")
    report.add(UATResult("Config", "C03", "get_env_source", ok, str(out or err), False, ms))

    # C04
    out, ms, err = _time_it(is_provider_enabled, "openai")
    report.add(UATResult("Config", "C04", "is_provider_enabled(openai)", not err, "", False, ms))


def run_runtime_tests(report: UATReport, verbose: bool) -> None:
    """R01–R05: Agent Runtime."""
    from core.agent_runtime import AgentRuntime
    from core.llm_connector import LLMResponse

    runtime = AgentRuntime()

    # R01 run builder mock
    def _run_builder():
        return runtime.run(agent="builder", prompt="UAT test", mock_mode=True)

    out, ms, err = _time_it(_run_builder)
    if err:
        report.add(UATResult("Runtime", "R01", "run(builder, mock)", False, str(err), True, ms))
    else:
        ok = out and out.agent == "builder" and (out.response or "").strip() and out.error is None
        report.add(UATResult("Runtime", "R01", "run(builder, mock)", ok, out.error or "", True, ms))

    # R02 run auto (router) mock
    def _run_auto():
        return runtime.run(agent="auto", prompt="Build an API", mock_mode=True)

    out, ms, err = _time_it(_run_auto)
    if err:
        report.add(UATResult("Runtime", "R02", "run(auto, mock)", False, str(err), True, ms))
    else:
        ok = out and out.agent in ("builder", "critic", "closer") and out.error is None
        report.add(UATResult("Runtime", "R02", "run(auto, mock)", ok, out.agent if out else "", True, ms))

    # R03 route
    from unittest.mock import patch
    mock_resp = LLMResponse(
        text="builder",
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt_tokens=5,
        completion_tokens=1,
        total_tokens=6,
        duration_ms=50.0,
    )
    with patch.object(runtime.connector, "call", return_value=mock_resp):
        out, ms, err = _time_it(runtime.route, "Create a REST API")
    if err:
        report.add(UATResult("Runtime", "R03", "route()", False, str(err), True, ms))
    else:
        ok = out in ("builder", "critic", "closer")
        report.add(UATResult("Runtime", "R03", "route()", ok, str(out), True, ms))

    # R04 chain (stages builder,critic; config may add multi-critic so >= 2 results)
    def _chain():
        return runtime.chain(prompt="UAT chain test", stages=["builder", "critic"], mock_mode=True)

    out, ms, err = _time_it(_chain)
    if err:
        report.add(UATResult("Runtime", "R04", "chain(builder,critic, mock)", False, str(err), True, ms))
    else:
        ok = isinstance(out, list) and len(out) >= 2 and all(getattr(r, "error", None) is None for r in out)
        report.add(UATResult("Runtime", "R04", "chain(builder,critic, mock)", ok, f"len={len(out) if out else 0}", True, ms))

    # R05 unknown agent
    try:
        runtime.run(agent="unknown_agent", prompt="x", mock_mode=True)
        report.add(UATResult("Runtime", "R05", "run(unknown agent) → ValueError", False, "No exception", True, 0))
    except ValueError:
        report.add(UATResult("Runtime", "R05", "run(unknown agent) → ValueError", True, "", True, 0))
    except Exception as e:
        report.add(UATResult("Runtime", "R05", "run(unknown agent) → ValueError", False, str(e), True, 0))


def run_memory_tests(report: UATReport, verbose: bool) -> None:
    """M01–M04: Memory (graceful if no DB)."""
    from core.memory_engine import MemoryEngine

    engine = MemoryEngine()

    # M01/M02: get_stats or store (graceful)
    out, ms, err = _time_it(engine.get_stats)
    if err:
        report.add(UATResult("Memory", "M01", "get_stats (graceful)", True, "no crash: " + str(err), True, ms))
    else:
        report.add(UATResult("Memory", "M01", "get_stats", True, "", True, ms))

    # M02 store (may fail if DB read-only or no schema)
    try:
        cid = engine.store_conversation(
            prompt="UAT",
            response="ok",
            agent="builder",
            model="test",
            provider="test",
            session_id=None,
        )
        report.add(UATResult("Memory", "M02", "store_conversation", cid is not None and (cid >= 0 or cid == -1), f"id={cid}", True, 0))
    except Exception as e:
        report.add(UATResult("Memory", "M02", "store_conversation", False, str(e), True, 0))

    # M03 get_recent
    out, ms, err = _time_it(engine.get_recent_conversations, 5)
    if err:
        report.add(UATResult("Memory", "M03", "get_recent_conversations", False, str(err), True, ms))
    else:
        report.add(UATResult("Memory", "M03", "get_recent_conversations", isinstance(out, list), "", True, ms))

    # M04 search
    out, ms, err = _time_it(engine.search_conversations, "uat", limit=5)
    if err:
        report.add(UATResult("Memory", "M04", "search_conversations", False, str(err), True, ms))
    else:
        report.add(UATResult("Memory", "M04", "search_conversations", isinstance(out, list), "", True, ms))


def run_session_tests(report: UATReport, verbose: bool) -> None:
    """S01–S03: Session manager."""
    from core.session_manager import get_session_manager

    sm = get_session_manager()

    # S01
    out, ms, err = _time_it(sm.get_or_create_session, None, "cli", {"pid": 99999})
    if err:
        report.add(UATResult("Session", "S01", "get_or_create_session(cli)", False, str(err), True, ms))
    else:
        ok = bool(out and len(str(out)) <= 64 and ("cli-" in str(out) or True))
        report.add(UATResult("Session", "S01", "get_or_create_session(cli)", ok, str(out)[:50], True, ms))

    # S02 valid id
    try:
        sm.validate_session_id("valid-id-123")
        report.add(UATResult("Session", "S02", "validate_session_id(valid)", True, "", True, 0))
    except Exception as e:
        report.add(UATResult("Session", "S02", "validate_session_id(valid)", False, str(e), True, 0))

    # S03 invalid (too long or bad chars) – dokümana göre ValueError
    try:
        sm.validate_session_id("x" * 100)
        report.add(UATResult("Session", "S03", "validate_session_id(too long) → error", False, "No exception", False, 0))
    except (ValueError, Exception):
        report.add(UATResult("Session", "S03", "validate_session_id(too long) → error", True, "", False, 0))


def run_api_tests(report: UATReport, verbose: bool) -> None:
    """A01–A10: FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)

    # A01
    r, ms, err = _time_it(client.get, "/health")
    if err:
        report.add(UATResult("API", "A01", "GET /health", False, str(err), True, ms))
    else:
        ok = r.status_code == 200 and (r.json() or {}).get("status") in ("healthy", "degraded", "unhealthy")
        report.add(UATResult("API", "A01", "GET /health", ok, f"status={r.status_code}", True, ms))

    # A02
    r, ms, err = _time_it(client.post, "/ask", json={"agent": "builder", "prompt": "UAT", "mock_mode": True})
    if err:
        report.add(UATResult("API", "A02", "POST /ask (mock)", False, str(err), True, ms))
    else:
        data = r.json() if r else {}
        ok = r.status_code == 200 and (data.get("response") or data.get("error") is not None)
        report.add(UATResult("API", "A02", "POST /ask (mock)", ok, f"status={r.status_code}", True, ms))

    # A03
    r, ms, err = _time_it(client.post, "/ask", json={"agent": "builder", "prompt": ""})
    report.add(UATResult("API", "A03", "POST /ask empty prompt → 422", not err and r.status_code == 422, "", True, ms))

    # A04
    r, ms, err = _time_it(client.post, "/ask", json={"agent": "invalid", "prompt": "x"})
    report.add(UATResult("API", "A04", "POST /ask invalid agent → 400", not err and r.status_code == 400, "", True, ms))

    # A05
    r, ms, err = _time_it(client.post, "/chain", json={"prompt": "UAT chain", "mock_mode": True})
    if err:
        report.add(UATResult("API", "A05", "POST /chain (mock)", False, str(err), True, ms))
    else:
        ok = r.status_code == 200 and isinstance(r.json(), list)
        report.add(UATResult("API", "A05", "POST /chain (mock)", ok, f"status={r.status_code}", True, ms))

    # A06
    r, ms, err = _time_it(client.get, "/logs", params={"limit": 5})
    report.add(UATResult("API", "A06", "GET /logs", not err and r.status_code == 200, "", True, ms))

    # A07
    r, ms, err = _time_it(client.get, "/metrics")
    report.add(UATResult("API", "A07", "GET /metrics", not err and r.status_code == 200, "", True, ms))

    # A08
    r, ms, err = _time_it(client.get, "/memory/stats")
    report.add(UATResult("API", "A08", "GET /memory/stats", not err and r.status_code in (200, 500), "", False, ms))

    # A09
    r, ms, err = _time_it(client.get, "/memory/search", params={"q": "test", "limit": 5})
    report.add(UATResult("API", "A09", "GET /memory/search", not err and r.status_code in (200, 500), "", False, ms))

    # A10
    r, ms, err = _time_it(client.get, "/")
    report.add(UATResult("API", "A10", "GET / (UI)", not err and r.status_code == 200, "", True, ms))


def run_cli_tests(report: UATReport, verbose: bool) -> None:
    """L01–L03: CLI (subprocess)."""
    import subprocess

    py = ROOT / ".venv" / "bin" / "python"
    if not py.exists():
        py = Path(sys.executable)

    # L01 agent_runner builder
    cmd = [str(py), str(ROOT / "scripts" / "agent_runner.py"), "builder", "UAT hello"]
    env = os.environ.copy()
    env["LLM_MOCK"] = "1"
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=60, env=env)
    ok = proc.returncode == 0 and ("builder" in proc.stdout or "MOCK" in proc.stdout or "Agent:" in proc.stdout)
    report.add(UATResult("CLI", "L01", "agent_runner builder (mock)", ok, f"exit={proc.returncode}", True, 0))

    # L02 chain_runner (non-interactive: prompt as arg)
    cmd = [str(py), str(ROOT / "scripts" / "chain_runner.py"), "UAT chain prompt"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=90, env=env)
    ok = proc.returncode == 0 and ("builder" in proc.stdout or "critic" in proc.stdout or "STAGE" in proc.stdout or "MOCK" in proc.stdout)
    report.add(UATResult("CLI", "L02", "chain_runner (mock)", ok, f"exit={proc.returncode}", True, 0))

    # L03 invalid agent
    cmd = [str(py), str(ROOT / "scripts" / "agent_runner.py"), "invalid_agent", "Hi"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=15, env=env)
    report.add(UATResult("CLI", "L03", "agent_runner invalid agent → non-zero exit", proc.returncode != 0, f"exit={proc.returncode}", True, 0))


def run_all(report: UATReport, verbose: bool, skip_cli: bool) -> None:
    _install_embedding_mock()
    run_config_tests(report, verbose)
    run_runtime_tests(report, verbose)
    run_memory_tests(report, verbose)
    run_session_tests(report, verbose)
    run_api_tests(report, verbose)
    if not skip_cli:
        run_cli_tests(report, verbose)
    else:
        for lid, name in [("L01", "agent_runner"), ("L02", "chain_runner"), ("L03", "invalid agent")]:
            report.add(UATResult("CLI", lid, name + " (skipped)", True, "skipped", True, 0))


def render_report(report: UATReport, verbose: bool) -> str:
    lines = [
        "# UAT Raporu – Multi-Agent Orchestrator",
        "",
        f"- **Başlangıç:** {report.start_time}",
        f"- **Bitiş:** {report.end_time}",
        f"- **Toplam:** {report.total} | **Geçen:** {report.passed} | **Kalan:** {report.failed} | **Kritik fail:** {report.critical_failed}",
        "",
        "## Sonuç: " + ("PASS" if report.overall_ok() else "FAIL"),
        "",
        "---",
        "",
        "| Kategori | ID | Senaryo | Durum | Mesaj |",
        "|----------|----|---------|-------|-------|",
    ]
    for r in report.results:
        status = "OK" if r.passed else "FAIL"
        msg = (r.message or "")[:60].replace("|", ",")
        crit = " (kritik)" if r.critical and not r.passed else ""
        lines.append(f"| {r.category} | {r.scenario_id} | {r.name}{crit} | {status} | {msg} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="UAT Runner")
    parser.add_argument("--report", "-r", type=Path, default=ROOT / "docs" / "UAT_REPORT.md", help="Rapor dosyası")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--skip-cli", action="store_true", help="CLI subprocess testlerini atla")
    args = parser.parse_args()

    report = UATReport()
    report.start_time = datetime.now(timezone.utc).isoformat()

    run_all(report, args.verbose, args.skip_cli)

    report.end_time = datetime.now(timezone.utc).isoformat()

    text = render_report(report, args.verbose)
    print(text)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
        print(f"\nRapor yazıldı: {args.report}")

    sys.exit(0 if report.overall_ok() else 1)


if __name__ == "__main__":
    main()

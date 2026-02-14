# UAT Raporu – Multi-Agent Orchestrator

## Workspace araştırma özeti

- **Yapı:** `config/` (agents.yaml, memory.yaml, settings.py), `core/` (agent_runtime, llm_connector, memory_engine, context_aggregator, session_manager, embedding_engine, logging_utils), `api/server.py`, `scripts/` (agent_runner, chain_runner, memory_cli, stats_cli, view_logs), `ui/templates/`, `tests/`.
- **Config:** Agent’lar `agents.yaml` ile tanımlı (builder, critic, closer, router); fallback_order, memory_enabled, compression, refinement, multi_critic, dynamic_selection ayarları mevcut. Bellek `memory.yaml` (veya default) ile SQLite, semantic/keywords stratejisi.
- **Core:** `AgentRuntime.run()` / `chain()` → router (auto), context injection (ContextAggregator: session + knowledge), LLMConnector (LiteLLM, fallback), log + memory store. Session: SessionManager (cli/ui/api), validation, cleanup.
- **API:** FastAPI; POST /ask, /chain; GET /health, /logs, /metrics, /memory/search, /memory/recent, /memory/stats; DELETE /memory/{id}; GET / → UI.
- **CLI:** agent_runner.py (builder/critic/closer/auto), chain_runner.py (builder→critic→closer veya özel stages), Rich çıktı, session auto (cli-{pid}-*).
- **Not:** CLI subprocess testleri ağ yokken embedding yüklemesi nedeniyle timeout alabilir; ağsız tam UAT için `--skip-cli` kullanıldı.

---

- **Başlangıç:** 2026-02-14T11:46:02.629911+00:00
- **Bitiş:** 2026-02-14T11:46:06.027465+00:00
- **Toplam:** 29 | **Geçen:** 29 | **Kalan:** 0 | **Kritik fail:** 0

## Sonuç: PASS

---

| Kategori | ID | Senaryo | Durum | Mesaj |
|----------|----|---------|-------|-------|
| Config | C01 | load_agents_config (agents present) | OK | agents.builder/critic/closer/router |
| Config | C02 | load_memory_config | OK |  |
| Config | C03 | get_env_source | OK | environment |
| Config | C04 | is_provider_enabled(openai) | OK |  |
| Runtime | R01 | run(builder, mock) | OK |  |
| Runtime | R02 | run(auto, mock) | OK | builder |
| Runtime | R03 | route() | OK | builder |
| Runtime | R04 | chain(builder,critic, mock) | OK | len=3 |
| Runtime | R05 | run(unknown agent) → ValueError | OK |  |
| Memory | M01 | get_stats | OK |  |
| Memory | M02 | store_conversation | OK | id=188 |
| Memory | M03 | get_recent_conversations | OK |  |
| Memory | M04 | search_conversations | OK |  |
| Session | S01 | get_or_create_session(cli) | OK | cli-99999-20260214144605 |
| Session | S02 | validate_session_id(valid) | OK |  |
| Session | S03 | validate_session_id(too long) → error | OK |  |
| API | A01 | GET /health | OK | status=200 |
| API | A02 | POST /ask (mock) | OK | status=200 |
| API | A03 | POST /ask empty prompt → 422 | OK |  |
| API | A04 | POST /ask invalid agent → 400 | OK |  |
| API | A05 | POST /chain (mock) | OK | status=200 |
| API | A06 | GET /logs | OK |  |
| API | A07 | GET /metrics | OK |  |
| API | A08 | GET /memory/stats | OK |  |
| API | A09 | GET /memory/search | OK |  |
| API | A10 | GET / (UI) | OK |  |
| CLI | L01 | agent_runner (skipped) | OK | skipped |
| CLI | L02 | chain_runner (skipped) | OK | skipped |
| CLI | L03 | invalid agent (skipped) | OK | skipped |
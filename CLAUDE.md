# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🆕 Recent Changes (For Claude Code)

### 2025-11-11: CLI Feature Parity (v0.12.0) - Rich Formatting & Cost Tracking
**Goal**: Bring CLI to feature parity with Web UI (syntax highlighting, error messages, cost tracking)

**Key Features**:
1. **Rich Terminal Formatting** - Libraries: Rich, Colorama, Tabulate, Pygments
   - Colored output (success=green, error=red, info=cyan, warning=yellow)
   - Code syntax highlighting (monokai theme, 300+ languages)
   - Memory context visibility (session + knowledge breakdown with token counts)
   - Boxed sections and progress indicators

2. **Enhanced Error Messages** - 6+ error types with actionable solutions
   - API key errors → .env configuration guide
   - Rate limits → wait times and alternative providers
   - Timeouts → optimization tips
   - Model not found → available model list

3. **Cost Tracking Dashboard** (scripts/stats_cli.py - 331 lines)
   - Commands: `make stats`, `make stats DAYS=7`, `make stats DAYS=30 TRENDS=1`
   - Overall stats: conversations, tokens, cost, avg duration
   - Agent breakdown: usage %, request count, cost per agent
   - Model breakdown: token distribution with percentages
   - Daily cost trends with visual bars

**Dependencies**: `rich>=13.7.0`, `colorama>=0.4.6`, `tabulate>=0.9.0`, `pygments>=2.17.0`

**Files**: scripts/stats_cli.py (+331), agent_runner.py (+80), chain_runner.py (+120), requirements.txt (+4)

**Post-Release Fixes (v1.0.1)**:
- Tool usage policy added to all agents (prevents LLM hallucination)
- COST_TABLE updated with claude-sonnet-4-5 and gemini-2.5-flash
- Fixed hardcoded compression model - now reads from config
- Fixed Makefile venv paths

### 2025-11-09: Session Tracking & Dual-Context Model (v0.11.0)
**Feature**: ChatGPT-style conversation continuity with intelligent context aggregation
**Problem Solved**: Stateless architecture → Stateful sessions across CLI, API, and Web UI
**Architecture**: Dual-context model (session context + knowledge context) with flexible token budget

**What Changed**:
- **Before**: Memory only retrieved semantically similar conversations from any session
- **After**: Prioritizes recent messages from same session (continuity) + semantic search from other sessions (knowledge)

**Key Components**:
- `core/session_manager.py` (NEW) - Session ID generation, validation, cleanup
- `core/context_aggregator.py` (NEW) - Dual-context model with priority-based token budget
- `scripts/migrate_add_session_tracking.py` (NEW) - Database migration (sessions table + session_id column)

**Token Budget Strategy**:
- Session context: Up to 75% of budget (priority)
- Knowledge context: Remaining tokens (flexible)
- Example: 600 token budget → session gets 300 → knowledge gets remaining 300 (not fixed 50/50)

**Session Behavior**:
- **CLI**: Duration-based (2h idle timeout), auto-generated from PID
- **Web UI**: Browser sessionStorage (survives refresh, resets on tab close)
- **API**: User-provided or auto-generated

**Security**: Input validation (SQL injection, XSS, path traversal, null byte prevention)

**Backward Compatible**: All `session_id` parameters optional, graceful degradation if database unavailable

**Migration**: `python scripts/migrate_add_session_tracking.py` (idempotent, auto-backup)

**See**: Full documentation in "Session Tracking & Conversation Continuity" section below

### 2025-11-09: UI/UX Improvements (v0.11.2-4)
**Progress**: Fixed 9/10 issues from friend's comprehensive review (score: 6/10 → 9/10)

**v0.11.4 - P2 Medium Priority** (7h):
- Enhanced error messages (6+ types with context-aware solutions)
- Keyboard shortcuts: `Ctrl+Enter` (submit), `Ctrl+K` (search), `Esc` (clear), `/` (focus)
- Cost tracking with visual progress bars (agent/model breakdown, auto-updates every 10s)
- Files: ui/templates/index.html (+253 lines)

**v0.11.3 - P1 High Priority** (4h):
- Code syntax highlighting (Highlight.js 11.9.0, theme-aware, 300+ languages)
- Chain progress indicator (3-stage progress bar with pulse animation)
- Files: ui/templates/index.html (+244 lines)

**v0.11.2 - P0 Critical** (1h):
- Updated model list (claude-sonnet-4-5, gemini-2.5-flash)
- Memory context visibility (clickable badge with session/knowledge breakdown)
- Copy button, search placeholder, button tooltips
- Files: ui/templates/index.html (+78 lines)

### 2025-11-09: Code Quality Fixes (v0.11.1)
**Status**: Fixed 4/11 issues identified in code review (5 already fixed, 2 design choices)

**Fixes**:
- P0: Token budget overflow - replaced 4 chars/token heuristic with tiktoken binary search (accurate for Chinese/emoji)
- P1: Silent exception handling - added `logger.warning()` to 6 `except Exception:` blocks
- P2: Empty context fallback - fallback to most recent conversation when no semantic matches
- P2: Database connection leaks - wrapped 10 methods in try/finally for guaranteed `conn.close()`

**Files**: context_aggregator.py (+35), memory_engine.py (+5), logging_utils.py (+2), memory_backend.py (10 methods)

### 2025-11-08: Memory System Fixes (v0.10.1-2) - CRITICAL BUGS
**v0.10.2 - Token Budget Overflow**:
- Problem: Full responses (2000-4000 tokens) exceeded 600-token budget
- Fix: Truncate to first 300 chars in memory context
- Impact: Multiple high-relevance conversations now fit within budget
- Also: Updated models to claude-sonnet-4-5 and gemini-2.5-flash

**v0.10.1 - Memory Injection Non-Functional**:
- Root causes: Missing `embedding` column, lazy generation broken, `min_relevance: 0.3` too strict
- Fixes: Added embedding field, created `update_embedding()` method, lowered threshold to 0.15
- Result: 0 tokens → 269 tokens injected
- Also: Migrated FastAPI to `lifespan` context manager, replaced `len(text)//4` with tiktoken

### 2025-11-05: Semantic Search & System Improvements (v0.4.0-0.5.0)
**Semantic Search (v0.4.0)**:
- Model: paraphrase-multilingual-MiniLM-L12-v2 (50+ languages, 384 dims)
- Why: Turkish morphology broke keyword search ("chart" ≠ "chart'a")
- Strategies: semantic (pure), hybrid (70% semantic + 30% keyword), keywords (old)
- Performance: First load ~30s (420MB download), subsequent <1s, search <100ms
- Files: embedding_engine.py (NEW), memory_engine.py (+3 methods), migrate_add_embeddings.py (NEW)

**Memory Storage Fix** (Critical):
- Problem: Conversations not persisting - `LLMResponse` missing `estimated_cost` field
- Hidden by: Bare `except: pass` silencing exceptions
- Lesson: Always log exceptions

**Token Limit Optimization** (v0.5.0):
- Builder: 2500 → 9000 tokens (3.6x), Critic: 2000 → 7000 (3.5x), Closer: 1800 → 9000 (5x)
- Why 9K not 32K: 4x cost savings, 3x speed improvement, 1K safety buffer

**New CLI Tools**:
- `mao-chain`, `mao-last-chain`, `mao-logs` - User-friendly alternatives to Makefile commands
- Files: view_logs.py (NEW), chain_runner.py (+argparse)

## System Overview

Multi-Agent Orchestrator is a production-ready system that routes user queries across multiple LLM providers (OpenAI, Anthropic, Google) using specialized agent roles. The architecture follows a three-layer design: **LLMConnector** (unified API wrapper) → **AgentRuntime** (orchestration) → **Interfaces** (CLI/API/UI).

## Core Architecture

### Agent System
Four specialized agents defined in `config/agents.yaml`:
- **builder**: Creates implementations (Claude Sonnet 4.5 - creative/thorough)
- **critic**: Reviews and finds issues (GPT-4o - analytical)
- **closer**: Synthesizes action items (Claude Sonnet 4.5 - decisive)
- **router**: Auto-routes queries to appropriate agent (Gemini 2.5 Flash - fast/cheap)

Each agent has distinct `system` prompts, `temperature`, and `max_tokens` settings that define their behavior.

**Current Token Limits** (as of v0.5.0):
- Builder: 9000 tokens (comprehensive code examples with 1K buffer)
- Critic: 7000 tokens (detailed analysis with examples and 1K buffer)
- Closer: 9000 tokens (synthesis + action plans with 1K buffer)
- Router: 10 tokens (just agent name)

### Request Flow
```
User Query → AgentRuntime.run()
  → (if agent="auto") router.route() determines agent
  → LLMConnector.call() via LiteLLM
  → logging_utils.write_json() creates conversation log
  → Returns RunResult with response + metadata
```

### Chain Execution
Multi-agent workflows (`AgentRuntime.chain()`) pass context between stages:
- Default: builder → critic → closer
- **Context passing** (agent_runtime.py:300-350):
  - Closer receives: original prompt + 1500 chars from builder + 1500 chars from critic
  - Other stages: original prompt + 600-1000 chars from previous stage
  - Smart truncation prevents token explosion while maintaining context
- **Progress indicators**: Real-time callback shows "Stage X/Y: Running AGENT..."
- **Fallback transparency**: Logs show model switches (e.g., Claude → Gemini when API key missing)

### Configuration System
- **Environment detection** (`config/settings.py:get_env_source()`): Checks if API keys from `.env` file or shell environment
- **Model override**: Runtime can override agent's default model per request
- **Cost estimation**: `COST_TABLE` tracks per-token costs for budget tracking
- **Paths**: All data in `data/CONVERSATIONS/` (auto-created, gitignored)

## Development Commands

### User-Facing CLI (Recommended - v0.3.0+)
These are what users actually use (simpler than Makefile):
```bash
# Single agent
mao auto "your question"
mao builder "create code"
mao critic "review this"

# Multi-agent chain (PREFERRED METHOD)
mao-chain "Design a system"              # Interactive if no prompt
mao-chain "prompt" --save-to report.md   # Save full output to file
mao-chain "prompt" builder critic        # Custom stages

# View results
mao-last-chain    # See FULL chain output (all stages)
mao-last          # See last single conversation
mao-logs 10       # Browse 10 recent conversations
```

### Legacy Makefile Commands (Still Supported)
For development/testing only:
```bash
# Run API server (also serves Web UI)
make run-api              # http://localhost:5050

# CLI interactions (prefer direct aliases above)
make agent-ask AGENT=builder Q="Your prompt"
make agent-chain Q="Design a system"  # Harder to use than mao-chain
make agent-last

# Memory operations
make memory-search Q="keyword" AGENT=builder LIMIT=5
make memory-recent LIMIT=10
make memory-stats
make memory-export FORMAT=json > backup.json

# Testing
make test                 # Run all tests (pytest)
pytest tests/test_api.py -v  # Single test file
pytest tests/test_memory_engine.py -v  # Memory tests
```

### Code Quality
```bash
make lint                 # ruff + black check
black .                   # Format code
ruff check . --fix        # Fix linting issues
```

### Environment Setup
```bash
make install              # Creates venv, installs deps
make clean                # Remove venv, caches
```

## Key Implementation Details

### LLMConnector (`core/llm_connector.py`)
- Wraps LiteLLM for unified multi-provider API
- **Model format**: `"provider/model-name"` (e.g., `"anthropic/claude-3-5-sonnet-20241022"`)
- Built-in retry logic (configurable `retry_count`)
- Extracts provider from model string: `model.split("/")[0]`
- Returns `LLMResponse` dataclass with tokens, duration, cost data

### Logging System (`core/logging_utils.py`)
- **Filename format**: `YYYYMMDD_HHMMSS-{agent}-{uuid8}.json`
- **Auto-masking**: Regex patterns detect and mask API keys in logs
- **Metrics**: Aggregates last 1000 logs for total tokens, cost, duration stats
- Logs are **write-only** - never read by agents, only by UI/metrics endpoints

### API Server (`api/server.py`)
- **FastAPI** with auto-generated docs at `/docs`
- **HTMX UI** served at `/` (templates in `ui/templates/index.html`)
- **Startup hook**: Prints API key source detection (`get_env_source()`)
- **Validation**: Pydantic models for all requests (type-safe)
- **Endpoints**:
  - `POST /ask`: Single agent execution
  - `POST /chain`: Multi-agent workflow
  - `GET /logs?limit=N`: Recent conversation history
  - `GET /metrics`: Aggregate usage stats
  - `GET /health`: Service health check

### Testing Strategy
- **Mocking**: `unittest.mock` for LLM calls (avoid real API costs)
- **Fixtures**: `tests/` uses pytest fixtures for config loading
- All tests must pass before commits
- Coverage includes: config loading, routing logic, API endpoints, chain execution, model overrides

## Common Patterns

### Adding a New Agent
1. Add definition to `config/agents.yaml` with model, system prompt, temp, max_tokens
2. Agent is immediately available - no code changes needed
3. Use via CLI: `make agent-ask AGENT=newagent Q="test"`

### Changing Models
- **Per-request**: Pass `override_model` in API/UI
- **Permanent**: Edit `agents.yaml` default model for agent
- **Routing**: Cheaper models (Gemini 2.5 Flash) for routing, expensive (Claude Sonnet 4.5) for building/closing, mid-tier (GPT-4o) for criticism

### Debugging Requests
```bash
# View last log with pretty formatting
make agent-last

# Check specific log file
cat data/CONVERSATIONS/20231104_120000-builder-abc12345.json | python -m json.tool

# Monitor metrics
curl http://localhost:5050/metrics
```

## API Keys and Security
- **Two methods**: Environment variables (production) or `.env` file (development)
- **Precedence**: Environment variables override `.env` if both present
- **Detection**: Startup message shows which source is active
- **Masking**: Regex in `logging_utils.py` catches keys in logs (patterns: `sk-*`, `API_KEY=*`, etc.)

## Memory System (Conversation Memory)

The orchestrator includes a **persistent conversation memory system** that stores all interactions and enables context-aware responses across sessions.

### Architecture

**Core Component**: `core/memory_engine.py` - SQLite-backed storage with thread-safe singleton pattern

**Database**: `data/MEMORY/conversations.db` (auto-created, uses WAL mode for concurrency)

**Schema**:
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    duration_ms REAL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost_usd REAL,
    fallback_used BOOLEAN DEFAULT 0,
    session_id TEXT,
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_agent (agent)
);
```

### Memory Flow

1. **Before LLM call** (`AgentRuntime.run()`):
   - If agent has `memory_enabled: true` in config
   - Calls `memory.get_context_for_prompt()` to retrieve relevant past conversations
   - Relevance scoring: `score = keyword_overlap × exp(-age_hours / decay_hours)`
   - Top-scoring conversations injected into system prompt
   - Token budget enforced (default: 350 tokens max)

2. **After LLM call**:
   - If request succeeded and agent has memory enabled
   - Calls `memory.store_conversation()` to persist prompt, response, and metadata
   - Stores: agent, model, tokens, cost, duration, fallback metadata, session_id

3. **Context Injection Format**:
   ```
   [MEMORY CONTEXT - Relevant past conversations]
   Previous conversation (relevance: 0.82):
   Q: "Set up JWT tokens"
   A: "Here's your JWT implementation..."
   ---
   ```

### Configuration

**Global config** (`config/memory.yaml`):
```yaml
memory:
  enabled: true
  backend: "sqlite"
  database_path: "data/MEMORY/conversations.db"

  context:
    max_context_tokens_default: 350
    prompt_header: "[MEMORY CONTEXT - Relevant past conversations]\n"

  filtering:
    min_relevance: 0.35  # Minimum score (0-1)
    time_decay_hours: 96  # Decay factor (4 days)
    exclude_same_turn: true  # Don't inject from current session
```

**Per-agent config** (`config/agents.yaml`):
```yaml
builder:
  model: "anthropic/claude-3-5-sonnet-20241022"
  memory_enabled: true  # Enable memory for this agent
  memory:
    strategy: "keywords"  # Relevance algorithm
    max_context_tokens: 350  # Agent-specific limit
    min_relevance: 0.35  # Agent-specific threshold
    time_decay_hours: 96
    exclude_same_turn: true
```

**By default**: Builder and Critic have memory enabled, Closer does not (decisiveness over context).

### Memory CLI

All memory operations available via CLI (`scripts/memory_cli.py`):

```bash
# Search conversations
make memory-search Q="authentication" AGENT=builder LIMIT=5

# View recent
make memory-recent LIMIT=10

# Statistics
make memory-stats

# Delete conversation
python scripts/memory_cli.py delete 123 -y

# Cleanup old records
make memory-cleanup DAYS=90 CONFIRM=1

# Export
make memory-export FORMAT=json > backup.json
```

### Memory API Endpoints

Added to `api/server.py`:

- **GET /memory/search?q={query}&agent={agent}&limit={n}**: Search by keyword
- **GET /memory/recent?limit={n}&agent={agent}**: Get recent conversations
- **GET /memory/stats**: Aggregate statistics (total conversations, tokens, cost)
- **DELETE /memory/{conversation_id}**: Delete specific conversation

**Example**:
```bash
curl "http://localhost:5050/memory/search?q=JWT&agent=builder&limit=5"
```

### Implementation Details

- **Lazy initialization**: Memory engine only initialized when first needed (reduces overhead)
- **Graceful degradation**: If database unavailable (e.g., test environment), system continues without memory
- **Thread-safe**: Singleton pattern with lock for database operations
- **Session isolation**: `session_id` prevents injecting context from same conversation
- **Performance**: Indexed queries, <50ms search time, <10MB per 1000 conversations

### Relevance Algorithm

**Keyword-based scoring with time decay**:
```python
# 1. Extract keywords from current prompt (lowercase, split on whitespace)
current_keywords = set(prompt.lower().split())

# 2. For each past conversation:
past_keywords = set(past_prompt.lower().split())
overlap = len(current_keywords & past_keywords) / len(current_keywords)

# 3. Apply time decay
age_hours = (now - conversation_timestamp).total_seconds() / 3600
decay_factor = exp(-age_hours / time_decay_hours)

# 4. Final score
score = overlap * decay_factor

# 5. Filter by min_relevance, sort by score descending
# 6. Take top N conversations within token budget
```

### Testing Memory

Test suite includes (`tests/test_memory_*.py`):
- Store and retrieve conversations
- Search by keyword, agent, model, date range
- Relevance scoring algorithm
- Context injection with token budgeting
- API endpoints (200, 404, 422 responses)
- CLI command output validation
- Session filtering
- Concurrent access (thread safety)

Run memory-specific tests:
```bash
pytest tests/test_memory_engine.py -v
pytest tests/test_memory_api.py -v
```

## Session Tracking & Conversation Continuity (v0.11.0+)

**Problem Solved**: Stateless → Stateful sessions with dual-context model (session + knowledge)

**Dual-Context Architecture**:
1. **Session Context** (Priority 1): Recent messages from same session, up to 75% of budget (450/600 tokens)
2. **Knowledge Context** (Priority 2): Semantic search from other sessions, uses remaining tokens (flexible)

**Token Budget Example** (600 total):
- Session needs 300 → Session: 300, Knowledge: 300 (uses remaining)
- Session needs 500 → Session: 450 (75% cap), Knowledge: 150
- Session needs 100 → Session: 100, Knowledge: 500 (uses remaining)

### Core Components

**SessionManager** (`core/session_manager.py`):
- Lifecycle: generation, validation, storage, cleanup
- Formats: CLI=`cli-{pid}-{timestamp}`, WebUI=`ui-{timestamp}-{random}`, API=user-provided
- CLI sessions: 2h idle timeout, PID-based reuse
- Cleanup: Probabilistic (10% calls), 7-day retention, orphan deletion

**ContextAggregator** (`core/context_aggregator.py`):
- Aggregates session + knowledge context
- Returns formatted context + metadata (token counts, message counts)
- Flow: Query session (last 5 msgs) → Query knowledge (semantic) → Apply budget (75% cap) → Truncate → Format

### Session Behavior

| Interface | Generation | Lifetime | Storage |
|-----------|-----------|----------|---------|
| CLI | Auto `cli-{pid}-{ts}` | 2h idle | Database |
| Web UI | Auto `ui-{ts}-{rand}` | Tab close | sessionStorage + DB |
| API | User or auto | User-controlled | Database |

### Configuration

**Per-Agent** (`config/agents.yaml`):
- `session_context`: enabled, limit (5 messages)
- `knowledge_context`: enabled, strategy (semantic/hybrid/keywords), min_relevance (0.15), time_decay (96h)
- `max_context_tokens`: 600 (session max 450/75%, knowledge uses remaining)

**Session Manager** (hardcoded):
- Validation: 64 chars max, alphanumeric + `_-` only
- CLI reuse: 2 hours
- Cleanup: 10% probability, 7-day retention

### Integration

**CLI**: Auto-generates session via `get_session_manager().get_or_create_session(source="cli", metadata={"pid": os.getpid()})`

**API**: Optional `session_id` in request body, validates + saves if provided

**Web UI**: JavaScript generates `ui-{ts}-{rand}` and stores in sessionStorage

**Runtime**: Uses `ContextAggregator.get_full_context()` to retrieve session + knowledge, injects into system prompt, stores with metadata

### Database & Migration

**New**: `sessions` table (session_id PK, timestamps, source, metadata)
**Updated**: `conversations` table (added session_id column + index)
**Migration**: `python scripts/migrate_add_session_tracking.py` (idempotent, auto-backup, rollback available)

### Security

**Validation**: 64 chars max, alphanumeric + `_-` only, prevents SQL injection/XSS/path traversal
**Database**: Parameterized queries, WAL mode, transactions

### Performance

- Session ops: <1ms (gen/validate), ~5ms (save), ~3ms (query)
- Context aggregation: ~60ms total (~10ms session, ~50ms semantic, <1ms budget calc)
- Cleanup: ~2ms average per request (10% × 20ms when triggered)

### Testing

**Coverage**: Session ID formats, validation, storage, context aggregation, budget enforcement, CLI reuse, migration, backward compat
**Manual**: Mock mode (`LLM_MOCK=1`), database inspection, cleanup testing

### Backward Compatibility

- All `session_id` parameters optional (auto-generates if omitted)
- Graceful degradation (DB unavailable → no sessions, invalid ID → warning + continue)
- No breaking changes (existing clients work without modification)

## Architecture Decisions

### Why LiteLLM?
Unified API across providers - single `completion()` call works for OpenAI, Anthropic, Google, 100+ models. No provider-specific client code.

### Why Separate Agents?
Each LLM model has strengths. Builder uses Claude Sonnet 4.5 (creative/thorough), Critic uses GPT-4o (analytical review), Closer uses Claude Sonnet 4.5 (synthesis), Router uses Gemini 2.5 Flash (fast/cheap routing). Mix-and-match based on task economics.

### Why JSON Logs?
- Machine-readable for metrics aggregation
- API key masking applied before write
- Token and cost tracking built-in
- Easy to parse for analytics/debugging

### Chain Context Strategy (Updated v0.3.0)
Passing full outputs between chain stages causes token explosion. Solution:
- **Closer stage**: Gets original prompt + 1500 chars from builder + 1500 chars from critic (needs full context for synthesis)
- **Other stages**: Get original prompt + 600-1000 chars from previous stage
- **Implementation**: See `agent_runtime.py:chain()` around line 300-350
- Trade-off: Maintains context while controlling token costs (previously was just 200 chars - too little)

## File Organization
```
config/            # agents.yaml, memory.yaml, settings.py (config loader)
core/
  ├── llm_connector.py       # LiteLLM wrapper
  ├── agent_runtime.py       # Orchestration engine
  ├── memory_engine.py       # Conversation storage & retrieval
  ├── session_manager.py     # Session lifecycle (v0.11.0+)
  ├── context_aggregator.py  # Dual-context model (v0.11.0+)
  └── logging_utils.py       # JSON logging
api/               # server.py (FastAPI app + memory endpoints)
ui/templates/      # index.html (HTMX web interface)
scripts/
  ├── agent_runner.py                   # CLI tool (powers `mao` command)
  ├── chain_runner.py                   # Chain CLI (powers `mao-chain` command)
  ├── view_logs.py                      # Log viewer (powers `mao-last-chain`, `mao-logs`)
  ├── memory_cli.py                     # Memory operations CLI
  ├── migrate_add_session_tracking.py   # v0.11.0 database migration
  └── rollback_session_tracking.py      # Rollback migration
tests/             # pytest test suite (60+ tests)
data/CONVERSATIONS/# JSON logs (auto-created, gitignored)
data/MEMORY/
  ├── conversations.db     # SQLite database (auto-created)
  └── *.db.backup.*        # Migration backups (timestamped)
```

## Provider Fallback & Feature Flags

### Overview
The orchestrator supports **provider fallback** - if a primary provider is unavailable (missing API key, disabled, or auth failure), it automatically tries fallback models defined in `agents.yaml`.

### Feature Flags
Disable providers via environment variables:
```bash
export DISABLE_ANTHROPIC=1  # Disables Claude models
export DISABLE_OPENAI=1     # Disables GPT models
export DISABLE_GOOGLE=1     # Disables Gemini models
```

Providers are also **auto-disabled** if their API key is missing.

### Fallback Configuration
Each agent in `config/agents.yaml` has a `fallback_order` list:
```yaml
builder:
  model: "anthropic/claude-3-5-sonnet-20241022"
  fallback_order:
    - "openai/gpt-4o"
    - "openai/gpt-4o-mini"
    - "gemini/gemini-2.0-flash-exp"
```

If Anthropic is unavailable, builder automatically tries OpenAI, then Google.

### Fallback Flow
1. `LLMConnector.call()` checks if primary provider is enabled (`is_provider_enabled()`)
2. If disabled/missing key → tries first fallback in `fallback_order`
3. Continues through fallback list until success or exhaustion
4. Logs include `original_model`, `fallback_reason`, and `fallback_used` metadata

### Check Provider Status
```bash
# Via API
curl http://localhost:5050/health | jq '.providers'

# Via Python
from config.settings import get_provider_status, get_available_providers
print(get_available_providers())  # ['openai', 'google']
print(get_provider_status())      # Detailed status dict
```

### Startup Logging
API server prints provider status on startup:
```
🔑 API keys loaded from environment variables (shell/CI)
✓ Available providers: openai, google
✗ Disabled providers: anthropic
```

### Testing Fallback
```bash
# Disable Anthropic, test builder (should fallback to OpenAI)
export DISABLE_ANTHROPIC=1
make agent-ask AGENT=builder Q="Test fallback"

# Check logs for fallback metadata
make agent-last | jq '.fallback_used'
```

## Important Constraints

### For Claude Code (Development Rules)
- **No direct LLM calls**: Always go through `LLMConnector` (ensures logging, retries, cost tracking, fallback)
- **Agent config in YAML**: Don't hardcode prompts or models in Python
- **Log everything**: `write_json()` called for every LLM interaction (includes fallback metadata)
- **Never silent exceptions**: Bare `except: pass` hides bugs - at minimum log the error (see memory bug 2025-11-05)
- **Validate inputs**: API uses Pydantic models - maintain this for type safety
- **Auto-reload enabled**: Uvicorn watches for code changes in dev mode
- **Fallback transparency**: All fallback usage is logged - never silent failover

### For Users (What to Know)
- **Memory is persistent**: All conversations stored in SQLite - context builds over time
- **Fallback is automatic**: If Claude unavailable, falls back to Gemini/GPT seamlessly
- **Chains are saved**: Use `--save-to` to export full chain output for documentation
- **Logs are local**: All data in `~/.orchestrator/data/` - never sent to cloud

## Historical Context & Development Decisions

This section documents important architectural decisions and lessons learned during development. For full development history, see `docs/claude-history/CONVERSATION_SUMMARY.md` and `docs/DEVELOPMENT_HISTORY.md`.

### Critical Decisions

**1. Virtual Environment in CLI** - Fixed `ModuleNotFoundError` by using `.venv/bin/python` in aliases (system Python lacks deps)

**2. Chain Context Passing** - Evolution: 200 chars (v0.1.0) → full output (v0.2.0, token explosion) → smart truncation (v0.3.0: closer gets 1500 chars, others 600-1000). Balances context vs cost.

**3. Token Limits** - Builder/Closer: 9K, Critic: 7K (not 32K max). Why: 4x cost savings, 3x speed, 1K safety buffer.

**4. Memory Silent Failure** - `LLMResponse` missing `estimated_cost` field + bare `except: pass` hid bug for days. **Lesson: Always log exceptions.**

**5. Multi-Provider Fallback** - Order: Claude (primary) → GPT-4o (premium) → GPT-4o-mini (budget) → Gemini (free). Logged transparently.

**6. Semantic Search** - Turkish morphology ("chart" ≠ "chart'a") broke keyword search. Solution: `paraphrase-multilingual-MiniLM-L12-v2` (50+ langs, ~30s first load, <100ms search).

### Common Pitfalls

**1. Running Without venv** - Use `.venv/bin/python` or aliases (`mao`), not system Python

**2. Memory Not Finding Context** - Threshold too high (lower to 0.15), keywords don't match (use semantic), time decay (increase from 96h to 168h)

**3. Config Changes Not Applied** - CLI applies immediately, API server needs restart (`pkill -f uvicorn`, then `make run-api`)

**4. Testing Without Keys** - Use `LLM_MOCK=1` for tests, check key source with `get_env_source()`

### Development Timeline

- **v0.1.0** (11-03): Initial release - 4 agents, CLI/API/UI
- **v0.2.0** (11-04): Memory system - SQLite storage, context injection
- **v0.3.0** (11-05): Chain optimization - smart truncation, fallback transparency
- **v0.4.0** (11-05): Semantic search - multilingual embeddings, Turkish support
- **v0.5.0** (11-05): Token limits - 9K builder/closer, 7K critic, memory bug fix
- **v0.6.0** (11-06): Semantic compression - 90% token reduction, JSON format
- **v0.7.0** (11-06): Auto-refinement - critical issue detection
- **v0.8.0** (11-06): Multi-iteration - up to 3 cycles, convergence detection
- **v0.9.0** (11-06): Multi-critic - 3 specialists, parallel execution, consensus
- **v0.10.0** (11-06): Dynamic selection - relevance scoring, 30-50% cost savings
- **v0.11.0** (11-09): Session tracking - dual-context, 2h timeout, migration
- **v0.12.0** (11-11): CLI parity - rich formatting, syntax highlighting, stats dashboard
- **v1.0.0** (11-11): Production ready - 89/89 tests, stable API, full docs

### Key Files Modified (Historical Reference)

**Most Frequently Modified:**
1. `config/agents.yaml` - 15+ updates (token limits, memory config, agent prompts)
2. `core/agent_runtime.py` - 10+ updates (chain logic, memory integration, refinement)
3. `core/llm_connector.py` - 5+ updates (fallback logic, cost estimation)
4. `CLAUDE.md` - This file (continuous documentation updates)

**Critical Files for Understanding:**
- `config/agents.yaml` - Agent definitions, all customizable parameters
- `core/agent_runtime.py` - Chain execution, memory injection, refinement loop
- `core/memory_engine.py` - Conversation storage, context retrieval, semantic search
- `api/server.py` - REST API, health monitoring, memory endpoints

### Quick Reference: Where to Find Answers

**"Why was X designed this way?"**
→ Check this Historical Context section or `docs/DEVELOPMENT_HISTORY.md`

**"How do I customize Y?"**
→ See main sections above (Development Commands, Common Patterns)

**"What changed in version Z?"**
→ See `CHANGELOG.md` for detailed version history

**"System isn't working as expected"**
→ Check Common Pitfalls above, then `TROUBLESHOOTING.md`

**"Want to see full development conversation?"**
→ `docs/claude-history/` (14.7 MB, 4,985 events across 2 major sessions)

### Future Claude Code Instances: Start Here

If you're a new Claude Code instance working on this project:

1. **Read this entire file first** - Understand architecture and decisions
2. **Check recent changes** - See top of file for latest features
3. **Review common pitfalls** - Avoid repeating known issues
4. **Test your environment** - Run `make test` to verify setup
5. **Check provider status** - `curl http://localhost:5050/health | jq`
6. **Understand constraints** - See "Important Constraints" section
7. **When in doubt** - Check `docs/` directory for specialized guides

**Remember:**
- Config changes in `agents.yaml` apply immediately (no restart)
- Always use venv Python for scripts (`.venv/bin/python`)
- Memory system requires valid database (check with `make memory-stats`)
- Fallback is automatic and logged (check logs for `fallback_used`)

---

**Documentation Maintenance:**
- Update this file when making architectural decisions
- Document "why" not just "what" (code shows "what")
- Add to CHANGELOG.md for version-specific changes
- Keep TROUBLESHOOTING.md updated with new issues/solutions

**Last Updated:** 2025-11-11 (v1.0.0 - Production Ready Release)
**Maintained By:** Claude Code conversations + Human review

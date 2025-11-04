# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

Multi-Agent Orchestrator is a production-ready system that routes user queries across multiple LLM providers (OpenAI, Anthropic, Google) using specialized agent roles. The architecture follows a three-layer design: **LLMConnector** (unified API wrapper) → **AgentRuntime** (orchestration) → **Interfaces** (CLI/API/UI).

## Core Architecture

### Agent System
Four specialized agents defined in `config/agents.yaml`:
- **builder**: Creates implementations (Claude Sonnet - creative/thorough)
- **critic**: Reviews and finds issues (GPT-4o-mini - fast/analytical)
- **closer**: Synthesizes action items (Gemini Pro - decisive)
- **router**: Auto-routes queries to appropriate agent (GPT-4o-mini - fast/cheap)

Each agent has distinct `system` prompts, `temperature`, and `max_tokens` settings that define their behavior.

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
- Each stage receives: original prompt + summary of previous output (first 200 chars)
- Prevents token explosion while maintaining context

### Configuration System
- **Environment detection** (`config/settings.py:get_env_source()`): Checks if API keys from `.env` file or shell environment
- **Model override**: Runtime can override agent's default model per request
- **Cost estimation**: `COST_TABLE` tracks per-token costs for budget tracking
- **Paths**: All data in `data/CONVERSATIONS/` (auto-created, gitignored)

## Development Commands

### Essential Workflows
```bash
# Run API server (also serves Web UI)
make run-api              # http://localhost:5050

# CLI interactions
make agent-ask AGENT=builder Q="Your prompt"
make agent-ask AGENT=auto Q="Your prompt"     # Auto-routes

# Multi-agent chains
make agent-chain Q="Design a system"

# View last conversation log
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
- **Routing**: Cheaper models (gpt-4o-mini) for routing, expensive (Claude Sonnet) for building

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

## Architecture Decisions

### Why LiteLLM?
Unified API across providers - single `completion()` call works for OpenAI, Anthropic, Google, 100+ models. No provider-specific client code.

### Why Separate Agents?
Each LLM model has strengths. Builder uses Claude (creative), Critic uses GPT-4o-mini (fast analysis), Closer uses Gemini (decisive). Mix-and-match based on task economics.

### Why JSON Logs?
- Machine-readable for metrics aggregation
- API key masking applied before write
- Token and cost tracking built-in
- Easy to parse for analytics/debugging

### Chain Context Strategy
Passing full outputs between chain stages causes token explosion. Solution: Pass original prompt + 200-char summary of previous stage. Maintains context while controlling costs.

## File Organization
```
config/            # agents.yaml, memory.yaml, settings.py (config loader)
core/              # llm_connector.py, agent_runtime.py, memory_engine.py, logging_utils.py
api/               # server.py (FastAPI app + memory endpoints)
ui/templates/      # index.html (HTMX web interface)
scripts/           # agent_runner.py (CLI tool), memory_cli.py (memory CLI)
tests/             # pytest test suite (55+ tests)
data/CONVERSATIONS/# JSON logs (auto-created, gitignored)
data/MEMORY/       # conversations.db (SQLite database, auto-created)
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
    - "google/gemini-2.0-flash-exp"
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
- **No direct LLM calls**: Always go through `LLMConnector` (ensures logging, retries, cost tracking, fallback)
- **Agent config in YAML**: Don't hardcode prompts or models in Python
- **Log everything**: `write_json()` called for every LLM interaction (includes fallback metadata)
- **Validate inputs**: API uses Pydantic models - maintain this for type safety
- **Auto-reload enabled**: Uvicorn watches for code changes in dev mode
- **Fallback transparency**: All fallback usage is logged - never silent failover

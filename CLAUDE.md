# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🆕 Recent Changes (For Claude Code)

### 2025-11-05: Semantic Search (v0.4.0) - MULTILINGUAL SUPPORT
**Feature**: Embedding-based semantic search for memory context retrieval
**Model**: paraphrase-multilingual-MiniLM-L12-v2 (384 dimensions, 50+ languages)
**Why**: Keyword-based search failed with Turkish prompts (0.25 overlap < 0.3 threshold)
  - Example: "chart" vs "chart'a" counted as different keywords
  - Semantic approach: understands meaning despite morphological differences

**Files Changed**:
- `core/embedding_engine.py` (NEW) - Embedding generation, serialization, cosine similarity
- `core/memory_engine.py` - Added `_score_semantic()`, `_score_hybrid()`, `_get_or_generate_embedding()`
- `scripts/migrate_add_embeddings.py` (NEW) - Adds `embedding` BLOB column to conversations table
- `config/memory.yaml` - Changed `strategy_default: "keywords"` → `"semantic"`
- `config/agents.yaml` - Builder now uses `strategy: "semantic"`
- `requirements.txt` - Added `sentence-transformers>=2.2.2` (+1.7GB deps)

**Usage**:
```bash
# Test semantic search
pytest tests/test_memory_engine.py::test_semantic_search -v

# Run migration (if needed)
python scripts/migrate_add_embeddings.py

# Check model status
python -c "from core.embedding_engine import get_embedding_engine; print(get_embedding_engine().model_name)"
```

**Performance**:
- First load: ~30s (downloads 420MB model)
- Subsequent: <1s (cached)
- Embedding: ~50ms per conversation
- Search: <100ms for 500 candidates

**Strategies**: `semantic` (pure embedding), `hybrid` (70% semantic + 30% keyword), `keywords` (old)

**GOTCHA**: Embeddings generated on-demand for old conversations (NULL → lazy generation)

### 2025-11-05: Memory System Fix (CRITICAL)
**Problem**: Memory storage silently failing - conversations not being persisted to database
**Root Cause**: `LLMResponse` dataclass missing `estimated_cost` field
**Symptom**: `agent_runtime.py:271` catching exceptions silently with bare `except: pass`
**Solution**: Added `estimated_cost: float = 0.0` to `LLMResponse` (llm_connector.py:23)
**Lesson**: Never use bare `except: pass` - at minimum log the error. Added debug logging.
**Verification**: Test with `mao auto "test"` then check `sqlite3 data/MEMORY/conversations.db "SELECT COUNT(*) FROM conversations"`

### 2025-11-05: Truncation Fix & Token Limit Optimization
**Problem**: Agent responses cut off mid-sentence (hitting max_tokens limit)
**Example**: Builder response was 2496/2500 tokens - incomplete code examples
**Solution**: Progressive token limit increases in `config/agents.yaml`:
- Builder: 2500 → 4096 → 8000 → 9000 (3.6x increase)
- Critic: 2000 → 3072 → 6000 → 7000 (3.5x increase)
- Closer: 1800 → 2560 → 8000 → 9000 (5x increase)
**Rationale**: Modern LLMs need space for comprehensive code examples + explanations. Final limits include 1K buffer for complex responses while maintaining cost efficiency (9K chosen over 32K max for 4x cost savings and 3x speed improvement).

### 2025-11-05: New User-Facing Tools
Added CLI tools (user doesn't need to know Makefile syntax):
- `mao-chain "prompt"` - Interactive chain runner (easier than `make agent-chain Q="..."`)
- `mao-chain --save-to file.md` - Save full output for documentation
- `mao-last-chain` - View complete chain execution (all stages)
- `mao-logs 10` - Browse recent conversation history
- `scripts/view_logs.py` - Comprehensive log viewer (powers above aliases)

**Implementation**: Added argparse to chain_runner.py, created view_logs.py, updated .bashrc aliases

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

### Chain Context Strategy (Updated v0.3.0)
Passing full outputs between chain stages causes token explosion. Solution:
- **Closer stage**: Gets original prompt + 1500 chars from builder + 1500 chars from critic (needs full context for synthesis)
- **Other stages**: Get original prompt + 600-1000 chars from previous stage
- **Implementation**: See `agent_runtime.py:chain()` around line 300-350
- Trade-off: Maintains context while controlling token costs (previously was just 200 chars - too little)

## File Organization
```
config/            # agents.yaml, memory.yaml, settings.py (config loader)
core/              # llm_connector.py, agent_runtime.py, memory_engine.py, logging_utils.py
api/               # server.py (FastAPI app + memory endpoints)
ui/templates/      # index.html (HTMX web interface)
scripts/
  ├── agent_runner.py    # CLI tool (powers `mao` command)
  ├── chain_runner.py    # Chain CLI (powers `mao-chain` command)
  ├── view_logs.py       # Log viewer (NEW - powers `mao-last-chain`, `mao-logs`)
  └── memory_cli.py      # Memory operations CLI
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

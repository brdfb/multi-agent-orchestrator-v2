# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🆕 Recent Changes (For Claude Code)

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

### 2025-11-09: UI/UX Improvements (v0.11.2)
**Context**: Friend's comprehensive UI analysis identified 10 issues (overall score: 6/10)
**Work Done**: Fixed 2 P0 critical issues + 3 Phase 1 quick wins (1 hour total)

**P0 Critical Fixes**:
1. **Outdated Model List** (ui/templates/index.html:476-482)
   - Problem: UI showed deprecated models causing API errors
   - Fix: `claude-3-5-sonnet-20241022` → `claude-sonnet-4-5`, `gemini-1.5-pro` → `gemini-2.5-flash`
   - Impact: Model override now works without 404 errors

2. **Memory Context Invisibility** (ui/templates/index.html:602-712)
   - Problem: "🧠 320 tokens" badge with no explanation
   - Fix: Clickable badge with popup showing session vs knowledge breakdown
   - Display: "📝 Session: 150 tokens (3 msgs)" + "🔍 Knowledge: 170 tokens (2 msgs)"
   - Implementation: `showMemoryDetails()` function with alert (simple, 30 min implementation)

**Phase 1 Quick Wins**:
3. **Copy Button** (ui/templates/index.html:585-662)
   - Added 📋 button to all responses (single agent + chain)
   - Visual feedback: "✓ Copied!" with green highlight for 2s
   - Uses Clipboard API with error handling

4. **Search Placeholder** (ui/templates/index.html:518)
   - Changed: "Search by keyword..." → "Search conversations (semantic)..."
   - Clarifies semantic search behavior

5. **Button Tooltips** (ui/templates/index.html:475, 491-492)
   - Send: "Send to selected agent"
   - Run Chain: "Run multi-agent pipeline: builder → critic → closer (thorough analysis)" + ⓘ
   - Model Override: "Override the agent's default model (useful for testing different LLMs)" + ⓘ

**Files Changed**: ui/templates/index.html (+78 lines, -12 lines)

**Remaining Work** (not requested yet):
- P1: Code syntax highlighting (1 hour)
- P1: Chain progress indicator (3 hours)
- P2: Keyboard shortcuts (2 hours)
- P2: Conversation threading UI (2 days)

### 2025-11-09: Code Quality Fixes (v0.11.1)
**Context**: Friend's detailed code review (45 min analysis) identified 11 issues
**Status**: 5 already fixed, 4 valid bugs fixed now, 2 design choices (not bugs)

**P0 Critical: Token Budget Overflow** (core/context_aggregator.py:416-450)
- Problem: Regression of Bug #13 - used 4 chars/token approximation (inaccurate for Chinese/emoji)
- Impact: Chinese/emoji text exceeds budget by 2x
- Fix: Binary search with tiktoken for precise token counting
- Before:
  ```python
  words = text.split()
  truncated = " ".join(words[:target_tokens])  # ❌ Assumes 1 word = 1 token
  ```
- After:
  ```python
  # Binary search for optimal truncation point
  while left <= right:
      mid = (left + right) // 2
      candidate = " ".join(words[:mid])
      candidate_tokens = count_tokens(candidate)  # ✅ Accurate tiktoken
      if candidate_tokens <= target_tokens:
          best_truncation = candidate
          left = mid + 1
      else:
          right = mid - 1
  ```

**P1 High: Silent Exception Handling** (core/memory_engine.py, core/logging_utils.py)
- Problem: 6 `except Exception:` blocks with no logging
- Impact: Debugging nightmare when errors occur
- Fix: Added `logger.warning()` to all silent handlers
- Example:
  ```python
  # Before
  except Exception:
      pass  # ❌ Silent failure

  # After
  except Exception as e:
      logger.warning(f"Failed to generate embedding: {e}")  # ✅ Logged
      pass
  ```

**P2 Medium: Empty Context Fallback** (core/context_aggregator.py:225-244)
- Problem: Returns empty list when no semantic matches above threshold
- Fix: Fallback to most recent conversation (score 0.05) with logging
- Ensures users always get some context, even if not highly relevant

**P2 Medium: Database Connection Leaks** (core/memory_backend.py)
- Problem: `conn.close()` not in `try/finally` (10 methods)
- Fix: Wrapped all DB operations in try/finally
- Example:
  ```python
  # Before
  def get_recent(self, limit):
      conn = self._get_connection()
      cursor = conn.cursor()
      cursor.execute("SELECT ...")
      rows = cursor.fetchall()
      conn.close()  # ❌ Not in finally - leaks on error
      return rows

  # After
  def get_recent(self, limit):
      conn = self._get_connection()
      cursor = conn.cursor()
      try:
          cursor.execute("SELECT ...")
          rows = cursor.fetchall()
          return rows
      finally:
          conn.close()  # ✅ Always closes
  ```

**Issues Already Fixed** (v0.10.0-v0.11.0):
- Multi-critic parallel execution (v0.9.0)
- Convergence detection (v0.8.0)
- No-progress detection (v0.8.0)
- Zero-critic fallback (v0.10.0)
- Null value checks (v0.10.1)

**Files Changed**:
- core/context_aggregator.py (+35 lines)
- core/memory_engine.py (+5 lines)
- core/logging_utils.py (+2 lines)
- core/memory_backend.py (10 methods refactored)

### 2025-11-08: Token Budget Overflow Fix (v0.10.2) - ACTUAL ROOT CAUSE
**Problem**: Memory context injection still returning 0 tokens even after v0.10.1 fixes
**Discovery**: Friend's builder analysis + detailed debugging revealed token budget overflow
**Root Cause**: `_estimate_tokens()` counted full responses (2000-4000 tokens) but budget only 600
**Debug Evidence**:
- 10 conversations passed min_relevance filter (similarity 0.151-0.655)
- Top conversation: similarity 0.655 (excellent!), estimated 3389 tokens → ❌ Exceeds 600 budget
- 9/10 high-scoring conversations rejected due to budget overflow
- Only 1 tiny conversation (21 tokens) picked → explains why injected_context_tokens still 0

**Fix**: Truncate responses to first 300 chars in memory context
- `core/memory_engine.py:420-426` - Truncate in `_estimate_tokens()`
- `core/memory_engine.py:446-447` - Truncate in `_format_context()`

**Impact**: Now multiple high-relevance conversations fit within 600 token budget

**Also Fixed**:
- Bug #11: Updated Anthropic models to `claude-sonnet-4-5` (was `claude-3-5-sonnet-20241022` - deprecated)
- Bug #12: Updated Gemini models to `gemini-2.5-flash` (was `gemini-2.0-flash` - outdated)

**Why This Matters**: v0.10.1 fixed embedding persistence, but context was still empty due to budget overflow. v0.10.2 actually makes memory injection work end-to-end.

### 2025-11-08: Memory Context Injection Fix (v0.10.1) - CRITICAL BUG
**Problem**: Memory system completely non-functional - 0 tokens injected despite 100+ conversations
**Discovered By**: External tester during "idiot testing" session
**Root Causes**:
  1. Backend `_row_to_dict()` missing `embedding` column → embeddings never retrieved
  2. Lazy generation using non-existent `self.backend._conn` → embeddings never persisted
  3. `min_relevance: 0.3` too strict for semantic search (top score: 0.194)

**Fixes**:
- Added `embedding` field to `_row_to_dict()` (core/memory_backend.py:446)
- Created `update_embedding()` method in SQLiteBackend (core/memory_backend.py:377-401)
- Updated lazy generation to use proper method (core/memory_engine.py:590)
- Lowered `min_relevance` from 0.3 to 0.15 (config/agents.yaml:172)

**Why 0.15?** Semantic similarity scores are naturally lower than keyword overlap. Cosine similarity of 0.15-0.20 can still represent meaningful semantic connections.

**Test Results**:
```bash
# Before fix:
"injected_context_tokens": 0  # Every conversation

# After fix:
"injected_context_tokens": 269  # Context working!
```

**Verification**:
```bash
# Test memory injection
make agent-ask AGENT=builder Q="Implement JWT auth"
sleep 5
make agent-ask AGENT=builder Q="How to refresh tokens?"

# Check last log
cat data/CONVERSATIONS/*.json | tail -1 | jq '.injected_context_tokens'
# Should be > 0
```

### 2025-11-08: Quick Wins (v0.10.1)
**Bug #8 - FastAPI Deprecation**: Migrated from `@app.on_event()` to `lifespan` context manager
**Bug #9 - Token Standardization**: Replaced `len(text) // 4` heuristic with `tiktoken` (44% more accurate)

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

## Session Tracking & Conversation Continuity (v0.11.0+)

The orchestrator implements **ChatGPT-style session tracking** for conversation continuity across multiple interactions. Unlike the original memory system (which only used semantic search), v0.11.0 introduces a **dual-context model** that prioritizes recent messages from the same session while still leveraging cross-session knowledge.

### Problem Solved

**Before v0.11.0** (Stateless):
- Every request treated as new conversation
- Memory only retrieved semantically similar past conversations (no session awareness)
- Multi-turn conversations had no continuity: "add red to the chart" → "What chart?"

**After v0.11.0** (Stateful):
- Sessions track related conversations
- Recent messages from same session get priority in context
- Cross-session knowledge still available via semantic search
- Natural conversation flow: "create a chart" → "add red color" → understands reference

### Architecture: Dual-Context Model

The system aggregates two types of context with priority-based token allocation:

**1. Session Context** (Priority 1):
- Recent messages from **same session** (conversation continuity)
- Up to 75% of token budget
- Ordered chronologically (oldest to newest)
- Format: "3 messages ago: User: '...' Assistant: '...'"

**2. Knowledge Context** (Priority 2):
- Semantic search from **other sessions** (cross-session knowledge)
- Uses remaining tokens (flexible allocation)
- Ordered by relevance score
- Format: "Relevance: 0.82, 2 days ago: Topic: '...' Summary: '...'"

**Token Budget Strategy** (Flexible Allocation):
```
Max Budget: 600 tokens
Session Max: 450 tokens (75% cap)

Case 1: Session needs 300 tokens
→ Session: 300, Knowledge: 300 (uses remaining)

Case 2: Session needs 500 tokens
→ Session: 450 (capped at 75%), Knowledge: 150

Case 3: Session needs 100 tokens
→ Session: 100, Knowledge: 500 (uses remaining)
```

This prevents session context overflow while maximizing total context usage.

### Core Components

#### SessionManager (`core/session_manager.py`)
Manages session lifecycle: generation, validation, storage, cleanup.

**Key Methods**:
```python
session_manager = get_session_manager()

# Auto-generate or validate session
session_id = session_manager.get_or_create_session(
    session_id=None,  # None = auto-generate
    source="cli",     # "cli", "ui", "api"
    metadata={"pid": 12345}
)

# Validate session ID format
session_manager.validate_session_id("cli-12345-20251109120000")
# Raises ValueError if invalid

# Save session to database
session_manager.save_session(
    session_id="cli-12345-20251109120000",
    source="cli",
    metadata={"pid": 12345}
)
```

**Session ID Formats**:
- **CLI**: `cli-{pid}-{timestamp}` (e.g., `cli-12345-20251109120000`)
- **Web UI**: `ui-{timestamp}-{random}` (e.g., `ui-1699516800-a7b3c2d1`)
- **API**: User-provided or auto-generated with random UUID

**Duration-Based CLI Sessions** (Not Hourly Reset):
- Checks for recent session with same PID within 2 hours
- If found → reuses session ID (conversation continues)
- If not → generates new session ID (new conversation)
- Example: PID 12345 at 10:00 AM → same session at 10:30 AM, new session at 12:30 PM

**Cleanup Strategy** (Probabilistic):
- 10% of `save_session()` calls trigger cleanup
- Deletes sessions inactive for >7 days
- Deletes conversations orphaned by session deletion
- Not database trigger (avoids performance overhead)

#### ContextAggregator (`core/context_aggregator.py`)
Implements dual-context model with priority-based token budget.

**Key Method**:
```python
aggregator = ContextAggregator()

context_text, metadata = aggregator.get_full_context(
    prompt="Add red color to the chart",
    session_id="cli-12345-20251109120000",
    config=agent_memory_config  # from agents.yaml
)

# context_text contains formatted context:
# [SESSION CONTEXT - Recent conversation]
# [3 messages ago]
# User: "Create a bar chart with matplotlib"
# Assistant: "Here's your chart code..."
#
# [1 message ago]
# User: "Make it bigger"
# Assistant: "Updated chart size..."
#
# [KNOWLEDGE CONTEXT - Relevant past topics]
# [Relevance: 0.82, 2 days ago]
# Topic: Matplotlib customization best practices
# Summary: "Use rcParams for global settings..."

# metadata contains token counts:
# {
#     'session_context_tokens': 250,
#     'knowledge_context_tokens': 300,
#     'total_context_tokens': 550,
#     'session_messages': 3,
#     'knowledge_messages': 2
# }
```

**How It Works**:
1. Query session context (last 5 messages from same session)
2. Query knowledge context (semantic search excluding current session)
3. Apply priority-based token budget (75% session cap, knowledge uses remaining)
4. Truncate if needed (smart truncation preserves important content)
5. Format final context string

### Session Behavior by Interface

| Interface | Session ID Generation | Lifetime | Storage |
|-----------|----------------------|----------|---------|
| **CLI** | Auto: `cli-{pid}-{timestamp}` | 2h idle timeout | Database |
| **Web UI** | Auto: `ui-{timestamp}-{random}` | Tab close | sessionStorage + Database |
| **API** | User-provided or auto-generated | User-controlled | Database |

**CLI Example**:
```bash
# Terminal 1 (PID 12345)
mao builder "Create a chart"
# session_id: cli-12345-20251109100000

# Same terminal, 30 minutes later (still PID 12345)
mao builder "Add red color"
# session_id: cli-12345-20251109100000 (SAME SESSION - reused)

# Same terminal, 3 hours later (PID 12345)
mao builder "Show me the chart"
# session_id: cli-12345-20251109130000 (NEW SESSION - timeout)
```

**Web UI Example**:
```javascript
// Page load: Generate or retrieve session ID
let sessionId = sessionStorage.getItem('agent_session_id');
if (!sessionId) {
    sessionId = 'ui-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('agent_session_id', sessionId);
}

// Page refresh: Same session ID (sessionStorage persists)
// New tab: Different session ID (sessionStorage per tab)
// Tab close + reopen: New session ID (sessionStorage cleared)
```

**API Example**:
```bash
# Provide session ID (user-controlled)
curl -X POST http://localhost:5050/ask \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "builder",
    "prompt": "Create a chart",
    "session_id": "my-custom-session-123"
  }'

# Auto-generate session ID (omit field)
curl -X POST http://localhost:5050/ask \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "builder",
    "prompt": "Create a chart"
  }'
# Response includes auto-generated session_id
```

### Configuration

**Global Config** (`config/agents.yaml` - per agent):
```yaml
builder:
  model: "anthropic/claude-sonnet-4-5"
  memory_enabled: true
  memory:
    # Session context config
    session_context:
      enabled: true
      limit: 5  # Last 5 messages from same session

    # Knowledge context config (semantic search from other sessions)
    knowledge_context:
      enabled: true
      strategy: "semantic"  # or "hybrid", "keywords"
      min_relevance: 0.15
      time_decay_hours: 96

    # Token budget
    max_context_tokens: 600  # Total budget
    # Session gets up to 450 (75% cap), knowledge uses remaining
```

**Session Manager Config** (hardcoded in `core/session_manager.py`):
```python
# Session validation
MAX_SESSION_ID_LENGTH = 64
ALLOWED_CHARS = r'^[a-zA-Z0-9_-]+$'

# CLI session reuse
CLI_SESSION_REUSE_HOURS = 2

# Cleanup
CLEANUP_PROBABILITY = 0.1  # 10% of save_session() calls
SESSION_RETENTION_DAYS = 7
```

### Integration Points

**CLI Tools** (`scripts/agent_runner.py`, `scripts/chain_runner.py`):
```python
import os
from core.session_manager import get_session_manager

# Auto-generate CLI session
session_manager = get_session_manager()
session_id = session_manager.get_or_create_session(
    source="cli",
    metadata={"pid": os.getpid()}
)

# Pass to runtime
runtime = AgentRuntime()
result = runtime.run(agent=agent, prompt=prompt, session_id=session_id)
```

**API Server** (`api/server.py`):
```python
from pydantic import BaseModel
from core.session_manager import get_session_manager

class AskRequest(BaseModel):
    agent: str
    prompt: str
    session_id: Optional[str] = None  # v0.11.0+

@app.post("/ask")
async def ask(request: AskRequest):
    session_id = request.session_id

    # Validate and save if provided
    if session_id:
        session_manager = get_session_manager()
        session_manager.validate_session_id(session_id)
        session_manager.save_session(
            session_id=session_id,
            source="api",
            metadata={"endpoint": "/ask"}
        )

    result = runtime.run(..., session_id=session_id)
    return result
```

**Web UI** (`ui/templates/index.html`):
```html
<input type="hidden" name="session_id" id="session_id" value="">

<script>
function getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem('agent_session_id');
    if (!sessionId) {
        sessionId = 'ui-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('agent_session_id', sessionId);
    }
    return sessionId;
}

document.addEventListener('DOMContentLoaded', function() {
    const sessionId = getOrCreateSessionId();
    document.getElementById('session_id').value = sessionId;
});
</script>
```

**Agent Runtime** (`core/agent_runtime.py`):
```python
def run(
    self,
    agent: str,
    prompt: str,
    session_id: Optional[str] = None,  # v0.11.0+
    ...
) -> RunResult:
    # Use ContextAggregator for dual-context retrieval
    context_text, context_metadata = self.context_aggregator.get_full_context(
        prompt=prompt,
        session_id=session_id,
        config=agent_memory_config
    )

    # Inject into system prompt
    if context_text:
        system_prompt = agent_config["system"] + "\n\n" + context_text

    # Store conversation with session_id
    self.memory.store_conversation(
        ...,
        session_id=session_id,
        metadata={
            "session_context_tokens": context_metadata.get('session_context_tokens', 0),
            "knowledge_context_tokens": context_metadata.get('knowledge_context_tokens', 0),
        }
    )
```

### Database Schema Changes

**New Table: `sessions`**:
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL,  -- "cli", "ui", "api"
    metadata TEXT,  -- JSON string
    INDEX idx_sessions_last_active (last_active)
);
```

**Updated Table: `conversations`**:
```sql
-- Added column (v0.11.0):
ALTER TABLE conversations ADD COLUMN session_id TEXT;

-- Added index:
CREATE INDEX idx_session_id ON conversations(session_id);
```

**Migration**:
```bash
# Run migration (idempotent, safe to run multiple times)
python scripts/migrate_add_session_tracking.py

# Migration features:
# - Auto-backup before changes (timestamped)
# - Idempotent (checks if already migrated)
# - Preserves existing data
# - Transaction-based (rollback on error)

# Rollback if needed
python scripts/rollback_session_tracking.py
```

### Security Features

**Input Validation** (`core/session_manager.py:validate_session_id()`):
```python
# 1. Length check
if len(session_id) > 64:
    raise ValueError("Session ID too long")

# 2. Character whitelist (alphanumeric + _ -)
if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
    raise ValueError("Invalid characters in session ID")

# 3. Prevents:
# - SQL injection (no quotes, semicolons allowed)
# - XSS (no < > allowed)
# - Path traversal (no / \ allowed)
# - Null byte injection (no \x00 allowed)
```

**Database Safety**:
- All queries use parameterized statements (SQLite `?` placeholders)
- No string concatenation in SQL
- WAL mode prevents corruption
- Transaction-based operations

### Testing

**Test Coverage** (`tests/`):
- Session ID generation (CLI, UI, API formats)
- Session validation (valid/invalid characters, length limits)
- Session storage and retrieval
- Context aggregation (session + knowledge)
- Token budget enforcement (75% cap, flexible allocation)
- CLI session reuse (duration-based)
- Database migration (idempotent, rollback)
- Backward compatibility (session_id optional)

**Manual Testing**:
```bash
# Test CLI session continuity
export LLM_MOCK=1
mao builder "Create a chart"
sleep 2
mao builder "Add red color"
# Should see session context in logs

# Check database
sqlite3 data/MEMORY/conversations.db
> SELECT session_id, prompt FROM conversations ORDER BY timestamp DESC LIMIT 5;
> SELECT * FROM sessions ORDER BY last_active DESC LIMIT 5;

# Test session cleanup
python -c "
from core.session_manager import get_session_manager
sm = get_session_manager()
sm.save_session('test-old-session', 'cli', {})
# Manually set last_active to 8 days ago in database
sm.save_session('test-trigger-cleanup', 'cli', {})  # May trigger cleanup
"
```

### Backward Compatibility

**All `session_id` parameters are optional**:
- CLI: Auto-generates if not provided (transparent to user)
- API: Works without session_id (stateless mode)
- Web UI: Auto-generates via JavaScript

**Graceful Degradation**:
- If database unavailable → session tracking disabled, system continues
- If session_id invalid → logs warning, continues without session
- If migration not run → session_id column NULL, system works without sessions

**No Breaking Changes**:
- Existing API clients work without modification
- Existing CLI scripts work without modification
- Memory system works with or without sessions

### Performance

**Session Operations**:
- Session ID generation: <1ms (string concatenation)
- Session validation: <1ms (regex match)
- Session save: ~5ms (SQLite insert)
- Session query: ~3ms (indexed lookup)

**Context Aggregation**:
- Session context retrieval: ~10ms (last 5 messages)
- Knowledge context retrieval: ~50ms (semantic search, 50 candidates)
- Token budget calculation: <1ms
- Total overhead: ~60ms per request

**Cleanup**:
- Probabilistic trigger: 10% of requests
- When triggered: ~20ms (deletes old sessions + orphaned conversations)
- Impact: <2ms average per request (10% × 20ms)

### Common Use Cases

**Use Case 1: Multi-Turn Conversation**
```bash
# Turn 1: Create feature
mao builder "Create a REST API for user auth"
# Response: JWT implementation with /login endpoint

# Turn 2: Extend feature (same session)
mao builder "Add refresh token support"
# Context includes Turn 1 → understands existing auth system
# Response: Adds refresh token endpoint to existing implementation

# Turn 3: Fix issue (same session)
mao builder "Fix the token expiry bug"
# Context includes Turn 1 + Turn 2 → knows about refresh token system
# Response: Fixes specific bug in context
```

**Use Case 2: Cross-Session Knowledge**
```bash
# Day 1: User asks about JWT
mao builder "How to implement JWT auth in FastAPI?"
# Response: JWT implementation guide

# Day 2: User asks about similar topic (NEW session)
mao builder "How to refresh JWT tokens?"
# Session context: Empty (different session)
# Knowledge context: Includes Day 1 conversation (semantic match)
# Response: Builds on previous JWT knowledge
```

**Use Case 3: Web UI Multi-Tab**
```
Tab 1: "Design a database schema"
→ session_id: ui-1699516800-abc123

Tab 2: "Create API endpoints"
→ session_id: ui-1699516850-def456  (DIFFERENT)

Tab 1 refresh: Still ui-1699516800-abc123 (SAME)
Tab 1 close + reopen: ui-1699517000-ghi789 (NEW)
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

### Critical Decisions & Rationale

#### 1. Virtual Environment in CLI Aliases (2025-11-05)
**Problem:** Initial `mao` alias used system Python, causing `ModuleNotFoundError: litellm`
**Root Cause:** System Python doesn't have project dependencies installed
**Solution:** Alias points directly to `.venv/bin/python`
```bash
# ❌ Original (broken):
alias mao="python3 $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# ✅ Fixed:
alias mao="$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/agent_runner.py"
```
**Why This Matters:** Users must always use venv Python for any orchestrator script execution. Makefile handles this automatically with `. .venv/bin/activate`.

#### 2. Chain Context Passing Strategy (v0.3.0)
**Problem:** Original 200-char truncation lost 96% of builder output, causing critic/closer to make uninformed decisions
**Evolution:**
- v0.1.0: 200 chars (too little context)
- v0.2.0: Full output (token explosion, >10K tokens per chain)
- v0.3.0: Smart truncation - 1500 chars to closer (builder + critic), 600-1000 for others

**Trade-off Decision:**
- **Option A:** Pass full outputs (comprehensive but 3x cost)
- **Option B:** Minimal truncation (cheap but quality loss)
- **Chosen:** Hybrid approach with role-specific limits

**Why This Works:** Closer needs synthesis (gets more context), intermediate agents need less (just enough for next step). See `agent_runtime.py:300-350`.

#### 3. Token Limit Optimization (v0.5.0)
**Problem:** Responses cut off mid-sentence (builder hit 2496/2500 tokens)
**Progression:**
- Initial: Builder 2500, Critic 2000, Closer 1800
- v0.4.0: Builder 4096, Critic 3072, Closer 2560
- v0.5.0: Builder 9000, Critic 7000, Closer 9000

**Why 9K instead of 32K max?**
- 4x cost savings ($0.003 vs $0.012 per response)
- 3x speed improvement (~15s vs ~45s)
- 1K buffer for complex responses (8K actual + 1K safety)

**When to Increase:** If you see truncated responses in logs, increase agent-specific `max_tokens` in `config/agents.yaml`. No restart needed.

#### 4. Memory System Silent Failure (2025-11-05 - CRITICAL BUG)
**Problem:** Conversations not persisting to database despite memory enabled
**Root Cause:** `LLMResponse` dataclass missing `estimated_cost` field, causing exception in `agent_runtime.py:271`
**Hidden by:** Bare `except: pass` silencing all errors
**Fix:** Added `estimated_cost: float = 0.0` to `LLMResponse` + debug logging

**LESSON LEARNED:** Never use bare `except: pass` - always log exceptions at minimum. This bug went undetected for days because errors were silently swallowed.

**Verification:** After any memory system change, test with:
```bash
mao auto "test"
sqlite3 data/MEMORY/conversations.db "SELECT COUNT(*) FROM conversations"
```

#### 5. Multi-Provider Fallback Architecture (v0.2.0)
**Problem:** Single API key failure = entire system down
**Design Choice:** Automatic fallback with transparency

**Fallback Order (per agent):**
```yaml
builder:
  model: "anthropic/claude-3-5-sonnet-20241022"
  fallback_order:
    - "openai/gpt-4o"           # Premium fallback
    - "openai/gpt-4o-mini"      # Budget fallback
    - "gemini/gemini-2.0-flash" # Free fallback
```

**Why This Order?**
1. Claude Sonnet: Best for creative building (primary)
2. GPT-4o: High quality, fast (first fallback)
3. GPT-4o-mini: Cheap, fast enough (budget fallback)
4. Gemini Flash: Free tier available (last resort)

**Logging:** All fallbacks logged with `original_model`, `fallback_reason`, `fallback_used` metadata. Check `/health` endpoint for provider status.

#### 6. Semantic Search for Turkish (v0.4.0)
**Problem:** Keyword-based memory failed with Turkish: "chart" vs "chart'a" counted as different (0.25 overlap < 0.3 threshold)
**Root Cause:** Turkish morphology - agglutinative language adds suffixes to root words
**Solution:** Semantic embeddings (`paraphrase-multilingual-MiniLM-L12-v2`)

**Performance:**
- First model load: ~30s (420MB download, one-time)
- Subsequent: <1s (cached)
- Search: <100ms for 500 conversations

**Strategy Comparison:**
- `keywords`: Fast, fails with morphology
- `semantic`: Understands meaning, handles 50+ languages
- `hybrid`: 70% semantic + 30% keywords (best of both)

**Default:** `semantic` for builder (configured in `config/agents.yaml`)

### Common Pitfalls (From Development History)

#### Pitfall 1: Running Scripts Without venv
```bash
# ❌ WRONG - Uses system Python
python3 scripts/agent_runner.py auto "test"

# ✅ CORRECT - Uses venv
.venv/bin/python scripts/agent_runner.py auto "test"

# ✅ BEST - Use aliases (handle venv automatically)
mao auto "test"
```

#### Pitfall 2: Expecting Immediate Memory Context
**Issue:** User: "Add to previous chart"
**Result:** "What chart?" (memory didn't find context)

**Why?**
- Relevance threshold too high (min_relevance: 0.35)
- Keywords didn't match (morphology issue)
- Time decay (conversation >96 hours old)

**Fix:**
```yaml
# config/agents.yaml - builder.memory section
min_relevance: 0.25  # Lower threshold
time_decay_hours: 168  # 7 days instead of 4
strategy: "semantic"  # Instead of keywords
```

#### Pitfall 3: Chain Not Using Latest Agent Configs
**Issue:** Changed `max_tokens` in `config/agents.yaml`, but chains still truncate

**Why?** You might be running cached chain runner or old server instance.

**Fix:**
```bash
# 1. Kill old server
pkill -f "uvicorn api.server:app"

# 2. Restart (auto-reloads on config change)
make run-api

# 3. Or use direct chain (no server needed)
make agent-chain Q="Your prompt"
```

**Note:** Config changes apply immediately to new requests - no restart needed for CLI (`mao` commands).

#### Pitfall 4: Testing Without API Keys
```bash
# ❌ WRONG - Real LLM calls fail
mao auto "test"  # Error: Missing API key

# ✅ CORRECT - Use mock mode for testing
export LLM_MOCK=1
make test  # All tests pass with mocked responses

# ✅ BEST - Check key detection first
python3 -c "from config.settings import get_env_source; print(get_env_source())"
# Should print: "environment variables" or ".env file"
```

### Development Timeline Highlights

**v0.1.0 (2025-11-03)** - Initial Release
- Core orchestration engine
- 4 agent roles (builder, critic, closer, router)
- CLI + REST API + Web UI

**v0.2.0 (2025-11-04)** - Memory System
- SQLite-backed conversation storage
- Context injection with relevance scoring
- Memory CLI and API endpoints

**v0.3.0 (2025-11-05)** - Chain Optimization
- Smart context truncation (1500 chars per stage)
- Progress indicators for chains
- Fallback transparency
- `mao` alias fix (venv Python)

**v0.4.0 (2025-11-05)** - Semantic Search
- Multilingual embeddings (50+ languages)
- Turkish morphology support
- Semantic/hybrid/keyword strategies

**v0.5.0 (2025-11-05)** - Token Optimization
- Builder: 9000 tokens (3.6x increase)
- Critic: 7000 tokens (3.5x increase)
- Closer: 9000 tokens (5x increase)
- Memory system critical bug fix

**v0.6.0 (2025-11-06)** - Semantic Compression
- 90% token reduction with 100% context preservation
- Structured JSON compression for chain context
- Gemini Flash for compression (fast & cheap)

**v0.7.0 (2025-11-06)** - Auto-Refinement
- Single-iteration builder refinement when critic finds critical issues
- Critical keyword detection (SECURITY, BUG, ERROR, etc.)
- Automatic fix attempt before closer synthesis

**v0.8.0 (2025-11-06)** - Multi-Iteration Refinement
- Up to 3 refinement cycles with convergence detection
- Progress tracking per iteration
- Automatic stopping on no progress or success

**v0.9.0 (2025-11-06)** - Multi-Critic Consensus
- 3 specialized critics (security, performance, code-quality)
- Parallel execution (no latency penalty)
- Weighted consensus merging

**v0.10.0 (2025-11-06)** - Dynamic Critic Selection
- Keyword-based critic relevance scoring
- 30-50% cost savings (only relevant critics run)
- 1-3 critics selected dynamically per prompt

**v0.11.0 (2025-11-09)** - Session Tracking & Dual-Context Model
- ChatGPT-style conversation continuity
- Dual-context model (session + knowledge)
- Priority-based token budget (75% session cap)
- Auto-session generation (CLI, Web UI, API)
- Duration-based CLI sessions (2h timeout)
- Database migration (sessions table)

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

**Last Updated:** 2025-11-09 (v0.11.0 - Session Tracking & Dual-Context Model)
**Maintained By:** Claude Code conversations + Human review

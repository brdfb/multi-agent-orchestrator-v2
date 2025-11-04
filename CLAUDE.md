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

# Testing
make test                 # Run all tests (pytest)
pytest tests/test_api.py -v  # Single test file
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

## Memory System Integration
The Makefile includes memory system commands (`memory-init`, `memory-sync`, `memory-note`, `memory-log`) for project note-taking and synchronization with an external memory system at `~/memory/`. These are optional organizational tools.

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
config/            # agents.yaml (agent definitions), settings.py (config loader)
core/              # llm_connector.py, agent_runtime.py, logging_utils.py
api/               # server.py (FastAPI app)
ui/templates/      # index.html (HTMX web interface)
scripts/           # agent_runner.py (CLI tool)
tests/             # pytest test suite
data/CONVERSATIONS/# JSON logs (auto-created, gitignored)
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

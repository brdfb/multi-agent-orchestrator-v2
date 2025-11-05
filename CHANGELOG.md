# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-11-05

### Added - Chain Improvements
- **Progress indicators** for chain execution (`🔄 Stage X/Y: Running AGENT...`)
- **Full output display** - removed 2000 character truncation limit
- **Fallback transparency** - shows detailed reasons for model fallbacks
  - `Missing API key for provider 'X'`
  - `Authentication failed for provider 'Y'`
  - `Empty response despite N tokens (possible content filter)`
- **Chain context optimization** - Closer agent now sees ALL previous stages (builder + critic)
- **Smart context truncation** - 1500 chars per stage for closer, 600-1000 for others
- **Progress callback system** in `AgentRuntime.chain()`

### Added - Google/Gemini Integration
- Complete Google Gemini model support
- Provider mapping: `gemini/*` models → `google` provider → `GOOGLE_API_KEY`
- Updated model versions: `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-flash-latest`
- Intelligent multi-provider fallback (premium → free)
- Cost table for all Gemini models

### Added - Error Handling
- Empty/filtered response detection
- Content filter detection (`content_filter`, `safety` finish reasons)
- Detailed error messages with automatic fallback triggering
- None-safe data masking in logging

### Improved - Agent System Prompts
- **Builder**: No fluff, concrete code examples required, technical accuracy checks
- **Critic**: Prioritized issues (Technical > Security > Performance), constructive feedback
- **Closer**: MUST synthesize all stages, MUST fix technical errors, MUST address critic's concerns
- **Router**: Clearer routing rules with examples

### Improved - Token Limits
- Builder: 2000 → 2500 tokens (+25% for detailed code)
- Critic: 1500 → 2000 tokens (+33% for thorough analysis)
- Closer: 1000 → 1800 tokens (+80% for comprehensive synthesis)

### Improved - Temperature Settings
- Builder: 0.3 → 0.2 (more deterministic)
- Critic: 0.4 → 0.3 (more consistent)
- Closer: 0.2 (unchanged)

### Fixed
- Python 3.12 deprecation warnings (`datetime.utcnow()` → `datetime.now(timezone.utc)`)
- API response validation (None-safe response field)
- Pydantic validation errors for empty responses
- Chain runner CLI (now uses `scripts/chain_runner.py` instead of API)

### Changed
- API version: 0.1.0 → 0.2.0
- Makefile `agent-chain` target now uses direct script (faster, better formatting)
- RunResultResponse model includes fallback metadata

## [0.2.0] - 2025-11-04

### Added
- Modern AI tool UI redesign (ChatGPT/Claude-inspired aesthetic)
- Persistent memory system with SQLite backend
- Memory CLI commands (`memory-search`, `memory-recent`, `memory-stats`)
- Memory REST API endpoints
- Context injection with relevance scoring
- Automated installation script (`setup.sh`)
- Provider status detection and reporting

## [0.1.0] - 2025-11-03

### Added
- Initial release of Multi-Agent Orchestrator
- Core orchestration engine with LiteLLM integration
- Four agent roles: builder, critic, closer, router
- CLI interface (`scripts/agent_runner.py`)
- REST API with FastAPI (5 endpoints)
- HTMX + PicoCSS web UI with dark/light themes
- Multi-agent chain execution (builder → critic → closer)
- JSON conversation logging with sensitive data masking
- Cost estimation and metrics tracking
- Model override capability
- Comprehensive test suite (6 test files)
- Make targets for common operations
- Complete documentation (README, QUICKSTART)
- Memory system integration (project tracking)

### Supported Providers
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet)
- Google (Gemini 1.5 Pro, Gemini 1.5 Flash)
- OpenRouter (optional)

### API Endpoints
- `POST /ask` - Single agent execution
- `POST /chain` - Multi-agent workflow
- `GET /logs` - View conversation history
- `GET /metrics` - Aggregate statistics
- `GET /health` - Health check

### Security
- API key masking in logs
- Input validation with Pydantic
- Environment-based configuration
- No hardcoded secrets

### Testing
- Config loading validation
- Router behavior tests
- Log writing and masking tests
- API endpoint tests (200, 4xx)
- Chain execution tests
- Model override tests

---

## [0.2.0] - 2025-11-04

### Added - Memory System (Phase 1-3)

**Phase 1: Core Memory Engine**
- SQLite-backed persistent conversation storage (`core/memory_engine.py`)
- `MemoryEngine` singleton with thread-safe database operations
- Store conversations with full metadata (tokens, cost, duration, provider)
- Search conversations by keyword, agent, model, date range
- Get recent conversations with filtering
- Delete conversations and cleanup old records
- Memory statistics (total conversations, tokens, cost by agent/model)
- Database schema with indexes for performance
- Automatic database initialization on first run
- Graceful degradation if database unavailable

**Phase 2: Context Injection & Auto-Storage**
- Automatic conversation storage after successful LLM calls
- Context injection system with relevance scoring
- Keyword-based relevance algorithm with time decay: `score = overlap × exp(-age_hours / decay_hours)`
- Token budgeting for injected context (configurable per agent)
- Agent-specific memory configuration (`memory_enabled`, `max_context_tokens`)
- Session-aware filtering (prevents same-turn repetition)
- Time decay filtering (96 hours default)
- Minimum relevance threshold (0.35 default)
- Memory context header in system prompts
- Integration with `AgentRuntime` for auto-storage
- Builder and Critic agents enabled by default
- Memory configuration file (`config/memory.yaml`)

**Phase 3: REST API & CLI**
- Memory REST API endpoints:
  - `GET /memory/search` - Search conversations by keyword with filters
  - `GET /memory/recent` - Get recent conversations
  - `GET /memory/stats` - Aggregate statistics
  - `DELETE /memory/{id}` - Delete conversation by ID
- Memory CLI tool (`scripts/memory_cli.py`) with commands:
  - `memory-search` - Search with filters
  - `memory-recent` - View recent conversations
  - `memory-stats` - Show statistics
  - `memory-delete` - Delete conversation
  - `memory-cleanup` - Cleanup old conversations
  - `memory-export` - Export to JSON/CSV
- Makefile targets for memory operations
- Full conversation display with formatting
- JSON and CSV export formats
- Confirmation prompts for destructive operations

### Enhanced
- Test suite expanded to 55+ tests (from 6)
- Documentation updated with comprehensive memory system guide
- Project structure updated to include memory components
- Agent configuration extended with memory settings

### Technical Details
- Database: SQLite with WAL mode for concurrency
- Backend: ~1,250 lines of Python (memory engine + CLI)
- API: 4 new endpoints in FastAPI server
- Storage: Auto-created `data/MEMORY/conversations.db`
- Performance: <50ms search queries, <10MB per 1000 conversations

---

## [Unreleased]

### Planned
- Streaming responses (SSE)
- WebSocket support for real-time updates
- Authentication middleware (OAuth2/JWT)
- Rate limiting
- Docker deployment configuration
- Cursor MCP bridge for IDE integration
- Additional agent roles (researcher, validator)
- Webhook notifications
- Log rotation and archiving
- Cost alerts and budgeting
- Performance monitoring dashboard
- Multi-language support
- Batch processing API
- Agent conversation history UI

---

**Legend:**
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities

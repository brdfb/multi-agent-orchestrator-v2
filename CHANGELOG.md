# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

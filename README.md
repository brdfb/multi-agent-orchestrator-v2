# 🤖 Multi-Agent Orchestrator

Production-ready multi-LLM agent system with CLI, REST API, and modern web UI. Route tasks intelligently across OpenAI, Anthropic Claude, and Google Gemini models.

## ⚡ Quick Start

### Option 1: Automated Setup (Recommended - 60 seconds)

**Single command - does everything:**

```bash
# Clone and run setup script
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
./setup.sh
```

**What it does:**
1. ✅ Checks Python 3.11+
2. ✅ Creates virtual environment
3. ✅ Installs dependencies
4. ✅ Interactive API key setup (or uses existing .env)
5. ✅ Initializes database
6. ✅ Runs health checks
7. ✅ Starts server + opens browser

**Non-interactive mode:**
```bash
# For CI/automation (uses environment variables)
./setup.sh --yes --no-browser --port 5050
```

### Option 2: Manual Setup

```bash
# 1. Configure API keys (choose ONE method)

# Method A: .env file (recommended for development)
cp .env.example .env
nano .env  # Add your API keys

# Method B: Environment variables (recommended for CI/production)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...

# 2. Install
make install

# 3. Run (UI + API)
make run-api
# System shows: 🔑 API keys loaded from [environment|.env file]

# Access UI at http://localhost:5050
```

## 🎯 Features

- **Multi-Provider Support**: OpenAI, Anthropic, Google Gemini via unified LiteLLM interface
- **Intelligent Routing**: Auto-route requests to the best agent for the task
- **Agent Roles**:
  - 🏗️ **Builder**: Creates implementations and solutions
  - 🔍 **Critic**: Reviews and analyzes with rigorous scrutiny
  - ✅ **Closer**: Synthesizes decisions into actionable steps
  - 🧭 **Router**: Automatically selects the right agent
- **Multi-Agent Chains**: Run builder → critic → closer workflows
- **🎭 Multi-Critic Consensus (v0.9.0)**: 3 specialized critics (security, performance, quality) run in parallel with weighted consensus
- **🔄 Multi-Iteration Refinement (v0.8.0)**: Iterative refinement with convergence detection (max 3 iterations)
- **🔄 Automatic Refinement (v0.7.0)**: Builder auto-fixes critical issues detected by critic
- **📦 Semantic Compression (v0.6.0)**: 86% token savings with 100% context preservation
- **Persistent Memory System**: SQLite-backed conversation memory with context injection
- **Three Interfaces**: CLI, REST API, Web UI (HTMX + PicoCSS)
- **Complete Observability**: JSON logs, metrics, token/cost tracking
- **Model Override**: Test any model on any agent
- **Security**: API key masking, input sanitization

## 📁 Project Structure

```
.
├── config/
│   ├── agents.yaml          # Agent definitions and prompts
│   ├── memory.yaml          # Memory system configuration
│   └── settings.py          # Configuration management
├── core/
│   ├── llm_connector.py     # LiteLLM wrapper with retry
│   ├── agent_runtime.py     # Orchestration engine
│   ├── memory_engine.py     # Memory system (SQLite backend)
│   └── logging_utils.py     # JSON logging and metrics
├── api/
│   └── server.py            # FastAPI REST API + Memory endpoints
├── ui/
│   └── templates/
│       └── index.html       # HTMX web interface
├── scripts/
│   ├── agent_runner.py      # CLI tool
│   └── memory_cli.py        # Memory system CLI
├── tests/                   # 55+ comprehensive tests
└── data/
    ├── CONVERSATIONS/       # JSON logs (auto-created)
    └── MEMORY/             # SQLite database (auto-created)
```

## 🔧 Configuration

### Environment Variables

**Two ways to provide API keys:**

**Option 1: Environment Variables (Recommended for CI/Production)**
```bash
# In ~/.bashrc, ~/.zshrc, or CI environment
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...

# Verify
echo $OPENAI_API_KEY
```

**Option 2: .env File (Recommended for Local Development)**
```bash
# Copy template
cp .env.example .env

# Edit .env and add keys
nano .env
```

**Important:** Environment variables take precedence over `.env` file. If you've already exported keys in your shell, you don't need a `.env` file.

**Get keys from:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **Google AI**: https://aistudio.google.com/app/apikey

**Check key source:**
```bash
# System will show on startup:
# 🔑 API keys loaded from environment variables
# or
# 📁 API keys loaded from .env file
```

### Agent Configuration

Edit `config/agents.yaml` to customize:
- Models per agent
- System prompts
- Temperature and max_tokens
- Add new agent roles

Example:
```yaml
agents:
  builder:
    model: "anthropic/claude-3-5-sonnet-20241022"
    system: "You are a pragmatic builder..."
    temperature: 0.3
    max_tokens: 2000
```

## 🚀 Usage

### CLI

```bash
# Ask a single agent
make agent-ask AGENT=builder Q="Create a REST API for todos"
make agent-ask AGENT=critic Q="Review this code: ..."
make agent-ask AGENT=auto Q="What should I do?"  # Auto-routes

# Direct script usage
python scripts/agent_runner.py builder "Your question"
```

### Web UI

```bash
make run-ui
# Open http://localhost:5050
```

Features:
- Select agent (auto/builder/critic/closer)
- Override model per request
- Run chains with one click
- View logs and metrics
- Dark/light theme toggle
- Export results

### REST API

```bash
make run-api
# API docs: http://localhost:5050/docs
```

**Endpoints:**

```bash
# Single agent request
curl -X POST http://localhost:5050/ask \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "builder",
    "prompt": "Create a Python function to validate emails",
    "override_model": "openai/gpt-4o"
  }'

# Multi-agent chain
curl -X POST http://localhost:5050/chain \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Design a microservices architecture",
    "stages": ["builder", "critic", "closer"]
  }'

# View logs
curl http://localhost:5050/logs?limit=10

# Get metrics
curl http://localhost:5050/metrics
```

### Multi-Agent Chains

Run coordinated workflows with real-time progress:

```bash
# Easy CLI command (recommended)
mao-chain "Design a scalable chat system"

# Interactive mode (no quotes needed)
mao-chain
# Enter your prompt: Design a scalable chat system

# Via Makefile (from orchestrator dir)
make agent-chain Q="Design a scalable chat system"
```

**Features:**
- 🔄 **Progress indicators**: See which agent is running in real-time
- ⚠️  **Fallback transparency**: Shows model fallback reasons (e.g., missing API keys)
- 📊 **Full output**: No truncation - see complete responses from all agents
- 🧠 **Smart context**: Closer sees ALL previous stages for better synthesis
- 💡 **Interactive mode**: Just run `mao-chain` without arguments

**Output example:**
```
🔗 Running chain: builder → critic → closer
📝 Prompt: Design a scalable chat system

🔄 Stage 1/3: Running BUILDER...
[Full builder response with code examples]

🔄 Stage 2/3: Running CRITIC...
[Full critic analysis with specific issues]

🔄 Stage 3/3: Running CLOSER...
[Synthesized plan addressing all concerns]

✅ Chain completed successfully!
Total duration: 45.2s | Total tokens: 7,391
```

**Custom stages:**
```bash
# Run specific agents (via CLI)
mao-chain "Review security" critic closer

# Via Makefile
make agent-chain Q="Review security" STAGES="critic closer"
```

Default flow: builder creates → critic reviews → closer synthesizes + decides

## 🧠 Memory System

The orchestrator includes a persistent memory system that stores all conversations and enables context-aware responses across sessions.

### Features

- **Automatic Storage**: Every successful conversation is automatically stored in SQLite
- **Context Injection**: Relevant past conversations are injected into agent prompts
- **Relevance Scoring**: Keyword-based matching with time decay
- **Agent-Specific Memory**: Each agent can access its own conversation history
- **Session Management**: Prevents same-session context repetition
- **REST API**: Search and manage conversations via HTTP
- **CLI Tools**: Command-line interface for memory operations

### How It Works

When memory is enabled for an agent (via `memory_enabled: true` in `config/agents.yaml`):

1. **Before LLM call**: System searches for relevant past conversations
2. **Relevance scoring**: `score = keyword_overlap × exp(-age_hours / decay_hours)`
3. **Context injection**: Top-scoring conversations are added to system prompt
4. **Token budgeting**: Context limited to configured max tokens (default: 350)
5. **After LLM call**: New conversation automatically stored for future retrieval

### CLI Commands

```bash
# Search conversations by keyword
make memory-search Q="authentication"
make memory-search Q="bug fix" AGENT=critic LIMIT=5

# View recent conversations
make memory-recent LIMIT=10
make memory-recent AGENT=builder LIMIT=5

# Show memory statistics
make memory-stats
# Output:
#   Total Conversations: 42
#   Total Tokens: 125,430
#   Total Cost: $2.34
#   By Agent: builder (20), critic (15), closer (7)

# Delete specific conversation
python scripts/memory_cli.py delete 123 -y

# Cleanup old conversations
make memory-cleanup DAYS=90 CONFIRM=1

# Export conversations
make memory-export FORMAT=json > conversations.json
make memory-export FROM=2024-01-01 TO=2024-12-31 FORMAT=csv
```

### REST API Endpoints

```bash
# Search conversations
curl "http://localhost:5050/memory/search?q=authentication&agent=builder&limit=10"

# Get recent conversations
curl "http://localhost:5050/memory/recent?limit=10&agent=critic"

# Get memory statistics
curl "http://localhost:5050/memory/stats"

# Delete conversation
curl -X DELETE "http://localhost:5050/memory/123"
```

**Response Format:**
```json
{
  "results": [
    {
      "id": 1,
      "timestamp": "2024-01-01T12:00:00",
      "agent": "builder",
      "model": "anthropic/claude-3-5-sonnet-20241022",
      "prompt": "Create a REST API...",
      "response": "Here's the implementation...",
      "total_tokens": 850,
      "estimated_cost_usd": 0.0255
    }
  ],
  "count": 1
}
```

### Configuration

Edit `config/memory.yaml`:

```yaml
memory:
  enabled: true
  backend: "sqlite"
  database_path: "data/MEMORY/conversations.db"

  # Context injection settings
  context:
    max_context_tokens_default: 350  # Max tokens for injected context
    prompt_header: "[MEMORY CONTEXT - Relevant past conversations]\n"

  # Relevance filtering
  filtering:
    min_relevance: 0.35  # Minimum relevance score (0-1)
    time_decay_hours: 96  # Reduce relevance over time
    exclude_same_turn: true  # Don't include current session
```

Per-agent memory settings in `config/agents.yaml`:

```yaml
agents:
  builder:
    model: "anthropic/claude-3-5-sonnet-20241022"
    memory_enabled: true  # Enable memory for this agent
    memory:
      strategy: "keywords"  # Relevance strategy
      max_context_tokens: 350  # Agent-specific token limit
      min_relevance: 0.35  # Agent-specific relevance threshold
```

### Database Schema

SQLite schema in `data/MEMORY/conversations.db`:

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

### Example: Context Injection

**Without Memory:**
```
User: "How do I authenticate users?"
Builder: [Generic authentication response]
```

**With Memory (sees past conversation about JWT):**
```
[MEMORY CONTEXT - Relevant past conversations]
Previous conversation (relevance: 0.82):
Q: "Set up JWT tokens"
A: "Here's your JWT implementation with refresh tokens..."

User: "How do I authenticate users?"
Builder: "Based on your JWT setup from earlier, you can use..."
```

## 📊 Observability

### Logs

Every request creates a JSON log in `data/CONVERSATIONS/`:

```json
{
  "agent": "builder",
  "model": "anthropic/claude-3-5-sonnet-20241022",
  "provider": "anthropic",
  "prompt": "...",
  "response": "...",
  "duration_ms": 1234,
  "prompt_tokens": 150,
  "completion_tokens": 500,
  "total_tokens": 650,
  "estimated_cost_usd": 0.0123,
  "timestamp": "2024-01-01T12:00:00"
}
```

### View Last Log

```bash
make agent-last
```

### Metrics

```bash
curl http://localhost:5050/metrics
```

Returns:
- Total requests
- Total tokens used
- Estimated costs (USD)
- Average duration
- Agent usage breakdown

## 🧪 Testing

```bash
# Run all tests
make test

# Lint code
make lint
```

Tests cover:
- Config loading and validation
- Router behavior with mocks
- Logging and masking
- API endpoints (200, 4xx responses)
- Chain execution
- Model override

## 🔐 Security

**Built-in protections:**
- API keys masked in logs (regex-based)
- Input validation (Pydantic models)
- Rate limiting ready (add middleware)
- CORS configurable

**⚠️ Important:**
- **Never commit .env** (in .gitignore)
- Rotate keys regularly
- Use environment-specific keys
- Add authentication before public deployment

## 💰 Cost Management

Approximate costs per 1M tokens (as of 2024):

| Model | Input | Output |
|-------|-------|--------|
| GPT-4o Mini | $0.15 | $0.60 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Gemini 1.5 Pro | $1.25 | $5.00 |

**Tips:**
- Use `gpt-4o-mini` for routing and critic (cheaper)
- Reserve Claude Sonnet for complex building tasks
- Monitor costs via `/metrics` endpoint
- Set usage alerts in provider dashboards

## 🎨 Customization

### Add New Agent

1. Edit `config/agents.yaml`:
```yaml
agents:
  researcher:
    model: "openai/gpt-4o"
    system: "You are a thorough researcher..."
    temperature: 0.4
```

2. Use immediately:
```bash
make agent-ask AGENT=researcher Q="Research X"
```

### Change Models

Override per request (UI or API) or edit `agents.yaml` defaults.

### Extend Chain

```python
runtime.chain(prompt, stages=["builder", "critic", "researcher", "closer"])
```

## 🔌 Integration

### Cursor MCP Bridge (Future)

Connect to Cursor IDE:
```json
{
  "mcpServers": {
    "agent-orchestrator": {
      "command": "python",
      "args": ["scripts/mcp_bridge.py"]
    }
  }
}
```

### API Webhooks

Add webhook notifications:
```python
# In api/server.py after agent execution
requests.post(WEBHOOK_URL, json=result.to_dict())
```

## 🛠 Development

```bash
# Format code
black .

# Check linting
ruff check .

# Run specific test
pytest tests/test_api.py -v

# Watch mode
make run-api  # Auto-reloads on file changes
```

## 📦 Deployment

### Docker (Future)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "5050"]
```

### Production Checklist

- [ ] Set production API keys
- [ ] Add authentication (OAuth2/JWT)
- [ ] Configure CORS properly
- [ ] Set up HTTPS (nginx/Caddy)
- [ ] Enable rate limiting
- [ ] Set up monitoring (Sentry/Datadog)
- [ ] Configure log rotation
- [ ] Set resource limits (uvicorn workers)

## 🐛 Troubleshooting

**For complete troubleshooting guide, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

### Quick Fixes

**"mao: command not found"**
```bash
source ~/.bashrc   # Reload shell configuration
```

**"ModuleNotFoundError: No module named 'dotenv'"**
```bash
cd ~/.orchestrator
make clean && make install
```

**"Why am I being asked for API keys again?"**

If you've already exported keys in your shell (`~/.bashrc`, `~/.zshrc`, etc.), you don't need a `.env` file. The system automatically detects and uses environment variables.

```bash
# Check if keys are in environment
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# If they're set, you're good to go!
```

**See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for:**
- Installation issues
- API key problems
- Agent execution errors
- Memory system debugging
- Network and performance issues
- Complete reset procedures

**Tests failing:**
```bash
# Check Python version
python --version  # Needs 3.11+
```

**Port in use:**
```bash
# Change port in Makefile or:
uvicorn api.server:app --port 5051
```

## 📚 Documentation

### User Guides (Non-Technical)

- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - Idiot-proof guide (English)
  - 5-year-old level explanations
  - Restaurant analogy
  - ASCII diagrams
  - FAQ for beginners

- **[NASIL_ÇALIŞIR.md](NASIL_ÇALIŞIR.md)** - Idiot-proof guide (Turkish)
  - Teknik olmayan anlatım
  - Restoran benzetmesi
  - ASCII akış diyagramları
  - Sıkça sorulan sorular

### Specialized Guides

- **[MEMORY_GUIDE.md](MEMORY_GUIDE.md)** - Complete memory system guide
  - How semantic search works
  - Multilingual examples (50+ languages)
  - Search strategies comparison
  - CLI commands reference
  - Best practices and troubleshooting

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
  - Installation problems
  - API key errors
  - Agent execution issues
  - Memory system debugging
  - Performance optimization

### Quick References

- **[QUICKSTART.md](QUICKSTART.md)** - 60-second setup and basic usage
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for Claude Code users
- **[docs/POSTSETUP_MANIFEST.md](docs/POSTSETUP_MANIFEST.md)** - Post-installation reference

### External Resources

- [LiteLLM Docs](https://docs.litellm.ai/)
- [FastAPI Guide](https://fastapi.tiangolo.com/)
- [HTMX Reference](https://htmx.org/reference/)
- [Pico CSS](https://picocss.com/)

## 🤝 Contributing

1. Fork and create feature branch
2. Add tests for new features
3. Run `make lint` and `make test`
4. Submit PR with clear description

## 📄 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

Built with:
- [LiteLLM](https://github.com/BerriAI/litellm) - Unified LLM API
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [HTMX](https://htmx.org/) - HTML-first dynamic UIs
- [Pico CSS](https://picocss.com/) - Minimal CSS framework

---

**Version**: 0.6.0
**Status**: Production Ready
**Maintained**: Active

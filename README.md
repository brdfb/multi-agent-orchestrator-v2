# 🤖 Multi-Agent Orchestrator

Production-ready multi-LLM agent system with CLI, REST API, and modern web UI. Route tasks intelligently across OpenAI, Anthropic Claude, and Google Gemini models.

## ⚡ Quick Start (60 seconds)

```bash
# 1. Setup (choose ONE method)

# Option A: Use .env file (recommended for development)
cp .env.example .env
# Edit .env and add your API keys

# Option B: Use environment variables (recommended for CI/production)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...

# 2. Install
make install

# 3. Run (UI + API)
make run-api
# On startup, you'll see where keys were loaded from:
# 🔑 API keys loaded from environment variables (if using export)
# 📁 API keys loaded from .env (if using .env file)

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
- **Three Interfaces**: CLI, REST API, Web UI (HTMX + PicoCSS)
- **Complete Observability**: JSON logs, metrics, token/cost tracking
- **Model Override**: Test any model on any agent
- **Security**: API key masking, input sanitization

## 📁 Project Structure

```
.
├── config/
│   ├── agents.yaml          # Agent definitions and prompts
│   └── settings.py          # Configuration management
├── core/
│   ├── llm_connector.py     # LiteLLM wrapper with retry
│   ├── agent_runtime.py     # Orchestration engine
│   └── logging_utils.py     # JSON logging and metrics
├── api/
│   └── server.py            # FastAPI REST API
├── ui/
│   └── templates/
│       └── index.html       # HTMX web interface
├── scripts/
│   └── agent_runner.py      # CLI tool
├── tests/                   # 6 comprehensive tests
└── data/
    └── CONVERSATIONS/       # JSON logs (auto-created)
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

Run coordinated workflows:

```bash
make agent-chain Q="Design a scalable chat system"
```

Default flow: builder creates → critic reviews → closer summarizes actions

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

**"Why am I being asked for API keys again?"**

If you've already exported keys in your shell (`~/.bashrc`, `~/.zshrc`, etc.), you don't need a `.env` file. The system automatically detects and uses environment variables.

Check your current environment:
```bash
# Check if keys are in environment
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# If they're set, you're good to go!
```

**API key errors:**
```bash
# Option 1: Check environment variables
printenv | grep API_KEY

# Option 2: Check .env file (if using)
cat .env | grep API_KEY

# Option 3: See what the system detects
make run-api
# Look for startup message:
# 🔑 API keys loaded from environment variables
# 📁 API keys loaded from .env file
# ⚠️  No API keys detected
```

**Module not found:**
```bash
# Reinstall in venv
make clean && make install
```

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

## 📚 Resources

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

**Version**: 0.1.0
**Status**: Production Ready
**Maintained**: Active

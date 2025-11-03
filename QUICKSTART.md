# Multi-Agent Orchestrator - Quick Start

## 60-Second Setup

```bash
# 1. Configure API keys (choose ONE)

# Option A: Environment variables (if already set in shell)
echo $OPENAI_API_KEY  # Check if already set
# If set, skip to step 2!

# Option B: Create .env file (for local dev)
cp .env.example .env
nano .env  # Add your keys

# 2. Install
make install

# 3. Run
make run-api
# System shows: 🔑 API keys loaded from [source]
# Access UI: http://localhost:5050
```

**Note:** If you've already exported API keys in `~/.bashrc` or `~/.zshrc`, you don't need a `.env` file. The system automatically uses environment variables.

## Main Features

### 🤖 Agent Roles
- **Builder**: Creates implementations and solutions
- **Critic**: Reviews and analyzes rigorously
- **Closer**: Synthesizes into action items
- **Router**: Auto-selects best agent

### 🚀 Three Interfaces

**1. Web UI** (Easiest)
```bash
make run-ui
# Open http://localhost:5050
```

**2. CLI**
```bash
make agent-ask AGENT=builder Q="Create a REST API"
make agent-ask AGENT=auto Q="What should I do?"
```

**3. REST API**
```bash
curl -X POST http://localhost:5050/ask \
  -H "Content-Type: application/json" \
  -d '{"agent": "builder", "prompt": "Your task"}'
```

## Multi-Agent Chains

Run coordinated workflows:
```bash
make agent-chain Q="Design a scalable system"
```

Flow: builder creates → critic reviews → closer summarizes

## Key Endpoints

- `POST /ask` - Single agent request
- `POST /chain` - Multi-agent workflow
- `GET /logs` - View history
- `GET /metrics` - Statistics
- `GET /health` - Health check

## Testing

```bash
make test        # Run all tests
make lint        # Check code quality
make agent-last  # View last log
```

## Configuration

**Models** - Edit `config/agents.yaml`:
```yaml
agents:
  builder:
    model: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.3
```

**Override per request** - Via UI or API

## Memory System Integration

```bash
make memory-init                    # Initialize project memory
make memory-note MSG="your note"    # Add a note
make memory-log MSG="log entry"     # Add log entry
make memory-sync                    # Sync QUICKSTART to ~/memory
```

## File Structure

```
.
├── config/              # Agent configurations
├── core/               # Orchestration engine
├── api/                # FastAPI server
├── ui/                 # HTMX web interface
├── scripts/            # CLI tools
├── tests/              # Test suite
└── data/CONVERSATIONS/ # JSON logs
```

## Observability

Every request creates a JSON log with:
- Agent, model, provider
- Tokens, duration, estimated cost
- Full prompt/response (masked keys)

View metrics:
```bash
curl http://localhost:5050/metrics
```

## Clean Up

```bash
make clean    # Remove virtual environment
```

## Next Steps

1. Check full docs: `README.md`
2. Customize agents: `config/agents.yaml`
3. Add new agents (no code changes needed)
4. Monitor costs via `/metrics`
5. Deploy to production (see README)

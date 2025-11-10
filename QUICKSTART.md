# Multi-Agent Orchestrator v1.0.0 - Quick Start

60-second guide to get Multi-Agent Orchestrator running on your machine.

---

## ⚡ Fastest Way (Automated Setup - Recommended)

**Single command - does everything!**

```bash
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
./setup.sh
```

**What happens:**
1. ✅ Checks Python 3.11+ installed
2. ✅ Creates virtual environment
3. ✅ Installs dependencies (~2 minutes)
4. ✅ Interactive API key setup
5. ✅ Initializes database
6. ✅ Runs health checks
7. ✅ Starts server + opens browser

**Done!** System running at `http://localhost:5050` 🎉

---

## ⏱️ Timing Expectations

**First-time installation (fresh system):**
- Automated setup (`./setup.sh`): ~5-10 minutes
- First test run (downloads ML models): +10-15 minutes
- **Total: 15-25 minutes** (depending on internet speed)

**Subsequent runs (everything cached):**
- `make test`: ~20 seconds
- `make run-api`: instant
- **Total: under 1 minute**

---

## 🔧 Alternative: Manual Setup

### Prerequisites
```bash
# Ensure you have Python 3.11+ installed
python3 --version  # Should be 3.11 or higher

# If not, install on Ubuntu/Debian:
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git make
```

### Installation
```bash
# 1. Clone repository
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2

# 2. Configure API keys (choose ONE)

# Option A: Environment variables (if already set in shell)
echo $OPENAI_API_KEY  # Check if already set
# If set, skip to step 3!

# Option B: Create .env file (for local dev)
cp .env.example .env
nano .env  # Add your keys

# 3. Install dependencies (takes 5-10 minutes first time)
make install
# ⏳ This downloads ~30+ Python packages

# 4. Run tests (takes 10-15 minutes first time for model download)
make test
# ⏳ First run downloads sentence-transformers model (~400MB)
# Subsequent runs: ~20 seconds

# 5. Start API server
make run-api
# System shows: 🔑 API keys loaded from [source]
# Access UI: http://localhost:5050
```

**Note:**
- If you've already exported API keys in `~/.bashrc` or `~/.zshrc`, you don't need a `.env` file
- The system automatically uses environment variables
- First-time model download happens during first test run or first semantic search operation

---

## ✅ Verify Installation

```bash
# Check health
curl http://localhost:5050/health

# Expected output:
# {
#   "status": "healthy",
#   "service": "multi-agent-orchestrator",
#   "version": "1.0.0",
#   "providers": {"openai": true, "anthropic": true, "google": true},
#   "memory": {"enabled": true, "database_connected": true}
# }

# Run test suite (89 tests)
make test
# Expected: ===== 89 passed in 16s =====
```

---

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

Run coordinated workflows (builder → critic → closer):

```bash
# Run a chain workflow
make agent-chain Q="Design a scalable e-commerce platform"

# Custom stages (optional)
make agent-chain Q="Review code" STAGES="builder critic"
```

**View chain results:**
```bash
# View last conversation log (formatted JSON)
make agent-last

# View specific log file
python scripts/view_logs.py data/CONVERSATIONS/<filename>.json
```

## Key Endpoints

- `POST /ask` - Single agent request
- `POST /chain` - Multi-agent workflow
- `GET /logs` - View history
- `GET /metrics` - Statistics
- `GET /health` - Health check
- `GET /memory/search` - Search conversations
- `GET /memory/recent` - Recent conversations
- `GET /memory/stats` - Memory statistics
- `DELETE /memory/{id}` - Delete conversation

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
    model: "anthropic/claude-sonnet-4-5"
    temperature: 0.2
```

**Override per request** - Via UI or API

## Conversation Memory

### Semantic Search (Multilingual!)

The memory system uses **semantic search** to understand meaning, not just keywords:

```bash
# Searches work even with Turkish suffixes:
# "Helm chart" finds "chart'a", "chart'ı", etc.

# Search conversations
make memory-search Q="authentication" AGENT=builder

# View recent conversations
make memory-recent LIMIT=10

# Show statistics
make memory-stats

# Export conversations
make memory-export FORMAT=json > backup.json

# Cleanup old conversations (90+ days)
make memory-cleanup DAYS=90 CONFIRM=1
```

**How it works:**
- Automatically stores all conversations with embeddings
- Semantic search finds related conversations (not just keyword matching)
- Supports 50+ languages including Turkish, Arabic, Chinese
- Automatically injects relevant context into new prompts

**Example:**
```
First prompt: "Create Kubernetes Helm chart"
Second prompt: "Add monitoring to previous chart"
→ Memory finds first conversation automatically! ✅
```

Configure in `config/agents.yaml`:
```yaml
builder:
  memory_enabled: true
  memory:
    strategy: "semantic"  # or "hybrid" or "keywords"
    max_context_tokens: 600
```

## File Structure

```
.
├── config/              # Agent configurations + memory.yaml
├── core/               # Orchestration engine + memory_engine.py
├── api/                # FastAPI server + memory endpoints
├── ui/                 # HTMX web interface
├── scripts/            # CLI tools + memory_cli.py
├── tests/              # Test suite (89 tests - all passing)
├── data/CONVERSATIONS/ # JSON logs
└── data/MEMORY/        # SQLite conversation database
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

1. **Read INSTALLATION.md** - Detailed setup guide
2. **Read MEMORY_GUIDE.md** - Understand the memory system
3. **Customize agents** - Edit `config/agents.yaml`
4. **Monitor costs** - Run `make stats` or check `/metrics`
5. **Add new agents** - No code changes needed, just YAML config

---

## 🆘 Need Help?

- **Full Documentation:** README.md
- **Installation Issues:** INSTALLATION.md
- **Common Problems:** TROUBLESHOOTING.md
- **Memory System:** MEMORY_GUIDE.md
- **GitHub Issues:** https://github.com/brdfb/multi-agent-orchestrator-v2/issues

---

**Version:** 1.0.0
**Status:** Production Ready (Developer Tool)
**Repository:** https://github.com/brdfb/multi-agent-orchestrator-v2

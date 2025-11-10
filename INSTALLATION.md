# Installation Guide - Multi-Agent Orchestrator v1.0.0

Complete installation guide for setting up Multi-Agent Orchestrator from scratch on a new machine.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Option 1: Automated Setup (Recommended)](#option-1-automated-setup-recommended)
3. [Option 2: Manual Setup](#option-2-manual-setup)
4. [Post-Installation Verification](#post-installation-verification)
5. [Troubleshooting](#troubleshooting)
6. [Platform-Specific Notes](#platform-specific-notes)

---

## 🔧 Prerequisites

### Minimum Requirements

- **Python:** 3.11+ (recommended: 3.12)
- **pip:** Python package manager
- **venv:** Python virtual environment
- **Disk:** ~2GB free space (includes dependencies and ML models)
- **OS:** Linux, macOS, WSL2 (Windows)

### Optional

- **git:** For cloning repository
- **make:** For Makefile commands
- **curl:** For API testing

### Quick Check

```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check pip
python3 -m pip --version

# Check git (optional)
git --version
```

**Install missing dependencies:**

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git make curl
```

**macOS (Homebrew):**
```bash
brew install python3 git
```

**Windows (WSL2):**
```bash
# Install WSL2 first, then follow Ubuntu instructions
wsl --install
```

---

## 🚀 Option 1: Automated Setup (Recommended)

**Single command - does everything for you!**

### Step 1: Clone Repository

```bash
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
```

### Step 2: Run Setup Script

```bash
./setup.sh
```

**What it does:**
1. ✅ Checks Python 3.11+ is installed
2. ✅ Creates virtual environment (`.venv/`)
3. ✅ Installs all dependencies (~2 minutes)
4. ✅ Interactive API key setup (or uses existing `.env`)
5. ✅ Initializes SQLite database
6. ✅ Runs health checks
7. ✅ Starts server + opens browser

**Non-interactive mode (for CI/automation):**
```bash
# Uses environment variables for API keys
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...

./setup.sh --yes --no-browser --port 5050
```

**Done!** The system is now running at `http://localhost:5050`

---

## 🔧 Option 2: Manual Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** First installation takes ~5-10 minutes (downloads ~30+ packages including PyTorch for semantic search).

### Step 4: Configure API Keys

**Option A: .env file (recommended for development)**

```bash
# Copy example file
cp .env.example .env

# Edit with your keys
nano .env  # or vim, code, etc.
```

Add your API keys:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

**Option B: Environment variables (recommended for production)**

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...
```

Or add to `~/.bashrc` / `~/.zshrc`:
```bash
echo 'export OPENAI_API_KEY=sk-...' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
echo 'export GOOGLE_API_KEY=...' >> ~/.bashrc
source ~/.bashrc
```

### Step 5: Initialize Database

```bash
# Database is auto-created on first run, but you can test:
python3 -c "from core.memory_engine import MemoryEngine; m = MemoryEngine(); print('✅ Database initialized')"
```

### Step 6: Run Tests (Optional)

```bash
# Run all tests
make test

# Or with pytest directly
.venv/bin/pytest tests/ -v
```

**Note:** First test run downloads semantic search model (~400MB), takes ~10-15 minutes. Subsequent runs: ~20 seconds.

### Step 7: Start Server

```bash
# Start API + Web UI
make run-api

# Or with uvicorn directly
.venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 5050
```

Access at: `http://localhost:5050`

---

## ✅ Post-Installation Verification

### 1. Health Check

```bash
curl http://localhost:5050/health | python3 -m json.tool
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "multi-agent-orchestrator",
  "version": "1.0.0",
  "providers": {
    "openai": true,
    "anthropic": true,
    "google": true
  },
  "memory": {
    "enabled": true,
    "database_connected": true
  }
}
```

### 2. Test Agent Execution

**CLI:**
```bash
# Activate virtual environment first
source .venv/bin/activate

# Test builder agent
python scripts/agent_runner.py --agent builder --prompt "Test: Print hello world in Python"
```

**API:**
```bash
curl -X POST http://localhost:5050/ask \
  -H "Content-Type: application/json" \
  -d '{"agent": "builder", "prompt": "Test: Print hello world"}'
```

### 3. Run Test Suite

```bash
make test
```

**Expected:** All 89 tests passing ✅

---

## 🐛 Troubleshooting

### Issue: `python3: command not found`

**Solution:**
```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

### Issue: `pip install` fails with permission error

**Solution:**
```bash
# DON'T use sudo! Use virtual environment:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: API keys not detected

**Check which source is being used:**
```bash
# Start server and look for startup message:
make run-api
# Should show: "🔑 API keys loaded from environment variables" or "📁 API keys loaded from .env file"
```

**Solution:**
```bash
# Verify keys are set:
echo $OPENAI_API_KEY    # Should not be empty
echo $ANTHROPIC_API_KEY # Should not be empty

# If empty, add to .env file:
cp .env.example .env
nano .env  # Add your keys
```

### Issue: Tests fail - `ModuleNotFoundError`

**Solution:**
```bash
# Ensure virtual environment is activated:
source .venv/bin/activate

# Reinstall dependencies:
pip install -r requirements.txt
```

### Issue: First test run very slow (~15 minutes)

**This is normal!** First test run downloads:
- Sentence transformers model (~400MB)
- PyTorch dependencies (~1.7GB)

Subsequent runs: ~20 seconds ✅

### Issue: Port 5050 already in use

**Solution:**
```bash
# Use different port:
uvicorn api.server:app --host 0.0.0.0 --port 8080

# Or kill existing process:
lsof -ti:5050 | xargs kill -9
```

### Issue: Database locked error

**Solution:**
```bash
# Close all running instances:
pkill -f "python.*api.server"

# Restart:
make run-api
```

---

## 🖥️ Platform-Specific Notes

### Linux (Ubuntu/Debian)

**Works out of the box!** Just follow automated setup.

```bash
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
./setup.sh
```

### macOS

**Install Homebrew first:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Then:**
```bash
brew install python3 git
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
./setup.sh
```

### Windows (WSL2)

**Install WSL2:**
```powershell
# Run in PowerShell as Administrator
wsl --install
wsl --set-default-version 2
```

**Then inside WSL2:**
```bash
# Follow Linux instructions
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git make
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
./setup.sh
```

**Note:** Native Windows (non-WSL) is not supported in v1.0.0.

### Docker (Coming Soon)

Docker deployment is planned for v1.1.0. For now, use automated setup or manual installation.

---

## 📚 Next Steps

**Once installed:**

1. **Read QUICKSTART.md** - 60-second feature overview
2. **Read MEMORY_GUIDE.md** - Understand the memory system
3. **Experiment with agents** - Try builder, critic, closer
4. **Run multi-agent chains** - `make agent-chain Q="your prompt"`
5. **Track costs** - `make stats` to see usage

---

## 🆘 Need Help?

- **Documentation:** See README.md and QUICKSTART.md
- **Troubleshooting:** See TROUBLESHOOTING.md
- **Issues:** https://github.com/brdfb/multi-agent-orchestrator-v2/issues
- **Health Check:** `curl http://localhost:5050/health`

---

**Version:** 1.0.0
**Last Updated:** November 2025
**Repository:** https://github.com/brdfb/multi-agent-orchestrator-v2

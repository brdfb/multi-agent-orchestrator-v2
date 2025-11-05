# 🔧 Troubleshooting Guide

Quick solutions to common issues with Multi-Agent Orchestrator.

---

## 🚨 Installation Issues

### Error: "mao: command not found"

**Symptom:**
```bash
$ mao auto "test"
bash: mao: command not found
```

**Cause:** Shell aliases not loaded

**Solution:**
```bash
# Reload your shell configuration
source ~/.bashrc   # For bash
source ~/.zshrc    # For zsh

# Test
mao auto "test"
```

**Still not working?**
```bash
# Verify ORCHESTRATOR_HOME is set
echo $ORCHESTRATOR_HOME
# Should print: /home/youruser/.orchestrator

# If empty, add to ~/.bashrc:
echo 'export ORCHESTRATOR_HOME="$HOME/.orchestrator"' >> ~/.bashrc
source ~/.bashrc
```

---

### Error: "ModuleNotFoundError: No module named 'dotenv'"

**Symptom:**
```bash
$ mao auto "test"
Traceback (most recent call last):
  File ".../agent_runner.py", line 3, in <module>
    from dotenv import load_dotenv
ModuleNotFoundError: No module named 'dotenv'
```

**Cause:** The `mao` alias uses system Python instead of virtual environment

**Solution:**
```bash
# Fix the alias in ~/.bashrc
nano ~/.bashrc

# Find this line:
alias mao="python3 $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# Change to:
alias mao="$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# Save and reload
source ~/.bashrc

# Test
mao auto "test"
```

**Alternative - Reinstall dependencies:**
```bash
cd ~/.orchestrator
make clean
make install
```

---

### Error: "No such file or directory: '.venv/bin/python'"

**Symptom:**
```bash
$ mao auto "test"
bash: .venv/bin/python: No such file or directory
```

**Cause:** Virtual environment not created

**Solution:**
```bash
cd ~/.orchestrator
make install
```

---

## 🔑 API Key Issues

### Error: "No API keys detected for any provider"

**Symptom:**
```
⚠️  No API keys detected for any provider
The system cannot function without at least one API key.
```

**Cause:** No API keys configured

**Solution Option 1 - Environment Variables (Recommended):**
```bash
# Add to ~/.bashrc or ~/.zshrc
nano ~/.bashrc

# Add these lines:
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AI..."

# Save and reload
source ~/.bashrc

# Test
echo $OPENAI_API_KEY  # Should show your key
mao auto "test"
```

**Solution Option 2 - .env File:**
```bash
cd ~/.orchestrator
cp .env.example .env
nano .env

# Add your keys:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...

# Save and test
mao auto "test"
```

---

### Error: "AuthenticationError: Incorrect API key"

**Symptom:**
```
litellm.AuthenticationError: AuthenticationError: OpenAIException -
Error code: 401 - {'error': {'message': 'Incorrect API key provided'}}
```

**Cause:** Invalid or expired API key

**Solution:**
```bash
# Check your key
echo $OPENAI_API_KEY

# Get new key from:
# OpenAI: https://platform.openai.com/api-keys
# Anthropic: https://console.anthropic.com/settings/keys
# Google: https://aistudio.google.com/app/apikey

# Update in ~/.bashrc or .env
nano ~/.bashrc  # or nano .env
```

---

### Error: "Billing hard limit has been reached"

**Symptom:**
```
litellm.RateLimitError: RateLimitError: OpenAIException -
Error code: 429 - You exceeded your current quota
```

**Cause:** API credit exhausted

**Solution:**
```bash
# Check your usage/billing at:
# OpenAI: https://platform.openai.com/usage
# Anthropic: https://console.anthropic.com/settings/billing

# Add credits or use another provider:
export DISABLE_OPENAI=1  # Use Anthropic/Google instead
mao auto "test"
```

---

## 🤖 Agent Execution Issues

### Error: "No agent named 'X' found"

**Symptom:**
```bash
$ mao unknown "test"
Error: No agent named 'unknown' found
Available: builder, critic, closer, router
```

**Cause:** Typo in agent name

**Solution:**
```bash
# Use one of: builder, critic, closer, auto
mao auto "test"      ✅
mao builder "test"   ✅
mao Unknown "test"   ❌
```

---

### Error: "JSONDecodeError: Expecting value"

**Symptom:**
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Cause:** API returned non-JSON response (often network/auth issue)

**Solution:**
```bash
# 1. Check internet connection
ping google.com

# 2. Verify API keys
make run-api  # Check startup logs for provider status

# 3. Check logs for details
mao-logs

# 4. Try with a specific provider
export DISABLE_OPENAI=1  # Test with other providers
mao auto "test"
```

---

### Response Truncated / Cut Off

**Symptom:**
Response ends mid-sentence like: `"Here's the code... def main():`

**Cause:** Hit max_tokens limit

**Solution:**
This should not happen anymore (we increased limits to 9K with buffer), but if it does:

```bash
# Check current limits
cat ~/.orchestrator/config/agents.yaml | grep max_tokens

# Should show:
# builder: 9000
# critic: 7000
# closer: 9000

# If not, update:
nano ~/.orchestrator/config/agents.yaml

# Change:
builder:
  max_tokens: 9000  # Increase if needed

# No restart needed - changes apply immediately
```

---

## 🔗 Chain Execution Issues

### Error: "Connection refused" when using mao-chain

**Symptom:**
```bash
$ mao-chain "Design system"
Error: Failed to connect to http://localhost:5050
Connection refused
```

**Cause:** API server not running

**Solution:**
```bash
# Terminal 1: Start server
cd ~/.orchestrator
make run-api

# Terminal 2: Run chain
mao-chain "Design system"
```

**Alternative - Use Makefile:**
```bash
# Doesn't need server running
make agent-chain Q="Design system"
```

---

### Chain Gets Stuck / Hangs

**Symptom:**
Chain shows "Stage 1/3..." and never progresses

**Cause:** API timeout or network issue

**Solution:**
```bash
# 1. Cancel with Ctrl+C
^C

# 2. Check server logs
cd ~/.orchestrator
tail -f logs/api.log  # If exists

# 3. Check last conversation
mao-logs

# 4. Retry with simpler prompt
mao-chain "Simple test"
```

---

### Chain Returns Empty Response

**Symptom:**
```
✅ Stages completed: 3/3
⏱️  Total duration: 45000ms (45.0s)

Stage 1 (builder):
Stage 2 (critic):
Stage 3 (closer):
```

**Cause:** All stages failed or returned empty

**Solution:**
```bash
# Check detailed logs
mao-last-chain

# Look for error messages
# Common causes:
# 1. All providers disabled
# 2. API rate limit
# 3. Network timeout

# Verify providers
curl http://localhost:5050/health | jq '.providers'
```

---

## 💾 Memory System Issues

### Error: "OperationalError: no such table: conversations"

**Symptom:**
```
sqlite3.OperationalError: no such table: conversations
```

**Cause:** Memory database not initialized

**Solution:**
```bash
cd ~/.orchestrator

# Database should auto-create, but if not:
rm -f data/MEMORY/conversations.db  # Delete corrupted DB
mao auto "test"  # Will recreate
```

---

### Memory Not Finding Previous Conversations

**Symptom:**
You know you talked about "authentication" before, but:
```bash
$ make memory-search Q="authentication"
📊 Found 0 conversations
```

**Possible Causes & Solutions:**

**1. Memory disabled for that agent:**
```bash
# Check config
cat config/agents.yaml | grep -A 10 "builder:"

# Ensure:
builder:
  memory_enabled: true  # Must be true
```

**2. Threshold too high:**
```yaml
# In config/agents.yaml, lower min_relevance:
memory:
  min_relevance: 0.25  # Instead of 0.35
```

**3. Embeddings not generated (v0.4.0 upgrade):**
```bash
# Check database
sqlite3 data/MEMORY/conversations.db "SELECT COUNT(*) FROM conversations WHERE embedding IS NULL;"

# If shows non-zero, embeddings missing
# They generate on-demand - just search:
make memory-search Q="test"
```

**4. Search terms too specific:**
```bash
# Try broader terms
make memory-search Q="auth"      # Instead of "authentication middleware JWT"
make memory-search Q="database"  # Instead of "PostgreSQL connection pooling"
```

---

### Memory Search Showing Irrelevant Results

**Symptom:**
Searching for "authentication" returns conversations about "deployment"

**Cause:** Threshold too low or embeddings issue

**Solution:**
```yaml
# In config/agents.yaml, raise threshold:
memory:
  min_relevance: 0.45  # Instead of 0.35

# Or use keyword strategy (more precise):
memory:
  strategy: "keywords"  # Instead of "semantic"
```

---

### Memory Search Is Slow

**Symptom:**
`make memory-search` takes 5+ seconds

**Cause:** Too many conversations (10,000+) or embedding generation

**Solution:**
```bash
# 1. Check conversation count
make memory-stats

# 2. If > 10,000 conversations, cleanup:
make memory-cleanup DAYS=90 CONFIRM=1

# 3. Or switch to keywords (faster):
# In config/agents.yaml:
strategy: "keywords"
```

---

## 🌐 Network & Performance Issues

### Error: "Connection timeout"

**Symptom:**
```
requests.exceptions.ConnectTimeout: Connection to api.openai.com timed out
```

**Cause:** Network issue or API service down

**Solution:**
```bash
# 1. Check internet
ping 8.8.8.8

# 2. Check API status pages:
# OpenAI: https://status.openai.com
# Anthropic: https://status.anthropic.com

# 3. Try different provider
export DISABLE_OPENAI=1
mao auto "test"

# 4. Increase timeout (advanced)
# Edit core/llm_connector.py:
# timeout=120  # Instead of 60
```

---

### Slow Response Times

**Symptom:**
Responses take 30+ seconds

**Possible Causes:**

**1. Using expensive models:**
```yaml
# In config/agents.yaml:
builder:
  model: "anthropic/claude-3-5-sonnet-20241022"  # Slower but thorough

# Try faster models:
builder:
  model: "openai/gpt-4o-mini"  # Much faster
```

**2. Long prompts:**
```bash
# Check token usage
mao-logs  # Look at prompt_tokens

# If > 2000 tokens:
# - Reduce context injection
memory:
  max_context_tokens: 300  # Instead of 600
```

**3. Chain mode is inherently slower:**
```bash
# Single agent (fast)
mao auto "Create API"  # ~5 seconds

# Chain mode (thorough but slow)
mao-chain "Create API"  # ~30 seconds (3 agents)
```

---

## 📝 Logging Issues

### Error: "Permission denied: data/CONVERSATIONS/"

**Symptom:**
```
PermissionError: [Errno 13] Permission denied:
'/home/user/.orchestrator/data/CONVERSATIONS/...'
```

**Cause:** Folder permissions issue

**Solution:**
```bash
cd ~/.orchestrator

# Fix permissions
chmod -R u+w data/
mkdir -p data/CONVERSATIONS data/MEMORY

# Test
mao auto "test"
```

---

### Logs Not Being Created

**Symptom:**
```bash
$ ls data/CONVERSATIONS/
# Empty or very few files
```

**Cause:** Logging disabled or errors being silenced

**Solution:**
```bash
# Check if conversations work
mao auto "test"

# Manually check logs
ls -lth data/CONVERSATIONS/ | head

# If still empty, check for errors:
cd ~/.orchestrator
python3 .venv/bin/python scripts/agent_runner.py auto "test"
# See detailed error output
```

---

## 🔧 Configuration Issues

### Error: "FileNotFoundError: config/agents.yaml"

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory:
'/.../config/agents.yaml'
```

**Cause:** Running command from wrong directory or file missing

**Solution:**
```bash
# Always run from orchestrator directory
cd ~/.orchestrator
mao auto "test"

# Or use the global alias
mao-dir  # Jumps to orchestrator directory
mao auto "test"

# If file missing:
cd ~/.orchestrator
git status  # Check if file deleted
git restore config/agents.yaml  # Restore
```

---

### Changes to agents.yaml Not Applied

**Symptom:**
You edited `config/agents.yaml` but agent still uses old settings

**Cause:** File not saved or syntax error

**Solution:**
```bash
# 1. Verify file saved
cat config/agents.yaml | grep -A 5 "builder:"

# 2. Check for YAML syntax errors
python3 -c "import yaml; yaml.safe_load(open('config/agents.yaml'))"

# 3. No restart needed! Changes apply immediately.
# Just run your command again:
mao builder "test"
```

---

## 🐛 Debugging Tips

### Enable Verbose Logging

```bash
# Run agent_runner.py directly for detailed output
cd ~/.orchestrator
.venv/bin/python scripts/agent_runner.py auto "test" --verbose
```

---

### Check System Health

```bash
# 1. API server health (if running)
curl http://localhost:5050/health | jq

# 2. Check providers
curl http://localhost:5050/health | jq '.providers'

# 3. Check metrics
curl http://localhost:5050/metrics | jq

# 4. Memory stats
make memory-stats
```

---

### View Recent Conversations

```bash
# Last 5 conversations
mao-logs 5

# View specific log file
cat data/CONVERSATIONS/20251105_*.json | jq .
```

---

### Test Each Component

```bash
# 1. Test single agent
mao builder "test"

# 2. Test routing
mao auto "test"

# 3. Test memory
make memory-stats

# 4. Test chain (requires API server)
cd ~/.orchestrator
make run-api  # Terminal 1
mao-chain "test"  # Terminal 2
```

---

## 🔄 Reset / Clean Install

### Nuclear Option: Complete Reset

If all else fails:

```bash
# 1. Backup important conversations
cd ~/.orchestrator
cp -r data/CONVERSATIONS ~/orchestrator-backup/
cp -r data/MEMORY ~/orchestrator-backup/

# 2. Clean everything
make clean
rm -rf .venv data/

# 3. Reinstall
make install

# 4. Restore conversations (optional)
cp -r ~/orchestrator-backup/CONVERSATIONS data/
cp -r ~/orchestrator-backup/MEMORY data/

# 5. Test
mao auto "test"
```

---

## 📞 Getting Help

### Before Asking for Help

Gather this information:

```bash
# 1. Python version
python3 --version

# 2. System info
uname -a

# 3. Recent logs
mao-logs 3

# 4. Error message (full traceback)

# 5. Config
cat config/agents.yaml
```

---

### Where to Ask

1. **GitHub Issues:** https://github.com/your-repo/issues
2. **Documentation:** `~/.orchestrator/README.md`
3. **Community:** [Your community link]

---

## 🎯 Common Issues Checklist

Use this checklist before asking for help:

- [ ] Ran `source ~/.bashrc` after installation
- [ ] Virtual environment exists (`.venv/` folder)
- [ ] At least one API key configured
- [ ] API key valid and has credits
- [ ] Running from `~/.orchestrator` directory or using `mao` alias
- [ ] Internet connection working
- [ ] Tried with `mao auto "test"` (simplest case)
- [ ] Checked `mao-logs` for error details
- [ ] Config file syntax valid (YAML)

---

## 📚 Reference

**Common Commands:**
```bash
mao auto "test"              # Test basic functionality
mao-logs                     # View recent conversations
make memory-stats            # Check memory system
make run-api                 # Start API server (for chains)
cat config/agents.yaml       # View configuration
source ~/.bashrc             # Reload shell config
```

**Common Files:**
```
~/.orchestrator/
├── config/agents.yaml       # Agent configuration
├── data/CONVERSATIONS/      # JSON logs
├── data/MEMORY/            # SQLite database
└── .env                     # API keys (optional)
```

**Environment Variables:**
```bash
ORCHESTRATOR_HOME            # Path to orchestrator
OPENAI_API_KEY              # OpenAI API key
ANTHROPIC_API_KEY           # Anthropic API key
GOOGLE_API_KEY              # Google API key
DISABLE_OPENAI              # Disable OpenAI provider
DISABLE_ANTHROPIC           # Disable Anthropic provider
DISABLE_GOOGLE              # Disable Google provider
```

---

**Most common issues are:**
1. Alias not loaded → `source ~/.bashrc`
2. No API keys → Add to `~/.bashrc` or `.env`
3. Wrong directory → Use `cd ~/.orchestrator`
4. Chain needs server → Run `make run-api` first

**Try these first before advanced troubleshooting!** 🚀

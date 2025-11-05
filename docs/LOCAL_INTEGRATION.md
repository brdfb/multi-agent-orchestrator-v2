# Local Integration Guide - Centralized Orchestrator

This guide shows how to set up the Multi-Agent Orchestrator as a **centralized system** that all your projects can use.

## Why Centralized?

**Before (Per-Project):**
- 🔴 Each project has its own copy
- 🔴 Multiple installations to maintain
- 🔴 Inconsistent versions
- 🔴 Wasted disk space

**After (Centralized):**
- ✅ Single installation at `~/.orchestrator`
- ✅ All projects share the same system
- ✅ One place to update and configure
- ✅ Available everywhere via shell alias

---

## Installation

### One-Command Setup

```bash
# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/your-org/orchestrator/main/setup_orchestrator_local.sh | bash

# Or if already downloaded
chmod +x ~/setup_orchestrator_local.sh
~/setup_orchestrator_local.sh
```

### What It Does

1. **Moves** `~/projects/client-xyz` → `~/.orchestrator`
2. **Organizes** projects under `~/projects/`
3. **Adds aliases** to `~/.bashrc`:
   - `mao` - Main command
   - `mao-builder`, `mao-critic`, `mao-closer` - Direct agents
   - `mao-dir` - Jump to orchestrator directory
4. **Creates** `~/.orchestrator/orchestrator.mk` for Makefile integration
5. **Generates** example project

### Manual Installation

If you prefer manual setup:

```bash
# 1. Move orchestrator
mv ~/projects/client-xyz ~/.orchestrator

# 2. Organize projects
mkdir -p ~/projects

# 3. Add to ~/.bashrc
cat >> ~/.bashrc <<'EOF'

# >>> Multi-Agent Orchestrator Integration >>>
export ORCHESTRATOR_HOME="$HOME/.orchestrator"
export PYTHONPATH="$ORCHESTRATOR_HOME:$PYTHONPATH"

# Quick access alias (uses venv Python to avoid module errors)
alias mao="$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/agent_runner.py"
# <<< Multi-Agent Orchestrator Integration <<<
EOF

# 4. Reload
source ~/.bashrc

# 5. Verify
mao auto "Hello, test"
```

---

## Usage

### Shell Alias (Recommended)

The fastest way to use the orchestrator anywhere:

```bash
# Auto-route to best agent
mao auto "Analyze this for security issues"

# Specific agents
mao builder "Create a REST API endpoint for users"
mao critic "Review my database schema"
mao closer "Summarize this discussion into action items"
```

**From any directory:**
```bash
cd ~/projects/my-app
mao auto "How can I optimize this React component?"

cd ~/projects/another-project
mao builder "Write a Python function to parse JSON"
```

### Makefile Integration

Add orchestrator to your project's Makefile:

**In your project's Makefile:**
```makefile
# Include orchestrator targets
include $(HOME)/.orchestrator/orchestrator.mk

# Your existing targets
build:
	npm run build

test:
	npm test

# Use orchestrator in your workflow
review:
	make mao-ask AGENT=critic Q="Review the build output"

design:
	make mao-chain Q="Design a caching strategy"
```

**Available targets:**
```bash
make mao-ask AGENT=auto Q="Your question"
make mao-chain Q="Your question"
make mao-last                    # View last conversation
make mao-help                    # Show help
```

### Python Integration

Import and use programmatically:

```python
import sys
sys.path.insert(0, os.path.expanduser('~/.orchestrator'))

from core.agent_runtime import AgentRuntime

runtime = AgentRuntime()
result = runtime.run("builder", "Create a REST endpoint")
print(result.response)
```

---

## Project Examples

### Example 1: Node.js Project

```makefile
# Makefile
include $(HOME)/.orchestrator/orchestrator.mk

.PHONY: dev build review

dev:
	npm run dev

build:
	npm run build

# Integrate AI review
review:
	@echo "Building project..."
	@npm run build
	@echo "Running AI code review..."
	@make mao-ask AGENT=critic Q="Review my TypeScript build output for issues"

# Chain for architecture decisions
design:
	make mao-chain Q="Design a scalable user authentication system"
```

Usage:
```bash
make dev        # Normal development
make review     # Build + AI review
make design     # AI architecture chain
```

### Example 2: Python Project

```makefile
# Makefile
include $(HOME)/.orchestrator/orchestrator.mk

.PHONY: test lint analyze

test:
	pytest

lint:
	ruff check .

# AI-powered code analysis
analyze:
	@make mao-ask AGENT=critic Q="Analyze Python code in $(shell pwd) for performance issues"

# Get implementation suggestions
implement:
	@if [ -z "$(FEATURE)" ]; then \
		echo "Usage: make implement FEATURE='feature description'"; \
		exit 1; \
	fi
	@make mao-ask AGENT=builder Q="Implement: $(FEATURE)"
```

Usage:
```bash
make test                                    # Run tests
make analyze                                 # AI code analysis
make implement FEATURE="Add caching layer"  # AI implementation
```

### Example 3: DevOps / Infrastructure

```makefile
# Makefile
include $(HOME)/.orchestrator/orchestrator.mk

.PHONY: deploy plan-review

deploy:
	terraform apply

# AI review of Terraform plan
plan-review:
	@terraform plan -out=tfplan
	@terraform show tfplan > tfplan.txt
	@make mao-ask AGENT=critic Q="Review this Terraform plan: $$(cat tfplan.txt)"
	@rm tfplan.txt

# Generate IaC code
generate-iac:
	@make mao-ask AGENT=builder Q="Create Terraform code for a 3-tier AWS architecture"
```

---

## Available Aliases

After setup, these aliases are available system-wide:

### Main Commands
```bash
mao <agent> <prompt>        # Main command
mao auto "Question"         # Auto-route
mao builder "Task"          # Direct to builder
mao critic "Code"           # Direct to critic
mao closer "Discussion"     # Direct to closer
```

### Quick Aliases
```bash
mao-builder "Task"          # Same as: mao builder "Task"
mao-critic "Code"           # Same as: mao critic "Code"
mao-closer "Summary"        # Same as: mao closer "Summary"
mao-auto "Question"         # Same as: mao auto "Question"
```

### Management
```bash
mao-dir                     # cd ~/.orchestrator
mao-status                  # Check git status (if repo)
mao-update                  # git pull (if repo)
```

---

## Configuration

### Global Settings

Edit `~/.orchestrator/config/agents.yaml` to customize:
- Agent models
- System prompts
- Temperature/tokens
- Add new agents

```yaml
agents:
  builder:
    model: "anthropic/claude-3-5-sonnet-20241022"
    temperature: 0.3

  # Add your custom agent
  researcher:
    model: "openai/gpt-4o"
    system: "You are a thorough researcher..."
    temperature: 0.4
```

### Per-Project Override

Create `.orchestrator.yaml` in your project root:

```yaml
# Override default settings for this project
default_agent: builder
agents:
  builder:
    model: "openai/gpt-4o-mini"  # Use cheaper model for this project
```

(Note: Override support needs to be implemented)

---

## Advanced Usage

### Multi-Project Workflow

```bash
# Terminal 1: Web app
cd ~/projects/webapp
mao builder "Create a login component"

# Terminal 2: API
cd ~/projects/api
mao builder "Create authentication endpoint"

# Terminal 3: Review both
cd ~/projects/docs
mao critic "Review login flow across webapp and API"
```

All share the same orchestrator, conversation logs are in `~/.orchestrator/data/CONVERSATIONS/`

### CI/CD Integration

**GitHub Actions:**
```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Orchestrator
        run: |
          curl -fsSL https://install.orchestrator.dev | bash
          source ~/.bashrc

      - name: AI Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          mao critic "Review changes in this PR: $(git diff HEAD~1)"
```

### Git Hooks

Add AI review to pre-commit:

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running AI code review..."
mao critic "Review these changes: $(git diff --cached)" > /tmp/review.txt
cat /tmp/review.txt
read -p "Proceed with commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi
```

---

## Directory Structure

After setup:

```
~/
├── .orchestrator/              # Main system (centralized)
│   ├── config/
│   │   ├── agents.yaml        # Agent configuration
│   │   └── settings.py
│   ├── core/
│   │   ├── llm_connector.py
│   │   ├── agent_runtime.py
│   │   └── logging_utils.py
│   ├── api/
│   │   └── server.py
│   ├── scripts/
│   │   └── agent_runner.py    # Used by 'mao' alias
│   ├── data/
│   │   └── CONVERSATIONS/     # All conversations logged here
│   ├── orchestrator.mk        # Shared Makefile
│   └── .venv/                 # Virtual environment
│
├── projects/                   # Your projects
│   ├── webapp/
│   ├── api/
│   ├── infra/
│   └── _ORCHESTRATOR_EXAMPLE/ # Example integration
│
├── .bashrc                     # Contains orchestrator aliases
└── setup_orchestrator_local.sh # Setup script
```

---

## Troubleshooting

### "mao: command not found"

```bash
# Reload bashrc
source ~/.bashrc

# Or restart terminal
```

### "No module named 'core'"

```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Should include ~/.orchestrator
# If not, re-run setup
~/setup_orchestrator_local.sh
```

### "ModuleNotFoundError: dotenv" or "ModuleNotFoundError: litellm"

**Problem:** System Python doesn't have required packages installed.

**Solution:** The `mao` alias must use the virtual environment Python:

```bash
# Fix the alias in ~/.bashrc
# Change this:
alias mao="python3 $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# To this:
alias mao="$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# Then reload
source ~/.bashrc

# Or reinstall dependencies
cd ~/.orchestrator
make install
```

### "API keys not found"

```bash
# Check environment
echo $OPENAI_API_KEY

# If not set, add to ~/.bashrc:
export OPENAI_API_KEY=sk-...

# Or create .env in ~/.orchestrator:
cd ~/.orchestrator
cp .env.example .env
nano .env
```

### Makefile integration not working

```bash
# Test if orchestrator.mk exists
ls -la ~/.orchestrator/orchestrator.mk

# Test include
cd ~/projects/_ORCHESTRATOR_EXAMPLE
make mao-help
```

---

## Migration from Per-Project Setup

If you have orchestrator installed in multiple projects:

```bash
# 1. Choose one as the source (latest version)
cd ~/projects/project-with-orchestrator

# 2. Move to centralized location
mv . ~/.orchestrator

# 3. Run setup script
~/setup_orchestrator_local.sh

# 4. Remove old installations
rm -rf ~/projects/project-a/orchestrator
rm -rf ~/projects/project-b/orchestrator

# 5. Update Makefiles to use shared version
# Add to each project:
# include $(HOME)/.orchestrator/orchestrator.mk
```

---

## Uninstallation

If you need to remove:

```bash
# 1. Remove orchestrator
rm -rf ~/.orchestrator

# 2. Remove from bashrc
nano ~/.bashrc
# Delete the "Multi-Agent Orchestrator Integration" section

# 3. Remove from projects
# Remove 'include $(HOME)/.orchestrator/orchestrator.mk' from Makefiles
```

---

## Benefits Summary

✅ **Single Source of Truth**
- One installation, one configuration
- Update once, affects all projects

✅ **Instant Access**
- Use `mao` from anywhere
- No per-project setup needed

✅ **Consistent Experience**
- Same agents, same models
- Unified conversation logs

✅ **Easy Integration**
- One line in Makefile
- Works with any project type

✅ **Resource Efficient**
- One virtual environment
- Shared dependencies

✅ **Maintainable**
- Easy to update
- Easy to backup/restore

---

## Next Steps

1. **Run setup:** `~/setup_orchestrator_local.sh`
2. **Test alias:** `mao auto "Hello"`
3. **Try in project:** Add `include $(HOME)/.orchestrator/orchestrator.mk` to Makefile
4. **Explore example:** `cd ~/projects/_ORCHESTRATOR_EXAMPLE && make help`
5. **Read docs:** Check `~/.orchestrator/README.md` for full features

---

**Version:** 0.3.0 - Local Integration
**Updated:** 2025-11-05

**Recent Updates:**
- ✅ Fixed `mao` alias to use venv Python (prevents ModuleNotFoundError)
- ✅ Added Web UI information (localhost:5050)
- ✅ Chain workflow support with progress indicators
- ✅ Google Gemini integration
- ✅ Enhanced troubleshooting section

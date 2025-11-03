# Environment Setup Guide

This guide explains how to configure API keys for the Multi-Agent Orchestrator in different scenarios.

## TL;DR

**The system is flexible**: Use whichever method works for you. Environment variables take precedence over `.env` files.

```bash
# Check if you already have keys set
echo $OPENAI_API_KEY

# If yes: You're done! Skip .env setup.
# If no: Choose a method below.
```

---

## Method 1: Environment Variables (Recommended for CI/Production)

### Permanent Setup (Recommended)

**For Bash users (`~/.bashrc`):**
```bash
# Add to ~/.bashrc
echo 'export OPENAI_API_KEY=sk-...' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
echo 'export GOOGLE_API_KEY=...' >> ~/.bashrc

# Reload
source ~/.bashrc
```

**For Zsh users (`~/.zshrc`):**
```bash
# Add to ~/.zshrc
echo 'export OPENAI_API_KEY=sk-...' >> ~/.zshrc
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.zshrc
echo 'export GOOGLE_API_KEY=...' >> ~/.zshrc

# Reload
source ~/.zshrc
```

### Temporary Setup (Current Session Only)

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...
```

### Verify

```bash
printenv | grep API_KEY
# Should show your keys (masked for security)
```

### Advantages
- ✅ Works across all projects
- ✅ Ideal for CI/CD (GitHub Actions, GitLab CI, etc.)
- ✅ No files to git-ignore
- ✅ System-wide availability

---

## Method 2: .env File (Recommended for Local Development)

### Setup

```bash
# 1. Copy template
cp .env.example .env

# 2. Edit with your favorite editor
nano .env
# or
vim .env
# or
code .env

# 3. Add your keys (replace placeholder values)
```

Example `.env` content:
```bash
OPENAI_API_KEY=sk-proj-abc123...
ANTHROPIC_API_KEY=sk-ant-xyz789...
GOOGLE_API_KEY=AIza...
```

### Verify

```bash
cat .env | grep API_KEY
# Should show your keys
```

### Advantages
- ✅ Project-specific configuration
- ✅ Easy to switch between projects
- ✅ Good for development/testing
- ✅ Can be shared (with dummy values) in repos

### Important Notes
- ⚠️ **Never commit `.env` to git** (it's in `.gitignore`)
- ⚠️ Use `.env.example` for templates only
- ⚠️ Environment variables override `.env` values

---

## Method 3: direnv (Advanced)

For users who want automatic environment switching per directory:

```bash
# 1. Install direnv
# macOS
brew install direnv

# Linux
sudo apt install direnv

# 2. Add to shell config
# For bash: add to ~/.bashrc
eval "$(direnv hook bash)"

# For zsh: add to ~/.zshrc
eval "$(direnv hook zsh)"

# 3. Create .envrc in project
cat > .envrc << 'EOF'
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...
EOF

# 4. Allow direnv
direnv allow
```

---

## Method 4: CI/CD Environments

### GitHub Actions

```yaml
# .github/workflows/test.yml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: make test
```

### GitLab CI

```yaml
# .gitlab-ci.yml
variables:
  OPENAI_API_KEY: $OPENAI_API_KEY
  ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
  GOOGLE_API_KEY: $GOOGLE_API_KEY

test:
  script:
    - make test
```

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN make install

# Keys passed at runtime
CMD ["make", "run-api"]
```

```bash
# Run with environment variables
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY \
           -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
           -e GOOGLE_API_KEY=$GOOGLE_API_KEY \
           myapp
```

---

## Precedence Order

The system loads keys in this order (later overrides earlier):

1. `.env` file (if exists) - loaded first
2. Environment variables - take precedence
3. System environment - highest priority

**Example:**
```bash
# .env contains:
OPENAI_API_KEY=from_dotenv_file

# Shell has:
export OPENAI_API_KEY=from_shell

# Result: Uses "from_shell" (environment wins)
```

---

## Verification

### Check What's Loaded

When you start the system, it shows the source:

```bash
make run-api

# You'll see ONE of:
# 🔑 API keys loaded from environment variables (shell/CI)
# 📁 API keys loaded from .env file (development mode)
# ⚠️  No API keys detected - requests will fail
```

### Manual Check

```bash
# Check environment
printenv | grep API_KEY

# Check .env file
cat .env | grep API_KEY 2>/dev/null || echo "No .env file"

# Test in Python
python3 -c "import os; print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

---

## FAQ

**Q: I have keys in both `.env` and environment. Which is used?**

A: Environment variables take precedence. The system uses shell/export values first.

**Q: Do I need a `.env` file if I've exported keys in `~/.bashrc`?**

A: No! The system automatically uses environment variables. `.env` is optional.

**Q: Why does the documentation mention both methods?**

A: Different users prefer different approaches:
- Developers often use `.env` per project
- CI/CD systems use environment variables
- Production deployments use system environment

**Q: Can I use both methods?**

A: Yes, but environment variables will override `.env` values.

**Q: How do I switch between different API keys?**

A:
- **Environment method**: Change exports in shell
- **.env method**: Edit `.env` file
- **direnv method**: Switch directories (automatic)

**Q: Is it safe to commit `.env.example`?**

A: Yes! It contains placeholder values only. Never commit `.env` with real keys.

**Q: How do I rotate keys?**

A:
```bash
# Environment method
export OPENAI_API_KEY=new_key_here

# .env method
nano .env  # Update and save

# Verify
make run-api  # Should show updated key source
```

---

## Security Best Practices

1. **Never commit `.env`** - It's in `.gitignore`, keep it that way
2. **Use separate keys per environment** - Dev, staging, prod should have different keys
3. **Rotate keys regularly** - Most providers allow creating new keys
4. **Check `.gitignore`** - Ensure `.env` is listed
5. **Use read-only keys** - If provider supports it (for read-heavy apps)
6. **Monitor usage** - Set alerts in provider dashboards

---

## Troubleshooting

**"No API keys detected"**

```bash
# 1. Check environment
echo $OPENAI_API_KEY

# 2. Check .env exists
ls -la .env

# 3. Check .env contents (should not be empty)
cat .env

# 4. Reload shell config
source ~/.bashrc  # or ~/.zshrc

# 5. Try explicit export
export OPENAI_API_KEY=sk-...
```

**"Keys not working after changing .env"**

- `.env` is only read on startup
- Restart the server: `Ctrl+C` then `make run-api`

**"Different keys in different terminals"**

- Check which shell config you're using (`.bashrc` vs `.bash_profile`)
- Ensure keys are exported, not just set (`export KEY=value`)

---

## Getting API Keys

### OpenAI
1. Visit https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy and save immediately (can't view again)

### Anthropic
1. Visit https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy the key (starts with `sk-ant-`)

### Google AI (Gemini)
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIza`)

---

## Summary

**Recommended Approach:**

- **Local Development**: Use `.env` file (easy to switch projects)
- **CI/CD**: Use environment variables (GitHub/GitLab secrets)
- **Production**: Use system environment or secrets manager (AWS Secrets Manager, HashiCorp Vault)

**The system is flexible** - choose what works for your workflow. It will automatically detect and use the available keys.

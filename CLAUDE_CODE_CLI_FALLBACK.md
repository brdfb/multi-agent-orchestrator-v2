# Provider Fallback & Feature Flags - Implementation Guide

## Problem Statement

**Objective**: Make the Multi-Agent Orchestrator **independent from Claude Code** and resilient to provider outages. The system should continue working even if Anthropic (Claude API) is unavailable, disabled, or has no API key.

**Before**: Single provider failure = system failure
**After**: Automatic transparent fallback to alternative providers

## Solution Architecture

### High-Level Design

```
User Request
    ↓
AgentRuntime.run(agent="builder", prompt="...")
    ↓
LLMConnector.call(model="anthropic/claude-...", fallback_order=[...])
    ↓
[Try Primary] is_provider_enabled("anthropic") → NO
    ↓
[Fallback #1] Try "openai/gpt-4o" → SUCCESS
    ↓
Return LLMResponse(
    model="openai/gpt-4o",
    original_model="anthropic/claude-3-5-sonnet-20241022",
    fallback_reason="Provider 'anthropic' unavailable",
    fallback_used=True
)
```

### Key Components

1. **Config Layer** (`config/settings.py`)
   - `is_provider_enabled(provider)`: Check if provider available
   - `get_available_providers()`: List active providers
   - `get_provider_status()`: Detailed status dict
   - `ProviderUnavailableError`: Custom exception

2. **Agent Config** (`config/agents.yaml`)
   - Each agent has `fallback_order` list
   - Example:
     ```yaml
     builder:
       model: "anthropic/claude-3-5-sonnet-20241022"
       fallback_order:
         - "openai/gpt-4o"
         - "openai/gpt-4o-mini"
         - "google/gemini-2.0-flash-exp"
     ```

3. **LLM Connector** (`core/llm_connector.py`)
   - `_try_model()`: Attempts single model call
   - `call(..., fallback_order)`: Main entry point with fallback logic
   - Returns `LLMResponse` with fallback metadata

4. **Runtime** (`core/agent_runtime.py`)
   - Passes `fallback_order` from agent config to `LLMConnector`
   - Logs fallback metadata to conversation JSON

5. **API Server** (`api/server.py`)
   - `/health` endpoint includes provider status
   - Startup logs show available/disabled providers

## Environment Matrix

| Scenario | ANTHROPIC_API_KEY | OPENAI_API_KEY | GOOGLE_API_KEY | DISABLE_ANTHROPIC | Result |
|----------|-------------------|----------------|----------------|-------------------|---------|
| 1. All keys | ✓ | ✓ | ✓ | - | All providers available |
| 2. No Anthropic key | ✗ | ✓ | ✓ | - | Anthropic auto-disabled, fallback works |
| 3. Explicit disable | ✓ | ✓ | ✓ | 1 | Anthropic disabled despite key |
| 4. Only Google | ✗ | ✗ | ✓ | - | Only Google available, deep fallback |
| 5. No keys | ✗ | ✗ | ✗ | - | All disabled, error returned |

## Feature Flags

### Environment Variables

```bash
# Disable specific providers
export DISABLE_ANTHROPIC=1    # Claude models unavailable
export DISABLE_OPENAI=1       # GPT models unavailable
export DISABLE_GOOGLE=1       # Gemini models unavailable
export DISABLE_OPENROUTER=1   # OpenRouter unavailable

# Truthy values: "1", "true", "yes", "on" (case-insensitive)
```

### Auto-Disable Logic

Providers are **automatically disabled** if:
1. Explicit disable flag is set (e.g., `DISABLE_ANTHROPIC=1`)
2. API key environment variable is missing or empty

## Example Usage

### CLI Commands

```bash
# 1. Normal operation (all providers available)
make agent-ask AGENT=builder Q="Create a REST API"
# Uses: anthropic/claude-3-5-sonnet-20241022

# 2. Anthropic disabled - automatic fallback
export DISABLE_ANTHROPIC=1
make agent-ask AGENT=builder Q="Create a REST API"
# Uses: openai/gpt-4o (first fallback)

# 3. Anthropic + OpenAI disabled - deep fallback
export DISABLE_ANTHROPIC=1
export DISABLE_OPENAI=1
make agent-ask AGENT=builder Q="Create a REST API"
# Uses: google/gemini-2.0-flash-exp (second fallback)

# 4. Check provider status
curl http://localhost:5050/health | jq '.providers'

# 5. View fallback in logs
make agent-last | jq '{fallback_used, original_model, model, fallback_reason}'
```

### API Usage

```bash
# Health check with provider status
curl -s http://localhost:5050/health | jq
{
  "status": "ok",
  "service": "multi-agent-orchestrator",
  "providers": {
    "openai": {"enabled": true, "has_api_key": true, "disabled_by_flag": false},
    "anthropic": {"enabled": false, "has_api_key": false, "disabled_by_flag": false},
    "google": {"enabled": true, "has_api_key": true, "disabled_by_flag": false}
  },
  "available_providers": ["openai", "google"],
  "total_available": 2
}

# Single agent request (fallback automatic)
curl -X POST http://localhost:5050/ask \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "builder",
    "prompt": "Test fallback"
  }'

# Chain request (all stages use fallback if needed)
curl -X POST http://localhost:5050/chain \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Design a system",
    "stages": ["builder", "critic", "closer"]
  }'
```

### Python API

```python
from config.settings import (
    is_provider_enabled,
    get_available_providers,
    get_provider_status,
    ProviderUnavailableError
)

# Check if provider available
if is_provider_enabled("anthropic"):
    print("Claude available")
else:
    print("Claude unavailable - fallback active")

# Get all available providers
available = get_available_providers()
print(f"Active: {', '.join(available)}")

# Detailed status
status = get_provider_status()
for provider, info in status.items():
    print(f"{provider}: enabled={info['enabled']}, has_key={info['has_api_key']}")
```

## Log Output Examples

### Normal Operation (No Fallback)
```json
{
  "agent": "builder",
  "model": "anthropic/claude-3-5-sonnet-20241022",
  "provider": "anthropic",
  "fallback_used": false,
  "response": "Here's your implementation...",
  "duration_ms": 1234
}
```

### With Fallback
```json
{
  "agent": "builder",
  "model": "openai/gpt-4o",
  "provider": "openai",
  "original_model": "anthropic/claude-3-5-sonnet-20241022",
  "fallback_reason": "Provider 'anthropic' unavailable",
  "fallback_used": true,
  "response": "Here's your implementation...",
  "duration_ms": 987
}
```

### All Providers Failed
```json
{
  "agent": "builder",
  "model": "anthropic/claude-3-5-sonnet-20241022",
  "provider": "anthropic",
  "fallback_used": false,
  "response": "",
  "error": "All models failed. Last error: Provider 'google' disabled or missing API key",
  "duration_ms": 123
}
```

## Startup Output

### All Providers Available
```
🔑 API keys loaded from environment variables (shell/CI)
✓ Available providers: openai, anthropic, google
```

### Anthropic Disabled
```
🔑 API keys loaded from environment variables (shell/CI)
✓ Available providers: openai, google
✗ Disabled providers: anthropic
```

### No Providers
```
⚠️  No API keys detected - requests will fail
⚠️  No providers available!
✗ Disabled providers: openai, anthropic, google, openrouter
```

## Common Errors & Solutions

### Error: "All models failed"
**Cause**: All providers in fallback chain unavailable
**Solution**:
```bash
# Check provider status
curl http://localhost:5050/health | jq '.available_providers'

# Ensure at least one provider has valid API key
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=...
```

### Error: "Provider 'anthropic' disabled or missing API key"
**Cause**: Anthropic explicitly disabled or key missing
**Solution**:
```bash
# If intentional - no action needed (fallback works)
# If unintentional:
unset DISABLE_ANTHROPIC
export ANTHROPIC_API_KEY=sk-ant-...
```

### Issue: Fallback not working
**Cause**: `fallback_order` missing in `agents.yaml`
**Solution**:
```yaml
# Add fallback_order to agent config
builder:
  model: "anthropic/claude-3-5-sonnet-20241022"
  fallback_order:
    - "openai/gpt-4o-mini"
    - "google/gemini-2.0-flash-exp"
```

### Issue: Override model bypasses fallback
**Behavior**: By design - model overrides skip fallback logic
**Reason**: User explicitly requested specific model
**Workaround**: Don't use override if fallback needed

## Testing

### Unit Tests
```bash
# Run fallback-specific tests
pytest tests/test_llm_connector_fallback.py -v
pytest tests/test_chain_fallback_e2e.py -v

# All tests
make test
```

### Manual Testing
```bash
# Test 1: Primary provider works
make agent-ask AGENT=builder Q="test"

# Test 2: Disable primary, fallback works
export DISABLE_ANTHROPIC=1
make agent-ask AGENT=builder Q="test"
make agent-last | jq '.fallback_used'  # Should be true

# Test 3: Chain with fallback
export DISABLE_ANTHROPIC=1
make agent-chain Q="short prompt"

# Test 4: Health check
curl http://localhost:5050/health | jq
```

## Architecture Decisions

### Why Fallback at LLMConnector Level?
- **Single responsibility**: Connector handles all LLM communication
- **Transparency**: Fallback logic centralized, not scattered
- **Logging**: Automatic fallback metadata in every log

### Why fallback_order in agents.yaml?
- **Flexibility**: Each agent can have different fallback strategy
- **Cost optimization**: Builder uses expensive → cheap, critic uses cheap only
- **No code changes**: Update fallback order without touching Python

### Why Auto-Disable on Missing Key?
- **Developer experience**: Don't require explicit disable flags
- **CI/CD friendly**: Partial key sets work automatically
- **Security**: No placeholder/invalid keys needed

### Why Not Silent Fallback?
- **Observability**: Every fallback logged with reason
- **Cost tracking**: Know when using more expensive fallback
- **Debugging**: Identify provider issues immediately

## Migration Guide

### For Existing Deployments

1. **Add API keys** (if not already present):
   ```bash
   export OPENAI_API_KEY=sk-...
   export GOOGLE_API_KEY=...
   # Anthropic is now optional
   ```

2. **Update agents.yaml** (automatic on git pull):
   ```bash
   git pull origin main
   # config/agents.yaml now has fallback_order for all agents
   ```

3. **Restart services**:
   ```bash
   # API server
   make run-api
   # Check startup logs for provider status
   ```

4. **Verify**:
   ```bash
   curl http://localhost:5050/health | jq '.available_providers'
   ```

### Breaking Changes
**None** - fully backward compatible. Existing configs without `fallback_order` still work (no fallback, original behavior).

## Performance Implications

- **Latency**: Fallback adds <100ms overhead (provider check)
- **Success path**: Zero overhead if primary provider available
- **Failure path**: Sequential fallback attempts (1-2 sec max)
- **Retry logic**: Unchanged (still 1 retry per model)

## Security Considerations

- **API keys**: Fallback doesn't expose keys (masked in logs)
- **Provider enumeration**: `/health` shows provider status (consider auth in prod)
- **Error messages**: Generic errors prevent provider enumeration attacks

## Future Enhancements

- **Load balancing**: Round-robin across available providers
- **Cost-based routing**: Auto-select cheapest available provider
- **Provider health checks**: Periodic availability probes
- **Fallback metrics**: Track fallback frequency per agent

---

**Version**: 0.2.0
**Status**: Production Ready
**Last Updated**: 2024-11-04

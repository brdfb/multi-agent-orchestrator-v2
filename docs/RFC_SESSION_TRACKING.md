# RFC: Session-Based Conversation Tracking

**Status:** Proposed
**Version:** 0.11.0 (Future)
**Author:** System Design Team
**Date:** 2025-11-08
**Implementation Effort:** 2-3 days

---

## 📋 Executive Summary

Add session-based conversation tracking to support sequential, ChatGPT-style conversations while maintaining long-term knowledge retrieval capabilities.

**Current State:** Stateless - each request independent
**Proposed State:** Hybrid - session context + knowledge context
**Impact:** Better UX for iterative work, consistent behavior across CLI/UI

---

## 🤔 Problem Statement

### Current System Behavior

```python
# Request 1:
make agent-ask Q="Python'da matplotlib ile chart nasıl çizilir?"
# Response: [Chart kodu]
# System: UNUT!

# Request 2:
make agent-ask Q="Chart'a kırmızı renk ekle"
# System: ❌ "Hangi chart?" - önceki request'i BİLMİYOR!
# Response: Generic renk değiştirme kodu (chart-specific değil)
```

**Root Cause:** System stateless - her request bağımsız, conversation thread yok.

---

### User Expectation (ChatGPT Mental Model)

```
User: "Chart nasıl çizilir?"
Assistant: [Chart kodu]

User: "Renk ekle"
Assistant: ✅ Önceki chart kodunu görür → renk ekler

User: "Başlık ekle"
Assistant: ✅ Chart + renk versiyonunu görür → başlık ekler

→ Sequential conversation, iterative development
```

**Expectation:** System should remember recent conversation (session context).

---

### Real-World Impact

**Tester Feedback (Friend):**

> "Chart visualization konuşuldu (ID 8), sonra 'Chart'a renk ekle' dedim.
> System chart conversation inject ETMEDİ, generic context aldı.
> Sequential conversation bekliyordum (WhatsApp-style) ama
> knowledge base gibi davrandı (Wikipedia-style)."

**Developer Experience:**

```bash
# Mevcut sistem (stateless):
make agent-ask Q="FastAPI projesi başlat"
make agent-ask Q="Authentication ekle"
# ↑ "Hangi projeye?" - her seferinde context tekrar vermek gerekir!

# Beklenen (stateful):
make agent-ask Q="FastAPI projesi başlat"
make agent-ask Q="Authentication ekle"
# ✅ Önceki projeye ekler, context tekrarı gerekmez
```

---

## 🎯 Goals

### Primary Goals

1. **Sequential Conversation Support**
   - "Chart'a renk ekle" → önceki chart conversation'ı görür
   - "Buna authentication ekle" → önceki kod/proje bağlamını bilir
   - ChatGPT-style iterative development mümkün olur

2. **CLI & UI Consistency**
   - CLI ve Web UI aynı davranış sergiler
   - User confusion minimize edilir
   - Unified UX across interfaces

3. **Backward Compatibility**
   - Mevcut stateless usage devam eder (optional)
   - Eski conversation'lar korunur
   - API backward compatible

### Secondary Goals

4. **Long-term Knowledge Preservation**
   - Session dışı (eski) conversation'lar semantic search ile bulunur
   - Knowledge base functionality korunur
   - Dual-context model (session + knowledge)

5. **Performance**
   - Session overhead minimal (< 100ms)
   - Auto-cleanup (eski session'lar silinir)
   - Scalable (1000+ concurrent sessions)

---

## 🏗️ Proposed Architecture

### High-Level Design

```
┌─────────────────────────────────────────────┐
│           User Request                      │
│  "Chart'a renk ekle" + session_id           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Session Manager                     │
│  - Get/Create session                       │
│  - Auto-generate ID (if not provided)       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Context Aggregator                  │
├─────────────────────────────────────────────┤
│  1. Session Context (recent 5 messages)     │
│     - Same session_id                       │
│     - Chronological order                   │
│     - Budget: 300 tokens                    │
│                                             │
│  2. Knowledge Context (semantic search)     │
│     - Exclude current session               │
│     - time_decay: 168h (gentle)             │
│     - Budget: 300 tokens                    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         LLM Call (with full context)        │
│  Prompt + Session + Knowledge               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Save to Database                    │
│  - Store with session_id                    │
│  - Track session metadata                   │
└─────────────────────────────────────────────┘
```

---

### Database Schema Changes

```sql
-- Add session_id to conversations table
ALTER TABLE conversations ADD COLUMN session_id TEXT;
CREATE INDEX idx_session_id ON conversations(session_id);

-- New table: sessions
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    source TEXT,  -- 'cli', 'ui', 'api'
    metadata TEXT  -- JSON: {terminal_pid, user_agent, etc.}
);

-- Auto-cleanup trigger (delete sessions older than 24 hours)
CREATE TRIGGER cleanup_old_sessions
AFTER INSERT ON sessions
BEGIN
    DELETE FROM sessions
    WHERE last_active < datetime('now', '-24 hours');
END;
```

---

### Session ID Generation Strategy

#### CLI (Terminal-Based)

```python
def generate_cli_session_id():
    """
    Auto-generate session ID for CLI based on terminal.

    Strategy: terminal_pid + hour
    - Same terminal, same hour = same session
    - New terminal = new session
    - New hour = new session (auto-reset)

    Example: cli-12345-2025110809
    """
    pid = os.getpid()
    hour = datetime.now().strftime("%Y%m%d%H")
    return f"cli-{pid}-{hour}"
```

**Rationale:**
- ✅ Auto-session per terminal (user doesn't think about it)
- ✅ Hourly reset (conversations don't grow unbounded)
- ✅ No user input required (seamless UX)

**Example:**
```bash
# Terminal 1 (PID 12345), 10:00-10:59
make agent-ask Q="Chart çiz"        # session: cli-12345-2025110810
make agent-ask Q="Renk ekle"        # session: cli-12345-2025110810 ✅ Same!

# Terminal 1, 11:00
make agent-ask Q="Yeni konu"        # session: cli-12345-2025110811 (new hour)

# Terminal 2 (PID 67890), 10:30
make agent-ask Q="Başka konu"       # session: cli-67890-2025110810 (new terminal)
```

---

#### Web UI (Browser-Based)

```javascript
// Browser sessionStorage (per-tab)
function getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem('agent_session_id');

    if (!sessionId) {
        sessionId = `ui-${generateUUID()}`;
        sessionStorage.setItem('agent_session_id', sessionId);
    }

    return sessionId;
}

// Auto-include in every request
fetch('/ask', {
    method: 'POST',
    body: JSON.stringify({
        agent: 'builder',
        prompt: 'Chart çiz',
        session_id: getOrCreateSessionId()  // Auto-injected
    })
});
```

**Rationale:**
- ✅ Per-browser-tab session (natural UX)
- ✅ Survives page refresh (sessionStorage)
- ✅ Auto-cleared when tab closed
- ✅ No backend cookie complexity

**UI Controls:**
```html
<!-- Optional: Manual session control -->
<button onclick="clearSession()">New Conversation</button>
<span>Session: [last 30 mins]</span>
```

---

#### API (Client-Provided)

```python
# API clients can provide session_id
POST /ask
{
    "agent": "builder",
    "prompt": "Chart çiz",
    "session_id": "custom-session-123"  # Optional
}

# If not provided, auto-generated
# Response includes session_id for client to track
{
    "session_id": "api-a1b2c3d4",
    "response": "...",
    ...
}
```

---

### Context Aggregation Logic

```python
# core/context_aggregator.py

def get_full_context(prompt: str, session_id: str, config: dict) -> str:
    """
    Aggregate session context + knowledge context.

    Args:
        prompt: User's current prompt
        session_id: Current session ID
        config: Agent memory config

    Returns:
        Formatted context string (session + knowledge)
    """
    contexts = []

    # 1. SESSION CONTEXT (recent conversation in this session)
    if config.get('session_context', {}).get('enabled', True):
        session_conv = get_session_conversations(
            session_id=session_id,
            limit=config['session_context'].get('limit', 5),
            exclude_current=True
        )

        if session_conv:
            session_text = format_session_context(session_conv)
            session_tokens = estimate_tokens(session_text)

            contexts.append({
                'type': 'session',
                'text': session_text,
                'tokens': session_tokens,
                'priority': 1  # Highest priority
            })

    # 2. KNOWLEDGE CONTEXT (semantic search, exclude current session)
    if config.get('knowledge_context', {}).get('enabled', True):
        knowledge_conv = semantic_search(
            prompt=prompt,
            exclude_session_id=session_id,  # Don't duplicate session context!
            min_relevance=config['knowledge_context'].get('min_relevance', 0.15),
            time_decay_hours=config['knowledge_context'].get('time_decay_hours', 168)
        )

        if knowledge_conv:
            knowledge_text = format_knowledge_context(knowledge_conv)
            knowledge_tokens = estimate_tokens(knowledge_text)

            contexts.append({
                'type': 'knowledge',
                'text': knowledge_text,
                'tokens': knowledge_tokens,
                'priority': 2  # Lower priority
            })

    # 3. TOKEN BUDGET ENFORCEMENT
    max_tokens = config.get('max_context_tokens', 600)
    selected = apply_token_budget(contexts, max_tokens)

    # 4. FORMAT FINAL CONTEXT
    return format_final_context(selected)


def format_session_context(conversations: List[dict]) -> str:
    """
    Format session conversations (recent messages in same session).

    Example output:
    ```
    [SESSION CONTEXT - Recent conversation]

    [5 messages ago]
    User: "Python'da matplotlib ile chart nasıl çizilir?"
    Assistant: "İşte basit bir bar chart örneği: ..."

    [3 messages ago]
    User: "Chart'a kırmızı renk ekle"
    Assistant: "Renk eklemek için colors parametresini kullan: ..."

    [1 message ago]
    User: "X-axis etiketlerini rotate et"
    Assistant: "plt.xticks(rotation=45) kullanabilirsin: ..."
    ```
    """
    parts = ["[SESSION CONTEXT - Recent conversation]\n"]

    for conv in reversed(conversations):  # Chronological order
        age = calculate_message_age(conv['timestamp'])
        parts.append(f"[{age}]")
        parts.append(f"User: \"{conv['prompt'][:100]}...\"")
        parts.append(f"Assistant: \"{conv['response'][:200]}...\"\n")

    return "\n".join(parts)


def format_knowledge_context(conversations: List[dict]) -> str:
    """
    Format knowledge conversations (semantic search from other sessions).

    Example output:
    ```
    [KNOWLEDGE CONTEXT - Relevant past topics]

    [Relevance: 0.82, 2 days ago]
    Topic: JWT authentication implementation
    Summary: "JWT tokens için PyJWT library kullan, secret key .env'de sakla..."

    [Relevance: 0.65, 1 week ago]
    Topic: FastAPI middleware best practices
    Summary: "Custom middleware için @app.middleware decorator kullan..."
    ```
    """
    parts = ["[KNOWLEDGE CONTEXT - Relevant past topics]\n"]

    for conv in conversations:
        score = conv.get('_score', 0.0)
        age = calculate_message_age(conv['timestamp'])
        parts.append(f"[Relevance: {score:.2f}, {age}]")
        parts.append(f"Topic: {conv['prompt'][:80]}")
        parts.append(f"Summary: \"{conv['response'][:200]}...\"\n")

    return "\n".join(parts)
```

---

### Configuration Schema

```yaml
# config/agents.yaml

builder:
  model: "anthropic/claude-sonnet-4-5"
  memory_enabled: true
  memory:
    # SESSION CONTEXT (new!)
    session_context:
      enabled: true           # Enable session tracking
      limit: 5                # Last N messages from session
      max_tokens: 300         # Token budget for session context
      format: "conversational"  # vs "summary"

    # KNOWLEDGE CONTEXT (existing, but enhanced)
    knowledge_context:
      enabled: true
      strategy: "semantic"    # Semantic search
      max_tokens: 300         # Token budget for knowledge
      min_relevance: 0.15
      time_decay_hours: 168   # Gentle decay (1 week)
      exclude_session: true   # Don't duplicate session messages

    # GLOBAL SETTINGS
    max_context_tokens: 600   # Total budget (session + knowledge)
```

**Backward Compatibility:**

```yaml
# Old config (still works):
builder:
  memory:
    strategy: "semantic"
    time_decay_hours: 168
    max_context_tokens: 600

# Auto-migrated to:
builder:
  memory:
    session_context:
      enabled: true  # Default ON
      limit: 5
      max_tokens: 300
    knowledge_context:
      enabled: true
      strategy: "semantic"
      time_decay_hours: 168
      max_tokens: 300
```

---

## 🔄 Migration Strategy

### Phase 1: Database Migration (10 minutes)

```bash
# Run migration script
python scripts/migrate_add_session_tracking.py

# What it does:
# 1. Add session_id column to conversations table
# 2. Create sessions table
# 3. Backfill existing conversations with session_id = NULL (stateless)
# 4. Create indexes
```

**Migration Script:**

```python
# scripts/migrate_add_session_tracking.py
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path("data/MEMORY/conversations.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("🔄 Adding session_id column...")
    cursor.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT")

    print("📊 Creating sessions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            metadata TEXT
        )
    """)

    print("🔍 Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON conversations(session_id)")

    print("✅ Migration complete!")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
```

---

### Phase 2: Code Implementation (2 days)

**Day 1: Core Session Management**

```
✅ core/session_manager.py (NEW)
   - get_or_create_session()
   - generate_cli_session_id()
   - generate_ui_session_id()
   - cleanup_old_sessions()

✅ core/context_aggregator.py (NEW)
   - get_full_context()
   - format_session_context()
   - format_knowledge_context()
   - apply_token_budget()

✅ core/memory_backend.py (UPDATE)
   - get_session_conversations()
   - save_with_session_id()
```

**Day 2: API & CLI Integration**

```
✅ api/server.py (UPDATE)
   - Extract session_id from request
   - Auto-generate if not provided
   - Return session_id in response

✅ scripts/agent_runner.py (UPDATE)
   - Auto-generate CLI session_id
   - Optional --session flag
   - Optional --no-session flag

✅ ui/templates/index.html (UPDATE)
   - sessionStorage management
   - New Session button
   - Session indicator
```

---

### Phase 3: Testing (1 day)

```
✅ Unit Tests
   - test_session_manager.py
   - test_context_aggregator.py
   - test_session_api.py

✅ Integration Tests
   - test_cli_session_workflow.sh
   - test_ui_session_workflow.py
   - test_cross_session_knowledge.py

✅ Manual Testing
   - CLI: Iterative chart development
   - UI: Chat-style conversation
   - API: Custom session IDs
```

---

## 📊 Trade-offs Analysis

| Aspect | Benefit | Cost | Mitigation |
|--------|---------|------|------------|
| **Memory Overhead** | Session tracking | +10% database size | Auto-cleanup (24h) |
| **Complexity** | Better UX | +500 LOC | Good documentation |
| **Token Usage** | Session context | +300 tokens/request | Configurable budget |
| **Performance** | Minimal (<50ms) | +1 DB query | Indexed session_id |
| **Backward Compat** | Old API works | Dual code paths | Auto-migration |

---

## 🎯 Success Metrics

### Functional Metrics

- ✅ Sequential conversation works: "Chart çiz" → "Renk ekle" (sees previous)
- ✅ CLI and UI consistent behavior
- ✅ Knowledge retrieval still works (cross-session search)
- ✅ Backward compatibility (old requests work)

### Performance Metrics

- Session lookup: < 50ms (p95)
- Context aggregation: < 100ms (p95)
- Database size increase: < 15%
- No regression in response time

### User Experience Metrics

- Reduced context repetition (user doesn't re-explain)
- Shorter prompts (iterative work)
- Fewer "clarification" responses from system

---

## 🚧 Implementation Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Session ID collision** | Data leak | Low | UUID + source prefix |
| **Unbounded session growth** | Memory leak | Medium | Auto-cleanup (24h) |
| **Context budget overflow** | Truncated context | Medium | Token budget enforcement |
| **CLI session confusion** | Poor UX | Low | Clear session indicator |
| **Breaking API changes** | Client errors | Low | Backward compatible design |

---

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_session_manager.py
def test_cli_session_id_generation():
    """CLI sessions are terminal + hour based."""
    session_id = generate_cli_session_id()
    assert session_id.startswith("cli-")
    assert len(session_id.split("-")) == 3  # cli-PID-TIMESTAMP

def test_session_context_retrieval():
    """Get last N messages from same session."""
    conversations = get_session_conversations(
        session_id="test-123",
        limit=5
    )
    assert len(conversations) <= 5
    assert all(c['session_id'] == "test-123" for c in conversations)

def test_knowledge_excludes_session():
    """Knowledge search excludes current session."""
    results = semantic_search(
        prompt="JWT authentication",
        exclude_session_id="test-123"
    )
    assert all(r['session_id'] != "test-123" for r in results)
```

---

### Integration Tests

```bash
# tests/test_cli_session_workflow.sh
#!/bin/bash

# Test: Sequential conversation in CLI
SESSION_ID="test-$(date +%s)"

# Step 1: Start project
make agent-ask Q="FastAPI projesi başlat" SESSION=$SESSION_ID

# Step 2: Add authentication (should see previous)
make agent-ask Q="Authentication ekle" SESSION=$SESSION_ID

# Verify: Second request should inject first conversation
LAST_LOG=$(ls -t data/CONVERSATIONS/*.json | head -1)
INJECTED=$(cat $LAST_LOG | jq '.injected_context_tokens')

if [ "$INJECTED" -gt 100 ]; then
    echo "✅ Session context injected!"
else
    echo "❌ Session context NOT injected!"
    exit 1
fi
```

---

### Manual Test Scenarios

**Scenario 1: Chart Development (CLI)**

```bash
# Terminal 1
make agent-ask Q="Python matplotlib bar chart nasıl çizilir?"
make agent-ask Q="Chart'a kırmızı renk ekle"
make agent-ask Q="X-axis etiketlerini 45 derece rotate et"
make agent-ask Q="Legend ekle"

# Expected: Her step öncekini görür, iterative development
```

**Scenario 2: Multi-Terminal Independence (CLI)**

```bash
# Terminal 1
make agent-ask Q="FastAPI projesi"

# Terminal 2 (farklı terminal = farklı session)
make agent-ask Q="Django projesi"

# Expected: İki session birbirinden bağımsız
```

**Scenario 3: Knowledge Retrieval Across Sessions (UI)**

```
Tab 1 (Pazartesi):
- "JWT authentication best practices"
- [Conversation happens...]

Tab 2 (Çarşamba - yeni tab = yeni session):
- "JWT refresh token nasıl implement edilir?"
- Expected: Pazartesi conversation'ı knowledge context'te görünür
            (session context'te değil, knowledge context'te)
```

---

## 📝 Documentation Updates

### User-Facing Documentation

**docs/SESSION_TRACKING_GUIDE.md** (NEW)
- What is session tracking?
- How does it work?
- CLI usage examples
- UI usage examples
- Session management (clear, create new)

**docs/QUICKSTART.md** (UPDATE)
- Add session tracking explanation
- Update examples to show sequential conversations

**docs/WEB_UI_GUIDE.md** (UPDATE)
- Add session management UI controls
- Explain auto-session behavior

---

### Developer Documentation

**docs/ARCHITECTURE.md** (UPDATE)
- Add session tracking architecture diagram
- Context aggregation flow
- Database schema updates

**CHANGELOG.md** (UPDATE)
- v0.11.0 section
- Breaking changes (none!)
- New features (session tracking)

---

## 🚀 Rollout Plan

### Week 1: Development

- Day 1-2: Core implementation (session manager, context aggregator)
- Day 3: API/CLI integration
- Day 4: Testing
- Day 5: Documentation

### Week 2: Testing & Refinement

- Day 1-2: Internal testing (team)
- Day 3-4: Beta testing (select users)
- Day 5: Bug fixes, refinement

### Week 3: Release

- Day 1: Final testing
- Day 2: Documentation review
- Day 3: Release v0.11.0
- Day 4-5: Monitor, support

---

## 🎓 Lessons from Analysis

### What We Learned

1. **User Mental Models Matter**
   - Users expect ChatGPT-style conversation (stateful)
   - Stateless design confused users ("why doesn't it remember?")
   - Technical correctness ≠ Good UX

2. **Single time_decay Can't Solve Both Use Cases**
   - time_decay: 2h → Sequential OK, Knowledge broken
   - time_decay: 168h → Knowledge OK, Sequential broken
   - Solution: Dual-context model (session + knowledge)

3. **CLI vs UI Consistency Critical**
   - Initially thought: "CLI stateless, UI stateful"
   - Reality: Inconsistency = confusion
   - Better: Same behavior, different auto-management

4. **Conversation Thread ≠ Knowledge Base**
   - Conversation thread: Recent messages (devamlılık)
   - Knowledge base: Semantic search (alakalı bilgi)
   - Both are needed!

---

## 🔮 Future Enhancements (Post-v0.11.0)

### Phase 2 Features (v0.12.0+)

1. **Smart Intent Detection**
   ```python
   # Detect sequential intent from keywords
   if "önceki" in prompt or "buna" in prompt:
       boost_session_context_priority()
   ```

2. **Session Summarization**
   ```
   Long sessions (20+ messages) → Auto-summarize
   Inject summary instead of full messages
   Saves tokens, preserves context
   ```

3. **Cross-Session References**
   ```
   User: "2 gün önce JWT konuşmuştuk, o session'a dön"
   System: Finds session by semantic search, switches context
   ```

4. **Session Export**
   ```bash
   make session-export SESSION=cli-12345-2025110810 FORMAT=markdown
   # Outputs: full conversation as Markdown
   ```

---

## ✅ Approval Checklist

Before implementation, confirm:

- [ ] Design reviewed by team
- [ ] Trade-offs understood and accepted
- [ ] Migration strategy validated
- [ ] Testing strategy complete
- [ ] Documentation plan approved
- [ ] Rollout timeline agreed
- [ ] Success metrics defined
- [ ] Rollback plan exists

---

## 📚 References

### Related Documents

- `docs/MEMORY_CONTEXT_ANALYSIS.md` - Original problem analysis
- `docs/WEB_UI_GUIDE.md` - UI design principles
- `config/agents.yaml` - Current memory configuration

### External References

- ChatGPT conversation model (OpenAI)
- Claude conversation threads (Anthropic)
- Session management patterns (Industry best practices)

---

## 🎯 Decision Required

**Question:** Proceed with session tracking implementation?

**Options:**

A) ✅ **Proceed** - Implement as designed (2-3 days)
B) 🔄 **Revise** - Adjust design based on feedback
C) ❌ **Reject** - Keep stateless, document limitations

**Recommended:** Option A - Proceed

**Rationale:**
- Clear user need (tester feedback)
- Well-designed solution (dual-context model)
- Manageable implementation (2-3 days)
- Backward compatible (no breaking changes)
- Measurable success criteria

---

**Next Steps:**

1. Review this RFC
2. Gather feedback/questions
3. Make go/no-go decision
4. If GO → Start implementation (Phase 1: Database migration)

---

**Version:** RFC v1.0
**Last Updated:** 2025-11-08
**Status:** ⏳ Awaiting Approval

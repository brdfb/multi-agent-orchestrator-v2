# RFC Review: Session-Based Conversation Tracking

**Reviewer:** System Design Team
**Review Date:** 2025-11-08
**RFC Version:** v1.0
**Status:** 🔄 In Review

---

## 📊 Executive Assessment

| Category | Rating | Notes |
|----------|--------|-------|
| **Problem Definition** | ⭐⭐⭐⭐⭐ | Clear, well-motivated with real examples |
| **Solution Design** | ⭐⭐⭐⭐☆ | Solid dual-context approach, minor concerns |
| **Implementation Plan** | ⭐⭐⭐⭐☆ | Detailed, realistic timeline |
| **Testing Strategy** | ⭐⭐⭐⭐⭐ | Comprehensive coverage |
| **Documentation** | ⭐⭐⭐⭐⭐ | Excellent detail, clear examples |
| **Risk Management** | ⭐⭐⭐☆☆ | Some gaps, needs enhancement |

**Overall:** ⭐⭐⭐⭐☆ (4.2/5) - **APPROVE WITH REVISIONS**

---

## ✅ STRENGTHS

### 1. Problem Analysis (Excellent)

**Strength:** Real-world examples make problem concrete

```
"Chart'a renk ekle" → ❌ "Hangi chart?"
```

This resonates! Clear UX gap identified.

**Strength:** Mental model mismatch clearly articulated

```
ChatGPT (stateful)  vs  Our System (stateless)
Wikipedia (topic)    vs  WhatsApp (recency)
```

Great analogy - makes problem accessible.

---

### 2. Dual-Context Design (Strong)

**Strength:** Separates concerns elegantly

```yaml
session_context:   # Recent messages (devamlılık)
  limit: 5
  max_tokens: 300

knowledge_context: # Semantic search (bilgi)
  strategy: "semantic"
  max_tokens: 300
```

**Why this works:**
- ✅ Session handles "az önce ne konuştuk?"
- ✅ Knowledge handles "2 gün önce JWT konuştuk"
- ✅ No single time_decay trying to do both

**Strength:** Exclude current session in knowledge search

```python
exclude_session_id=session_id  # No duplication!
```

Smart! Prevents redundant context.

---

### 3. Auto-Session Strategy (Clever)

**CLI approach:**
```python
session_id = f"cli-{pid}-{hour}"
```

**Why this works:**
- ✅ No user input required (seamless)
- ✅ Terminal-scoped (natural boundary)
- ✅ Hourly reset (prevents unbounded growth)

**UI approach:**
```javascript
sessionStorage.setItem('agent_session_id', uuid());
```

**Why this works:**
- ✅ Per-tab isolation (expected behavior)
- ✅ Survives refresh (sessionStorage)
- ✅ Auto-cleared on tab close (natural cleanup)

---

### 4. Testing Strategy (Comprehensive)

**Strength:** Three-tier testing

```
Unit Tests       → Individual components
Integration Tests → Workflows (CLI/UI)
Manual Scenarios → Real use cases
```

**Specific scenarios well-chosen:**
- Chart development (iterative)
- Multi-terminal independence
- Cross-session knowledge

---

## ⚠️ CONCERNS & QUESTIONS

### 🔴 CRITICAL: CLI Session Hourly Reset Edge Case

**Issue:** Session resets every hour, mid-conversation

**Scenario:**
```bash
10:55 - make agent-ask Q="FastAPI projesi başlat"
        session: cli-12345-2025110810

10:57 - make agent-ask Q="Authentication ekle"
        session: cli-12345-2025110810 ✅ Same!

11:02 - make agent-ask Q="Database bağlantısı ekle"
        session: cli-12345-2025110811 ❌ NEW SESSION!
        → Önceki 2 mesajı GÖRMEZ!
```

**Impact:** Mid-conversation context loss!

**Question:**
- Hourly reset too aggressive?
- Should be session duration-based? (e.g., 2 hours idle)
- Or explicit session management?

**Proposed Fix:**

```python
def generate_cli_session_id():
    """
    Session persists for 2 hours of activity.
    Reset only if last message > 2 hours ago.
    """
    # Check if recent session exists
    recent_session = get_recent_cli_session(pid=os.getpid(), within_hours=2)

    if recent_session:
        return recent_session.session_id  # Reuse
    else:
        # Create new
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"cli-{os.getpid()}-{timestamp}"
```

**Trade-off:**
- ✅ No mid-conversation reset
- ⚠️ Needs session state tracking (DB query)
- ⚠️ Slightly more complex

---

### 🔴 CRITICAL: Token Budget Overflow Risk

**Issue:** Session (300) + Knowledge (300) = 600, but what if session alone > 300?

**Scenario:**
```python
# Session has 5 long messages
session_context = get_session_conversations(limit=5)
# Each message ~100 tokens average
# Total: 5 × 100 = 500 tokens

# Budget enforcement
max_tokens = 300  # Config says 300!
# → Truncate session to 300? Or allow overflow?
```

**Current RFC says:**
```python
# 3. TOKEN BUDGET ENFORCEMENT
selected = apply_token_budget(contexts, max_tokens)
```

**Question:** Budget per-context or global?

**Option A: Per-Context Budget (Strict)**
```python
session_tokens = min(session_context_tokens, 300)
knowledge_tokens = min(knowledge_context_tokens, 300)
total = session_tokens + knowledge_tokens  # ≤ 600
```

**Option B: Global Budget with Priority**
```python
total_budget = 600
# Priority 1: Session (up to 450 if needed)
# Priority 2: Knowledge (remaining budget)
```

**Recommendation:** Option B (flexible)

**Rationale:**
- Session context more important for sequential conversation
- If session needs 450 tokens, knowledge gets 150
- If session only needs 150, knowledge gets 450

**RFC Update Needed:** Clarify budget allocation strategy

---

### 🟡 MEDIUM: Session Cleanup Race Condition

**Issue:** Auto-cleanup trigger runs AFTER INSERT

```sql
CREATE TRIGGER cleanup_old_sessions
AFTER INSERT ON sessions
BEGIN
    DELETE FROM sessions
    WHERE last_active < datetime('now', '-24 hours');
END;
```

**Problem:**
- Every INSERT triggers full table scan DELETE
- High frequency (every request) = performance issue
- 1000 requests/hour = 1000 DELETE scans!

**Question:** Is this performant?

**Proposed Fix:**

```python
# Option 1: Periodic cleanup (cron job)
# scripts/cleanup_sessions.py
def cleanup_old_sessions():
    """Run every hour via cron."""
    db.execute("DELETE FROM sessions WHERE last_active < datetime('now', '-24 hours')")

# Crontab:
# 0 * * * * cd /path && python scripts/cleanup_sessions.py
```

```python
# Option 2: Probabilistic cleanup (10% chance on INSERT)
def create_session(session_id, ...):
    # Insert session
    db.execute("INSERT INTO sessions ...")

    # 10% chance of cleanup
    if random.random() < 0.1:
        db.execute("DELETE FROM sessions WHERE last_active < datetime('now', '-24 hours')")
```

**Recommendation:** Option 2 (probabilistic)

**Rationale:**
- No external cron dependency
- Amortized cost (10% of requests)
- Self-maintaining

**RFC Update Needed:** Change auto-cleanup strategy

---

### 🟡 MEDIUM: Web UI Session Persistence Across Tabs

**Issue:** User opens multiple tabs, expects shared session?

**Scenario:**
```
Tab 1: "FastAPI projesi başlat"
Tab 2: User opens new tab → "Authentication ekle"
       ❌ Tab 2 has different session (different sessionStorage)
       → Doesn't see Tab 1's project!
```

**User Expectation:** Same browser = same session?

**Question:** Should we use `localStorage` instead?

**Option A: sessionStorage (Per-Tab - Current RFC)**
```javascript
sessionStorage.setItem('session_id', uuid());
// Each tab = separate session
```

**Pros:**
- ✅ Multiple independent conversations (Tab 1: Chart, Tab 2: JWT)
- ✅ Tab close = auto-cleanup

**Cons:**
- ❌ Can't continue conversation in new tab

---

**Option B: localStorage (Per-Browser)**
```javascript
localStorage.setItem('session_id', uuid());
// All tabs share session
```

**Pros:**
- ✅ Continue conversation in any tab
- ✅ User doesn't lose context

**Cons:**
- ❌ Can't have parallel conversations
- ❌ Browser close required for cleanup

---

**Option C: Hybrid (Default localStorage + Tab Override)**
```javascript
// Default: Share across tabs
let sessionId = localStorage.getItem('global_session_id');

// Optional: "New Session" button creates tab-specific
if (wantTabSession) {
    sessionId = sessionStorage.getItem('tab_session_id') || uuid();
    sessionStorage.setItem('tab_session_id', sessionId);
}
```

**Recommendation:** Option C (hybrid with user control)

**Rationale:**
- Default: Shared (most intuitive for users)
- Power users: Can create tab-specific sessions
- Best of both worlds

**RFC Update Needed:** Clarify UI session scope

---

### 🟡 MEDIUM: API session_id Validation

**Issue:** API accepts custom session_id - what if malicious?

**Scenario:**
```python
POST /ask
{
    "session_id": "../../etc/passwd",  # Path traversal?
    "session_id": "x" * 10000,         # DoS?
    "session_id": "user-A-session",    # Session hijacking?
}
```

**Question:** Input validation needed?

**Proposed Fix:**

```python
import re

def validate_session_id(session_id: str) -> bool:
    """
    Validate session_id format.

    Allowed:
    - cli-{digits}-{timestamp}
    - ui-{uuid}
    - api-{uuid}
    - Custom: alphanumeric + dash/underscore, max 64 chars
    """
    if not session_id:
        return False

    if len(session_id) > 64:
        raise ValueError("session_id too long (max 64 chars)")

    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise ValueError("session_id contains invalid characters")

    return True

# API endpoint
@app.post("/ask")
async def ask(request: AskRequest):
    if request.session_id:
        validate_session_id(request.session_id)  # Throws on invalid

    session_id = request.session_id or generate_session_id()
    ...
```

**RFC Update Needed:** Add input validation section

---

### 🟢 MINOR: Migration Rollback Plan Missing

**Issue:** What if migration fails halfway?

**Scenario:**
```bash
python scripts/migrate_add_session_tracking.py

# Migration steps:
✅ 1. Add session_id column
✅ 2. Create sessions table
❌ 3. Create index (FAILS - disk full?)

→ Database in inconsistent state!
```

**Question:** Rollback strategy?

**Proposed Fix:**

```python
# scripts/migrate_add_session_tracking.py

def migrate():
    conn = sqlite3.connect(db_path)

    try:
        conn.execute("BEGIN TRANSACTION")

        # Step 1
        conn.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT")

        # Step 2
        conn.execute("CREATE TABLE sessions ...")

        # Step 3
        conn.execute("CREATE INDEX idx_session_id ...")

        # All succeeded
        conn.execute("COMMIT")
        print("✅ Migration successful!")

    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Migration failed: {e}")
        print("🔄 Database rolled back to previous state")
        raise

    finally:
        conn.close()
```

**Also add:**

```python
def rollback_migration():
    """Manual rollback if needed."""
    conn = sqlite3.connect(db_path)

    # Remove session_id column (SQLite limitation: can't DROP COLUMN easily)
    # Workaround: Recreate table without session_id

    conn.execute("ALTER TABLE conversations RENAME TO conversations_backup")
    conn.execute("CREATE TABLE conversations (...)")  # Old schema
    conn.execute("INSERT INTO conversations SELECT [old columns] FROM conversations_backup")
    conn.execute("DROP TABLE conversations_backup")
    conn.execute("DROP TABLE sessions")
    conn.commit()
    conn.close()
```

**RFC Update Needed:** Add rollback section

---

### 🟢 MINOR: Concurrent Session Writes

**Issue:** Same session, multiple concurrent requests

**Scenario:**
```python
# User rapidly sends 2 messages (same session)
Request 1: "Chart çiz"      → Writes to session
Request 2: "Renk ekle"      → Reads from session (while Req1 writing)

# Race condition?
# Req2 might not see Req1's message if timing unlucky
```

**Question:** Transaction isolation needed?

**Proposed Fix:**

```python
# Use WAL mode (already enabled in our SQLite)
# Write-Ahead Logging allows concurrent reads during writes

# Also: Update last_active atomically
UPDATE sessions
SET last_active = datetime('now')
WHERE session_id = ?
```

**Note:** SQLite WAL mode already handles this well for our use case.

**RFC Update Needed:** Mention concurrency handled by WAL mode

---

## 🎯 RECOMMENDATIONS

### Must-Fix Before Implementation (Critical)

1. **CLI Session Hourly Reset**
   - Change to duration-based (2 hours idle)
   - OR add explicit session management (`--session` flag)

2. **Token Budget Strategy**
   - Clarify per-context vs global budget
   - Recommend flexible allocation (priority-based)

3. **Session Cleanup Performance**
   - Change from trigger to probabilistic cleanup
   - Avoid full table scan on every INSERT

---

### Should-Fix Before Implementation (Medium Priority)

4. **Web UI Session Scope**
   - Clarify localStorage vs sessionStorage
   - Recommend hybrid (shared by default, tab override option)

5. **API Input Validation**
   - Add session_id validation
   - Prevent injection/DoS

6. **Migration Rollback**
   - Add transaction wrapper
   - Document rollback procedure

---

### Nice-to-Have (Can Defer to v0.11.1)

7. **Session Analytics**
   - Track session duration, message count
   - Metrics for UX optimization

8. **Session Export**
   - "Download this conversation" feature
   - Already in "Future Enhancements" ✅

9. **Session Sharing**
   - Share session URL with teammate
   - Collaborative debugging

---

## 📝 PROPOSED RFC UPDATES

### Section 3.1: CLI Session Management (REVISE)

**Current:**
```python
session_id = f"cli-{pid}-{hour}"  # Hourly reset
```

**Proposed:**
```python
def generate_cli_session_id():
    """
    Session persists for 2 hours of activity.
    """
    recent = get_recent_cli_session(pid=os.getpid(), within_hours=2)

    if recent:
        return recent.session_id  # Continue existing
    else:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"cli-{os.getpid()}-{timestamp}"
```

---

### Section 4.2: Token Budget (CLARIFY)

**Add:**

```python
def apply_token_budget(contexts: List[dict], max_tokens: int) -> List[dict]:
    """
    Flexible budget allocation with priority.

    Strategy:
    - Session context: Priority 1 (up to 75% of budget if needed)
    - Knowledge context: Priority 2 (remaining budget)

    Example:
    - Budget: 600 tokens
    - Session needs 450 → gets 450
    - Knowledge gets 150 (remaining)

    - Session needs 150 → gets 150
    - Knowledge gets 450 (remaining)
    """
    session_max = int(max_tokens * 0.75)  # 75% cap
    knowledge_max = max_tokens

    selected = []
    used_tokens = 0

    # Priority 1: Session context
    for ctx in [c for c in contexts if c['priority'] == 1]:
        if used_tokens + ctx['tokens'] <= session_max:
            selected.append(ctx)
            used_tokens += ctx['tokens']

    # Priority 2: Knowledge context (fill remaining)
    remaining = max_tokens - used_tokens
    for ctx in [c for c in contexts if c['priority'] == 2]:
        if ctx['tokens'] <= remaining:
            selected.append(ctx)
            remaining -= ctx['tokens']

    return selected
```

---

### Section 5.1: Session Cleanup (REVISE)

**Current:**
```sql
CREATE TRIGGER cleanup_old_sessions
AFTER INSERT ON sessions ...
```

**Proposed:**
```python
# Probabilistic cleanup (10% of inserts)
def create_session(session_id, source, metadata):
    # Insert session
    db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", ...)

    # Probabilistic cleanup (amortized cost)
    if random.random() < 0.1:
        db.execute("DELETE FROM sessions WHERE last_active < datetime('now', '-24 hours')")
```

---

### Section 6.3: Input Validation (ADD NEW)

```python
# NEW SECTION: Security Considerations

def validate_session_id(session_id: str) -> bool:
    """
    Validate session_id to prevent injection/DoS.

    Rules:
    - Max 64 characters
    - Alphanumeric + dash/underscore only
    - No path traversal patterns
    """
    if not session_id or len(session_id) > 64:
        raise ValueError("Invalid session_id length")

    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise ValueError("Invalid session_id characters")

    return True
```

---

### Section 7.2: Migration Rollback (ADD NEW)

```python
# NEW SECTION: Rollback Procedure

def rollback_migration():
    """
    Rollback session tracking migration.

    Use cases:
    - Migration failed halfway
    - Critical bug discovered
    - Need to revert temporarily
    """
    print("⚠️  Rolling back session tracking migration...")

    conn = sqlite3.connect(db_path)

    try:
        # Drop sessions table
        conn.execute("DROP TABLE IF EXISTS sessions")

        # Remove session_id column (SQLite workaround)
        conn.execute("ALTER TABLE conversations RENAME TO conversations_old")
        conn.execute("CREATE TABLE conversations (...)")  # Old schema
        conn.execute("INSERT INTO conversations SELECT [old_cols] FROM conversations_old")
        conn.execute("DROP TABLE conversations_old")

        print("✅ Rollback complete!")
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        raise
    finally:
        conn.close()
```

---

## 🏆 FINAL VERDICT

### APPROVE ✅ with following conditions:

1. **Fix Critical Issues:**
   - CLI session hourly reset → duration-based
   - Token budget → flexible allocation
   - Session cleanup → probabilistic (not trigger)

2. **Add Missing Sections:**
   - Input validation
   - Migration rollback
   - Concurrency note (WAL mode)

3. **Clarify Ambiguities:**
   - Web UI session scope (localStorage vs sessionStorage)
   - Budget allocation strategy (priority-based)

### Timeline Impact:

**Original:** 2-3 days
**Revised:** 3-4 days (due to additional validation/cleanup logic)

**Breakdown:**
- Day 1: Core implementation (session_manager, context_aggregator)
- Day 2: API/CLI integration + input validation
- Day 3: UI updates + probabilistic cleanup
- Day 4: Testing + rollback script

---

## 📋 ACTION ITEMS

- [ ] **Update RFC** with proposed revisions
- [ ] **Review revisions** with team
- [ ] **Approve final RFC** (v1.1)
- [ ] **Begin implementation** (Phase 1: Migration)

---

**Review Status:** ✅ **CONDITIONALLY APPROVED**
**Next Step:** Update RFC → Final approval → Implementation

---

**Reviewer:** System Design Team
**Date:** 2025-11-08
**RFC Version Reviewed:** v1.0
**Recommended RFC Version:** v1.1 (with revisions)

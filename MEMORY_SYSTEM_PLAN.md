# Memory System Implementation Plan

## 🎯 Strategic Objective

Transform the orchestrator from **stateless** to **stateful** by adding persistent conversation memory, enabling:
- Multi-session context continuity
- Cross-conversation knowledge retrieval
- Claude Code integration via shared memory
- Long-term learning capabilities

## 📊 Current State vs. Target

| Aspect | Current (Stateless) | Target (Memory-Enabled) |
|--------|---------------------|-------------------------|
| Context | Lost after each run | Persistent across sessions |
| Search | Manual log parsing | Semantic search + filters |
| Integration | None | Claude Code can inject/retrieve |
| Analytics | Basic metrics | Trend analysis, conversation clustering |
| Chain Context | First 200 chars only | Full conversation history |

## 🏗️ Architecture Design

### Core Components

```
┌─────────────────────────────────────────────┐
│           Memory System Architecture         │
└─────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Agent       │────▶│  Memory      │────▶│  Storage     │
│  Runtime     │     │  Engine      │     │  Backend     │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │
       │                    │                     ├─ SQLite (primary)
       │                    │                     ├─ JSON (backup)
       │                    │                     └─ Vector DB (future)
       │                    │
       ▼                    ▼
  ┌──────────────┐    ┌──────────────┐
  │  Context     │    │  Retrieval   │
  │  Injection   │    │  API         │
  └──────────────┘    └──────────────┘
```

### File Structure

```
core/
  └── memory_engine.py      # Core memory operations
  └── memory_backend.py     # Storage abstraction (SQLite/JSON)
  └── memory_retrieval.py   # Search & filtering

api/
  └── memory_routes.py      # REST endpoints

config/
  └── memory.yaml           # Memory system config

data/
  └── MEMORY/
      ├── conversations.db  # SQLite database
      ├── embeddings/       # Future: vector embeddings
      └── exports/          # JSON exports

tests/
  └── test_memory_engine.py
  └── test_memory_api.py
  └── test_memory_retrieval.py
```

## 🔧 Implementation Phases

### Phase 1: Core Memory Engine (Day 1-2)

**File**: `core/memory_engine.py`

**Features**:
- `MemoryEngine` class (singleton pattern)
- `store_conversation(prompt, response, metadata)`
- `get_recent_conversations(limit, agent=None)`
- `search_conversations(query, filters)`
- SQLite schema design

**Schema**:
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    duration_ms REAL,
    tokens_used INTEGER,
    cost_usd REAL,
    fallback_used BOOLEAN DEFAULT 0,
    session_id TEXT,
    tags TEXT  -- JSON array
);

CREATE INDEX idx_timestamp ON conversations(timestamp DESC);
CREATE INDEX idx_agent ON conversations(agent);
CREATE INDEX idx_session ON conversations(session_id);
```

**Tests**:
- Store and retrieve conversation
- Search by agent/model
- Time-based filtering
- Concurrent access handling

---

### Phase 2: Context Injection (Day 2-3)

**File**: `core/memory_engine.py` (extension)

**Features**:
- `get_context_for_prompt(prompt, max_tokens=500)` - Retrieves relevant past conversations
- Simple keyword matching (upgrade to embeddings later)
- Token budgeting (don't exceed context limit)
- Context formatting for system prompt injection

**Integration Points**:
1. `AgentRuntime.run()` - Before calling LLM, optionally inject context:
   ```python
   if enable_memory:
       context = memory.get_context_for_prompt(prompt)
       system_prompt = f"{agent_config['system']}\n\nRelevant past conversations:\n{context}"
   ```

2. Add `enable_memory` flag to `agents.yaml`:
   ```yaml
   builder:
     model: "..."
     memory_enabled: true
     memory_max_tokens: 500
   ```

**Tests**:
- Context retrieval with token limit
- Relevance ranking (basic keyword scoring)
- Context disabled when flag is false

---

### Phase 3: REST API Endpoints (Day 3-4)

**File**: `api/memory_routes.py`

**Endpoints**:

```python
# Store conversation (called automatically by runtime)
POST /memory/store
Body: {conversation_data}
Response: {id, stored_at}

# Search conversations
GET /memory/search?q=<query>&agent=<agent>&from=<date>&to=<date>&limit=10
Response: {conversations: [...], total: N}

# Get recent conversations
GET /memory/recent?limit=10&agent=<agent>
Response: {conversations: [...]}

# Get conversation by ID
GET /memory/conversation/<id>
Response: {conversation_data}

# Export conversations (JSON/CSV)
GET /memory/export?format=json&from=<date>&to=<date>
Response: Download file

# Delete conversation
DELETE /memory/conversation/<id>
Response: {deleted: true}

# Get memory stats
GET /memory/stats
Response: {
  total_conversations: N,
  total_tokens: N,
  total_cost: N,
  by_agent: {...},
  by_model: {...}
}
```

**Tests**:
- All endpoint response codes (200, 404, 400)
- Search with various filters
- Export format validation

---

### Phase 4: CLI Commands (Day 4-5)

**File**: `scripts/memory_cli.py` (new)

**Commands**:
```bash
# Search memory
make memory-search Q="create a function"
make memory-search Q="bug fix" AGENT=critic

# View recent conversations
make memory-recent LIMIT=5

# Show memory stats
make memory-stats

# Export conversations
make memory-export FROM=2024-01-01 TO=2024-12-31 FORMAT=json

# Clear old conversations (cleanup)
make memory-cleanup DAYS=30
```

**Makefile additions**:
```makefile
memory-search:
	@python scripts/memory_cli.py search "$(Q)" --agent "$(AGENT)" --limit 10

memory-recent:
	@python scripts/memory_cli.py recent --limit $(LIMIT)

memory-stats:
	@python scripts/memory_cli.py stats

memory-export:
	@python scripts/memory_cli.py export --from "$(FROM)" --to "$(TO)" --format "$(FORMAT)"

memory-cleanup:
	@python scripts/memory_cli.py cleanup --days $(DAYS)
```

---

### Phase 5: Integration & Testing (Day 5-6)

**Integration with `AgentRuntime`**:

1. Auto-store conversations:
   ```python
   # In AgentRuntime.run() after LLM call
   if memory_engine.enabled:
       memory_engine.store_conversation(
           prompt=prompt,
           response=llm_response.text,
           metadata={
               "agent": agent,
               "model": llm_response.model,
               "tokens": llm_response.total_tokens,
               "cost": estimate_cost(...),
               "fallback_used": llm_response.fallback_used
           }
       )
   ```

2. Context injection (optional per agent):
   ```python
   if agent_config.get("memory_enabled", False):
       context = memory_engine.get_context_for_prompt(prompt)
       system_prompt += f"\n\nRelevant context:\n{context}"
   ```

**End-to-End Tests**:
- Run agent → verify conversation stored
- Run agent with memory enabled → verify context injected
- Search via API → verify results
- CLI commands → verify output

---

### Phase 6: Documentation (Day 6-7)

**File**: `MEMORY_SYSTEM.md`

**Contents**:
- Architecture overview
- API documentation
- CLI usage examples
- Configuration options
- Performance considerations
- Future enhancements (vector search, RAG)

**Update**: `CLAUDE.md` with memory system section

---

## 🧪 Test Matrix

| Test Case | Type | File | Description |
|-----------|------|------|-------------|
| Store conversation | Unit | test_memory_engine.py | Basic store/retrieve |
| Search by keyword | Unit | test_memory_engine.py | Keyword matching |
| Time-based filter | Unit | test_memory_engine.py | Date range queries |
| Context injection | Unit | test_memory_engine.py | Token budgeting |
| Concurrent access | Unit | test_memory_engine.py | Thread safety |
| API endpoints | Integration | test_memory_api.py | All REST routes |
| CLI commands | Integration | test_memory_cli.py | CLI output validation |
| End-to-end flow | E2E | test_memory_e2e.py | Agent → Store → Retrieve |
| Large dataset | Performance | test_memory_perf.py | 10k conversations |

**Coverage Target**: >90%

---

## 📋 Task Breakdown (GitHub Issues)

### Issue #1: Core Memory Engine
- [ ] Create `core/memory_engine.py`
- [ ] Implement SQLite backend
- [ ] Add `store_conversation()`
- [ ] Add `get_recent_conversations()`
- [ ] Add `search_conversations()`
- [ ] Write unit tests (80%+ coverage)

### Issue #2: Context Injection
- [ ] Implement `get_context_for_prompt()`
- [ ] Add keyword matching algorithm
- [ ] Add token budgeting logic
- [ ] Update `agents.yaml` schema (memory_enabled flag)
- [ ] Test context formatting

### Issue #3: REST API Endpoints
- [ ] Create `api/memory_routes.py`
- [ ] Implement `/memory/search`
- [ ] Implement `/memory/recent`
- [ ] Implement `/memory/stats`
- [ ] Implement `/memory/export`
- [ ] Add API tests

### Issue #4: CLI Commands
- [ ] Create `scripts/memory_cli.py`
- [ ] Implement `memory-search` command
- [ ] Implement `memory-recent` command
- [ ] Implement `memory-stats` command
- [ ] Implement `memory-export` command
- [ ] Update Makefile

### Issue #5: Integration
- [ ] Hook memory engine into `AgentRuntime`
- [ ] Auto-store conversations
- [ ] Optional context injection
- [ ] Config file (`config/memory.yaml`)
- [ ] E2E tests

### Issue #6: Documentation
- [ ] Create `MEMORY_SYSTEM.md`
- [ ] Update `CLAUDE.md`
- [ ] Add API documentation
- [ ] CLI usage examples
- [ ] Performance tuning guide

---

## ⚙️ Configuration

**File**: `config/memory.yaml`

```yaml
memory:
  enabled: true
  backend: "sqlite"  # or "json" for fallback
  database_path: "data/MEMORY/conversations.db"

  # Auto-cleanup (optional)
  cleanup:
    enabled: true
    keep_days: 90  # Delete conversations older than 90 days

  # Context injection settings
  context:
    enabled: true
    max_tokens: 500  # Max tokens for injected context
    min_relevance_score: 0.3  # Keyword match threshold

  # Search settings
  search:
    default_limit: 10
    max_limit: 100
```

---

## 🚀 Performance Considerations

1. **SQLite Performance**:
   - Index on `timestamp`, `agent`, `session_id`
   - Connection pooling (singleton pattern)
   - Async writes (background thread)

2. **Context Retrieval**:
   - Cache recent searches (TTL: 5 min)
   - Limit keyword matching to recent N conversations
   - Future: Vector embeddings for semantic search

3. **Storage**:
   - SQLite file size monitoring
   - Auto-cleanup of old conversations
   - Export to JSON for archival

---

## 🔮 Future Enhancements (Phase 2)

1. **Vector Embeddings**:
   - Use `sentence-transformers` for semantic search
   - Store embeddings in separate table
   - RAG-style context injection

2. **Session Management**:
   - Group conversations by session ID
   - Session-aware context retrieval
   - Session analytics

3. **Advanced Search**:
   - Full-text search (FTS5)
   - Faceted search (by agent, model, date range)
   - Regex patterns

4. **UI Dashboard**:
   - Conversation timeline visualization
   - Search interface
   - Export/import functionality

5. **Claude Code Integration**:
   - Shared memory pool
   - Cross-tool context sharing
   - Memory sync protocol

---

## ✅ Acceptance Criteria

Feature is **DONE** when:

1. ✅ All unit tests passing (>90% coverage)
2. ✅ E2E test: Agent run → Memory stored → Context injected in next run
3. ✅ API endpoints functional (tested with curl/Postman)
4. ✅ CLI commands working (`make memory-search`, etc.)
5. ✅ Documentation complete (`MEMORY_SYSTEM.md`)
6. ✅ No performance regression (<100ms overhead per run)
7. ✅ PR approved and merged to master

---

## 📝 Development Checklist

- [ ] Phase 1: Core Memory Engine (2 days)
- [ ] Phase 2: Context Injection (1 day)
- [ ] Phase 3: REST API (1 day)
- [ ] Phase 4: CLI Commands (1 day)
- [ ] Phase 5: Integration & Testing (1 day)
- [ ] Phase 6: Documentation (1 day)
- [ ] Code review & polish (1 day)
- [ ] **Total Estimate**: 7-8 days

---

## 🎯 Success Metrics

| Metric | Target |
|--------|--------|
| Unit test coverage | >90% |
| E2E test coverage | >80% |
| API response time | <50ms (search) |
| Storage overhead | <10MB per 1000 conversations |
| Context injection accuracy | >70% relevance (manual review) |

---

**Ready to start Phase 1?** 🚀

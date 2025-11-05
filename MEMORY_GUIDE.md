# 💾 Memory System Guide

## 🤔 What Is Memory?

The Multi-Agent Orchestrator has a **persistent memory system** that:

1. **Saves every conversation** in a database
2. **Searches past conversations** when you ask a new question
3. **Automatically adds relevant context** to your prompts
4. **Understands meaning, not just keywords** (semantic search)

**Think of it as:** The system never forgets what you talked about before!

---

## 🎯 Why Is This Useful?

### Without Memory (Traditional ChatGPT)

```
Monday:
You: "Create a user authentication system"
AI: [creates system...]

Friday:
You: "Add OAuth to the authentication system"
AI: "Which authentication system? Please provide details."
❌ You have to explain everything again!
```

### With Memory (Our Orchestrator)

```
Monday:
You: "Create a user authentication system"
AI: [creates system...]
💾 Saved to memory

Friday:
You: "Add OAuth to the authentication system"
💡 Memory finds Monday's conversation
✅ AI: "I'll add OAuth to the JWT-based system we created on Monday..."
```

**Magic:** You don't need to explain context every time!

---

## 🔍 How Does It Work?

### Step-by-Step Flow

```
1. You ask a new question
   ↓
2. Memory Engine searches database
   ↓
3. Finds relevant past conversations (semantic search)
   ↓
4. Adds top results to your prompt (context injection)
   ↓
5. AI sees both your question AND relevant history
   ↓
6. You get a context-aware answer
   ↓
7. New conversation is saved to memory
```

### Under the Hood

Every conversation is converted to **embeddings** (numbers that represent meaning):

```
"Create Kubernetes Helm chart"
↓
[0.234, -0.891, 0.456, ..., 0.123]  (384 numbers)

"Add monitoring to previous chart"
↓
[0.221, -0.875, 0.443, ..., 0.109]  (384 numbers)

Similarity = 0.87 (87% match!) ✅
→ These conversations are related!
```

---

## 🌍 Multilingual Support

### The Problem

Traditional keyword search fails with different languages:

```
Search: "chart"
❌ Won't find: "chart'ı" (Turkish - accusative case)
❌ Won't find: "chart'a" (Turkish - dative case)
❌ Won't find: "grafico" (Spanish)
```

### Our Solution: Semantic Search

```
Search: "chart"
✅ Finds: "chart'ı", "chart'a", "chart'tan"
✅ Finds: "grafico", "graphique", "图表"
✅ Finds: "Helm chart", "chart configuration", "chart values"
```

**Why?** Because we understand **meaning**, not just exact text!

### Supported Languages

**50+ languages including:**
- English
- Turkish (with suffix handling)
- Arabic
- Chinese
- Japanese
- Korean
- Spanish
- French
- German
- Russian
- And many more...

---

## 🎛️ Search Strategies

You can choose how memory searches work:

### 1. Semantic (Default)

**How it works:** Understands meaning using AI embeddings

**Best for:**
- Natural language questions
- Finding conceptually related conversations
- Multilingual searches

**Example:**
```
Search: "authentication"
Finds:
- "Create JWT login system" (90% relevance)
- "User authorization with tokens" (85% relevance)
- "OAuth integration" (78% relevance)
```

### 2. Keywords

**How it works:** Traditional text matching with stemming

**Best for:**
- Exact technical terms
- Finding specific function/class names
- Code snippets

**Example:**
```
Search: "PostgreSQL"
Finds:
- "Set up PostgreSQL database" (100% match)
- "postgres connection pooling" (95% match)
- "Database migration" (no match - too vague)
```

### 3. Hybrid (70% semantic + 30% keywords)

**How it works:** Combines both approaches

**Best for:**
- General use (balanced)
- When you want both conceptual and exact matches

**Example:**
```
Search: "Redis caching"
Finds:
- "Redis cache implementation" (95% - keyword match)
- "In-memory data store setup" (80% - semantic match)
- "Performance optimization with caching" (70% - semantic match)
```

---

## ⚙️ Configuration

### Per-Agent Settings

Each agent can have different memory settings. Edit `config/agents.yaml`:

```yaml
builder:
  memory_enabled: true
  memory:
    strategy: "semantic"        # Search strategy
    max_context_tokens: 600     # How much history to inject
    min_relevance: 0.35         # Minimum similarity score (0-1)
    time_decay_hours: 168       # 7 days - older = lower score
    exclude_same_turn: true     # Don't inject from current session
```

### What Each Setting Means

**memory_enabled:**
- `true`: Agent uses memory (builder, critic)
- `false`: Agent ignores history (closer - needs to be decisive)

**strategy:**
- `"semantic"`: AI-based meaning search (best for natural language)
- `"keywords"`: Text-based search (best for exact terms)
- `"hybrid"`: 70% semantic + 30% keywords (balanced)

**max_context_tokens:**
- How many tokens of history to inject
- Builder: 600 tokens (detailed context)
- Critic: 500 tokens (recent issues focus)
- Higher = more context but slower + more expensive

**min_relevance:**
- Threshold for including conversations (0.0 to 1.0)
- 0.35 = 35% similarity minimum
- Lower = more results (may include irrelevant)
- Higher = fewer results (only very relevant)

**time_decay_hours:**
- How fast old conversations lose relevance
- 168 hours (7 days) = exponential decay
- Recent conversations weighted higher

**exclude_same_turn:**
- `true`: Don't inject context from current session
- `false`: Include everything (may cause loops)

---

## 📊 Memory Commands

### 1. Search Conversations

```bash
# Basic search
make memory-search Q="authentication"

# Search specific agent's conversations
make memory-search Q="JWT" AGENT=builder

# Limit results
make memory-search Q="Kubernetes" LIMIT=5
```

**Output:**
```
🔍 Searching for: authentication
📊 Found 3 conversations (showing top 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ID: 42
📅 Date: 2025-11-03 14:32:15
🤖 Agent: builder (anthropic/claude-3-5-sonnet-20241022)
📊 Tokens: 3,245 | Cost: $0.048
🎯 Relevance: 0.89

💬 Prompt (first 200 chars):
Create a JWT-based authentication system with refresh tokens...

💬 Response (first 200 chars):
Here's a complete JWT authentication implementation...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. View Recent Conversations

```bash
# Last 10 conversations
make memory-recent

# Last 20 conversations
make memory-recent LIMIT=20

# Recent conversations from specific agent
make memory-recent AGENT=builder LIMIT=5
```

### 3. View Statistics

```bash
make memory-stats
```

**Output:**
```
📊 Memory Statistics

Total Conversations: 127
Total Tokens: 456,892
Estimated Total Cost: $6.84

By Agent:
  builder: 85 conversations (66.9%)
  critic: 38 conversations (29.9%)
  closer: 4 conversations (3.1%)

By Provider:
  anthropic: 85 (66.9%)
  google: 38 (29.9%)
  openai: 4 (3.1%)

Date Range:
  Oldest: 2025-10-15 09:23:41
  Newest: 2025-11-05 16:34:35
```

### 4. Export Conversations

```bash
# Export as JSON
make memory-export FORMAT=json > backup.json

# Export as CSV
make memory-export FORMAT=csv > conversations.csv

# Export as Markdown
make memory-export FORMAT=markdown > history.md
```

### 5. Cleanup Old Conversations

```bash
# Delete conversations older than 90 days (DRY RUN)
make memory-cleanup DAYS=90

# Actually delete (requires CONFIRM=1)
make memory-cleanup DAYS=90 CONFIRM=1
```

**Output:**
```
🧹 Cleanup: Deleting conversations older than 90 days

Found 15 conversations to delete:
  Oldest: 2025-08-01 10:15:23
  Newest: 2025-08-05 18:42:10
  Total tokens: 23,456
  Estimated cost: $0.35

❌ DRY RUN - No changes made
ℹ️  Run with CONFIRM=1 to actually delete
```

---

## 🎯 Real-World Examples

### Example 1: Continuing a Project

**Day 1:**
```bash
mao builder "Create a FastAPI server with user registration"
```

**Day 7:**
```bash
mao builder "Add email verification to the registration system"
```

**What happens:**
1. Memory searches for "registration"
2. Finds Day 1 conversation (relevance: 0.92)
3. Injects 350 tokens of context
4. Builder sees the original code and adds email verification

**Result:** Builder knows exactly which registration system you're talking about!

---

### Example 2: Multilingual Continuation (Turkish)

**Week 1:**
```bash
mao builder "Kubernetes için Helm chart oluştur"
```

**Week 2:**
```bash
mao builder "Önceki chart'a monitoring ekle"
```

**What happens:**
1. Semantic search understands "chart'a" = "chart" (dative case)
2. Finds Week 1 conversation
3. Adds Helm chart context
4. Builder extends the existing chart

**Result:** Works perfectly even with Turkish grammar! ✅

---

### Example 3: Finding Related Concepts

**Past conversations:**
- "Create JWT authentication"
- "Set up OAuth2 with Google"
- "Implement API key middleware"

**New question:**
```bash
mao builder "Add security to the API endpoints"
```

**What happens:**
1. Semantic search finds all three past conversations
2. Relevance scores: JWT (0.78), OAuth (0.71), API keys (0.82)
3. Injects top 2 conversations (API keys + JWT)
4. Builder creates security that's consistent with past work

**Result:** Coherent security implementation across your project!

---

### Example 4: Debugging with Memory

**Two weeks ago:**
```bash
mao builder "Create PostgreSQL connection pool"
```

**Today:**
```bash
mao critic "Why is the database connection failing?"
```

**What happens:**
1. Memory finds PostgreSQL conversation
2. Critic sees the original connection code
3. Spots the issue: "Missing connection timeout in pool configuration"

**Result:** Faster debugging with historical context!

---

## 🚀 Best Practices

### 1. Use Descriptive Prompts

**❌ Bad:**
```bash
mao builder "Fix this"
```

**✅ Good:**
```bash
mao builder "Fix the authentication timeout issue in the JWT middleware"
```

Why? Better prompts create better memory entries that are easier to find later!

---

### 2. Check Memory Before Starting

Before working on a feature, search if you've done something similar:

```bash
make memory-search Q="authentication" AGENT=builder
```

You might find you already solved this problem!

---

### 3. Use Chains for Complex Tasks

Chains create richer memory entries:

```bash
mao-chain "Design microservices architecture"
```

This saves:
- Builder's design
- Critic's analysis
- Closer's final decisions

All searchable later!

---

### 4. Periodic Cleanup

Delete old irrelevant conversations:

```bash
# Every 3 months, delete conversations older than 90 days
make memory-cleanup DAYS=90 CONFIRM=1
```

Keeps memory fast and relevant!

---

### 5. Export Important Sessions

Before cleaning up, export important conversations:

```bash
make memory-export FORMAT=markdown > project_history.md
```

You have permanent documentation!

---

## 🐛 Troubleshooting

### Problem: "No relevant conversations found"

**Possible causes:**
1. This is your first conversation (no history yet)
2. `min_relevance` threshold too high
3. Search terms too specific

**Solutions:**
```bash
# Lower threshold in config/agents.yaml
min_relevance: 0.25  # Instead of 0.35

# Or search manually with broader terms
make memory-search Q="database"  # Instead of "PostgreSQL connection pooling"
```

---

### Problem: Too many irrelevant results

**Possible causes:**
1. `min_relevance` threshold too low
2. Too many old conversations

**Solutions:**
```yaml
# Raise threshold
min_relevance: 0.45  # Instead of 0.35

# Increase time decay
time_decay_hours: 48  # Instead of 168 (prefer recent)
```

---

### Problem: Memory search is slow

**Possible causes:**
1. Too many conversations (1000+)
2. Embeddings need regenerating

**Solutions:**
```bash
# Delete old conversations
make memory-cleanup DAYS=60 CONFIRM=1

# Or use keywords strategy (faster)
# In config/agents.yaml:
strategy: "keywords"
```

---

### Problem: Context not being injected

**Check if:**
1. `memory_enabled: true` for that agent?
2. Any conversations match `min_relevance` threshold?
3. Check logs: `mao-logs` shows `injected_context_tokens: 0`?

**Debug:**
```bash
# Manually search
make memory-search Q="your search terms" AGENT=builder

# Check agent config
cat config/agents.yaml | grep -A 10 "builder:"
```

---

## 📈 Memory Performance

### Token Usage

Memory injection adds tokens to each request:

```
Without memory:
Prompt: 50 tokens
Response: 500 tokens
Total: 550 tokens

With memory (max_context_tokens=600):
Prompt: 50 tokens
Injected context: 350 tokens
Response: 500 tokens
Total: 900 tokens (+63% tokens, +$0.005 cost)
```

**Is it worth it?** YES! You save time by not re-explaining context.

---

### Database Size

Approximate storage needs:

```
100 conversations = ~2 MB
1,000 conversations = ~20 MB
10,000 conversations = ~200 MB
```

**Disk space is cheap** - don't worry unless you have 50,000+ conversations!

---

### Search Speed

Average search times:

```
100 conversations: <10ms
1,000 conversations: <50ms
10,000 conversations: <200ms
```

**Fast enough for real-time use!**

---

## 🎓 Advanced Features

### Session Filtering

The system automatically excludes conversations from the **same session** (prevents circular references):

```yaml
exclude_same_turn: true  # Don't inject from current conversation
```

Example:
```
You: "Create API"
[Conversation ID: 123]

You: "Add authentication"
→ Won't inject conversation 123 (same session)
→ Will inject older conversation 42 (different session)
```

---

### Time Decay Formula

Older conversations get lower scores:

```python
age_hours = (now - conversation_timestamp).hours
decay = exp(-age_hours / time_decay_hours)
final_score = relevance * decay

Example:
Conversation: "Create API" (relevance: 0.80)
Age: 7 days (168 hours)
Decay hours: 168
Decay factor: exp(-168/168) = 0.368
Final score: 0.80 * 0.368 = 0.294
```

If `min_relevance: 0.35`, this conversation **won't** be included!

---

### Hybrid Strategy Weights

```python
hybrid_score = (0.7 * semantic_score) + (0.3 * keyword_score)

Example:
Semantic: 0.60
Keyword: 0.90
Hybrid: (0.7 * 0.60) + (0.3 * 0.90) = 0.42 + 0.27 = 0.69
```

---

## 📚 Further Reading

- **Technical Details:** See `CLAUDE.md` - Memory System section
- **API Documentation:** `README.md` - Memory API Endpoints
- **Configuration:** `config/memory.yaml`
- **Database Schema:** `core/memory_engine.py`

---

## 🎯 Summary

**Memory system gives you:**

1. ✅ **Context continuity** - Never re-explain your project
2. ✅ **Multilingual support** - Works in 50+ languages
3. ✅ **Semantic search** - Finds by meaning, not just keywords
4. ✅ **Automatic injection** - Zero effort, just works
5. ✅ **Full control** - Search, export, delete as needed
6. ✅ **Cost-effective** - Small token overhead, huge time savings

**Start using it:**
```bash
# Your first conversation
mao builder "Create a REST API"

# Later (days/weeks)
mao builder "Add rate limiting to the API"
→ Memory finds the first conversation automatically!
```

**That's it! The system remembers so you don't have to!** 💾✨

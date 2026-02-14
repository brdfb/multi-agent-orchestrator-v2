# CLI Codebase Analysis Report

**Date:** 2025-11-11  
**Status:** Pre-Implementation Analysis  
**Purpose:** Comprehensive analysis of current CLI state before implementing CLI_ROADMAP.md

---

## 📊 Executive Summary

### Current State: **PARTIALLY IMPLEMENTED**

**Good News:**
- ✅ Core file I/O features (`--file`, `--save-to`) **ALREADY WORKING**
- ✅ Cost guardrails (`--max-usd`, `--max-input-tokens`, `--force`) **ALREADY IMPLEMENTED**
- ✅ Model override (`--model`) **ALREADY WORKING**
- ✅ Basic security validation **EXISTS** (but needs enhancement)

**Bad News:**
- ❌ **ZERO CLI tests** - No test coverage for CLI scripts
- ❌ Missing features: `--files` (multiple), memory flags, `--read-only`, `--confirm-write`
- ⚠️ Security model is **basic** - needs comprehensive `SecurityManager` class
- ⚠️ No audit logging for security events

**Verdict:** CLI_ROADMAP.md claims are **partially accurate** - some features exist but need enhancement and testing.

---

## 🔍 Detailed Feature Analysis

### ✅ Working Features

#### 1. File Input (`--file`)
**Status:** ✅ **WORKING**

**Location:** `scripts/agent_runner.py:202-223`, `scripts/chain_runner.py:202-244`

**Implementation:**
```python
parser.add_argument("--file", type=str, help="Read prompt from file")
# ...
if args.file:
    prompt = read_file_with_validation(args.file)
```

**What Works:**
- ✅ Reads single file
- ✅ Basic path validation (blocks `.env`, `.git`, etc.)
- ✅ File size check (10MB limit)
- ✅ UTF-8 encoding with error handling
- ✅ File existence check

**What's Missing:**
- ❌ `--files` (multiple files) - not implemented
- ❌ Automatic syntax detection/wrapping for code files
- ❌ Comprehensive security model (uses basic validation)

**Test Coverage:** ❌ **ZERO TESTS**

---

#### 2. File Output (`--save-to`)
**Status:** ✅ **WORKING** (but basic)

**Location:** `scripts/agent_runner.py:204-205, 351-361`, `scripts/chain_runner.py:203, 366-406`

**Implementation:**
```python
parser.add_argument("--save-to", type=str, help="Save response to file")
# ...
if args.save_to:
    validate_path_basic(args.save_to)
    with open(args.save_to, 'w', encoding='utf-8') as f:
        f.write(result.response)
```

**What Works:**
- ✅ Saves response to file
- ✅ Basic path validation
- ✅ Works in both `agent_runner.py` and `chain_runner.py`

**What's Missing:**
- ❌ `--format` (markdown/json/text) - always saves as plain text
- ❌ `--append` mode - always overwrites
- ❌ Metadata in saved files (agent, model, date, tokens, cost)
- ❌ `--confirm-write` flag for code/config files

**Test Coverage:** ❌ **ZERO TESTS**

---

#### 3. Cost Guardrails
**Status:** ✅ **WORKING**

**Location:** `scripts/agent_runner.py:212-275`, `scripts/chain_runner.py:209-294`

**Implementation:**
```python
parser.add_argument("--max-usd", type=float, help="Abort if estimated cost exceeds threshold")
parser.add_argument("--max-input-tokens", type=int, help="Reject prompts over N tokens")
parser.add_argument("--force", action="store_true", help="Bypass cost limits (logged)")

# Pre-flight check
input_tokens, estimated_cost = estimate_input_cost(prompt, args.model or "gpt-4o")
if args.max_input_tokens and input_tokens > args.max_input_tokens:
    if not args.force:
        console.print(f"❌ Input exceeds limit...")
        sys.exit(1)
```

**What Works:**
- ✅ `--max-usd` - aborts if cost > threshold
- ✅ `--max-input-tokens` - rejects large prompts
- ✅ `--force` - bypasses limits with warning
- ✅ Pre-flight cost estimation using `tiktoken`
- ✅ Works in both single agent and chain

**What's Missing:**
- ❌ `--read-only` flag (disable all writes)
- ❌ Audit logging for `--force` bypasses
- ❌ Daily/monthly budget tracking
- ❌ Cost estimation accuracy validation

**Test Coverage:** ❌ **ZERO TESTS**

---

#### 4. Model Override (`--model`)
**Status:** ✅ **WORKING**

**Location:** `scripts/agent_runner.py:208-251`, `scripts/chain_runner.py:206-267`

**Implementation:**
```python
parser.add_argument("--model", type=str, help="Override agent's default model")
# ...
if args.model:
    provider = args.model.split('/')[0] if '/' in args.model else 'openai'
    if not is_provider_enabled(provider):
        console.print(f"❌ Provider '{provider}' is disabled")
        sys.exit(1)
    override_model = args.model
```

**What Works:**
- ✅ Overrides agent's default model
- ✅ Validates provider is enabled
- ✅ Shows available providers on error
- ✅ Works in both single agent and chain

**What's Missing:**
- ❌ Model whitelist validation (any string accepted)
- ❌ Better error messages with model suggestions

**Test Coverage:** ❌ **ZERO TESTS**

---

### ❌ Missing Features

#### 1. Multiple File Input (`--files`)
**Status:** ❌ **NOT IMPLEMENTED**

**Expected:**
```bash
mao builder --files design.md impl.py tests.py
```

**Current:** Only `--file` (single file) exists.

---

#### 2. Memory Control Flags
**Status:** ❌ **NOT IMPLEMENTED**

**Missing Flags:**
- `--use-memory` - Force enable memory
- `--no-memory` - Disable memory
- `--show-context` - Display injected context
- `--context-budget N` - Override token budget
- `--min-relevance X` - Override relevance threshold
- `--search-memory QUERY` - Manual search before prompt

**Note:** Memory system works automatically (backend), but CLI has no control flags.

---

#### 3. Enhanced Security Model
**Status:** ⚠️ **BASIC IMPLEMENTATION**

**Current:** `validate_path_basic()` in both scripts
- ✅ Blocks obvious files (`.env`, `.git`, `.ssh`)
- ✅ Warns if outside CWD
- ✅ 10MB file size limit

**Missing:**
- ❌ `config/security.yaml` - No security config file
- ❌ `core/security.py` - No SecurityManager class
- ❌ Allow-list / block-list patterns
- ❌ Confirmation prompts for code/config writes
- ❌ Audit logging (JSONL format)
- ❌ Path traversal prevention (basic exists but not comprehensive)

---

#### 4. Output Format Options
**Status:** ❌ **NOT IMPLEMENTED**

**Missing:**
- `--format {markdown,json,text}` - Output format selection
- `--append` - Append mode instead of overwrite
- Metadata in saved files (agent, model, date, tokens, cost)

**Current:** Always saves as plain text response only.

---

#### 5. Read-Only Mode
**Status:** ❌ **NOT IMPLEMENTED**

**Missing:**
- `--read-only` - Disable all writes (memory, files, DB)

---

## 🧪 Test Coverage Analysis

### Current Test Suite

**Total Tests:** 89 tests across 11 files

**Test Files:**
- `test_api.py` - FastAPI endpoints (6 tests)
- `test_chain.py` - Chain execution (2 tests)
- `test_config.py` - Config loading (3 tests)
- `test_llm_connector_fallback.py` - Fallback logic (7 tests)
- `test_logs.py` - Logging (3 tests)
- `test_memory_engine.py` - Memory system (25 tests)
- `test_override.py` - Model override (2 tests)
- `test_runtime.py` - Agent runtime (29 tests)
- `test_semantic_search.py` - Semantic search (5 tests)
- `test_chain_fallback_e2e.py` - E2E fallback (6 tests)
- `test_sequential_conversation.sh` - Sequential conversation (manual)

**CLI Test Coverage:** ❌ **ZERO TESTS**

### Missing Test Categories

1. **CLI Script Tests** (`test_cli_*.py`)
   - File input/output
   - Cost guardrails
   - Model override
   - Security validation
   - Error handling

2. **Integration Tests**
   - CLI → AgentRuntime integration
   - CLI → Memory system integration
   - CLI → Session tracking integration

3. **Security Tests**
   - Path traversal prevention
   - File access validation
   - Audit logging

4. **Edge Case Tests**
   - Large files (>10MB)
   - Binary files
   - Missing files
   - Permission errors
   - Network failures

---

## 📋 Implementation Priority (Revised)

### Week 1 - Critical Gaps

**P1.1: CLI Test Suite** (6 hours) - **NEW PRIORITY**
- Create `tests/test_cli_agent_runner.py`
- Create `tests/test_cli_chain_runner.py`
- Test all existing features
- Test error handling
- Test security validation

**P1.2: Enhanced Security Model** (5 hours)
- Create `config/security.yaml`
- Create `core/security.py` (SecurityManager)
- Replace `validate_path_basic()` with SecurityManager
- Add audit logging

**P1.3: Documentation Fix** (2 hours) - **REDUCED** (some features exist)
- Update README with accurate status
- Document existing features
- Mark missing features clearly

**P1.4: Multiple File Input** (3 hours)
- Add `--files` flag
- Implement concatenation with headers
- Add syntax detection

**P1.5: Output Format Options** (2 hours)
- Add `--format` flag
- Add `--append` mode
- Add metadata to saved files

**Total:** 18 hours (same as roadmap, but different priorities)

---

## 🎯 Test Plan

### Test File Structure

```
tests/
├── test_cli_agent_runner.py    # NEW - Agent runner CLI tests
├── test_cli_chain_runner.py     # NEW - Chain runner CLI tests
├── test_cli_security.py         # NEW - Security validation tests
└── fixtures/
    ├── test_prompt.md           # Test file for --file
    ├── test_code.py             # Test code file
    └── large_file.txt           # >10MB file for size tests
```

### Test Categories

#### 1. File Input Tests
- ✅ Read single file (`--file`)
- ✅ Read multiple files (`--files`) - after implementation
- ✅ File not found error
- ✅ File too large error (>10MB)
- ✅ Binary file error
- ✅ Path traversal prevention
- ✅ Blocked file access (.env, .git)

#### 2. File Output Tests
- ✅ Save to file (`--save-to`)
- ✅ Save with format (`--format markdown/json/text`) - after implementation
- ✅ Append mode (`--append`) - after implementation
- ✅ Write to blocked path error
- ✅ Permission denied error

#### 3. Cost Guardrail Tests
- ✅ `--max-usd` aborts on high cost
- ✅ `--max-input-tokens` rejects large prompts
- ✅ `--force` bypasses limits
- ✅ Cost estimation accuracy
- ✅ Token counting accuracy

#### 4. Model Override Tests
- ✅ Valid model override
- ✅ Invalid model error
- ✅ Disabled provider error
- ✅ Model validation

#### 5. Security Tests
- ✅ Path traversal prevention
- ✅ Blocked file access
- ✅ File size limits
- ✅ Audit logging (after implementation)

---

## 📊 Feature Completeness Matrix

| Feature | Status | Test Coverage | Priority |
|---------|--------|---------------|----------|
| `--file` (single) | ✅ Working | ❌ None | P1.1 (test) |
| `--files` (multiple) | ❌ Missing | ❌ None | P1.4 |
| `--save-to` | ✅ Working | ❌ None | P1.1 (test) |
| `--format` | ❌ Missing | ❌ None | P1.5 |
| `--append` | ❌ Missing | ❌ None | P1.5 |
| `--model` | ✅ Working | ❌ None | P1.1 (test) |
| `--max-usd` | ✅ Working | ❌ None | P1.1 (test) |
| `--max-input-tokens` | ✅ Working | ❌ None | P1.1 (test) |
| `--force` | ✅ Working | ❌ None | P1.1 (test) |
| `--use-memory` | ❌ Missing | ❌ None | P2.1 |
| `--show-context` | ❌ Missing | ❌ None | P2.1 |
| `--read-only` | ❌ Missing | ❌ None | P2.x |
| `--confirm-write` | ❌ Missing | ❌ None | P1.2 |
| Security model | ⚠️ Basic | ❌ None | P1.2 |
| Audit logging | ❌ Missing | ❌ None | P1.2 |

---

## 🔧 Code Quality Issues

### 1. Code Duplication

**Problem:** `validate_path_basic()` and `read_file_with_validation()` duplicated in both scripts.

**Location:**
- `scripts/agent_runner.py:22-76`
- `scripts/chain_runner.py:22-76`

**Solution:** Extract to `core/cli_utils.py` or `core/security.py`

---

### 2. Error Handling

**Current:** Uses `sys.exit(1)` directly in functions.

**Better:** Return errors and handle in `main()` for better testability.

---

### 3. Testability

**Problem:** CLI scripts are hard to test because:
- Direct `sys.exit()` calls
- Direct `console.print()` calls
- No dependency injection

**Solution:** Refactor to use dependency injection for console, file operations, etc.

---

## ✅ Recommendations

### Immediate Actions (Before Implementation)

1. **Create CLI Test Suite** (P1.1)
   - Test all existing features
   - Establish test patterns
   - Identify edge cases

2. **Extract Common Code**
   - Move `validate_path_basic()` to `core/security.py`
   - Move `read_file_with_validation()` to `core/cli_utils.py`
   - Reduce duplication

3. **Enhance Security Model** (P1.2)
   - Create `config/security.yaml`
   - Create `core/security.py` (SecurityManager)
   - Replace basic validation

4. **Update Documentation**
   - Mark existing features as "working"
   - Mark missing features clearly
   - Update CLI_ROADMAP.md with current state

### Implementation Order

1. **Week 1:**
   - P1.1: CLI Test Suite (6h)
   - P1.2: Enhanced Security (5h)
   - P1.3: Documentation Fix (2h)
   - P1.4: Multiple Files (3h)
   - P1.5: Output Format (2h)

2. **Week 2:**
   - P2.1: Memory Integration (5h)
   - P2.2: Read-Only Mode (2h)
   - P2.3: Additional features

---

## 📝 Conclusion

**Current State:** CLI has **more features than expected** but **zero test coverage**.

**Key Findings:**
- ✅ File I/O, cost guardrails, model override **already work**
- ❌ Missing: multiple files, memory flags, enhanced security
- ❌ **Critical:** Zero test coverage for CLI scripts

**Next Steps:**
1. Create comprehensive CLI test suite
2. Enhance security model
3. Add missing features
4. Update documentation

---

**Last Updated:** 2025-11-11  
**Analyst:** Claude Code  
**Status:** ✅ Ready for Implementation


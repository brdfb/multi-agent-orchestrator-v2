# CLI Development Roadmap & Implementation Guide

**Created:** 2025-11-11
**Status:** 🔴 **ACTIVE - Primary Reference Document**
**Purpose:** Comprehensive CLI improvement plan with analysis, priorities, and security model
**Supersedes:** `clitodo.md`, `CLI_FILE_CONTEXT_ANALYSIS.md`, `DOCUMENTATION_CORRECTIONS.md`

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Critical Issues & Corrections](#critical-issues--corrections)
4. [Implementation Roadmap](#implementation-roadmap)
5. [Security & Safety Model](#security--safety-model)
6. [Acceptance Criteria Template](#acceptance-criteria-template)
7. [Week-by-Week Plan](#week-by-week-plan)

---

## 1. Executive Summary

### What's Wrong?

**Documentation Claims vs. Reality:**
- ❌ README claims "CLI Feature Parity (v0.12.0)" - **MISLEADING**
- ❌ v0.12.0 only added cosmetic features (syntax highlighting, colors)
- ❌ Core file I/O and security features **MISSING**

**Critical Gaps:**
1. **File Input:** Cannot read prompts from files (`prompt.md`, `code.py`)
2. **File Output:** Single agent cannot save responses (only chains can)
3. **Security:** No file operation validation, path traversal possible
4. **Guardrails:** No cost caps, token limits, or confirmation prompts
5. **Memory Visibility:** Context injection hidden, no control flags
6. **Context Management:** Cannot summarize or inject old conversations manually

### What Works?

**Backend Infrastructure:** ⭐⭐⭐⭐⭐ **Excellent**
- ✅ Dual-context model (session + knowledge)
- ✅ Session tracking (2h timeout, auto-reuse)
- ✅ Semantic compression (86% token savings)
- ✅ Memory engine (SQLite + embeddings)
- ✅ Cost tracking & metrics

**CLI Exposure:** ⭐⭐☆☆☆ **Needs Work**
- ⚠️ Rich formatting (colors, syntax highlighting) - cosmetic only
- ❌ File I/O - missing
- ❌ Security controls - missing
- ❌ Cost guardrails - missing
- ❌ Memory integration - fragmented

### Quick Wins (Week 1 - 18 hours)

1. **Fix Documentation** (4h) - Remove misleading "parity" claims
2. **Cost Guardrails** (4h) - Prevent accidental $15+ charges
3. **Security Model** (5h) - File validation, audit logging
4. **File Input** (4h) - `--file` and `--files` flags
5. **Acceptance Criteria** (1h) - Add to all tasks

---

## 2. Current State Analysis

### 2.1 Can CLI Read Files? ❌ NO

**Current Behavior:**
```bash
# ❌ This doesn't work:
mao builder --file prompt.md

# ⚠️ Manual workaround (error-prone):
mao builder "$(cat prompt.md)"
```

**Issues with Workaround:**
- Shell escaping problems with special characters
- No file type detection (Python vs Markdown)
- No multi-file support
- No error handling for missing files

**What's Needed:** `--file` and `--files` flags with security validation

---

### 2.2 Can CLI Save Responses? ⚠️ PARTIAL

**What Works:**
```bash
# ✅ Chain runner has --save-to:
mao-chain "Design API" --save-to report.md
```

**What Doesn't Work:**
```bash
# ❌ Single agent runner missing --save-to:
mao builder "Create API" --save-to design.md
# Error: Unknown option --save-to
```

**Test Result:**
```bash
# ✅ VERIFIED: Chain output saved successfully
ls -lh /tmp/test_output.md
# -rw-r--r-- 1 beredhome 24K Nov 11 09:38 /tmp/test_output.md
```

**What's Needed:** Add `--save-to` to `agent_runner.py` with format options

---

### 2.3 Can CLI Summarize Conversations? ⚠️ BACKEND YES, CLI NO

**Surprising Finding:**
```python
# ✅ BACKEND HAS THIS: core/agent_runtime.py:80-141
def _compress_semantic(self, text: str, max_tokens: int = 500):
    """Extract semantic essence using structured JSON compression."""
    # Uses Gemini-2.5-flash for 86% token savings
    # Structured output: decisions, specs, warnings, actions
```

**But CLI Cannot Access It:**
```bash
# ❌ These commands don't exist:
mao summarize --session cli-12345-...
mao summarize --id 123 --max-tokens 300
mao builder "Continue" --use-summary session.md
```

**What's Needed:** `summarize_cli.py` to expose compression feature

---

### 2.4 Does Infrastructure Support Context Continuity? ✅ YES

**Dual-Context Model (v0.11.0):**

```
┌─────────────────────────────────────────┐
│  AUTOMATIC CONTEXT MANAGEMENT           │
├─────────────────────────────────────────┤
│  1. SESSION CONTEXT (Priority 1)        │
│     ↳ Last 5 messages (same session)    │
│     ↳ Up to 75% of token budget         │
│     ↳ Conversation continuity           │
│                                         │
│  2. KNOWLEDGE CONTEXT (Priority 2)      │
│     ↳ Semantic search (other sessions)  │
│     ↳ Remaining token budget            │
│     ↳ Cross-session learning            │
└─────────────────────────────────────────┘
```

**Example:**
```bash
# Terminal 1 - 10:00 AM (PID 12345)
mao builder "Create a chart"
# session_id: cli-12345-20251111100000

# Same terminal - 10:30 AM (within 2h)
mao builder "Add red color"
# ✅ SAME SESSION - "Create a chart" context automatically injected
# 🧠 Memory: 250 tokens injected
#    ├─ Session: 200 tokens (1 message)
#    └─ Knowledge: 50 tokens (semantic search)

# Same terminal - 1:30 PM (>2h timeout)
mao builder "Show the chart"
# ❌ NEW SESSION (timeout)
# 🧠 Memory: 170 tokens injected
#    ├─ Session: 0 tokens (new session)
#    └─ Knowledge: 170 tokens (morning chart found via semantic search)
```

**Evidence:**
- ✅ `core/context_aggregator.py` - Dual-context engine
- ✅ `core/session_manager.py` - Auto session tracking
- ✅ `core/memory_engine.py` - SQLite + embeddings
- ✅ Tested and verified working

---

## 3. Critical Issues & Corrections

### Issue #1: False "CLI Feature Parity" Claim 🚨

**Location:** `README.md:120-125`, `README.md:877`

**Current (Misleading):**
```markdown
- **💻 CLI Feature Parity (v0.12.0)**:
  - Rich terminal formatting
  - Code syntax highlighting
  - Memory context visibility
  - Enhanced error messages
  - Cost tracking dashboard

...

- ✅ Rich CLI + Web UI feature parity
```

**Reality Check:**

| Feature | Web UI | CLI | Parity? |
|---------|--------|-----|---------|
| File upload/input | ✅ | ❌ | **NO** |
| Model override dropdown | ✅ | ❌ | **NO** |
| Save response to file | ✅ | ⚠️ Partial | **NO** |
| Interactive history browser | ✅ | ❌ | **NO** |
| Syntax highlighting | ✅ | ✅ | YES |
| Error messages | ✅ | ✅ | YES |
| Cost tracking | ✅ | ✅ | YES |

**Verdict:** v0.12.0 added **cosmetic features only** - functional parity does NOT exist.

**REQUIRED CORRECTION:**

```markdown
# BEFORE (misleading):
- **💻 CLI Feature Parity (v0.12.0)**

# AFTER (accurate):
- **💻 CLI UX Enhancements (v0.12.0)**:
  - Rich terminal formatting (colored output, emojis, boxes)
  - Code syntax highlighting (monokai theme)
  - Memory context visibility (session + knowledge breakdown)
  - Enhanced error messages (6+ types with solutions)
  - Cost tracking dashboard (`make stats` with trends)
  - ⚠️ **Note:** Core file I/O and security features pending (see `docs/CLI_ROADMAP.md`)
```

**Files to Update:**
- [ ] `README.md:120-125` - Change heading and add disclaimer
- [ ] `README.md:877` - Change "feature parity" to "enhanced UX"
- [ ] `executive_summary.md` - Update claims if present

---

### Issue #2: Missing Cost/Budget Guardrails 💸

**Current Danger:**
```bash
# User accidentally pastes large file
mao builder "$(cat 50KB_file.txt)"
# 💸 Result: $15 charge, NO WARNING!
```

**Missing Features:**

| Guardrail | Status | Risk Level |
|-----------|--------|------------|
| `--max-usd` (cost cap) | ❌ | 🔴 HIGH |
| `--max-input-tokens` (input limit) | ❌ | 🔴 HIGH |
| `--max-output-tokens` (output limit) | ❌ | 🟡 MEDIUM |
| `--confirm-write` (file write approval) | ❌ | 🔴 HIGH |
| `--read-only` (disable all writes) | ❌ | 🟡 MEDIUM |
| Budget tracking (daily/monthly) | ❌ | 🟡 MEDIUM |

**REQUIRED IMPLEMENTATION:**

```python
# scripts/agent_runner.py (enhanced)
parser.add_argument("--max-usd", type=float, help="Abort if estimated cost > threshold")
parser.add_argument("--max-input-tokens", type=int, help="Reject prompts exceeding limit")
parser.add_argument("--max-output-tokens", type=int, help="Override agent max_tokens")
parser.add_argument("--confirm-write", action="store_true", help="Require approval for writes")
parser.add_argument("--read-only", action="store_true", help="Disable all writes")
parser.add_argument("--force", action="store_true", help="Bypass guardrails (explicit)")

def enforce_guardrails(prompt: str, args):
    """Prevent accidental cost overruns."""
    input_tokens = count_tokens(prompt)

    # Token limit check
    if args.max_input_tokens and input_tokens > args.max_input_tokens:
        if not args.force:
            raise ValueError(
                f"Input exceeds limit: {input_tokens} > {args.max_input_tokens} tokens\n"
                f"Estimated cost: ${estimate_cost(input_tokens):.2f}\n"
                f"Use --force to override"
            )

    # Cost limit check
    if args.max_usd:
        estimated = estimate_request_cost(prompt, agent_config)
        if estimated > args.max_usd:
            raise ValueError(
                f"Estimated cost ${estimated:.2f} exceeds budget ${args.max_usd:.2f}\n"
                f"Reduce prompt size or use --force"
            )
```

**Usage:**
```bash
# Safe mode (abort if >$0.50)
mao builder "Complex task" --max-usd 0.50

# Token budget
mao builder "Analyze" --max-input-tokens 2000

# Read-only (no writes to memory/files)
mao builder "Quick question" --read-only

# Force bypass (logged to audit)
mao builder "Large task" --max-usd 0.50 --force
# ⚠️  FORCE: Bypassing budget ($1.20 > $0.50)
```

---

### Issue #3: Missing Security Controls 🔒

**Current Vulnerabilities:**
```bash
# ❌ Path traversal attack
mao builder --file ../../../etc/passwd "Read this"

# ❌ Backdoor injection
mao builder "Code" --save-to ../../.git/hooks/pre-commit

# ❌ No confirmation for code writes
mao builder "Generate script" --save-to deploy.sh
# Writes without asking!
```

**REQUIRED: Security Model**

#### config/security.yaml (NEW FILE)

```yaml
cli:
  # File operation controls
  file_operations:
    default_mode: "confirm-write"  # read-only | confirm-write | unrestricted

    allowed_read_paths:
      - "./data/**"
      - "./config/**"
      - "./docs/**"
      - "./scripts/**"
      - "/tmp/**"

    allowed_write_paths:
      - "./data/CONVERSATIONS/**"
      - "./data/MEMORY/**"
      - "./data/AUDIT/**"
      - "/tmp/**"

    blocked_paths:
      - ".env"
      - ".env.*"
      - ".git/**"
      - "**/*.key"
      - "**/*credentials*"
      - "**/*password*"
      - "/etc/**"
      - "/root/**"
      - "~/.ssh/**"

    max_file_size_mb: 10

    require_confirmation_for:
      - "*.py"
      - "*.sh"
      - "*.bash"
      - "*.zsh"
      - "config/**"
      - ".bashrc"
      - ".zshrc"

  # Cost controls
  budget:
    daily_limit_usd: 10.0
    monthly_limit_usd: 100.0
    warn_threshold: 0.80  # Warn at 80%
    track_in_db: true
    db_path: "data/AUDIT/budget.db"

  # Audit logging
  audit:
    enabled: true
    log_file: "data/AUDIT/cli_audit.jsonl"
    log_events:
      - file_read
      - file_write
      - file_delete
      - guardrail_bypass
      - cost_warning
      - cost_limit_exceeded
      - security_violation
```

#### core/security.py (NEW FILE)

```python
"""Security manager for CLI operations."""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
import yaml

class SecurityManager:
    """Enforce CLI security policies."""

    def __init__(self, config_path: str = "config/security.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def validate_file_read(self, file_path: str) -> None:
        """Check if file read is allowed."""
        path = Path(file_path).resolve()  # Resolve symlinks, normalize

        # 1. Check blocked paths (absolute deny)
        for pattern in self.config['cli']['file_operations']['blocked_paths']:
            if self._matches_pattern(path, pattern):
                self.log_audit("security_violation", {
                    "action": "file_read_blocked",
                    "path": str(path),
                    "pattern": pattern
                })
                raise PermissionError(
                    f"🔒 Access denied: {file_path}\n"
                    f"Matches blocked pattern: {pattern}\n"
                    f"Security policy prevents reading this file."
                )

        # 2. Check allowed paths (must match at least one)
        allowed = self.config['cli']['file_operations']['allowed_read_paths']
        if not any(self._matches_pattern(path, p) for p in allowed):
            self.log_audit("security_violation", {
                "action": "file_read_denied",
                "path": str(path),
                "reason": "not_in_allowed_paths"
            })
            raise PermissionError(
                f"🔒 Access denied: {file_path}\n"
                f"Path not in allowed read locations.\n"
                f"Allowed: {', '.join(allowed)}"
            )

        # 3. Check file size
        max_size = self.config['cli']['file_operations']['max_file_size_mb'] * 1024 * 1024
        if path.exists() and path.stat().st_size > max_size:
            raise ValueError(
                f"File too large: {path.stat().st_size / 1024 / 1024:.1f}MB\n"
                f"Limit: {max_size / 1024 / 1024:.0f}MB"
            )

        self.log_audit("file_read", {"path": str(path)})

    def validate_file_write(self, file_path: str, require_confirm: bool = False) -> bool:
        """Check if file write is allowed. Returns True if should proceed."""
        path = Path(file_path).resolve()

        # 1. Check blocked paths
        for pattern in self.config['cli']['file_operations']['blocked_paths']:
            if self._matches_pattern(path, pattern):
                self.log_audit("security_violation", {
                    "action": "file_write_blocked",
                    "path": str(path),
                    "pattern": pattern
                })
                raise PermissionError(
                    f"🔒 Write denied: {file_path}\n"
                    f"Matches blocked pattern: {pattern}"
                )

        # 2. Check allowed paths
        allowed = self.config['cli']['file_operations']['allowed_write_paths']
        if not any(self._matches_pattern(path, p) for p in allowed):
            self.log_audit("security_violation", {
                "action": "file_write_denied",
                "path": str(path)
            })
            raise PermissionError(
                f"🔒 Write denied: {file_path}\n"
                f"Path not in allowed write locations.\n"
                f"Allowed: {', '.join(allowed)}"
            )

        # 3. Check if confirmation required
        confirm_patterns = self.config['cli']['file_operations']['require_confirmation_for']
        needs_confirm = any(self._matches_pattern(path, p) for p in confirm_patterns)

        if needs_confirm or require_confirm:
            from rich.console import Console
            console = Console()
            console.print(f"\n[yellow]⚠️  Write to:[/yellow] {file_path}")
            console.print(f"[dim]Type: {path.suffix or 'unknown'}[/dim]")
            response = input("Confirm? [y/N]: ").strip().lower()

            if response != 'y':
                console.print("[red]✗ Write cancelled[/red]")
                self.log_audit("file_write_cancelled", {"path": str(path)})
                return False

            self.log_audit("file_write_confirmed", {"path": str(path)})

        return True

    def _matches_pattern(self, path: Path, pattern: str) -> bool:
        """Check if path matches glob pattern."""
        # Handle both absolute and relative patterns
        if pattern.startswith('/'):
            return path.match(pattern)
        else:
            # Relative pattern - match against any part of path
            return any(p.match(pattern) for p in [path] + list(path.parents))

    def log_audit(self, event: str, data: dict) -> None:
        """Log security event to audit trail."""
        if not self.config['cli']['audit']['enabled']:
            return

        audit_file = Path(self.config['cli']['audit']['log_file'])
        audit_file.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": data,
            "pid": os.getpid()
        }

        with open(audit_file, "a") as f:
            f.write(json.dumps(record) + "\n")

# Global instance
_security_manager = None

def get_security_manager() -> SecurityManager:
    """Get singleton security manager."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
```

**Usage in CLI:**
```python
# scripts/agent_runner.py
from core.security import get_security_manager

security = get_security_manager()

# File input
if args.file:
    security.validate_file_read(args.file)  # Raises PermissionError if blocked
    content = read_file(args.file)

# File output
if args.save_to:
    if security.validate_file_write(args.save_to, require_confirm=args.confirm_write):
        save_response(result, args.save_to)
```

**Security Tests:**
```bash
# ❌ Should fail: blocked path
mao builder --file .env "Read this"
# 🔒 Access denied: .env
# Matches blocked pattern: .env
# Security policy prevents reading this file.

# ❌ Should fail: path traversal
mao builder --file ../../../etc/passwd "Read this"
# 🔒 Access denied: /etc/passwd
# Path not in allowed read locations.

# ✅ Should prompt: code write
mao builder "Generate script" --save-to deploy.sh
# ⚠️  Write to: deploy.sh
# Type: .sh
# Confirm? [y/N]:

# ✅ Should work: allowed path
mao builder "Test" --save-to data/CONVERSATIONS/test.md
```

---

### Issue #4: Memory Integration Fragmented 🧠

**Current Problem:**
```bash
# Memory features in separate script
python scripts/memory_cli.py search "auth"

# Main CLI doesn't expose controls
mao builder "Continue auth work"
# Uses memory IF enabled in config - user has no control
```

**User Doesn't Know:**
1. What context was injected?
2. Session vs knowledge breakdown?
3. How to force enable/disable memory?
4. What relevance threshold is used?
5. How to adjust context budget?

**REQUIRED INTEGRATION:**

```python
# scripts/agent_runner.py (enhanced)
parser.add_argument("--use-memory", action="store_true",
                   help="Force memory context (override config)")
parser.add_argument("--no-memory", action="store_true",
                   help="Disable memory for this request")
parser.add_argument("--search-memory", type=str,
                   help="Manual memory search before prompt")
parser.add_argument("--context-budget", type=int, default=600,
                   help="Max context tokens (default: 600)")
parser.add_argument("--min-relevance", type=float,
                   help="Override memory relevance threshold (0.0-1.0)")
parser.add_argument("--show-context", action="store_true",
                   help="Display full injected context before LLM call")
```

**Enhanced Output:**
```bash
mao builder "Continue work" --show-context

Output:
┌─ INJECTED CONTEXT (450 tokens)
│
├─ Session Context (300 tokens, 2 messages)
│  [3 messages ago, 15 minutes ago] - Decay: 1.00 (recent)
│  User: "Create JWT authentication system"
│  Assistant: "Here's a secure JWT implementation..."
│
│  [1 message ago, 5 minutes ago] - Decay: 1.00 (recent)
│  User: "Add refresh token support"
│  Assistant: "Adding refresh tokens to JWT..."
│
└─ Knowledge Context (150 tokens, 1 message)
   [Relevance: 0.65, 2 days ago] - Decay: 0.71 (4-day half-life)
   Session: cli-12340-20251109080000
   Topic: "OAuth 2.0 best practices and security patterns"
   Summary: "Discussion of token expiry, secure storage..."

[Context Selection Criteria]
• Session timeout: 2 hours (reuse within 2h)
• Session budget: 75% cap (max 450/600 tokens)
• Knowledge min relevance: 0.15 (configurable)
• Time decay half-life: 96 hours
```

---

### Issue #5: Missing Acceptance Criteria 📋

**Current State of Tasks:**
```markdown
❌ BAD EXAMPLE:
#### P1.1 - CLI Model Override Flag
**Estimate:** 2 hours
**Impact:** High
```

No definition of "done"! No quality gates!

**REQUIRED TEMPLATE:**

```markdown
✅ GOOD EXAMPLE:
#### P1.1 - CLI Model Override Flag

**Usage:**
```bash
mao builder "Create API" --model gpt-4o
mao auto "Review" --model claude-sonnet-4-5
```

**Estimate:** 2 hours
**Impact:** High
**Files:** `scripts/agent_runner.py`, `scripts/chain_runner.py`

**Acceptance Criteria:**
- [ ] `--model MODEL` flag accepted in both agent_runner and chain_runner
- [ ] Model validated against available providers (fail fast if disabled)
- [ ] Error message: "Model 'xyz' not available. Available: [list]"
- [ ] Override logged in conversation metadata: `"override_model": "gpt-4o"`
- [ ] Works with `--dry-run` for cost estimation
- [ ] Help text: `--model MODEL  Override agent's default model`
- [ ] Performance: <50ms overhead for validation
- [ ] Security: Whitelist validation (no arbitrary strings)

**Test Cases:**
```bash
# ✅ Valid override
mao builder "Test" --model gpt-4o

# ❌ Invalid model
mao builder "Test" --model fake-model
# Error: Model 'fake-model' not available
#        Available: gpt-4o, claude-sonnet-4-5, gemini-2.5-flash

# ❌ Disabled provider
export DISABLE_ANTHROPIC=1
mao builder "Test" --model claude-sonnet-4-5
# Error: Provider 'anthropic' is disabled

# ✅ Dry-run with override
mao builder "Prompt" --model gpt-4o --dry-run
# Estimated cost: $0.15 (gpt-4o pricing)
```

**Security:**
- Model string validated against allowed list
- No shell injection via model parameter
- No path traversal (no `/`, `..` allowed)
```

---

## 4. Implementation Roadmap

### Priority 1 - Week 1 (MUST-HAVE - 18 hours)

#### P1.1: Fix Documentation (4 hours)

**Tasks:**
- [ ] Update `README.md:120-125` - Change "CLI Feature Parity" → "CLI UX Enhancements"
- [ ] Update `README.md:877` - Remove "feature parity" claim
- [ ] Add disclaimer: "Core file I/O and security features pending"
- [ ] Add "Context & Memory Behavior" section to README
- [ ] Update `executive_summary.md` if similar claims exist
- [ ] Add acceptance criteria to ALL tasks in this roadmap

#### P1.2: Cost & Safety Guardrails (4 hours)

**Features:**
- `--max-usd AMOUNT` - Abort if estimated cost > threshold
- `--max-input-tokens N` - Reject prompts over N tokens
- `--max-output-tokens N` - Override agent's max_tokens
- `--confirm-write` - Require approval for file writes
- `--read-only` - Disable all writes
- `--force` - Explicit bypass (logged to audit)

**Acceptance Criteria:**
- [ ] Cost estimation within ±15% accuracy
- [ ] Token counting uses `tiktoken` (same as billing)
- [ ] Applies to both single agent and chain
- [ ] `--force` logs warning to console and metadata
- [ ] `--read-only` disables: memory, file, DB writes
- [ ] Error messages include cost breakdown
- [ ] Performance: <100ms overhead

**Files:** `scripts/agent_runner.py`, `scripts/chain_runner.py`

#### P1.3: Security Model (5 hours)

**Deliverables:**
- `config/security.yaml` - Security policies
- `core/security.py` - SecurityManager class
- Integration in CLI scripts

**Features:**
- Path validation (allow-list, block-list)
- File size limits (10MB default)
- Confirmation prompts for code/config writes
- Audit logging (JSONL format)
- Path traversal prevention

**Acceptance Criteria:**
- [ ] `config/security.yaml` with sensible defaults
- [ ] Blocked paths (.env, .git, *.key) cannot be accessed
- [ ] File size limit enforced
- [ ] Confirmation required for .py, .sh, config writes
- [ ] Audit log: `data/AUDIT/cli_audit.jsonl`
- [ ] Path traversal prevented (resolve real path)
- [ ] Symlink attacks prevented

**Security Tests:**
```bash
# ❌ Blocked path
mao builder --file .env "Read"
# Error: Access denied

# ❌ Path traversal
mao builder --file ../../etc/passwd "Read"
# Error: Path not in allowed locations

# ✅ Confirmation prompt
mao builder "Script" --save-to deploy.sh
# Prompt: Confirm? [y/N]
```

**Files:** NEW `config/security.yaml`, NEW `core/security.py`

#### P1.4: File Input Support (4 hours)

**Features:**
- `--file PATH` - Read prompt from single file
- `--files PATH1 PATH2 ...` - Read and concatenate multiple files
- Automatic syntax detection (.py, .md, .js, etc.)
- Security validation via SecurityManager

**Acceptance Criteria:**
- [ ] `--file` reads single file with error handling
- [ ] `--files` concatenates multiple files with headers
- [ ] Syntax detection for code files (wrap in ``` blocks)
- [ ] Security: Path validation before read
- [ ] File size limit enforced
- [ ] UTF-8 encoding with error handling
- [ ] Performance: <150ms for 1MB file
- [ ] Error message if file not found

**Implementation:**
```python
def read_file_content(file_path: str, security: SecurityManager) -> str:
    """Read file with automatic syntax detection."""
    # 1. Security validation
    security.validate_file_read(file_path)

    # 2. Read file
    path = Path(file_path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 3. Detect syntax and wrap if code
    suffix = path.suffix.lower()
    if suffix in ['.py', '.js', '.java', '.cpp', '.rs', '.go']:
        lang = suffix[1:]
        return f"```{lang}\n{content}\n```\n\nAnalyze this {lang} code."

    return content

def read_multiple_files(file_paths: List[str], security: SecurityManager) -> str:
    """Concatenate multiple files with headers."""
    parts = []
    for file_path in file_paths:
        security.validate_file_read(file_path)
        content = read_file_content(file_path, security)
        parts.append(f"## File: {file_path}\n\n{content}")

    return "\n\n---\n\n".join(parts)
```

**Usage:**
```bash
# Single file
mao builder --file prompt.md

# Code file (auto-wrapped)
mao critic --file code.py
# Sends: ```python\n<code>\n```\nAnalyze this python code.

# Multiple files
mao builder --files design.md implementation.py tests.py
# Sends:
# ## File: design.md
# <content>
# ---
# ## File: implementation.py
# ```python
# <code>
# ```
# ---
# ## File: tests.py
# ...
```

**Files:** `scripts/agent_runner.py`, `scripts/chain_runner.py`

#### P1.5: Acceptance Criteria for All Tasks (1 hour)

- [ ] Add "Acceptance Criteria" section to P2.x tasks
- [ ] Add "Test Cases" section to P2.x tasks
- [ ] Add "Security" section where applicable
- [ ] Review and validate all criteria

---

### Priority 2 - Week 2 (SHOULD-HAVE - 15 hours)

#### P2.1: Enhanced Memory Integration (5 hours)

**Features:**
- `--use-memory` - Force enable (override config)
- `--no-memory` - Disable for this request
- `--search-memory QUERY` - Manual search before prompt
- `--context-budget N` - Override default 600 tokens
- `--min-relevance X` - Override threshold (0.0-1.0)
- `--show-context` - Display injected context

**Acceptance Criteria:**
- [ ] All flags work in agent_runner and chain_runner
- [ ] `--use-memory` / `--no-memory` override agent config
- [ ] `--search-memory` shows results before LLM call
- [ ] `--context-budget` validated (100-5000 range)
- [ ] `--min-relevance` validated (0.0-1.0)
- [ ] `--show-context` displays formatted breakdown
- [ ] Context shows: Session tokens, Knowledge tokens, messages count
- [ ] Performance: Memory search <200ms for 1000 conversations
- [ ] Always show "🧠 Memory: N tokens" in output

**Output Format:**
```
┌─ INJECTED CONTEXT (450 tokens)
│
├─ Session Context (300 tokens, 2 messages)
│  [3 messages ago, 15 min] - Decay: 1.00
│  User: "Create JWT auth"
│  ...
│
└─ Knowledge Context (150 tokens, 1 message)
   [Relevance: 0.65, 2 days ago] - Decay: 0.71
   Topic: "OAuth patterns"
   ...

[Criteria]
• Session timeout: 2h
• Session budget: 75% cap
• Min relevance: 0.15
• Time decay: 96h half-life
```

**Files:** `scripts/agent_runner.py`

#### P2.2: Single Agent Output Save (3 hours)

**Features:**
- `--save-to PATH` - Save response to file
- `--format {markdown,json,text}` - Output format
- `--append` - Append instead of overwrite

**Acceptance Criteria:**
- [ ] Works in `agent_runner.py` (currently only chain_runner has it)
- [ ] Markdown format includes metadata (agent, model, date, tokens, cost)
- [ ] JSON format includes full response object
- [ ] Text format includes response only
- [ ] Append mode works correctly
- [ ] Error handling for write failures
- [ ] Security: Validates path via SecurityManager
- [ ] Success message: "💾 Saved to: /path/file.md"

**Implementation:**
```python
def save_response(result, output_path: str, format: str, append: bool, security):
    """Save agent response to file."""
    security.validate_file_write(output_path)

    mode = "a" if append else "w"
    with open(output_path, mode, encoding="utf-8") as f:
        if format == "markdown":
            f.write(f"# Agent Response\n\n")
            f.write(f"**Agent:** {result.agent}\n")
            f.write(f"**Model:** {result.model}\n")
            f.write(f"**Date:** {datetime.now().isoformat()}\n")
            f.write(f"**Tokens:** {result.total_tokens}\n")
            f.write(f"**Cost:** ${result.estimated_cost:.4f}\n\n")
            f.write("## Prompt\n\n" + result.prompt + "\n\n")
            f.write("## Response\n\n" + result.response)
        elif format == "json":
            json.dump(result.to_dict(), f, indent=2)
        else:  # text
            f.write(result.response)
```

**Usage:**
```bash
# Markdown (default)
mao builder "Create API" --save-to design.md

# JSON (all metadata)
mao builder "Review" --save-to review.json --format json

# Plain text (response only)
mao critic "Analyze" --save-to analysis.txt --format text

# Append mode
mao builder "Next task" --save-to project.md --append
```

**Files:** `scripts/agent_runner.py`

#### P2.3: Multi-File Input (3 hours)

**Enhancement to P1.4** - Already covered above as part of `--files` flag.

#### P2.4: Model Override Flag (2 hours)

**Features:**
- `--model MODEL` - Override agent's default model

**Acceptance Criteria:**
- See detailed template in Issue #5 above

**Usage:**
```bash
mao builder "Test" --model gpt-4o
mao auto "Review" --model claude-sonnet-4-5
```

**Files:** `scripts/agent_runner.py`, `scripts/chain_runner.py`

#### P2.5: Manual Summarization CLI (5 hours)

**New Script:** `scripts/summarize_cli.py`

**Features:**
- `summarize --id ID` - Summarize conversation by ID
- `summarize --session SESSION_ID` - Summarize entire session
- `summarize --last N` - Summarize last N conversations
- `--max-tokens N` - Max summary length (default: 300)
- `--output FILE` - Save summary to file

**Acceptance Criteria:**
- [ ] Uses existing `_compress_semantic()` from agent_runtime
- [ ] ID lookup from memory database
- [ ] Session lookup retrieves all conversations
- [ ] Output shows structured JSON summary
- [ ] `--output` saves to file with security validation
- [ ] Performance: <5s per conversation
- [ ] Works with `--format {json,markdown,text}`

**Implementation:**
```python
# scripts/summarize_cli.py
def summarize_conversation(conversation_id: int, max_tokens: int = 300):
    """Summarize specific conversation."""
    memory = MemoryEngine()
    conv = memory.backend.get_by_id(conversation_id)

    runtime = AgentRuntime()
    full_text = f"User: {conv['prompt']}\n\nAssistant: {conv['response']}"
    summary = runtime._compress_semantic(full_text, max_tokens)

    return summary

def summarize_session(session_id: str, max_tokens: int = 500):
    """Summarize all conversations in session."""
    memory = MemoryEngine()
    convs = memory.search_conversations(session_id=session_id, limit=100)

    full_text = "\n\n".join([
        f"Turn {i+1}:\nUser: {c['prompt']}\nAssistant: {c['response']}"
        for i, c in enumerate(convs)
    ])

    runtime = AgentRuntime()
    summary = runtime._compress_semantic(full_text, max_tokens)

    return summary
```

**Usage:**
```bash
# Summarize specific conversation
mao summarize --id 123 --max-tokens 300

# Summarize entire session
mao summarize --session cli-12345-20251111100000

# Summarize last N
mao summarize --last 10 --output recent_summary.md

# Save to file
mao summarize --id 123 --output conv_123_summary.json --format json
```

**Files:** NEW `scripts/summarize_cli.py`

---

### Priority 3 - Week 3+ (NICE-TO-HAVE)

#### P3.1: Context Injection (3 hours)

**Features:**
- `--use-summary FILE` - Inject summary as context

**Usage:**
```bash
# Summarize old session
mao summarize --session old-session --output old_context.md

# Use in new request
mao builder "Continue that work" --use-summary old_context.md
```

#### P3.2: Batch File Processing (5 hours)

**Features:**
- `--batch-dir DIR` - Process all files in directory
- `--batch-pattern GLOB` - Filter by pattern

**Usage:**
```bash
mao batch --batch-dir prompts/ --agent builder --output results/
```

#### P3.3: Interactive TUI Mode (2 days)

**Library:** `textual` or `rich.tui`

**Usage:**
```bash
mao tui  # Opens full-screen interface
```

---

## 5. Security & Safety Model

### Security Layers

1. **Path Validation** (`core/security.py`)
   - Allow-list for reads
   - Allow-list for writes
   - Block-list (absolute deny)
   - Path traversal prevention
   - Symlink resolution

2. **File Size Limits**
   - Default: 10MB max
   - Prevents memory exhaustion
   - Configurable per deployment

3. **Confirmation Prompts**
   - Code files (.py, .sh, .bash)
   - Config files (config/**)
   - System files (.bashrc, .zshrc)

4. **Cost Guardrails**
   - `--max-usd` - Hard budget cap
   - `--max-input-tokens` - Input limit
   - `--max-output-tokens` - Output limit
   - Daily/monthly tracking

5. **Audit Logging**
   - All file operations logged
   - Guardrail bypasses logged
   - Security violations logged
   - Format: JSONL (one record per line)

### Audit Log Format

```jsonl
{"timestamp": "2025-11-11T10:30:00Z", "event": "file_read", "data": {"path": "data/test.md"}, "pid": 12345}
{"timestamp": "2025-11-11T10:35:00Z", "event": "file_write_confirmed", "data": {"path": "deploy.sh"}, "pid": 12345}
{"timestamp": "2025-11-11T10:40:00Z", "event": "guardrail_bypass", "data": {"flag": "--force", "reason": "token_limit", "actual": 5000, "limit": 2000}, "pid": 12345}
{"timestamp": "2025-11-11T10:45:00Z", "event": "security_violation", "data": {"action": "file_read_blocked", "path": ".env", "pattern": ".env"}, "pid": 12345}
```

### Threat Model

**Threats Mitigated:**
- ✅ Path traversal attacks (`../../etc/passwd`)
- ✅ Symlink attacks (resolve to real path)
- ✅ Accidental credential leaks (.env, *.key)
- ✅ Accidental cost overruns (large files)
- ✅ Backdoor injection (.git/hooks/*)
- ✅ Configuration corruption (config/**)

**Threats NOT Mitigated:**
- ⚠️ Malicious prompt injection (LLM-level attack)
- ⚠️ Network-based attacks (out of scope)
- ⚠️ Supply chain attacks (dependencies)

---

## 6. Acceptance Criteria Template

**Copy-paste template for new tasks:**

```markdown
#### PX.Y: [Task Name]

**Features:**
- Feature 1
- Feature 2

**Usage:**
```bash
# Example usage
mao command --flag value
```

**Estimate:** X hours
**Impact:** High/Medium/Low
**Files:** `path/to/file.py`

**Acceptance Criteria:**
- [ ] Core functionality works as documented
- [ ] Error handling covers edge cases
- [ ] Performance meets requirements (<Xms)
- [ ] Security validated (no injection, traversal, etc.)
- [ ] Help text updated
- [ ] Works with related flags (--dry-run, --force, etc.)
- [ ] Logging/audit trail if applicable

**Test Cases:**
```bash
# ✅ Happy path
command --flag valid

# ❌ Error case 1
command --flag invalid
# Expected error: ...

# ❌ Error case 2
command --flag dangerous
# Expected error: ...
```

**Security:**
- Input validation rules
- No injection vectors
- Path traversal prevented (if file ops)
- Audit logging (if security-relevant)
```

---

## 7. Week-by-Week Plan

### Week 1 (18 hours) - Foundation & Safety

**Monday (6h):**
- [ ] P1.1: Fix documentation (4h)
- [ ] P1.5: Add acceptance criteria to all tasks (2h)

**Tuesday (6h):**
- [ ] P1.2: Cost guardrails implementation (6h)

**Wednesday (6h):**
- [ ] P1.3: Security model (config/security.yaml + core/security.py) (6h)

**Thursday-Friday:**
- Code review, testing, documentation updates

### Week 2 (15 hours) - Core Features

**Monday (4h):**
- [ ] P1.4: File input support (4h)

**Tuesday (5h):**
- [ ] P2.1: Enhanced memory integration (5h)

**Wednesday (3h):**
- [ ] P2.2: Single agent output save (3h)

**Thursday (2h):**
- [ ] P2.4: Model override flag (2h)

**Friday:**
- Testing, bug fixes, integration

### Week 3 (5 hours) - Advanced Features

**Monday (5h):**
- [ ] P2.5: Manual summarization CLI (5h)

**Tuesday-Friday:**
- P3.x tasks (nice-to-have)
- Documentation updates
- Final testing

---

## 📝 Summary

### Critical Path (Must Complete)

1. ✅ **Fix documentation** - Remove misleading claims
2. ✅ **Cost guardrails** - Prevent $$ accidents
3. ✅ **Security model** - Prevent data leaks
4. ✅ **File I/O** - Core functionality

### Success Metrics

**Week 1 Complete:**
- [ ] README updated with accurate claims
- [ ] `--max-usd` and `--max-input-tokens` prevent overruns
- [ ] SecurityManager blocks .env, .git access
- [ ] `--file` and `--files` work with validation
- [ ] All P1 tasks have acceptance criteria

**Week 2 Complete:**
- [ ] `--show-context` reveals memory injection
- [ ] `--save-to` works for single agents
- [ ] `--model` overrides agent defaults
- [ ] All core features functional

**Week 3 Complete:**
- [ ] `summarize` command exposes compression
- [ ] P3 nice-to-have features implemented
- [ ] Full test coverage
- [ ] Documentation complete

---

## 📞 Questions & Decisions

**Open Questions:**
1. Should audit logs be opt-in or opt-out? (Recommendation: opt-out, always log)
2. Default daily budget limit? (Recommendation: $10/day, $100/month)
3. Should `--force` require explicit reason string? (Recommendation: yes, for audit)
4. Path to security.yaml - hardcoded or configurable? (Recommendation: hardcoded for security)

**Design Decisions Made:**
- ✅ Security-first approach (P1.3 in Week 1)
- ✅ Cost protection mandatory (P1.2 in Week 1)
- ✅ File I/O with validation only (no unrestricted mode)
- ✅ Acceptance criteria for all tasks
- ✅ Single master roadmap document

---

**Last Updated:** 2025-11-11
**Maintainer:** Claude Code
**Status:** 🔴 **ACTIVE - Primary Reference**
**Next Review:** After Week 1 completion

---

## Appendix: Archived Documents

The following documents have been **consolidated** into this roadmap:

1. ~~`clitodo.md`~~ → Merged into "Implementation Roadmap" section
2. ~~`CLI_FILE_CONTEXT_ANALYSIS.md`~~ → Merged into "Current State Analysis"
3. ~~`DOCUMENTATION_CORRECTIONS.md`~~ → Merged into "Critical Issues"

**Location:** These files can be moved to `docs/archive/` for historical reference.

**Reason:** Single source of truth prevents confusion and duplication.

# CLI Testing Guide

**Date:** 2025-11-11  
**Status:** Test Suite Created  
**Purpose:** Guide for running CLI tests

---

## 🚨 Important: Use WSL/Venv Python

**Problem:** CLI test files import modules that require dependencies (litellm, etc.). These are only available in the project's virtual environment.

**Solution:** Always use the project's venv Python, not system Python.

---

## ✅ Running Tests

### Option 1: Using Make (Recommended)

```bash
# Run all CLI tests
make test

# Or specifically CLI tests
.venv/bin/pytest tests/test_cli_*.py -v
```

### Option 2: Direct Venv Python

```bash
# Activate venv first
source .venv/bin/activate  # Linux/WSL
# or
.venv\Scripts\activate  # Windows

# Then run tests
pytest tests/test_cli_agent_runner.py -v
pytest tests/test_cli_chain_runner.py -v
pytest tests/test_cli_security.py -v
```

### Option 3: WSL (If on Windows)

```bash
# In WSL terminal
cd ~/.orchestrator
.venv/bin/pytest tests/test_cli_*.py -v
```

---

## 📋 Test Files

1. **`tests/test_cli_agent_runner.py`**
   - Tests for `scripts/agent_runner.py`
   - Path validation, file I/O, cost guardrails, error handling

2. **`tests/test_cli_chain_runner.py`**
   - Tests for `scripts/chain_runner.py`
   - Chain execution, interactive mode, custom stages

3. **`tests/test_cli_security.py`**
   - Security validation tests
   - Path traversal, blocked files, size limits

---

## 🐛 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'litellm'`

**Cause:** Using system Python instead of venv Python.

**Fix:**
```bash
# Use venv Python
.venv/bin/pytest tests/test_cli_*.py -v
```

### Error: `ImportError while importing test module`

**Cause:** Dependencies not installed in venv.

**Fix:**
```bash
# Install dependencies
make install
# or
.venv/bin/pip install -r requirements.txt
```

### Error: `No tests collected`

**Cause:** Test files not found or import errors.

**Fix:**
```bash
# Check if files exist
ls tests/test_cli_*.py

# Run with verbose output
pytest tests/test_cli_*.py -v -s
```

---

## 📊 Expected Test Results

**Total Tests:** ~40+ tests across 3 files

**Categories:**
- Path validation: ~10 tests
- File I/O: ~8 tests
- Cost guardrails: ~6 tests
- Security: ~12 tests
- Integration: ~8 tests

**Expected Pass Rate:** 100% (after dependencies installed)

---

## 🔧 Test Development

### Adding New Tests

1. **Add to appropriate file:**
   - `test_cli_agent_runner.py` - Single agent features
   - `test_cli_chain_runner.py` - Chain features
   - `test_cli_security.py` - Security features

2. **Follow patterns:**
   ```python
   def test_feature_name(self, tmp_path):
       """Test description."""
       from scripts.agent_runner import function_name
       
       # Test code
       result = function_name(...)
       assert result == expected
   ```

3. **Use fixtures:**
   - `tmp_path` - Temporary directory
   - `capsys` - Capture stdout/stderr
   - `monkeypatch` - Mock imports

---

## ✅ Pre-Commit Checklist

Before committing test changes:

- [ ] All tests pass: `pytest tests/test_cli_*.py -v`
- [ ] No import errors
- [ ] Test coverage > 70%
- [ ] Tests are isolated (no side effects)
- [ ] Tests use fixtures properly

---

**Last Updated:** 2025-11-11  
**Status:** ✅ Ready for Use


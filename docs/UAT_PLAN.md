# UAT Planı – Multi-Agent Orchestrator

**Amaç:** Workspace içeriğine göre sistemin gerçekten belgelenen davranışı sergileyip sergilemediğini kullanıcı kabul testleri ile doğrulamak.

**Kapsam:** Config, Core (Runtime, Memory, Session, LLM), API, CLI akışları.

**Ortam:** Mümkün olduğunca `LLM_MOCK=1` ile API çağrısı yapılmadan çalışacak senaryolar.

---

## 1. Konfigürasyon

| ID | Senaryo | Beklenti | Kritik |
|----|---------|----------|--------|
| C01 | `load_agents_config()` | agents.yaml yüklenir, `agents.builder`, `agents.critic`, `agents.closer`, `agents.router` var | Evet |
| C02 | `load_memory_config()` | memory.yaml (veya default) yüklenir, `memory.enabled`, `memory.db_path` var | Evet |
| C03 | `get_env_source()` | "none" | "dotenv" | "environment" döner | Hayır |
| C04 | `is_provider_enabled("openai")` | API key / DISABLE_OPENAI’a göre True/False | Hayır |

---

## 2. Core – Agent Runtime

| ID | Senaryo | Beklenti | Kritik |
|----|---------|----------|--------|
| R01 | `runtime.run(agent="builder", prompt="Hi", mock_mode=True)` | RunResult döner, `result.agent=="builder"`, `result.response` dolu, `result.error is None` | Evet |
| R02 | `runtime.run(agent="auto", prompt="...", mock_mode=True)` | Router çağrılır, geçerli agent adı döner (builder/critic/closer) | Evet |
| R03 | `runtime.route("Create API")` (mock) | "builder" | "critic" | "closer" | Evet |
| R04 | `runtime.chain(prompt="Test", stages=["builder","critic"], mock_mode=True)` | 2 elemanlı RunResult listesi, her biri error=None | Evet |
| R05 | Bilinmeyen agent ile run | ValueError | Evet |

---

## 3. Core – Bellek (Memory)

| ID | Senaryo | Beklenti | Kritik |
|----|---------|----------|--------|
| M01 | DB yokken `get_stats()` veya store | Graceful: exception yok veya anlamlı hata | Evet |
| M02 | DB varken `store_conversation(...)` | int (conversation id) döner | Evet |
| M03 | `get_recent_conversations(limit=5)` | Liste (boş olabilir) | Evet |
| M04 | `search_conversations(query="test", limit=5)` | Liste (boş olabilir) | Evet |

---

## 4. Core – Oturum (Session)

| ID | Senaryo | Beklenti | Kritik |
|----|---------|----------|--------|
| S01 | `get_or_create_session(source="cli", metadata={"pid": 12345})` | Geçerli session_id (örn. cli-12345-...) | Evet |
| S02 | `validate_session_id("valid-id-123")` | Geçerli format için hata fırlatmaz | Evet |
| S03 | `validate_session_id("x"*100)` veya geçersiz karakter | ValueError | Hayır |

---

## 5. API (FastAPI TestClient)

| ID | Senaryo | Beklenti | Kritik |
|----|---------|----------|--------|
| A01 | GET /health | 200, status (healthy/degraded/unhealthy), providers, memory, system | Evet |
| A02 | POST /ask (agent=builder, prompt="Test", mock) | 200, response.response dolu | Evet |
| A03 | POST /ask prompt="" | 422 | Evet |
| A04 | POST /ask agent=invalid | 400 | Evet |
| A05 | POST /chain (prompt="Test", mock) | 200, liste RunResult | Evet |
| A06 | GET /logs?limit=5 | 200, liste | Evet |
| A07 | GET /metrics | 200, total_tokens vb. | Evet |
| A08 | GET /memory/stats | 200 veya DB yoksa 500 (kabul edilir) | Hayır |
| A09 | GET /memory/search?q=test&limit=5 | 200 veya 500 | Hayır |
| A10 | GET / | 200, HTML | Evet |

---

## 6. CLI (Programatik / Subprocess)

| ID | Senaryo | Beklenti | Kritik |
|----|---------|----------|--------|
| L01 | agent_runner.py builder "Hello" (LLM_MOCK=1) | Exit 0, çıktıda agent/model ve response | Evet |
| L02 | chain_runner.py "Hello" --no-input (LLM_MOCK=1) | Exit 0, stage çıktıları | Evet |
| L03 | agent_runner.py invalid "Hi" | Exit != 0 veya hata mesajı | Evet |

---

## 7. Özet Kriterler

- **Geçiş:** Tüm kritik senaryolar geçer.
- **Uyarı:** Kritik olmayanlar fail ederse rapora uyarı olarak yazılır.
- **Ortam:** UAT, `.venv` veya `python3` ile ve `LLM_MOCK=1` ile çalıştırılabilir.

---

## Çalıştırma

```bash
# Venv ile
.venv/bin/python scripts/uat_runner.py

# Rapor dosyaya da yazılsın (varsayılan: docs/UAT_REPORT.md)
.venv/bin/python scripts/uat_runner.py --report docs/UAT_REPORT.md
```

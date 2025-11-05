# Development Continuation Guide - Sistemi Nasıl Geliştirirsin

Bu kılavuz, sistemin geliştirilmesine kaldığın yerden devam etmeni sağlar.

---

## 🧠 Sistem Hafızası - "Nerede Kaldık?"

### 1. Memory Sistemi (Otomatik)

**Konuşma Geçmişi:**
```bash
# Tüm AI konuşmaları burada
ls -lt ~/.orchestrator/data/CONVERSATIONS/

# Son konuşma
ls -lt ~/.orchestrator/data/CONVERSATIONS/ | head -2

# JSON olarak oku
cat ~/.orchestrator/data/CONVERSATIONS/20241103_*.json | jq .
```

**Proje Notları:**
```bash
# Manuel notlarını tut
cat ~/memory/NOTES/client-xyz.notes

# Yeni not ekle
make memory-note MSG="Bugün streaming response üzerinde çalıştım"
```

**Proje Logları:**
```bash
# Gelişim geçmişi
cat ~/memory/HISTORY/client-xyz.log

# Yeni log
make memory-log MSG="v0.2.0 - Streaming support eklendi"
```

### 2. Git Geçmişi (Önerilen)

**İlk Git Setup:**
```bash
cd ~/projects/client-xyz

# Git başlat
git init

# İlk commit
git add .
git commit -m "v0.1.0 - Initial: Multi-Agent Orchestrator

- 4 agent roles (builder, critic, closer, router)
- 3 interfaces (CLI, API, Web UI)
- Environment-aware configuration
- Central installation system
- Comprehensive documentation
"

# GitHub'a yükle (opsiyonel)
gh repo create multi-agent-orchestrator --private
git remote add origin https://github.com/yourusername/multi-agent-orchestrator.git
git push -u origin main
```

**Her Geliştirmeden Sonra:**
```bash
# Değişiklikleri gör
git status
git diff

# Commit et
git add .
git commit -m "feat: Add streaming response support"

# Detaylı mesaj için
git commit
# Editörde:
# feat: Add streaming response support
#
# - Implemented SSE endpoint
# - Updated UI for streaming
# - Added tests for streaming
```

### 3. SESSION_SUMMARY.md (Manuel Güncelleme)

Her önemli geliştirmeden sonra:

```bash
# SESSION_SUMMARY.md'ye ekle
nano ~/projects/client-xyz/SESSION_SUMMARY.md

# Yeni bölüm ekle:
## 8. Streaming Response Implementation (2025-11-04)

**Ne istendi:** Real-time streaming responses

**Ne yapıldı:**
- ✅ SSE endpoint (/stream)
- ✅ UI streaming support
- ✅ Tests

**Dosyalar:**
...
```

### 4. CHANGELOG.md (Versiyon Takibi)

```bash
# CHANGELOG.md güncelle
nano ~/projects/client-xyz/CHANGELOG.md

# Ekle:
## [0.2.0] - 2025-11-04

### Added
- Streaming response support via SSE
- Real-time token display in UI

### Changed
- API now supports streaming mode

### Fixed
- Memory leak in long conversations
```

---

## 🔄 Geliştirmeye Devam Etme Workflow'u

### Senaryo 1: Yeni Özellik Eklemek

**1. Önce Durumu Kontrol Et:**
```bash
# Geçmişe bak
cat ~/projects/client-xyz/SESSION_SUMMARY.md | grep -A 10 "Final Durum"

# Son notları oku
cat ~/memory/NOTES/client-xyz.notes

# Git durumu
cd ~/projects/client-xyz
git log --oneline -10
```

**2. Planlama:**
```bash
# Todo oluştur (opsiyonel)
cat > ~/projects/client-xyz/TODO.md << 'EOF'
# TODO - Streaming Response

- [ ] API endpoint (/stream)
- [ ] SSE implementation
- [ ] UI update for streaming
- [ ] Tests
- [ ] Documentation
EOF
```

**3. Geliştirme:**
```bash
cd ~/projects/client-xyz

# Branch oluştur (iyi pratik)
git checkout -b feat/streaming-response

# Kodla...
nano api/server.py

# Test et
make test
```

**4. Dokümante Et:**
```bash
# Memory'ye not
make memory-note MSG="Streaming response endpoint eklendi"

# CHANGELOG güncelle
nano CHANGELOG.md

# Git commit
git add .
git commit -m "feat: Add streaming response support

- Implemented SSE endpoint
- Updated UI components
- Added streaming tests
"
```

### Senaryo 2: Bug Fix

**1. Problemi Tespit Et:**
```bash
# Logları kontrol et
ls -lt ~/.orchestrator/data/CONVERSATIONS/ | head -5

# Hata loglarını oku
cat ~/.orchestrator/data/CONVERSATIONS/latest.json | jq .error
```

**2. Fix Yap:**
```bash
git checkout -b fix/memory-leak

# Kodu düzelt
nano core/agent_runtime.py

# Test
make test
```

**3. Dokümante Et:**
```bash
make memory-log MSG="Memory leak bug fixed"
git commit -m "fix: Resolve memory leak in long conversations"
```

### Senaryo 3: Refactoring

**1. Değişiklikleri Planla:**
```bash
# Mevcut yapıyı anla
cat ~/projects/client-xyz/SESSION_SUMMARY.md
```

**2. Refactor:**
```bash
git checkout -b refactor/improve-logging

# Refactor...
make test  # Her adımda test
```

**3. Dokümante Et:**
```bash
git commit -m "refactor: Improve logging structure

- Separated log levels
- Added structured logging
- Improved performance
"
```

---

## 🤖 AI/Claude ile Geliştirme Devamı

### Yeni Conversation Başlatırken

**Context Sağlama:**
```bash
# Cursor/Claude'da yeni chat başlat
# Şunu paylaş:

cat ~/projects/client-xyz/SESSION_SUMMARY.md
# veya
cat ~/projects/client-xyz/README.md

# Ekle:
"
Mevcut sistem durumu:
- v0.1.0 production-ready
- Son geliştirme: Merkezi kurulum sistemi
- Şimdi yapmak istediğim: [HEDEF]

Detaylar için: SESSION_SUMMARY.md okudum
"
```

**Önerilen Prompt Template:**
```
Merhaba! Multi-Agent Orchestrator projemi geliştirmeye devam etmek istiyorum.

MEVCUT DURUM:
- Versiyon: 0.1.0
- Lokasyon: ~/projects/client-xyz
- Son geliştirme: [son commit mesajı]
- Detaylar: SESSION_SUMMARY.md okudum

HEDEF:
[Yapmak istediğin şey]

SORU:
[Spesifik soru veya talep]

Lütfen mevcut mimariye uygun şekilde öner.
```

### AI'ya Context Vermek için Dosyalar

**En Önemli 5 Dosya:**
```bash
# 1. Genel bakış
cat ~/projects/client-xyz/SESSION_SUMMARY.md

# 2. Mimari
cat ~/projects/client-xyz/README.md

# 3. Son durum
git log -1 --stat

# 4. Mevcut config
cat ~/projects/client-xyz/config/agents.yaml

# 5. Son notlar
cat ~/memory/NOTES/client-xyz.notes
```

---

## 📂 Proje Yapısı Anlama

### Hızlı Navigasyon

```bash
# Ana dizine git
cd ~/projects/client-xyz

# veya kurulum sonrası
mao-dir  # → cd ~/.orchestrator

# Dosya yapısını gör
find . -type f -name "*.py" | head -20
find . -type f -name "*.md"

# Spesifik dosya bul
fd agent_runtime.py
fd agents.yaml
```

### Kod Anlama

```bash
# Core dosyaları
ls core/
# → llm_connector.py    (LLM calls)
# → agent_runtime.py    (orchestration)
# → logging_utils.py    (logging)

# Agent tanımları
cat config/agents.yaml

# API endpoints
grep -n "def " api/server.py | head -20

# Test coverage
ls tests/
```

---

## 🎯 Spesifik Senaryolar

### "Yeni Ajan Eklemek İstiyorum"

**1. Geçmişi Kontrol Et:**
```bash
# Mevcut ajanları gör
cat config/agents.yaml | grep -A 5 "agents:"
```

**2. Ajan Ekle:**
```bash
nano config/agents.yaml

# Ekle:
  researcher:
    model: "anthropic/claude-3-5-sonnet-20241022"
    system: "Sen detaylı araştırmacısın..."
    temperature: 0.4
    max_tokens: 2000
```

**3. Test Et:**
```bash
cd ~/.orchestrator
source .venv/bin/activate
python scripts/agent_runner.py researcher "Test"
```

**4. Dokümante Et:**
```bash
make memory-note MSG="Researcher ajanı eklendi"
git commit -m "feat: Add researcher agent"
```

### "API'ye Yeni Endpoint Eklemek"

**1. Mevcut Endpoint'leri Anla:**
```bash
grep "@app" api/server.py
# → Şunları görürsün: /ask, /chain, /logs, /metrics, /health
```

**2. Yeni Endpoint Ekle:**
```bash
nano api/server.py

# Ekle (diğer endpoint'lerin yanına):
@app.post("/stream")
async def stream_response(...):
    ...
```

**3. Test Ekle:**
```bash
nano tests/test_api.py

def test_stream_endpoint():
    ...
```

**4. Dokümante:**
```bash
# README güncelle
nano README.md  # API Endpoints bölümüne ekle

make memory-log MSG="Streaming endpoint eklendi"
```

### "UI'da Değişiklik Yapmak"

**1. Mevcut UI'ı Anla:**
```bash
cat ui/templates/index.html | grep -A 3 "function\|@app"
```

**2. Değiştir:**
```bash
nano ui/templates/index.html
```

**3. Test:**
```bash
make run-api
# http://localhost:5050
```

---

## 🔍 Debug & Troubleshooting Geçmişi

### Hata Loglarını Bulma

```bash
# AI conversation logları
ls -lt ~/.orchestrator/data/CONVERSATIONS/ | grep error

# Spesifik hata ara
grep -r "error" ~/.orchestrator/data/CONVERSATIONS/*.json

# Son hatalı çağrı
cat ~/.orchestrator/data/CONVERSATIONS/*.json | jq 'select(.error != null)'
```

### Test Geçmişi

```bash
# Test sonuçlarını gör
make test 2>&1 | tee test_results.log

# Geçmiş test sonuçları (git'te)
git log --grep="test"
```

---

## 📊 Progress Tracking

### Haftalık/Aylık Takip

**Haftalık Özet:**
```bash
# Bu haftaki değişiklikler
git log --since="1 week ago" --oneline

# Bu haftaki notlar
grep -A 2 "$(date +%Y-%m)" ~/memory/NOTES/client-xyz.notes

# Bu haftaki loglar
grep "$(date +%Y-%m)" ~/memory/HISTORY/client-xyz.log
```

**Aylık Rapor:**
```bash
# Son 30 günde ne yaptın
git log --since="30 days ago" --pretty=format:"%h - %s (%cr)" --graph

# İstatistikler
git log --since="30 days ago" --stat | tail -20
```

### TODO Takibi

**TODO.md Oluştur:**
```bash
cat > ~/projects/client-xyz/TODO.md << 'EOF'
# TODO List - Multi-Agent Orchestrator

## v0.2.0 (Planned)
- [ ] Streaming response support
- [ ] WebSocket integration
- [ ] Authentication middleware
- [ ] Rate limiting

## v0.6.0 (Future)
- [ ] Cursor MCP bridge
- [ ] VSCode extension
- [ ] Additional agents (researcher, validator)

## Bugs
- [ ] None currently

## Documentation
- [ ] Video tutorial
- [ ] API reference docs
EOF
```

**TODO Güncellemeleri:**
```bash
# Tamamlandı işaretle
nano ~/projects/client-xyz/TODO.md
# [ ] → [x]

# Git commit
git add TODO.md
git commit -m "docs: Update TODO - streaming completed"
```

---

## 🚀 Quick Start Commands (Her Gün)

### Geliştirmeye Başlarken

```bash
# 1. Durumu kontrol et
cd ~/projects/client-xyz
git status
git log -5 --oneline

# 2. Son notları oku
cat ~/memory/NOTES/client-xyz.notes | tail -10

# 3. TODO'ya bak
cat TODO.md 2>/dev/null || echo "TODO.md yok"

# 4. Virtual env aktif et
cd ~/.orchestrator
source .venv/bin/activate

# 5. Test et (hala çalışıyor mu?)
make test
```

### Günü Bitirirken

```bash
# 1. Değişiklikleri kaydet
git status
git add .
git commit -m "..."

# 2. Not al
make memory-note MSG="Bugün şunu yaptım: ..."

# 3. Log tut
make memory-log MSG="v0.x.y - Özellik eklendi"

# 4. TODO güncelle
nano TODO.md

# 5. Push (opsiyonel)
git push
```

---

## 📖 Documentation Cheat Sheet

### Her Zaman Güncelle

| Dosya | Ne Zaman | Ne Yaz |
|-------|----------|--------|
| `CHANGELOG.md` | Her release | Versiyon değişiklikleri |
| `SESSION_SUMMARY.md` | Büyük geliştirmeler | Yeni adım ekle |
| `README.md` | Yeni özellik | Kullanım örneği ekle |
| `TODO.md` | Her gün | İlerleme işaretle |
| `~/memory/NOTES/` | İhtiyaç duyarsan | Hızlı notlar |
| `~/memory/HISTORY/` | Önemli milestone | Log girişi |

### Template: Yeni Özellik Dokümantasyonu

```markdown
## [Özellik Adı] - [Tarih]

**Ne istendi:** [Hedef]

**Ne yapıldı:**
- ✅ [İş 1]
- ✅ [İş 2]

**Dosyalar:**
- [dosya1] (YENİ)
- [dosya2] (güncellendi)

**Test:**
```bash
[test komutları]
```

**Notlar:**
[Özel notlar, dikkat edilmesi gerekenler]
```

---

## 🎓 Best Practices

### 1. Her Zaman Git Kullan
```bash
# Her özellik için branch
git checkout -b feat/new-feature

# Düzenli commit
git commit -m "..."  # Her mantıksal değişiklik

# Merge yap
git checkout main
git merge feat/new-feature
```

### 2. Test Önce Commit
```bash
make test  # Önce test geç
git commit  # Sonra commit
```

### 3. Dokümantasyon Senkron
```bash
# Kod değiştirdin → Dokümantasyon da değiştir
nano api/server.py
nano README.md  # API bölümünü güncelle
```

### 4. Memory Sistemi Kullan
```bash
# Her önemli değişiklik
make memory-note MSG="..."
make memory-log MSG="..."
```

---

## 🆘 Kaybolursan Ne Yaparsın?

### "Nerede kaldım bilmiyorum"

```bash
# 1. Son SESSION_SUMMARY'yi oku
cat ~/projects/client-xyz/SESSION_SUMMARY.md

# 2. Son commitlere bak
git log -10 --oneline

# 3. Son notları oku
cat ~/memory/NOTES/client-xyz.notes

# 4. TODO'ya bak
cat ~/projects/client-xyz/TODO.md
```

### "Kod nasıl çalışıyor hatırlamıyorum"

```bash
# 1. README oku
cat ~/projects/client-xyz/README.md

# 2. QUICKSTART oku
cat ~/projects/client-xyz/QUICKSTART.md

# 3. Test çalıştır (öğretici)
make test -v

# 4. Basit örnek dene
mao auto "Test"
```

### "Bir şey bozdum, geri dönmek istiyorum"

```bash
# Son commit'e dön
git reset --hard HEAD

# Belirli commit'e dön
git log --oneline
git reset --hard abc123

# Branch oluşturup dene
git checkout -b experiment
# Bozarsan sil, geçersin
```

---

## 📌 Özet: Tek Sayfa Cheat Sheet

```bash
# 🔍 DURUM KONTROLÜ
git log -5 --oneline                    # Son 5 commit
cat ~/memory/NOTES/client-xyz.notes     # Son notlar
cat ~/projects/client-xyz/TODO.md       # TODO liste

# 🚀 GELİŞTİRME BAŞLAT
cd ~/projects/client-xyz
git checkout -b feat/new-feature
source ~/.orchestrator/.venv/bin/activate

# ✏️ KODLA & TEST
nano [dosya]
make test

# 💾 KAYDET
git add .
git commit -m "feat: ..."
make memory-note MSG="..."

# 📚 DOKÜMANTE
nano CHANGELOG.md
nano README.md (gerekirse)

# 🎯 BİTİR
git checkout main
git merge feat/new-feature
git push
```

---

**Sonuç:** Bu kılavuzla, herhangi bir zaman geliştirmeye kaldığın yerden devam edebilirsin!

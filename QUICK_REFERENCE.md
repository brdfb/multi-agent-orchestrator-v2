# Quick Reference Card - Hızlı Başvuru

Sistemi geliştirmeye devam ederken ihtiyacın olan her şey.

---

## 🎯 "Nerede Kaldım?" - 3 Komut

```bash
# 1. Genel durum
cat ~/projects/client-xyz/SESSION_SUMMARY.md | head -50

# 2. Son notlar
cat ~/memory/NOTES/client-xyz.notes

# 3. Git geçmişi
cd ~/projects/client-xyz && git log -10 --oneline
```

---

## 📂 Önemli Dosyalar (İlk Bakış)

| Dosya | Ne İçin |
|-------|---------|
| `SESSION_SUMMARY.md` | Tüm süreç (7 adım) |
| `README.md` | Kullanım kılavuzu |
| `DEVELOPMENT_CONTINUATION.md` | Geliştirme rehberi |
| `config/agents.yaml` | Ajan tanımları |
| `TODO.md` | Yapılacaklar (oluştur) |
| `CHANGELOG.md` | Versiyon geçmişi |

---

## 🔍 Kod Yapısı (5 Dakikada Anla)

```
core/
├── llm_connector.py     ← LLM çağrıları (LiteLLM)
├── agent_runtime.py     ← Ana orchestrator (run, route, chain)
└── logging_utils.py     ← JSON logging

config/
├── agents.yaml          ← 4 ajan tanımı
└── settings.py          ← Konfig yönetimi

api/
└── server.py            ← FastAPI (5 endpoint)

scripts/
└── agent_runner.py      ← CLI arayüz

tests/
└── test_*.py            ← 6 test dosyası
```

---

## 🚀 Günlük Workflow

### Sabah (Başlarken)

```bash
cd ~/projects/client-xyz
git status
cat ~/memory/NOTES/client-xyz.notes | tail -5
```

### Geliştirme

```bash
# Branch oluştur
git checkout -b feat/yeni-ozellik

# Kodla
nano [dosya]

# Test
make test

# Commit
git add .
git commit -m "feat: Açıklama"
```

### Akşam (Bitirirken)

```bash
# Not al
make memory-note MSG="Bugün X yaptım"

# Merge
git checkout main
git merge feat/yeni-ozellik

# Dokümante (önemliyse)
nano CHANGELOG.md
```

---

## 🤖 AI ile Devam Etme

### Yeni Chat Başlatırken

```
Merhaba! Multi-Agent Orchestrator projemi geliştirmeye devam ediyorum.

DURUM:
- Versiyon: 0.1.0
- Lokasyon: ~/projects/client-xyz
- Son: [git log -1 --oneline]

HEDEF:
[Ne yapmak istiyorum]

Context için SESSION_SUMMARY.md okudum.
```

### Context Dosyaları

```bash
# AI'ya göster
cat ~/projects/client-xyz/SESSION_SUMMARY.md
cat ~/projects/client-xyz/config/agents.yaml
git log -5 --stat
```

---

## 🔧 Sık Kullanılan Komutlar

### Memory Sistemi

```bash
make memory-note MSG="Not"
make memory-log MSG="Log"
cat ~/memory/NOTES/client-xyz.notes
```

### Test

```bash
make test              # Tüm testler
pytest tests/test_api.py -v  # Spesifik test
```

### Development Server

```bash
cd ~/.orchestrator
make run-api           # Port 5050
```

### Logs

```bash
# Son konuşmalar
ls -lt ~/.orchestrator/data/CONVERSATIONS/ | head -5

# Son log oku
make agent-last
```

---

## 📝 Yeni Özellik Eklerken

### 1. Yeni Ajan

```bash
# config/agents.yaml
nano config/agents.yaml

# Ekle:
  researcher:
    model: "..."
    system: "..."
```

### 2. Yeni API Endpoint

```bash
# api/server.py
nano api/server.py

# Ekle:
@app.post("/yeni")
async def yeni_endpoint():
    ...

# Test ekle
nano tests/test_api.py
```

### 3. UI Değişikliği

```bash
nano ui/templates/index.html
make run-api  # Test
```

---

## 🐛 Sorun Giderme

### Test Fail

```bash
make test -v          # Detaylı
pytest tests/test_X.py --pdb  # Debug
```

### Kod Bozuldu

```bash
git status
git diff              # Ne değişmiş
git reset --hard      # İptal et
```

### Dependency Sorunu

```bash
cd ~/.orchestrator
pip install -r requirements.txt --upgrade
```

---

## 📊 İlerleme Takibi

### Bu Hafta Ne Yaptım?

```bash
git log --since="1 week ago" --oneline
grep "$(date +%Y-%m)" ~/memory/NOTES/client-xyz.notes
```

### TODO

```bash
# TODO.md yoksa oluştur
cat > ~/projects/client-xyz/TODO.md << 'EOF'
# TODO

## v0.2.0
- [ ] Streaming
- [ ] Auth

## Bugs
- [ ] None
EOF

# Kontrol et
cat ~/projects/client-xyz/TODO.md
```

---

## 🎓 Best Practices (1 Sayfa)

✅ **Her özellik = Ayrı branch**
```bash
git checkout -b feat/X
```

✅ **Test önce, commit sonra**
```bash
make test && git commit
```

✅ **Küçük, sık commit**
```bash
git commit -m "feat: X"  # Her mantıksal değişiklik
```

✅ **Dokümantasyon senkron**
```bash
# Kod değişti → README de değişsin
```

✅ **Memory kullan**
```bash
make memory-note MSG="..."
```

---

## 🆘 Kayboldum?

### Adım Adım Kurtar

```bash
# 1. Neredeyim?
pwd

# 2. Ne yaptım?
git log -5 --oneline

# 3. Notlarım ne diyor?
cat ~/memory/NOTES/client-xyz.notes

# 4. Dokümana bak
cat ~/projects/client-xyz/SESSION_SUMMARY.md

# 5. Test çalışıyor mu?
cd ~/projects/client-xyz
make test
```

---

## 📞 Hangi Dosyaya Bakmalıyım?

| Soru | Dosya |
|------|-------|
| "Baştan ne yaptık?" | `SESSION_SUMMARY.md` |
| "Nasıl kullanılır?" | `README.md` / `QUICKSTART.md` |
| "Nasıl geliştiririm?" | `DEVELOPMENT_CONTINUATION.md` |
| "Ajanlar nasıl tanımlı?" | `config/agents.yaml` |
| "API'de ne var?" | `api/server.py` (grep @app) |
| "Test nasıl yazarım?" | `tests/test_*.py` (örnek) |
| "Environment nasıl?" | `docs/ENVIRONMENT_SETUP.md` |
| "Merkezi sistem nasıl?" | `docs/LOCAL_INTEGRATION.md` |

---

## 🔗 Hızlı Linkler (Dosya Yolları)

```bash
# Ana proje
cd ~/projects/client-xyz

# Kurulu sistem (production)
cd ~/.orchestrator

# Memory
cd ~/memory

# Notlar
nano ~/memory/NOTES/client-xyz.notes

# Loglar
ls -lt ~/.orchestrator/data/CONVERSATIONS/

# Setup
~/setup_orchestrator_local.sh
```

---

## ⚡ En Önemli 5 Komut

```bash
# 1. Durum kontrolü
git log -5 --oneline && cat ~/memory/NOTES/client-xyz.notes

# 2. Test
make test

# 3. Geliştirme başlat
git checkout -b feat/X

# 4. Commit
git add . && git commit -m "..."

# 5. Not al
make memory-note MSG="..."
```

---

**Bu kartı her zaman yakınında tut!**
**Kaybolursan: QUICK_REFERENCE.md → DEVELOPMENT_CONTINUATION.md → SESSION_SUMMARY.md**

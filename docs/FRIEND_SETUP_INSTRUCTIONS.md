# 🔑 .env DOSYASI VE FORK SYNC TALİMATLARI

Merhaba! Test ettiğin sistemde şu anda sadece Google Gemini API key var.
Diğer provider'ları (Anthropic Claude ve OpenAI GPT) aktif etmek için şu adımları izle.

---

## ⚠️ ÖNEMLİ: İLK ÖNCE FORK'UNU GÜNCELLE!

2 bug fix GitHub'a push edildi, önce bunları çek:

### Seçenek A: GitHub Web Üzerinden (Kolay)

1. **GitHub'da fork'una git:** https://github.com/SENIN_KULLANICI_ADIN/multi-agent-orchestrator-v2
2. **"Sync fork" butonuna tıkla** (sayfanın üst kısmında yeşil buton)
3. **"Update branch"** butonuna tıkla
4. **WSL'de pull çek:**
   ```bash
   cd ~/.orchestrator
   git pull origin master
   ```

### Seçenek B: Git Komutları ile (Manuel)

```bash
cd ~/.orchestrator

# Upstream'i ekle (bir kere yapılır)
git remote add upstream https://github.com/brdfb/multi-agent-orchestrator-v2.git

# Upstream'den değişiklikleri çek
git fetch upstream

# Master branch'i güncelle
git checkout master
git merge upstream/master

# Kendi fork'una push et
git push origin master
```

### 📝 Yeni Fix'ler (e6e9d32)

- ✅ **Bug #8**: FastAPI deprecation warning gitti (lifespan pattern)
- ✅ **Bug #9**: Token counting artık doğru (tiktoken ile %44 daha accurate)
- ✅ 23 memory test pass
- ✅ API server sorunsuz import

---

## 1️⃣ API KEY'LERİ AL

### A) ANTHROPIC (Claude) - Builder agent için gerekli

1. https://console.anthropic.com/ adresine git
2. **Sign up / Log in** yap
3. **"Get API Keys"** butonuna tıkla
4. **"Create Key"** ile yeni key oluştur
5. Key'i kopyala (örnek: `sk-ant-api03-abc123...`)
6. **NOT:** $5 minimum credit gerekir (ilk kullanımda ücretsiz credit verebilirler)

### B) OPENAI (GPT) - Critic agent için gerekli

1. https://platform.openai.com/api-keys adresine git
2. **Sign up / Log in** yap
3. **"+ Create new secret key"** ile key oluştur
4. Key'i kopyala (örnek: `sk-proj-abc123...` veya `sk-abc123...`)
5. **NOT:** $5 minimum credit gerekir - https://platform.openai.com/account/billing adresinden ödeme yöntemi ekle

### C) GOOGLE (Gemini) - Zaten var

Senin sistemde zaten var, değiştirmene gerek yok.

---

## 2️⃣ .env DOSYASINI DÜZENLE

### WSL terminalde:

```bash
cd ~/.orchestrator
nano .env
```

### .env dosyasının içeriği şu şekilde olmalı:

```bash
# Anthropic (Claude) - Builder agent için
ANTHROPIC_API_KEY=sk-ant-api03-BURAYA_SENIN_CLAUDE_KEYIN_GELECEK

# OpenAI (GPT) - Critic agent için
OPENAI_API_KEY=sk-BURAYA_SENIN_OPENAI_KEYIN_GELECEK

# Google (Gemini) - Zaten çalışıyor, değiştirme
GOOGLE_API_KEY=MEVCUT_GOOGLE_KEYIN_BURADA_KALSIN
```

### Kaydet ve çık:

- **CTRL+O** → Enter (kaydet)
- **CTRL+X** (çık)

---

## 3️⃣ API SERVER'I YENİDEN BAŞLAT

Yeni değişiklikler için:

```bash
cd ~/.orchestrator

# Eski server'ı durdur (Ctrl+C ile)
# Veya başka terminalde çalışıyorsa:
pkill -f "uvicorn api.server:app"

# Yeni bağımlılıkları yükle (tiktoken)
.venv/bin/pip install -r requirements.txt

# Server'ı başlat
make run-api
```

Beklenen çıktı:
```
🔑 API keys loaded from .env file (development mode)
✓ Available providers: anthropic, openai, google
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:5050
```

**Eğer hala "✗ Disabled providers: anthropic" görüyorsan:**
- .env dosyasını tekrar kontrol et
- API key'lerde boşluk var mı?
- Key doğru kopyalandı mı?

---

## 4️⃣ TEST ET

### A) Provider'ları kontrol et:

```bash
curl http://localhost:5050/health | jq '.providers'
```

**Beklenen çıktı:**
```json
{
  "anthropic": {
    "available": true,
    "reason": "API key present"
  },
  "openai": {
    "available": true,
    "reason": "API key present"
  },
  "google": {
    "available": true,
    "reason": "API key present"
  }
}
```

### B) Builder'ı test et (şimdi Claude kullanacak):

**3 farklı yöntem** (hepsi aynı şeyi yapar):

```bash
# Yöntem 1: Makefile (en basit)
make agent-ask AGENT=builder Q="Write a hello world function"

# Yöntem 2: Direkt Python (eğer make çalışmazsa)
.venv/bin/python scripts/agent_runner.py builder "Write a hello world function"

# Yöntem 3: mao alias (eğer .bashrc'ye eklediysen)
mao builder "Write a hello world function"
```

**Beklenen sonuç:**
- ✅ Builder artık **0 token DEĞİL**
- ✅ Claude Sonnet ile yanıt üretmeli
- ✅ Token sayısı gösterilmeli (örn: 150 tokens)

### C) Chain test et:

**3 farklı yöntem:**

```bash
# Yöntem 1: Makefile (en basit)
make agent-chain Q="Design a simple REST API"

# Yöntem 2: Direkt Python
.venv/bin/python scripts/chain_runner.py "Design a simple REST API"

# Yöntem 3: mao-chain alias (eğer varsa)
mao-chain "Design a simple REST API"
```

**Beklenen sonuç:**
- ✅ Builder (Claude) → Critic (GPT-4o-mini) → Closer (Gemini)
- ✅ Her stage sonuç üretmeli
- ✅ Token sayıları doğru gösterilmeli

---

## 5️⃣ SORUN ÇÖZÜMÜ

### "builder-v2 complete (0 tokens)" Sorunu

**Sebep:** Anthropic API key eksik veya yanlış

**Çözüm:**
1. `.env` dosyasını kontrol et
2. Key'de boşluk yok mu kontrol et
3. Key doğru kopyalandı mı?
4. Server'ı yeniden başlat: `make run-api`
5. Health endpoint kontrol: `curl localhost:5050/health | jq`

### "Rate limit exceeded" Hatası

**Sebep:** API key'in credit'i tükendi

**Çözüm:**
- OpenAI: https://platform.openai.com/account/billing adresinden credit ekle
- Anthropic: https://console.anthropic.com/settings/billing adresinden credit ekle
- Veya başka provider kullan (fallback otomatik)

### "FastAPI deprecation warning" Görünüyor

**Sebep:** Fork güncel değil, yeni fix'leri çekmedin

**Çözüm:** Yukarıdaki "Fork'unu Güncelle" adımlarını tekrar yap

### "ModuleNotFoundError: tiktoken"

**Sebep:** Yeni bağımlılık yüklenmedi

**Çözüm:**
```bash
.venv/bin/pip install tiktoken
# Veya tümünü güncelle:
.venv/bin/pip install -r requirements.txt
```

---

## 6️⃣ BAŞARILI KURULUM SONRASI

### A) Temel Komutlar (Makefile ile)

```bash
# Single agent
make agent-ask AGENT=builder Q="Create a Python function"
make agent-ask AGENT=critic Q="Review this code: def foo(): pass"

# Multi-agent chain
make agent-chain Q="Design a microservices architecture"

# Memory
make memory-stats
make memory-recent LIMIT=10
make memory-search Q="authentication"
```

### B) Direkt Python Komutları (make yoksa)

```bash
# Single agent
.venv/bin/python scripts/agent_runner.py builder "Create a Python function"
.venv/bin/python scripts/agent_runner.py critic "Review code"

# Multi-agent chain
.venv/bin/python scripts/chain_runner.py "Design a microservices architecture"

# View logs
.venv/bin/python scripts/view_logs.py last
.venv/bin/python scripts/view_logs.py last-chain
.venv/bin/python scripts/view_logs.py recent 10
```

### C) Kısayol Alias'ları (İsteğe Bağlı)

Eğer her seferinde uzun komut yazmak istemiyorsan, `.bashrc`'ye şunları ekle:

```bash
# ~/.bashrc dosyasını aç
nano ~/.bashrc

# En alta şunları ekle:
export ORCHESTRATOR_HOME="$HOME/.orchestrator"
alias mao="$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/agent_runner.py"
alias mao-chain='$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/chain_runner.py'
alias mao-last='$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/view_logs.py last'

# Kaydet ve çık (CTRL+O, Enter, CTRL+X)

# Yeniden yükle
source ~/.bashrc

# Şimdi şöyle kullanabilirsin:
mao builder "Write code"
mao-chain "Design API"
mao-last
```

---

## 📊 Hangi Agent Hangi Provider'ı Kullanır?

| Agent | Primary Provider | Fallback 1 | Fallback 2 |
|-------|-----------------|------------|------------|
| **builder** | Claude Sonnet | GPT-4o | GPT-4o-mini |
| **critic** | GPT-4o-mini | GPT-4o | Gemini Flash |
| **closer** | Gemini Pro | GPT-4o | Claude Sonnet |
| **router** | GPT-4o-mini | Gemini Flash | - |

**Eğer sadece Gemini varsa:**
- Builder → Gemini'ye fallback (düşük kalite)
- Critic → Gemini'ye fallback (OK)
- Closer → Gemini (zaten primary)

**İdeal setup:** Her 3 provider da aktif (en iyi sonuç için)

---

## ✅ CHECKLIST

- [ ] Fork GitHub'da sync edildi
- [ ] `git pull origin master` çekildi
- [ ] Anthropic API key alındı
- [ ] OpenAI API key alındı
- [ ] `.env` dosyası düzenlendi
- [ ] `pip install -r requirements.txt` çalıştırıldı
- [ ] API server yeniden başlatıldı
- [ ] Health endpoint 3 provider'ı gösteriyor
- [ ] `mao builder "test"` çalışıyor (0 token değil)
- [ ] `mao-chain "test"` tüm stages çalışıyor
- [ ] FastAPI deprecation warning yok

---

**Sorular için:** Discord/Telegram'dan yaz veya GitHub issue aç
**Bug bulursan:** `docs/COP/` klasörüne chain output'u at, inceleriz

**Son güncelleme:** 2025-11-08
**Commit:** e6e9d32 (Quick wins - FastAPI + token standardization)

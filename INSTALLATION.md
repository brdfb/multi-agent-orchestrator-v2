# Installation Guide - Multi-Agent Orchestrator

Bu dokuman, Multi-Agent Orchestrator sistemini **sıfırdan** yeni bir makineye kurmanız için hazırlanmıştır.

---

## 📋 İçindekiler

1. [Sistem Gereksinimleri](#sistem-gereksinimleri)
2. [Hızlı Kurulum (Git)](#hızlı-kurulum-git)
3. [Manuel Kurulum (Git olmadan)](#manuel-kurulum-git-olmadan)
4. [Kurulum Sonrası Doğrulama](#kurulum-sonrası-doğrulama)
5. [API Key Ekleme](#api-key-ekleme)
6. [Troubleshooting](#troubleshooting)
7. [Farklı İşletim Sistemleri](#farklı-işletim-sistemleri)

---

## 🔧 Sistem Gereksinimleri

### Minimum Gereksinimler

- **Python:** 3.10 veya üstü (önerilen: 3.12+)
- **pip:** Python paket yöneticisi
- **venv:** Python virtual environment
- **Disk:** ~100MB boş alan
- **İşletim Sistemi:** Linux, macOS, WSL2 (Windows)

### Opsiyonel

- **git:** Repo klonlamak için (önerilen)
- **make:** Makefile komutları için
- **curl:** API testleri için

### Gereksinimler Kontrolü

```bash
# Python versiyonu
python3 --version  # 3.10+ olmalı

# pip
python3 -m pip --version

# venv
python3 -m venv --help

# git (opsiyonel)
git --version
```

**Ubuntu/Debian'da eksikler varsa:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git make curl
```

**macOS'ta (Homebrew ile):**
```bash
brew install python3 git
```

---

## 🚀 Hızlı Kurulum (Git)

### Adım 1: Repository Klonlama

```bash
# Option A: GitHub'dan klonla (public repo ise)
git clone https://github.com/KULLANICI_ADI/orchestrator.git ~/.orchestrator

# Option B: Private repo için SSH
git clone git@github.com:KULLANICI_ADI/orchestrator.git ~/.orchestrator

# Option C: GitLab, Bitbucket, vs.
git clone https://gitlab.com/KULLANICI_ADI/orchestrator.git ~/.orchestrator
```

### Adım 2: Virtual Environment ve Dependencies

```bash
cd ~/.orchestrator

# Virtual environment oluştur
python3 -m venv .venv

# Aktive et
source .venv/bin/activate

# Dependencies yükle
pip install -r requirements.txt
```

### Adım 3: Shell Entegrasyonu

```bash
# Orchestrator alias'larını .bashrc'ye ekle
cat >> ~/.bashrc << 'EOF'

# >>> Multi-Agent Orchestrator Integration >>>
export ORCHESTRATOR_HOME="$HOME/.orchestrator"
export PYTHONPATH="$ORCHESTRATOR_HOME:$PYTHONPATH"

# Quick access alias
alias mao="python3 $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# Enhanced aliases with common tasks
alias mao-builder='mao builder'
alias mao-critic='mao critic'
alias mao-closer='mao closer'
alias mao-auto='mao auto'

# Orchestrator management
alias mao-status='cd $ORCHESTRATOR_HOME && git status 2>/dev/null || echo "Not a git repo"'
alias mao-update='cd $ORCHESTRATOR_HOME && git pull 2>/dev/null || echo "Not a git repo"'
alias mao-dir='cd $ORCHESTRATOR_HOME'

# Welcome message (shows once per session)
if [ -z "$ORCHESTRATOR_WELCOME_SHOWN" ] && [ -f "$ORCHESTRATOR_HOME/docs/POSTSETUP_MANIFEST.md" ]; then
  export ORCHESTRATOR_WELCOME_SHOWN=1
  echo ""
  echo "🧠 Multi-Agent Orchestrator aktif — mao komutunu kullanabilirsin!"
  echo "📖 Detaylar: cat ~/.orchestrator/docs/POSTSETUP_MANIFEST.md"
  echo "💡 Hızlı test: mao auto 'Merhaba!'"
  echo ""
fi
# <<< Multi-Agent Orchestrator Integration <<<
EOF

# Aktive et
source ~/.bashrc
```

### Adım 4: Memory Sistemi (Opsiyonel)

```bash
# Memory klasör yapısını oluştur
mkdir -p ~/memory/{NOTES,HISTORY,BIN}

# Memory script'lerini kopyala
cp ~/.orchestrator/scripts/memory_post_setup.sh ~/memory/BIN/

# Memory Makefile hedeflerini kullanabilmek için
cd ~/.orchestrator
make memory-init
```

### Adım 5: Doğrulama

```bash
# Test suite çalıştır
cd ~/.orchestrator
make test

# Alias'ları test et
mao-dir && pwd  # /home/USER/.orchestrator olmalı
```

**Beklenen çıktı:**
```
======================== 19 passed, 7 warnings in 3s ========================
```

✅ Kurulum tamamlandı! [API Key Ekleme](#api-key-ekleme) bölümüne geçin.

---

## 📦 Manuel Kurulum (Git olmadan)

Git kullanmadan, tar arşivi veya dosya transferi ile kurulum.

### Adım 1: Dosyaları Aktar

**Kaynak makinede (eski sistemde):**
```bash
# Arşiv oluştur
cd ~
tar -czf orchestrator-$(date +%Y%m%d).tar.gz \
    .orchestrator/ \
    setup_orchestrator_local.sh \
    memory/ 2>/dev/null || true

# Dosya boyutunu kontrol et
ls -lh orchestrator-*.tar.gz

# Dosyayı yeni makineye aktar (USB, scp, email, vs.)
# Örnek: scp orchestrator-*.tar.gz user@new-machine:~/
```

**Hedef makinede (yeni sistem):**
```bash
# Arşivi aç
cd ~
tar -xzf orchestrator-*.tar.gz

# Dizin yapısını kontrol et
ls -la ~/.orchestrator/
```

### Adım 2: Virtual Environment Yeniden Oluştur

Virtual environment taşınabilir değil, yeniden oluşturmalısın:

```bash
cd ~/.orchestrator

# Eski venv'i sil (varsa)
rm -rf .venv

# Yeni venv oluştur
python3 -m venv .venv

# Aktive et
source .venv/bin/activate

# Dependencies yükle
pip install -r requirements.txt
```

### Adım 3: Shell Entegrasyonu

```bash
# Setup script'i çalıştır (eğer taşıdıysan)
~/setup_orchestrator_local.sh

# VEYA manuel olarak ekle (yukarıdaki Adım 3'teki gibi)
# ~/.bashrc'ye alias'ları ekle

# Aktive et
source ~/.bashrc
```

### Adım 4: Doğrulama

```bash
cd ~/.orchestrator
make test
```

---

## ✅ Kurulum Sonrası Doğrulama

### Test Checklist

```bash
# 1. Python environment
cd ~/.orchestrator
source .venv/bin/activate
python3 --version
python3 -c "import litellm; print('LiteLLM OK')"

# 2. Testler
make test  # 19/19 geçmeli

# 3. Alias'lar
type mao  # alias göstermeli
mao-dir && pwd  # ~/.orchestrator göstermeli

# 4. Config
python3 -c "from config.settings import AGENTS_CONFIG; print('Config OK')"

# 5. Memory (opsiyonel)
ls ~/memory/NOTES/ ~/memory/HISTORY/ ~/memory/BIN/
```

### Beklenen Klasör Yapısı

```
~/.orchestrator/
├── .venv/                # Virtual environment
├── api/                  # FastAPI server
├── config/               # agents.yaml, settings.py
├── core/                 # llm_connector, agent_runtime
├── data/
│   └── CONVERSATIONS/    # JSON logs
├── docs/                 # Dokümantasyon
├── scripts/              # agent_runner.py
├── tests/                # Test suite
├── ui/                   # Web interface
├── requirements.txt
├── Makefile
├── README.md
└── ...

~/memory/                 # Project memory (opsiyonel)
├── NOTES/
├── HISTORY/
└── BIN/
```

---

## 🔑 API Key Ekleme

Sistemi gerçek LLM'lerle kullanmak için API key'leri eklemelisin.

### Yöntem 1: Environment Variables (.bashrc)

**Önerilen yöntem** - Tüm projelerden erişilebilir:

```bash
# API key'leri .bashrc'ye ekle
cat >> ~/.bashrc << 'EOF'

# LLM API Keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-proj-..."
export GOOGLE_API_KEY="..."
EOF

# Aktive et
source ~/.bashrc

# Doğrula (masked)
env | grep -E "(ANTHROPIC|OPENAI|GOOGLE).*API" | sed 's/=.*/=***MASKED***/'
```

### Yöntem 2: .env Dosyası

**Geliştirme ortamı için** - Sadece orchestrator'dan erişilebilir:

```bash
# .env dosyası oluştur
cd ~/.orchestrator
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...
EOF

# Doğrula
cat .env
```

**NOT:** `.env` dosyası `.gitignore`'da, git'e commit edilmez (güvenlik).

### API Key Nereden Alınır?

| Provider | URL | Ücretlendirme |
|----------|-----|---------------|
| **Anthropic (Claude)** | https://console.anthropic.com/settings/keys | Ücretli - $5 minimum |
| **OpenAI (GPT)** | https://platform.openai.com/api-keys | Ücretli - Pay-as-you-go |
| **Google (Gemini)** | https://aistudio.google.com/app/apikey | Ücretsiz tier mevcut ✨ |

### Test Etme

```bash
# API key var mı kontrol et
cd ~/.orchestrator
source .venv/bin/activate
python3 -c "from config.settings import get_env_source; print(get_env_source())"

# Mock ile test (API key gerektirmez)
make test

# Gerçek LLM ile test (API key gerektirir)
mao auto "Kısa bir test mesajı"
```

---

## 🐛 Troubleshooting

### Problem 1: "python3: command not found"

**Çözüm:**
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv

# macOS
brew install python3
```

### Problem 2: "ensurepip is not available"

**Çözüm:**
```bash
# Ubuntu/Debian
sudo apt install -y python3.12-venv  # Veya python3-venv

# macOS
# Python3 reinstall
brew reinstall python3
```

### Problem 3: "ModuleNotFoundError: No module named 'litellm'"

**Çözüm:**
```bash
cd ~/.orchestrator
source .venv/bin/activate
pip install -r requirements.txt
```

### Problem 4: "make: command not found"

**Çözüm 1:** make yükle:
```bash
sudo apt install -y make  # Ubuntu/Debian
brew install make          # macOS
```

**Çözüm 2:** make kullanmadan çalıştır:
```bash
# Test yerine
python3 -m pytest tests/

# Run yerine
cd ~/.orchestrator
source .venv/bin/activate
python3 api/server.py
```

### Problem 5: Testler fail oluyor

**Doğrulama:**
```bash
cd ~/.orchestrator
source .venv/bin/activate

# Tek tek test et
python3 -m pytest tests/test_config.py -v
python3 -m pytest tests/test_runtime.py -v

# Detaylı hata
python3 -m pytest tests/ -vv --tb=short
```

### Problem 6: "mao: command not found"

**Çözüm:**
```bash
# .bashrc'ye eklendi mi kontrol et
grep "ORCHESTRATOR_HOME" ~/.bashrc

# Yoksa manuel ekle
cat >> ~/.bashrc << 'EOF'
export ORCHESTRATOR_HOME="$HOME/.orchestrator"
alias mao="python3 $ORCHESTRATOR_HOME/scripts/agent_runner.py"
EOF

# Aktive et
source ~/.bashrc

# Test et
type mao
```

### Problem 7: API Key çalışmıyor

**Kontrol:**
```bash
# Environment'ta var mı?
env | grep API_KEY

# .env dosyasında var mı?
cat ~/.orchestrator/.env

# Config doğru mu?
cd ~/.orchestrator
source .venv/bin/activate
python3 -c "from config.settings import get_env_source; print(get_env_source())"
```

**Çözüm:**
```bash
# Environment variable ekle
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
source ~/.bashrc

# Veya .env oluştur
cd ~/.orchestrator
nano .env  # .env.example'dan kopyala
```

### Problem 8: Port 5050 kullanımda

**Çözüm:**
```bash
# Başka port kullan
cd ~/.orchestrator
source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 5051 --reload
```

---

## 🖥️ Farklı İşletim Sistemleri

### Linux (Ubuntu/Debian)

En kolay kurulum, yukarıdaki adımlar direkt çalışır.

```bash
# Sistem paketleri
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git make curl

# Kuruluma devam et
git clone ... ~/.orchestrator
cd ~/.orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### macOS

Homebrew kullanımı önerilir.

```bash
# Homebrew yükle (yoksa)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python ve Git
brew install python3 git

# Kuruluma devam et
git clone ... ~/.orchestrator
cd ~/.orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# .bashrc yerine .zshrc kullan (macOS Catalina+)
# Yukarıdaki ~/.bashrc'yi ~/.zshrc olarak değiştir
```

### Windows (WSL2)

**WSL2 kurulumu (PowerShell - Admin):**
```powershell
wsl --install
wsl --set-default-version 2
```

**WSL içinde (Ubuntu):**
```bash
# Linux adımlarını takip et
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

git clone ... ~/.orchestrator
cd ~/.orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**NOT:** Native Windows (CMD/PowerShell) desteklenmez, WSL2 kullanın.

---

## 📚 Ek Kaynaklar

Kurulum sonrası bu dokümanları okuyun:

```bash
cat ~/.orchestrator/README.md                          # Ana kılavuz
cat ~/.orchestrator/QUICKSTART.md                      # Hızlı başlangıç
cat ~/.orchestrator/QUICK_REFERENCE.md                 # Komut referansı
cat ~/.orchestrator/docs/ENVIRONMENT_SETUP.md          # Environment detayları
cat ~/.orchestrator/docs/LOCAL_INTEGRATION.md          # Merkezi sistem
cat ~/.orchestrator/docs/POSTSETUP_MANIFEST.md         # Kurulum sonrası
cat ~/.orchestrator/docs/DEVELOPMENT_CONTINUATION.md   # Geliştirme
```

---

## 🆘 Yardım

### Hızlı Yardım

```bash
# Sistem durumu
cd ~/.orchestrator
git log -3 --oneline
make test

# Alias'lar çalışıyor mu?
type mao
mao-dir && pwd

# Virtual env aktif mi?
which python3

# Config yükleniyor mu?
python3 -c "from config.settings import AGENTS_CONFIG; print('OK')"
```

### Dokümantasyon

- **README.md** - Sistem kullanımı
- **QUICKSTART.md** - 60 saniye'de başla
- **SESSION_SUMMARY.md** - Tüm geliştirme süreci
- **CONTEXT_HANDOFF.md** - Context yönetimi

### İletişim

GitHub Issues: [Repo URL]/issues

---

## ✅ Kurulum Başarılı mı?

Şu checklist'i tamamladıysan hazırsın:

- [ ] Python 3.10+ kurulu
- [ ] `~/.orchestrator/` dizini var
- [ ] Virtual environment oluşturuldu ve dependencies yüklendi
- [ ] `.bashrc` veya `.zshrc`'ye alias'lar eklendi
- [ ] `source ~/.bashrc` çalıştırıldı
- [ ] `make test` → 19/19 test geçti
- [ ] `mao-dir` çalışıyor
- [ ] API key'ler eklendi (opsiyonel)

**Hepsi tamam mı? Tebrikler! 🎉**

```bash
mao auto "Merhaba! Sistem kurulumu tamamlandı."
```

---

**Son güncelleme:** 2025-11-03
**Versiyon:** v0.1.0

# 🎯 Multi-Agent Orchestrator — Local Integration Completed

```
╔══════════════════════════════════════════════════════════════╗
║  ✅ SİSTEM HAZIR - MERKEZI LLM AJAN ALTYAPISI AKTİF         ║
╚══════════════════════════════════════════════════════════════╝
```

## 🚀 Hızlı Başlangıç

Artık aşağıdaki komutlar **her yerden** çalışır:

### Temel Komutlar

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `mao auto "..."` | Otomatik ajan seçimi | `mao auto "Bu kodu analiz et"` |
| `mao builder "..."` | Kod/plan üretimi | `mao builder "REST API oluştur"` |
| `mao critic "..."` | Güvenlik/kalite analizi | `mao critic "Bu tasarımı değerlendir"` |
| `mao closer "..."` | Özet ve aksiyon planı | `mao closer "Tartışmayı özetle"` |

### Yönetim Komutları

| Komut | Açıklama |
|-------|----------|
| `mao-dir` | Orchestrator dizinine git (`~/.orchestrator`) |
| `mao-status` | Git durumunu kontrol et |
| `mao-update` | Sistemi güncelle (git pull) |
| `mao-last-chain` | Son chain çalıştırmasının detaylarını göster |
| `mao-logs [N]` | Son N konuşmayı listele (varsayılan: 10) |

### Memory (Konuşma Hafızası) Komutları

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `make memory-search Q="..."` | Konuşmalarda arama yap | `make memory-search Q="JWT" AGENT=builder` |
| `make memory-recent LIMIT=N` | Son N konuşmayı göster | `make memory-recent LIMIT=20` |
| `make memory-stats` | Hafıza istatistiklerini göster | `make memory-stats` |
| `make memory-export FORMAT=json` | Tüm konuşmaları dışa aktar | `make memory-export FORMAT=json > backup.json` |
| `make memory-cleanup DAYS=N CONFIRM=1` | N günden eski konuşmaları sil | `make memory-cleanup DAYS=90 CONFIRM=1` |

## 📍 Önemli Lokasyonlar

```
~/.orchestrator/              # Ana sistem
├── config/agents.yaml       # Ajan yapılandırması (buradan özelleştir)
├── data/CONVERSATIONS/      # Tüm konuşma logları
├── docs/                    # Dokümantasyon
├── orchestrator.mk          # Paylaşımlı Makefile
└── .env                     # API anahtarları (oluştur)
```

## ⚡ İlk Test

Hemen test et:

```bash
mao auto "Merhaba! Sistem testi yapıyorum."
```

Cevap alırsan ✅ her şey çalışıyor demektir!

## 🔧 Proje Entegrasyonu

Herhangi bir projeye eklemek için:

**1. Makefile'a bir satır ekle:**
```makefile
include $(HOME)/.orchestrator/orchestrator.mk
```

**2. Kullan:**
```bash
make mao-ask AGENT=auto Q="Proje hakkında soru"
make mao-chain Q="Mimari tasarla"
make mao-last  # Son konuşmayı göster
```

## 🎯 Kullanım Senaryoları

### Senaryo 1: Kod İncelemesi
```bash
cd ~/projects/my-app
mao critic "src/ klasöründeki kodları güvenlik açısından incele"
```

### Senaryo 2: Yeni Feature
```bash
mao builder "User authentication için JWT tabanlı sistem oluştur"
```

### Senaryo 3: Çoklu Ajan Zinciri
```bash
# Komut satırından (en kolay)
mao-chain "Scalable chat sistemi tasarla"

# İnteraktif mod (prompt yazmadan)
mao-chain
# Enter your prompt: [buraya yazın]

# API ile
cd ~/.orchestrator
curl -X POST http://localhost:5050/chain \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Scalable chat sistemi tasarla"}'
```

### Senaryo 4: Makefile ile Workflow
```makefile
# Projenizde
deploy:
	npm run build
	make mao-ask AGENT=critic Q="Build çıktısını kontrol et"
	kubectl apply -f k8s/
```

## 📊 Konuşma Logları

Tüm konuşmalar otomatik olarak saklanır:

```bash
# Son konuşmayı göster
ls -lt ~/.orchestrator/data/CONVERSATIONS/ | head -5

# JSON olarak oku
cat ~/.orchestrator/data/CONVERSATIONS/20241103_*.json | jq .
```

Her log şunları içerir:
- Kullanılan ajan ve model
- Token sayısı ve tahmini maliyet
- Tam prompt ve response
- Zaman damgası

## 🔐 API Anahtarları

Eğer henüz yapılandırmadıysan:

```bash
# .env dosyası oluştur
cd ~/.orchestrator
cp .env.example .env
nano .env

# Veya environment variable kullan (önerilen)
echo 'export OPENAI_API_KEY=sk-...' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc
source ~/.bashrc
```

Sistem otomatik olarak hangi kaynağı kullandığını gösterir.

## 🎨 Özelleştirme

### Ajan Konfigürasyonu

```bash
nano ~/.orchestrator/config/agents.yaml
```

Örnek değişiklik:
```yaml
agents:
  builder:
    model: "openai/gpt-4o-mini"  # Daha ucuz model
    temperature: 0.2              # Daha deterministik

  # Yeni ajan ekle
  researcher:
    model: "anthropic/claude-3-5-sonnet-20241022"
    system: "Sen detaylı araştırmacısın..."
    temperature: 0.4
```

Değişiklikler anında aktif olur!

### Yeni Komut Alias'ı

```bash
# ~/.bashrc'a ekle
alias mao-research='mao researcher'
alias mao-quick='mao auto'
```

## 📚 Dokümantasyon

Detaylı rehberler:

- **Genel:** `~/.orchestrator/README.md`
- **Hızlı:** `~/.orchestrator/QUICKSTART.md`
- **Entegrasyon:** `~/.orchestrator/docs/LOCAL_INTEGRATION.md`
- **Environment:** `~/.orchestrator/docs/ENVIRONMENT_SETUP.md`

## 🐛 Sorun Giderme

### "mao: command not found"
```bash
source ~/.bashrc  # Aliasları yükle
```

### "ModuleNotFoundError: No module named 'dotenv'" veya benzeri

**Problem:** `mao` komutu sistem Python'unu kullanıyor, virtual environment'daki paketleri bulamıyor.

**Çözüm:**
```bash
# ~/.bashrc dosyasındaki alias'ı düzelt
nano ~/.bashrc

# Şunu bul:
alias mao="python3 $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# Şuna değiştir:
alias mao="$ORCHESTRATOR_HOME/.venv/bin/python $ORCHESTRATOR_HOME/scripts/agent_runner.py"

# Kaydet ve yenile
source ~/.bashrc

# Test et
mao auto "test"
```

### "No API keys detected"
```bash
echo $OPENAI_API_KEY  # Kontrol et
cd ~/.orchestrator && cat .env  # veya .env kontrol
```

### "Module not found" (paket eksikliği)
```bash
cd ~/.orchestrator
make install  # Bağımlılıkları yeniden kur
```

### "Server not running" (chain için)
```bash
cd ~/.orchestrator
make run-api  # API sunucusunu başlat
```

## 🎓 İleri Seviye

### CI/CD Entegrasyonu

**GitHub Actions:**
```yaml
# .github/workflows/ai-review.yml
- name: AI Review
  run: |
    source ~/.bashrc
    mao critic "Review PR changes: $(git diff)"
```

**Git Hook (pre-commit):**
```bash
#!/bin/bash
echo "🤖 AI code review..."
mao critic "Review changes: $(git diff --cached)"
```

### Python Entegrasyonu

```python
import sys
sys.path.insert(0, '/home/beredhome/.orchestrator')

from core.agent_runtime import AgentRuntime

runtime = AgentRuntime()
result = runtime.run("builder", "Create function")
print(result.response)
```

### Multi-Proje Workflow

```bash
# Terminal 1: Frontend
cd ~/projects/webapp
mao builder "React component oluştur"

# Terminal 2: Backend
cd ~/projects/api
mao builder "API endpoint ekle"

# Terminal 3: Review
cd ~/projects/
mao critic "Frontend ve backend entegrasyonunu değerlendir"
```

Tüm konuşmalar `~/.orchestrator/data/CONVERSATIONS/` altında birleşir!

## 📈 Metrikler

Kullanım istatistiklerini görmek için:

```bash
# API çalışıyorsa
curl http://localhost:5050/metrics

# Veya loglardan
cd ~/.orchestrator/data/CONVERSATIONS
wc -l *.json  # Toplam konuşma sayısı
```

## 🎉 İpuçları

1. **Her zaman auto ile başla** - Sistem doğru ajanı seçer
2. **Logları tut** - Gelecekte referans olarak kullanabilirsin
3. **config/agents.yaml'ı özelleştir** - Senin iş akışına göre ayarla
4. **Maliyeti izle** - `/metrics` endpoint'ini kullan
5. **Proje başına .env** - Farklı API key'leri kullanabilirsin

## 🔄 Güncelleme

Sistem güncellemesi:

```bash
mao-update  # veya
cd ~/.orchestrator && git pull && make install
```

## 🌟 Sonraki Adımlar

- [ ] İlk test: `mao auto "Merhaba"`
- [ ] API anahtarlarını yapılandır
- [ ] Bir projede dene
- [ ] Kendi ajan rolünü ekle
- [ ] CI/CD ile entegre et

---

**Sistem Versiyonu:** 0.5.0
**Kurulum Tarihi:** Otomatik tespit edilir
**Destek:** `~/.orchestrator/docs/` altındaki tüm dokümantasyon

## 🆕 v0.5.0 Yenilikleri

- ✅ **Token limit optimizasyonu** - Builder: 9000, Critic: 7000, Closer: 9000 tokens (truncation tamamen çözüldü)
- ✅ **İdiot-proof dokümantasyon** - NASIL_ÇALIŞIR.md (teknik olmayan, sade Türkçe anlatım)
- ✅ **Gelişmiş CLI komutları** - `mao-last-chain`, `mao-logs` komutları eklendi
- ✅ **Memory system komutları** - Konuşma arama, istatistik ve export komutları

## 🆕 v0.4.0 Yenilikleri

- ✅ **Semantic Search Memory** - Çok dilli (50+ dil) anlam bazlı konuşma hafızası
- ✅ **Multilingual Support** - Türkçe ekleri otomatik tanıyor ("chart" → "chart'ı", "chart'a")
- ✅ **Context Injection** - Önceki konuşmalar otomatik bulunup ekleniyor
- ✅ **Memory Strategies** - semantic, hybrid, keywords arama stratejileri
- ✅ **SQLite Memory Database** - data/MEMORY/conversations.db ile kalıcı hafıza

## 🆕 v0.3.0 Yenilikleri

- ✅ **Chain workflows** - Multi-agent zincirleri (builder → critic → closer)
- ✅ **Google Gemini desteği** - Gemini 2.5 Pro, 2.0 Flash entegrasyonu
- ✅ **İlerleme göstergeleri** - Gerçek zamanlı stage tracking
- ✅ **Fallback şeffaflığı** - Model değişim sebepleri gösteriliyor
- ✅ **Akıllı context** - Closer tüm önceki stage'leri görüyor
- ✅ **Optimized prompts** - Daha teknik, daha az "fluff"
- ✅ **Düzeltme:** `mao` alias artık venv Python kullanıyor (ModuleNotFoundError çözüldü)

```
╔══════════════════════════════════════════════════════════════╗
║  🎯 HER PROJE, HER YER, TEK SİSTEM                          ║
║  Merkezi LLM ajan altyapısı hazır ve çalışıyor! 🚀          ║
╚══════════════════════════════════════════════════════════════╝
```

**💡 Şimdi dene:** `mao auto "Bu projeyi analiz et"`

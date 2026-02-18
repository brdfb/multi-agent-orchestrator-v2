# Ragıp Aga — Kullanım Dokümantasyonu

**Versiyon:** 2.0.0 | **Tarih:** 2026-02-18

Ragıp Aga, nakit akışı yönetimi, vade müzakeresi ve sözleşme uyuşmazlıkları için geliştirilmiş bir iş danışmanı ajanıdır. İki ayrı arayüz üzerinden çalışır.

---

## İki Arayüz, İki Altyapı

| | `scripts/ragip_aga.py` (Terminal) | `.claude/agents/ragip-aga.md` (Claude Code) |
|---|---|---|
| **Nasıl çağırılır** | `ragip "soru"` | `/agents` → ragip-aga veya Task tool |
| **Altyapı** | LiteLLM → Anthropic / OpenAI / Google | Claude Code → Anthropic direkt |
| **Model** | claude-sonnet-4-5 (varsayılan) | sonnet |
| **Fallback** | Evet: GPT-4o → Gemini 2.5 Flash | Hayır |
| **Tools** | Dahili hesap motoru + dosya okuma | WebSearch, Read, Bash |
| **Geçmiş** | `data/RAGIP_AGA/history.jsonl` | Yok (oturum bazlı) |
| **Bağımsızlık** | Claude Code olmadan çalışır | Claude Code'a bağlı |

---

## 1. Terminal CLI — `ragip`

### Kurulum

```bash
source ~/.bashrc
```

### Temel Kullanım

```bash
# Tek soru (TCMB oranı otomatik eklenir)
ragip "Disti vade farkı faturası kesti, ne yapmalıyım?"

# Sözleşme/fatura dosyasıyla birlikte
ragip "Bu faturadaki vade farkı doğru mu?" --file fatura.pdf
ragip "Vade maddelerini analiz et" --file sozlesme.docx

# Sohbet modu
ragip --interactive

# Geçmiş
ragip --history
ragip --history-limit 10

# Yanıtı dosyaya kaydet
ragip "90 gün vade müzakere stratejisi" --save-to plan.md

# Model override
ragip "soru" --model openai/gpt-4o
```

### Finansal Hesap Motoru (`--calc`)

LLM çağrısı yapmadan, anında hesaplar:

```bash
# Vade farkı hesabı
# 250.000 TL, %3/ay, 45 gün
ragip --calc vade-farki --anapara 250000 --oran 3 --gun 45

# TVM - Paranın fırsat maliyeti (repo oranıyla)
# 100.000 TL'yi 30 gün tutmanın maliyeti
ragip --calc tvm --anapara 100000 --gun 30
ragip --calc tvm --anapara 100000 --gun 30 --repo-orani 42.5

# Erken ödeme için max iskonto
# 30 gün erken ödersen ne kadar indirim isteyebilirsin?
ragip --calc iskonto --anapara 100000 --oran 3 --gun 30

# Nakit çevrim döngüsü
# Stok: 45 gün, Tahsilat: 30 gün, Ödeme vadesi: 60 gün
ragip --calc ncd --dio 45 --dso 30 --dpo 60
```

### TCMB Faiz Oranları

```bash
ragip --tcmb
```

Çıktı:
```
TCMB Politika Faizi: %42.50
Yasal Gecikme Faizi: %52.00
TÜFE Yıllık: %44.40
```

### Desteklenen Dosya Formatları (`--file`)

| Format | Gereksinim |
|--------|------------|
| `.pdf` | `pip install pypdf` veya `pip install pdfplumber` |
| `.docx` | `pip install python-docx` |
| `.txt` | Ek kurulum yok |
| `.md`, `.csv` | Ek kurulum yok |

---

## 2. Claude Code Agent — `ragip-aga`

Claude Code içinde çalışır. **LiteLLM yoktur** — Claude Code'un kendi API bağlantısını kullanır.

### Tools (Aktif)

| Tool | Ne İçin |
|------|---------|
| **WebSearch** | Güncel TCMB faizi, yasal mevzuat araması |
| **Read** | Kullanıcının paylaştığı sözleşme/fatura dosyası okuma |
| **Bash** | TVM, vade farkı, erken ödeme iskontosu hesaplama |

### Çalışma Akışı

Her analizde Ragıp Aga şunu yapar:
1. **WebSearch** → Güncel TCMB politika faizini arar
2. **Read** (dosya varsa) → Sözleşme/faturayı okur, maddeleri alıntılar
3. **Bash** → Python ile somut hesaplamalar yapar
4. **Analiz** → Hesaplara dayalı strateji sunar

### Nasıl Çağırılır

```
# Claude Code içinde:
/agents → ragip-aga seç

# Veya doğrudan söyle:
"ragip-aga ile şu senaryoyu analiz et: ..."
```

### Ne Zaman Hangisini Kullan

| Durum | Kullan |
|-------|--------|
| Claude Code kapalı | Terminal CLI (`ragip`) |
| Geçmiş kaydetmek istiyorsun | Terminal CLI |
| Otomasyona entegre edeceksin | Terminal CLI |
| Hızlı hesap lazım | Terminal CLI (`--calc`) |
| Zaten Claude Code içindesin | Claude Code Agent |
| Dosyaları otomatik aramasını istiyorsun | Claude Code Agent |
| Güncel web verisi kritik | Claude Code Agent (WebSearch var) |

---

## Uzmanlık Alanları

1. **Nakit akışı yönetimi** — DIO + DSO - DPO analizi, repo, vadeli mevduat
2. **Vade müzakeresi** — Distribütör/tedarikçi taktikleri, TVM analizi
3. **Fatura uyuşmazlıkları** — Matematiksel hata, KDV, vade hesaplama kontrolü
4. **Sözleşme itirazları** — Gerçek maddelere dayalı argümanlar
5. **Alacak takibi** — İcra öncesi uzlaşma, borçlu müzakeresi

**Kapsam dışı:** Sahte bahane üretimi, ödeme durumu yanıltma, psikolojik manipülasyon.

---

## Örnek Sorular

```bash
ragip "Sözleşmede %2/ay vade farkı yazıyor, disti 3 ay geriye dönük kesti"
ragip "60 gün vade almak istiyorum, şu an 30 günde çalışıyoruz"
ragip "Faturada KDV matrahı yanlış, nasıl itiraz ederim"
ragip "3 distribütöre borcum var, hangisini önce ödemeliyim"
ragip "Alacağım 90 gündür ödenmedi, icra açmadan çözüm var mı"
ragip "Bu faturanın vade farkı doğru mu hesaplanmış?" --file fatura.pdf
```

---

## Skills (Claude Code içi çağrılabilir iş akışları)

Skills, `/skill-adı` ile doğrudan çağrılır veya Claude konuşmaya göre otomatik yükler.

| Skill | Komut | Ne yapar |
|-------|-------|---------|
| **ragip-vade-farki** | `/ragip-vade-farki 250000 3 45` | Vade farkı + TVM + iskonto hesabı |
| **ragip-ihtar** | `/ragip-ihtar vade-farki` | Resmi ihtar yazısı taslağı (sadece manuel) |
| **ragip-analiz** | `/ragip-analiz sozlesme.pdf` | Sözleşme/fatura analizi + risk skoru |
| **ragip-dis-veri** | `/ragip-dis-veri "ABC Dağıtım"` | Sicil, vergi, icra, kredi sorgulama |
| **ragip-gorev** | `/ragip-gorev listele` | Aksiyon takip listesi |
| **ragip-strateji** | `/ragip-strateji "vade farkı uyuşmazlığı"` | 3 senaryo × haftalık plan |

```bash
# Örnekler
/ragip-vade-farki 250000 3 45       # 250.000 TL, %3/ay, 45 gün
/ragip-ihtar vade-farki             # Vade farkı itiraz ihtarı
/ragip-analiz /path/to/fatura.pdf   # Fatura analizi
```

**Not:** `ragip-ihtar` sadece manuel çağrılır (`disable-model-invocation: true`) — Claude otomatik ihtar göndermez.

---

## Dosya Yapısı

```
config/ragip_aga.yaml                          # Terminal CLI config
scripts/ragip_aga.py                           # Terminal CLI
.claude/agents/ragip-aga.md                   # Claude Code sub-agent
.claude/skills/ragip-vade-farki/SKILL.md      # Hesaplama skill
.claude/skills/ragip-ihtar/SKILL.md           # İhtar yazısı skill
.claude/skills/ragip-analiz/SKILL.md          # Belge analiz skill
data/RAGIP_AGA/history.jsonl                  # Terminal geçmişi (otomatik)
docs/RAGIP_AGA.md                             # Bu dosya
```

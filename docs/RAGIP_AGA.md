# Ragıp Aga — Kullanım Dokümantasyonu

**Versiyon:** 2.2.0 | **Tarih:** 2026-02-21

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

# İndiferans (kayıtsızlık) noktası
# İki ödeme planı arasında hangi faiz oranında fark etmez?
ragip --calc indiferans --anapara 100000 --oran 3 --gun 30

# Döviz forward kuru
# 10.000 USD, 90 gün sonra teorik TL karşılığı
ragip --calc doviz --anapara 10000 --gun 90

# İthalat maliyet hesabı
# FOB 50.000 USD, navlun 2000 USD, sigorta %0.3
ragip --calc ithalat --fob 50000 --navlun 2000 --sigorta 0.3

# CIP faiz paritesi arbitrajı
# Piyasa forward kuru vs teorik forward karşılaştırması
ragip --calc cip-arbitraj --market-forward 45.50 --gun 90

# Üçgen kur arbitrajı
# EUR-USD-TRY döngüsünde tutarsızlık tespiti (TCMB kurlarıyla)
ragip --calc ucgen-arbitraj

# Vade farkı vs mevduat arbitrajı
# Tedarikçiye geç ödemek mi, bankaya yatırıp erken ödemek mi?
ragip --calc vade-mevduat --anapara 500000 --oran 3 --gun 60

# Carry trade analizi
# USD borç al → TL mevduata yatır → başabaş kur hesapla
ragip --calc carry-trade --gun 90
ragip --calc carry-trade --gun 90 --beklenen-kur 46.00
```

### TCMB Faiz Oranları

TCMB EVDS3 API'den canlı veri çeker. API key yoksa fallback değerler kullanılır.

```bash
ragip --tcmb
```

Çıktı (örnek):
```
TCMB Politika Faizi : %37.00
Reeskont Oranı      : %38.75
Avans Faizi (yasal) : %39.75
USD/TRY             : 43.6900
EUR/TRY             : 51.4800
Kaynak: TCMB EVDS3
```

EUR/USD cross rate (TCMB verilerinden hesaplanır):
```bash
ragip --eur-usd
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

| Skill | Komut | Ne yapar | Sub-agent |
|-------|-------|---------|-----------|
| **ragip-vade-farki** | `/ragip-vade-farki 250000 3 45` | Vade farkı + TVM + iskonto hesabı | ragip-hesap |
| **ragip-arbitraj** | `/ragip-arbitraj cip 45.50 90` | CIP, üçgen kur, vade-mevduat, carry trade arbitrajı | ragip-hesap |
| **ragip-analiz** | `/ragip-analiz sozlesme.pdf` | Sözleşme/fatura analizi + risk skoru | ragip-arastirma |
| **ragip-dis-veri** | `/ragip-dis-veri "ABC Dağıtım"` | Kamuya açık sicil/haber araştırması | ragip-arastirma |
| **ragip-strateji** | `/ragip-strateji "vade farkı uyuşmazlığı"` | 3 senaryo × haftalık plan | ragip-arastirma |
| **ragip-ihtar** | `/ragip-ihtar vade-farki` | Resmi ihtar yazısı taslağı (sadece manuel) | ragip-arastirma |
| **ragip-firma** | `/ragip-firma ekle ABC vergi_no=123` | Firma kartı CRUD (ekle/sil/listele/guncelle) | ragip-veri |
| **ragip-gorev** | `/ragip-gorev listele` | Aksiyon takip listesi | ragip-veri |
| **ragip-import** | `/ragip-import cari.csv` | CSV/Excel veri aktarımı | ragip-veri |
| **ragip-ozet** | `/ragip-ozet` | Günlük brifing özeti | ragip-veri |
| **ragip-profil** | `/ragip-profil kaydet firma_adi=X sektor=Y` | Kendi firma profilini yönet (goster/kaydet/guncelle/sil) | ragip-veri |

```bash
# Örnekler
/ragip-vade-farki 250000 3 45         # 250.000 TL, %3/ay, 45 gün
/ragip-arbitraj cip 45.50 90          # CIP arbitraj, piyasa forward 45.50, 90 gün
/ragip-arbitraj ucgen                  # Üçgen kur arbitrajı (TCMB kurlarıyla)
/ragip-arbitraj vade-mevduat 500000 3 60  # Vade farkı vs mevduat
/ragip-arbitraj carry-trade 90         # Carry trade, 90 gün
/ragip-ihtar vade-farki               # Vade farkı itiraz ihtarı
/ragip-analiz /path/to/fatura.pdf     # Fatura analizi
/ragip-firma listele                  # Kayıtlı firmaları göster
/ragip-profil goster                  # Kendi firma profilini göster
/ragip-profil kaydet firma_adi=X sektor=ithalat is_tipi=ithalat
```

**Not:** `ragip-ihtar` sadece manuel çağrılır (`disable-model-invocation: true`) — Claude otomatik ihtar göndermez.

---

## Sub-Agent Mimarisi

```
ragip-aga (orchestrator, sonnet, 0 skill)
  |
  +-- ragip-hesap (haiku, 2 skill)
  |     +-- ragip-vade-farki    # Vade farkı + TVM + iskonto
  |     +-- ragip-arbitraj      # CIP, üçgen kur, vade-mevduat, carry trade
  |
  +-- ragip-arastirma (sonnet, 4 skill)
  |     +-- ragip-analiz        # Sözleşme/fatura analizi
  |     +-- ragip-dis-veri      # Karşı taraf araştırması
  |     +-- ragip-strateji      # 3 senaryolu strateji planı
  |     +-- ragip-ihtar         # İhtar taslağı (sadece manuel)
  |
  +-- ragip-veri (haiku, 5 skill)
        +-- ragip-firma         # Firma kartı CRUD
        +-- ragip-gorev         # Görev takibi
        +-- ragip-import        # CSV/Excel import
        +-- ragip-ozet          # Günlük brifing özeti
        +-- ragip-profil        # Kendi firma profili
```

**Toplam:** 4 agent + 11 skill

---

## Dosya Yapısı

```
config/ragip_aga.yaml                          # Terminal CLI config
scripts/ragip_aga.py                           # Terminal CLI + hesap motoru
scripts/ragip_rates.py                         # TCMB EVDS3 canlı oran çekici

.claude/agents/
  ragip-aga.md                                 # Orchestrator (hub)
  ragip-arastirma.md                           # Araştırma & analiz sub-agent
  ragip-hesap.md                               # Hesap motoru sub-agent
  ragip-veri.md                                # Veri yönetimi sub-agent

.claude/skills/
  ragip-analiz/SKILL.md                        # Sözleşme/fatura analizi
  ragip-arbitraj/SKILL.md                      # Arbitraj hesaplamaları
  ragip-dis-veri/SKILL.md                      # Karşı taraf araştırması
  ragip-firma/SKILL.md                         # Firma kartı CRUD
  ragip-gorev/SKILL.md                         # Görev takibi
  ragip-ihtar/SKILL.md                         # İhtar taslağı
  ragip-import/SKILL.md                        # CSV/Excel import
  ragip-ozet/SKILL.md                          # Günlük brifing özeti
  ragip-strateji/SKILL.md                      # 3 senaryolu strateji
  ragip-vade-farki/SKILL.md                    # Vade farkı hesaplama
  ragip-profil/SKILL.md                        # Kendi firma profili

data/RAGIP_AGA/history.jsonl                   # Terminal geçmişi (otomatik)
data/RAGIP_AGA/profil.json                     # Firma profili (otomatik)
data/RAGIP_AGA/ciktilar/                       # Hesaplama çıktıları (otomatik)
docs/RAGIP_AGA.md                              # Bu dosya
```

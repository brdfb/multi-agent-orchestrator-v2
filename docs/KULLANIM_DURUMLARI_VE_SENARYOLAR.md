# Ne Zaman Kullanılır? – Kullanım Durumları ve Senaryolar

Bu dokümanda **Multi-Agent Orchestrator**'ı ne zaman kullanmanın mantıklı olduğu, pipeline'ın ne sunduğu ve Cursor/Claude gibi tek sohbet araçlarından farkı net biçimde anlatılıyor. Kullanıcı "bunu benim için mi?" sorusuna cevap bulabilsin diye yazıldı.

---

## 1. Hızlı karar: Bunu kullanmalı mıyım?

| Durum | Öneri |
|--------|--------|
| Haftalık/aylık **aynı tip tasarım veya rapor** üretiyorum; dosyaya yazıp saklamak istiyorum | ✅ Kullan |
| Rapor/tasarım üretimini **script, cron veya API** ile otomatik tetiklemek istiyorum | ✅ Kullan |
| Aynı projeyi **haftalar boyu farklı oturumlarda** konuşacağım; eski bağlam hep gelsin istiyorum | ✅ Kullan |
| "Tasarım = güçlü model, inceleme = ucuz model" gibi **rol ve maliyet dağıtmak** istiyorum | ✅ Kullan |
| Günlük işim **sohbet + kod**: soru sorar, kodu birlikte yazarız | ❌ Cursor/Claude yeter |
| Sadece **tek seferlik sorular** (açıklama, hata çözümü, kısa taslak) | ❌ Cursor/Claude yeter |
| Rapor/tasarım **ayda bir iki kez**; otomasyon veya kalıcı bellek önemsiz | ❌ Kuruluma değmeyebilir |

---

## 2. Pipeline özeti: Sistem ne yapıyor?

Orchestrator sabit bir **çok adımlı pipeline** çalıştırır; tek sohbet değil.

```
Senin cümlen ("Todo API tasarla...")
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Session + Bellek (opsiyonel)                                 │
│  • Aynı oturumdaki son N mesaj (session context)              │
│  • Diğer oturumlardan anlamsal benzer konuşmalar (knowledge)  │
│  → Bunlar system prompt'a eklenir; ana talimat hep senin cümlen│
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  BUILDER    │ →  │  CRITIC(S)  │ →  │  CLOSER     │
│  Tasarım   │    │  İnceleme   │    │  Özet +     │
│  Kod/şema  │    │  Risk/eksik │    │  Aksiyon    │
│  (Claude)  │    │  (GPT-4o-m) │    │  (Gemini)   │
└─────────────┘    └─────────────┘    └─────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
   Log + Memory       Log + Memory       Log + Memory
   (opsiyonel)        (opsiyonel)        (opsiyonel)
```

- **Builder:** Tasarla, kod/şema örneği ver, trade-off yaz.
- **Critic:** Eksikleri, riskleri, iyileştirmeleri bul (tek veya birden fazla uzman critic).
- **Closer:** Kararları netleştir, aksiyon listesi çıkar.

Her adım **ayrı model** (config’e göre) ve **ayrı log**; isteğe bağlı **bellek** ile sonraki sorularda bu konuşmalar bağlama eklenir.

---

## 3. Cursor / Claude (tek sohbet) vs Orchestrator

| | **Cursor’daki Claude / ben** | **Orchestrator** |
|--|------------------------------|------------------|
| **Kullanım** | Sohbet: yazıyorsun, cevap gelir; tasarım/inceleme/özet hep aynı konuşmada. | CLI/API: tek cümle + `mao-chain` veya HTTP; pipeline otomatik çalışır. |
| **Bellek** | Bu sohbet (+ proje bağlamı). Sohbet bitince otomatik kalıcı bellek yok. | SQLite + session: farklı oturumlarda "daha önce bu konuda konuşmuştuk" bağlamı gelir. |
| **Modeller** | Tek model (veya sen elle değiştirirsin). | Adım başı farklı: tasarım Claude, inceleme ucuz model, özet Gemini. |
| **Kod / proje** | Dosya açar, düzenler, terminal çalıştırır. | Sadece metin üretir (tasarım/rapor); repo’ya doğrudan müdahale etmez. |
| **Otomasyon** | Sen açıp soruyorsun; cron/script ile "Cursor’a sor" doğal değil. | Script/cron/API ile tam otomatik rapor/tasarım üretimi. |

**Özet:** Orchestrator "daha akıllı" değil; **otomasyon**, **rol/maliyet dağıtımı** ve **oturumlar arası kalıcı bellek** sunar. Günlük sohbet + kod için Cursor/Claude; tekrarlayan pipeline + rapor için Orchestrator.

---

## 4. Kullanım senaryoları (ne zaman kullanılır?)

### Senaryo A: Tekrarlayan tasarım / rapor üretimi

- **Durum:** Her hafta veya her sprint sonunda aynı formatta tasarım/rapor istiyorsun (örn. "X özelliği için API taslağı", "Değişiklik özeti").
- **Orchestrator ile:**  
  `mao-chain "Bu hafta Y özelliği için API taslağı: endpoint'ler, şema." --save-to haftalik-y.md`  
  Tek komut: tasarım → inceleme → özet → dosyaya yazılır.
- **Neden burada avantajlı:** Aynı akışı her seferinde tekrarlamak yerine tek cümle + `--save-to`; çıktı hep aynı yapıda.

### Senaryo B: Otomasyon (script / cron / API)

- **Durum:** Rapor veya taslak üretimini insan sohbeti olmadan tetiklemek istiyorsun (cron, CI, internal tool).
- **Orchestrator ile:**  
  API: `POST /chain` ile prompt gönderirsin; cevap JSON veya dosyaya yazdırılır.  
  CLI: `mao-chain "..." --save-to out.md` script içinde çalıştırılır.
- **Neden burada avantajlı:** Cursor/Claude’da "her pazartesi bu raporu üret" demek için sohbet açman gerekir; burada bir job tetikler, çıktı dosyada/API’de hazır olur.

### Senaryo C: Aynı konuda uzun süre devam (kalıcı bağlam)

- **Durum:** Aynı projeyi haftalar boyu konuşacaksın; "geçen hafta ne tasarlamıştık?" otomatik gelsin istiyorsun.
- **Orchestrator ile:** Aynı terminalde (aynı session) veya aynı session_id ile devam edersin; **session context** (son N mesaj) + **knowledge context** (benzer eski konuşmalar) modele eklenir.
- **Neden burada avantajlı:** Cursor’da her yeni sohbet "sıfırdan"; burada eski konuşmalar DB’de, yeni soruda otomatik referans olur.

### Senaryo D: Rol ve maliyet dağıtımı

- **Durum:** Tasarım için güçlü (pahalı) model, inceleme için hızlı/ucuz model kullanmak istiyorsun.
- **Orchestrator ile:** Config’te builder = Claude, critic = GPT-4o-mini, closer = Gemini; pipeline bunu otomatik uygular. Fallback ile bir provider yoksa diğeri kullanılır.
- **Neden burada avantajlı:** Tek sohbette "şimdi inceleme moduna geç, ucuz model kullan" demek yerine roller sabit; maliyet öngörülebilir.

### Senaryo E: Günlük sohbet + kod (Orchestrator kullanma)

- **Durum:** "Bu hatayı çöz", "Bu fonksiyonu refactor et", "Şu kodu açıkla" — sohbet edip kod üzerinde çalışıyorsun.
- **Ne yap:** Cursor/Claude kullan; dosya açar, düzenler, terminal çalıştırır. Orchestrator bu iş için tasarlanmadı.
- **İstisna:** Önce Orchestrator ile "bu modül için refactor planı tasarla" deyip rapor alırsın; sonra Cursor’da o plana göre kodu yazarsın (iki aracı birlikte kullanma).

---

## 5. Ne zaman kullanılmaz?

- **Sadece sohbet:** Günlük soru–cevap, açıklama, tek seferlik kısa taslak → Cursor/Claude yeter.
- **Sadece kod:** Dosya düzenleme, test çalıştırma, repo üzerinde doğrudan çalışma → Orchestrator bunu yapmaz; Cursor/Claude kullan.
- **Çok seyrek kullanım:** Ayda bir iki tasarım/rapor ve otomasyon/bellek ihtiyacın yoksa → Kurulum/bakım maliyeti fazla gelebilir.
- **"Daha akıllı cevap" beklentisi:** Orchestrator cevabı "daha zeki" yapmaz; **süreci** (pipeline, bellek, otomasyon) standartlaştırır.

---

## 6. Özet tablo: Kullanım durumları

| İhtiyaç | Orchestrator kullan? | Not |
|--------|----------------------|-----|
| Tekrarlayan tasarım/rapor, dosyaya yazılsın | ✅ Evet | `mao-chain "..." --save-to x.md` |
| Script/cron/API ile otomatik rapor | ✅ Evet | `POST /chain` veya CLI script içinde |
| Aynı konuyu uzun süre, eski bağlamla konuşmak | ✅ Evet | Session + memory |
| Tasarım/inceleme/özet için farklı modeller | ✅ Evet | Config’te rol başına model |
| Günlük sohbet + kod yazma | ❌ Hayır | Cursor/Claude |
| Tek seferlik soru / hata çözümü | ❌ Hayır | Cursor/Claude |
| Proje dosyalarını düzenlemek | ❌ Hayır | Cursor/Claude |

---

## 7. İlgili dokümanlar

- **Adım adım kullanım:** [KULLANIM_ORNEGI_TAM_AKIS.md](KULLANIM_ORNEGI_TAM_AKIS.md) — Tek konu üzerinden komutlar, ekranda ne görürsün, arka planda ne olur.
- **Kurulum ve komutlar:** [README.md](../README.md) — Kurulum, Quick Start, CLI/API özeti.
- **Config ve mimari:** [CLAUDE.md](../CLAUDE.md) — Agent’lar, bellek, session, token bütçesi.

Bu doküman, kullanıcının "bunu ne zaman kullanmalıyım?" sorusuna net cevap vermek için yazıldı; senaryolar ve pipeline özeti burada toplandı.

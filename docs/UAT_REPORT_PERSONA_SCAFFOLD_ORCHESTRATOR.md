# UAT Raporu: Persona Factory Scaffold — Orchestrator ile Simülasyon

**Tarih:** 2026-02-14  
**Amaç:** Persona Factory Scaffold konusunu Orchestrator’a “konu” olarak verip pipeline’ı (builder → critic → closer) çalıştırmak; böylece hem konuyu işlemesini hem de UAT olarak sistemi test etmek.

---

## 1. Ne yapıldı?

### 1.1 Girdi

- **Prompt dosyası:** `docs/UAT_PROMPT_PERSONA_SCAFFOLD.md`  
  İçerik: Persona Factory’nin L1/L2/L3 paket yapısı, 6 dosya kuralı, Persona Steward ve mevcut Orchestrator ile entegrasyon ihtiyacı tanımlandı. Görev olarak şunlar istendi:
  1. Scaffold v0 klasör/şablon tasarımı  
  2. Orchestrator entegrasyonu (persona → agent eşlemesi)  
  3. Riskler ve tek P0 lint kuralı  
  4. 5–7 maddelik uygulama checklist’i  

- **Komut:**  
  ```bash
  .venv/bin/python scripts/chain_runner.py \
    --file docs/UAT_PROMPT_PERSONA_SCAFFOLD.md \
    --save-to docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN.md
  ```
- **Pipeline:** Varsayılan `builder → critic → closer`; critic aşamasında **dynamic critic selection** ve **multi-critic consensus** kullanıldı.

### 1.2 Beklenen davranış

- Builder: Persona scaffold tasarımı (klasör yapısı, 6 dosya, entegrasyon önerisi)  
- Critic(lar): Tasarım incelemesi (eksikler, riskler, iyileştirmeler)  
- Refinement: Kritik konular varsa builder-v2 → critic-v2  
- Closer: Özet + aksiyon listesi  

---

## 2. Sonuç özeti

| Aşama | Durum | Not |
|-------|--------|-----|
| **Builder** | ❌ Hata | Gemini rate limit (429, quota exceeded) |
| **Performance-critic** | ❌ Hata | Anthropic API key yok |
| **Code-quality-critic** | ✅ Başarılı | Fallback: GPT-4o-mini → Gemini 2.5 Flash; ~5.7K token cevap |
| **Multi-critic consensus** | ✅ Çalıştı | 2 critic’ten biri boş, code-quality çıktısı kullanıldı |
| **Refinement** | ⚠️ Kısmen | “Critical issues” tetiklendi; builder-v2 0 token (muhtemelen aynı rate limit); convergence: no progress |
| **Closer** | ❌ Hata | Tüm provider’lar başarısız (rate limit / key) |
| **Çıktı dosyası** | ✅ Yazıldı | `docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN.md` |

**Exit code:** 1 (en az bir aşama hata verdi).

---

## 3. Çalışan kısımlar (UAT açısından)

### 3.1 Akış ve özellikler

- **Chain başlatıldı:** Prompt dosyadan okundu, API key kaynağı gösterildi (environment).  
- **Dynamic critic selection:** Sadece **performance-critic** ve **code-quality-critic** seçildi; **security-critic** “not relevant” (keyword) nedeniyle atlandı.  
- **Fallback:** Code-quality-critic için OpenAI key yok → Gemini 2.5 Flash’a geçildi; cevap alındı.  
- **Refinement tetiklenmesi:** Critic çıktısında “critical” sayıldığı için multi-iteration refinement devreye girdi.  
- **Çıktı raporu:** Tüm aşamalar (başarılı ve hatalı) `--save-to` ile tek Markdown dosyasına yazıldı.

### 3.2 Anlamlı çıktı: Code-quality-critic

Critic, **prompt’taki “Persona Factory Scaffold” tasarımını** (henüz kod yok) inceleyip şu tür çıktılar üretti:

- **SRP:** `persona_tools.py` içinde “tools” ve “memory policy” ayrılmalı; `persona_audit.py` içinde “audit” ve “fail-safes” ayrılmalı.  
- **DIP/Coupling:** PersonaLoader’ın doğrudan Orchestrator agent config’ine bağlanması yerine `IAgentConfigBuilder` gibi bir arayüz önerildi.  
- **Entegrasyon:** Prompt’ta istenen “concrete option” için: **`persona_id` in `agents.yaml`** + **PersonaLoader’ın agent config üretmesi** önerildi; örnek YAML ve `PersonaLoader` pseudocode’u verildi.  
- **6 dosya isimleri:** `persona_profile.yaml`, `persona_tools.py`, `persona_memory.yaml`, `persona_contracts.py`, `persona_permissions.yaml`, `persona_safeguards.py` (scaffold’daki isimlerle kısmen uyumlu, L3 audit+safeguards ayrımı net).

Yani Orchestrator, “Persona Factory” konusunu **gerçekten konu olarak işledi** ve critic aşamasında **tasarım seviyesinde** anlamlı, uygulanabilir öneriler üretti.

---

## 4. Hatalar ve nedenler

| Hata | Olası neden |
|------|----------------|
| Builder / Closer: “All API providers failed” | Gemini 2.5 Pro rate limit (free tier quota); fallback’lar da key/limit nedeniyle başarısız. |
| Performance-critic: “Missing API key for provider anthropic” | Ortamda Anthropic key yok; critic bu provider’a atanmış. |
| Builder-v2: 0 token | Refinement sırasında aynı rate limit veya boş cevap. |
| Embedding: Permission denied (Hugging Face cache) | Bellek/kayıt aşamasında embedding model indirme/cache dizini izni; chain’in ana akışını durdurmadı. |

**Sonuç:** Hatalar **ortam/konfigürasyon** (API key, quota, cache izni) kaynaklı; Orchestrator’ın chain mantığı, dosya okuma, dynamic selection, refinement tetikleme ve rapor yazma davranışları beklenen şekilde çalıştı.

---

## 5. UAT değerlendirmesi

### 5.1 Test edilenler

- Prompt’un **dosyadan** verilmesi  
- **builder → critic → closer** sırası ve aşamaların sırayla çalışması  
- **Dynamic critic selection** (keyword tabanlı)  
- **Multi-critic consensus** (2 critic, biri boş)  
- **Fallback** (OpenAI → Gemini)  
- **Refinement** tetiklenmesi (critical issues)  
- **--save-to** ile tam raporun yazılması  

### 5.2 Beklenen vs gözlenen

| Beklenti | Gözlenen |
|----------|----------|
| Builder tasarım üretir | Ortam hatası (rate limit) nedeniyle üretemedi. |
| Critic tasarımı inceler | Code-quality-critic tasarımı inceledi, SRP/DIP ve entegrasyon önerileri verdi. |
| Closer özet çıkarır | Ortam hatası nedeniyle çalışmadı. |
| Çıktı dosyaya yazılır | Yazıldı; tüm aşamalar (başarılı/hata) raporlandı. |

### 5.3 Kısa sonuç

- **Orchestrator’ı “Persona Factory” konusuyla konu olarak vermek** doğru şekilde yapıldı; prompt dosyası ve chain komutu uygun.  
- **Pipeline ve özellikler** (dynamic critics, fallback, refinement, save-to) tasarlandığı gibi çalıştı.  
- **Anlamlı içerik** en az bir aşamadan (code-quality-critic) geldi; tasarım incelemesi ve entegrasyon önerisi kullanılabilir.  
- **Tam UAT (builder + critic + closer hepsi başarılı)** için: birden fazla provider’da geçerli API key ve yeterli quota (ve gerekirse mock mode) ile tekrarlanmalı.

---

## 6. Tekrarlanabilir UAT için öneriler

1. **Çoklu provider:** En az 2 provider (örn. OpenAI + Anthropic veya OpenAI + Google) key’li olsun; birinde limit/quota olsa bile fallback ile chain tamamlanabilsin.  
2. **Mock mode:** Gerçek API çağrısı olmadan akışı doğrulamak için:  
   `LLM_MOCK=1 .venv/bin/python scripts/chain_runner.py --file docs/UAT_PROMPT_PERSONA_SCAFFOLD.md --save-to docs/UAT_OUTPUT_MOCK.md`  
   Builder/critic/closer çıktıları mock cevaplar olur ama sıra, dosya okuma ve rapor yazma aynı kalır.  
3. **Aynı promptla tekrar:** Quota/key sorunları giderildikten sonra aynı komut tekrar çalıştırılıp builder + closer çıktıları da alınabilir; mevcut critic çıktısıyla birlikte tam bir “Persona Scaffold tasarım + inceleme + özet” seti elde edilir.

---

## 7. İlgili dosyalar

- **Girdi prompt:** `docs/UAT_PROMPT_PERSONA_SCAFFOLD.md`  
- **Chain çıktısı (ham rapor):** `docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN.md`  
- **Scaffold analizi:** `docs/PERSONA_FACTORY_SCAFFOLD_ANALIZ.md`  

Bu UAT, Persona Factory’yi “Orchestrator’a konu olarak verme” ve pipeline’ı gerçek bir tasarım sorusuyla sınamak için kullanıldı; sistem akışı ve critic çıktısı beklentilerle uyumlu.

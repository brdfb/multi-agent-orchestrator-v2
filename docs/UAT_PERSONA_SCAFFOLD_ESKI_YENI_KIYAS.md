# Persona Scaffold UAT: Eski vs Yeni Kıyaslama

Aynı senaryo (`UAT_PROMPT_PERSONA_SCAFFOLD.md`) iki kez çalıştırıldı:
- **Eski:** Plan öncesi (orijinal closer/critic davranışı) → `UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN.md`
- **Yeni:** Plan sonrası (Tier 1 modeller, Closer gatekeeper, Critic rubrik + Proof of Review) → `UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN_V2_AFTER_PLAN.md`

Bu dokümanda yapı, süre, Closer kararı ve kalite farkları özetleniyor.

---

## 1. Sayısal özet

| Metrik | Eski (plan öncesi) | Yeni (plan sonrası) |
|--------|---------------------|----------------------|
| **Toplam stage** | 10 | 12 |
| **Toplam süre** | 430,7 s | 573,7 s |
| **Toplam token** | 34 537 | 50 709 |
| **Refinement döngüsü** | 2 (Builder→Critic iki kez) | 3 (max cap; Builder→Critic üç kez) |
| **Closer modeli** | openai/gpt-4o-mini (Gemini rate limit fallback) | anthropic/claude-sonnet-4-5 |
| **Closer çıktı türü** | Synthesis (özet + action items) | Gatekeeper (VERDICT + SPECIFIC_FAILURE_POINT) |

---

## 2. Closer davranışı

### Eski (plan öncesi)
- **Rol:** Sonucu özetleyen, “düzeltilmiş yaklaşım” ve aksiyon maddeleri üreten **synthesis**.
- **Açık karar yok:** ACCEPT/REJECT yok; “CORRECTED APPROACH”, “KEY DECISIONS”, “ACTION ITEMS”, “RISKS MITIGATED” ile bitiyor.
- **Model:** gpt-4o-mini (Closer için Gemini quota hatası sonrası fallback).
- **Sonuç:** Chain “başarıyla bitti” gibi görünüyor ama rubric’e göre açık bir kabul/red yok; ayrıca eski analizde belirtilen tutarsızlıklar (manifest vs metadata, tests vs validation) Closer tarafından red gerekçesi olarak sayılmadı.

### Yeni (plan sonrası)
- **Rol:** Invariant’lara ve rubric’e göre **gatekeeper**: sadece ACCEPT veya REJECT.
- **Karar:** `# VERDICT: REJECTED`
- **Gerekçe:** `RUBRIC_ITEM_FAILED: 1 (Does not satisfy explicit constraints from original request)`
- **SPECIFIC_FAILURE_POINT:** “**Exactly 6 files**” kuralı ihlal edilmiş:
  - İlk iterasyonlarda 6 dosya (MANIFEST, L1_TONE, L2_TOOLS, L2_MEMORY, L3_PERMISSIONS, L3_AUDIT) doğruydu.
  - Son Builder çıktısında pack başına 7+ dosya (persona.yaml, system_prompt.md, tools.yaml, … README.md; bir yerde TESTS.py, CHANGELOG.md ile 8 dosya) önerilmiş.
- **Model:** claude-sonnet-4-5 (Tier 1, planla uyumlu).
- **Sonuç:** Hatalı çıktı açıkça reddedildi; Builder’a “pack’te tam 6 dosya” için net geri bildirim verildi.

**Çıkarım:** Yeni Closer, orijinal istekteki “exactly 6 files” gibi net kısıtları yakalayıp REJECT ve SPECIFIC_FAILURE_POINT ile raporluyor; eski Closer ise sentez üretip açık red üretmiyordu.

---

## 3. Refinement ve critic akışı

### Eski
- Builder → Performance / Security / Code-quality critic → Multi-critic consensus → **Builder (S6)** → **Critic (S7)** → **Builder (S8)** → **Critic (S9)** → Closer (S10).
- 2 refinement turu; Critic her seferinde critical issue buldu, Builder revize etti.

### Yeni
- Builder → Security / Code-quality / Performance critic → Multi-critic → **Builder (S6)** → **Critic (S7)** → **Builder (S8)** → **Critic (S9)** → **Builder (S10)** → **Critic (S11)** → Closer (S12).
- 3 refinement turu (plan’daki `MAX_REFINEMENT_ITERATIONS = 3` ile sınırlı).
- Her turda critic’ler critical issue buldu; Builder revize etti ama son iterasyonda hâlâ “6 dosya” kuralı ihlal edildiği için Closer reddetti.

**Çıkarım:** Yeni akışta refinement sayısı cap’li (sonsuz döngü yok) ve Closer, invariant ihlalini gerekçe göstererek reddediyor.

---

## 4. Builder ve scaffold yapısı (kısa)

- **Eski:** İlk Builder (S1) 6 dosyayı net tanımladı (manifest, l1_tone, l2_tools, l3_permissions, tests, README). Refinement’da isimler ve dosya seti kaydı (metadata.yaml, validation.yaml, sonra Closer çıktısında metadata.json, validation.yaml).
- **Yeni:** İlk Builder (S1) 6 dosya: MANIFEST.yaml, L1_TONE.md, L2_TOOLS.yaml, L2_MEMORY.yaml, L3_PERMISSIONS.yaml, L3_AUDIT.yaml. Refinement’lar boyunca dosya listesi ve isimleri değişti; son Builder çıktısında 7+ (veya 8) dosya önerildiği için Closer “exactly 6 files” ihlalini tespit etti.

Her iki tarafta da “6 dosya” prompt’ta açık; yeni pipeline bu kısıtı Closer seviyesinde kontrol ediyor.

---

## 5. Critic sırası ve modeller

- **Eski:** Stage 2 Performance, 3 Security, 4 Code-quality → Multi-critic (S5).
- **Yeni:** Stage 2 Security, 3 Code-quality, 4 Performance → Multi-critic (S5).

Sıra farkı dinamik critic seçiminden kaynaklanıyor; her iki tarafta da aynı üç critic (security, performance, code-quality) çalışıyor. Plan sonrası critic prompt’larında rubrik + Proof of Review kullanılıyor.

---

## 6. Özet tablo: Ne değişti?

| Konu | Eski | Yeni |
|------|------|------|
| Closer kararı | Örtük (synthesis, “başarılı” hissi) | Açık **REJECT** + SPECIFIC_FAILURE_POINT |
| 6-dosya kuralı | Closer tarafından red gerekçesi yapılmadı | İhlal tespit edilip red gerekçesi yazıldı |
| Closer modeli | gpt-4o-mini (fallback) | claude-sonnet-4-5 (Tier 1) |
| Refinement üst sınırı | 2 tur (sabit değil, akışa bağlı) | 3 tur (MAX_REFINEMENT_ITERATIONS) |
| Invariant/rubric kontrolü | Yok | Var (orijinal istek + rubric) |

---

## 7. Sonuç

- **Eski çalıştırma:** Chain “tamamlandı” ve Closer özet + action items üretti; ancak analiz dokümanındaki tutarsızlıklar (manifest/metadata, tests/validation, dosya sayısı) Closer tarafından red sebebi olarak kullanılmadı.
- **Yeni çalıştırma:** Aynı senaryoda Closer, orijinal istekteki “exactly 6 files” kısıtını kontrol etti, ihlali tespit etti ve **REJECT** + net SPECIFIC_FAILURE_POINT ile raporladı. Refinement 3 turla sınırlı kaldı.

Plan sonrası değişiklikler (Tier 1 Closer, gatekeeper prompt, invariants anchor, rubrik + Proof of Review, refinement cap) hedeflenen davranışı getiriyor: kalite kapısı net, red gerekçesi okunabilir ve tekrarlanabilir.

---

**Dosya referansları**
- Eski çıktı: `docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN.md`
- Yeni çıktı: `docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN_V2_AFTER_PLAN.md`
- İlk UAT analizi: `docs/UAT_PERSONA_SCAFFOLD_ANALIZ.md`

# Persona Factory Scaffold — Mantıklı mı? Analiz

Bu dokümanda önerilen **persona factory scaffold** (tek şablon + tek süreç + Persona Steward) yaklaşımının mantıklı olup olmadığı, ne zaman işe yarayıp ne zaman aşırı olacağı ve mevcut Orchestrator repo’su ile ilişkisi özetleniyor.

---

## 1. Özet cevap: Mantıklı mı?

**Evet, koşullu.** Aşağıdaki koşullar sağlanıyorsa **mantıklı ve değerli**:

| Koşul | Açıklama |
|-------|----------|
| **Birden fazla domain persona** | En az 3–5 farklı rol (FinOps, CFO-asistan, onay katmanı, raporlama vb.) planlanıyorsa. Tek persona için scaffold ağır kalır. |
| **Governance / uyum ihtiyacı** | RBAC, onay kapıları, audit, PII/limit kuralları gerekiyorsa. “Sadece sohbet” değil, “yetki + denetim” varsa. |
| **Aynı kalıptan üretim** | Yeni persona eklemek “form doldur + aynı 6 dosyayı üret” olacaksa; her persona farklı yapıda olmayacaksa. |
| **Tek kaynak (persona_pack.yaml)** | Dağılmayı önlemek için tek source of truth kabul ediliyorsa. |

Bu koşullar yoksa (tek rol, governance yok, “deneysel” kullanım) scaffold **overkill** olur; basit bir `agents.yaml` + birkaç prompt yeter.

---

## 2. Mevcut repo ile ilişki

### Orchestrator’daki “agent” vs önerilen “persona”

| | Mevcut (`config/agents.yaml`) | Önerilen (persona pack) |
|--|-------------------------------|--------------------------|
| **Amaç** | Pipeline rolü: tasarla → incele → özetle | Domain rolü: FinOps, CFO-asistan, onay, raporlama |
| **Kapsam** | L1 benzeri: prompt, model, token, bellek | L1 + L2 + L3: ton + araçlar/şema + yetki/onay/audit |
| **Governance** | Yok (trusted network, log-only) | Var: RBAC, limit, approval gate, audit schema |
| **Kullanım** | `mao`, `mao-chain`, API `/ask`, `/chain` | Henüz tanımlı değil (yeni katman) |

**Sonuç:** Önerilen scaffold **mevcut agent sisteminin yerine geçmez**; **üzerine inşa edilebilecek bir katman** olarak düşünülmeli. Yani:

- **Mevcut:** builder / critic / closer → “nasıl cevap üretilir” (orchestration).
- **Persona pack:** “Kim, hangi yetkiyle, hangi araçlarla, hangi denetimle çalışır?” (domain + governance).

İkisi birlikte kullanılabilir: örn. “CFO-asistan persona” bir **agent gibi** çalışır ama tanımı persona pack’ten (L1/L2/L3) gelir.

---

## 3. Ne zaman mantıklı?

### Mantıklı olduğu durumlar

1. **CFO-AI / FinOps gibi alanlar**  
   Farklı roller (junior controller, onay veren, raporlama) ve net “yapabilir / yapamaz” sınırları varsa.

2. **Uyum ve denetim**  
   Audit, policy versiyonu, tool contract versiyonu, PII/limit kuralları gerekiyorsa. “Persona ekleye ekleye” dağılmayı önlemek için tek şablon + lint şart.

3. **Takım / süreç**  
   Persona’yı farklı kişiler ekleyecekse veya “Persona Steward” gibi tek rol (HR) süreci yönetecekse. Süreç şablonu (L3 → L2 → L1, registry, lint) kaosu azaltır.

4. **Versiyonlama ve traceability**  
   Hangi persona’nın hangi policy/tool/audit versiyonuyla çalıştığı kayıt altında olacaksa. `persona_pack.yaml` + `CHANGELOG.md` + registry tam bunun için.

### Mantıklı olmadığı / ertelebileceğin durumlar

1. **Tek persona, basit kullanım**  
   Sadece “bir asistan” varsa ve governance/onay/audit yoksa; tek YAML + tek prompt yeter, 6 dosyalık pack gereksiz.

2. **Henüz domain net değil**  
   Roller ve yetkiler sık değişiyorsa önce domain’i netleştirip sonra scaffold’a geçmek daha iyi.

3. **Sadece prototip**  
   “Önce çalışan bir şey çıkar” aşamasındaysan, scaffold’ı “v0” ile sadece iskelet olarak kurup içeriği sonra doldurmak mantıklı; tam detayı erteleyebilirsin.

---

## 4. Avantajlar ve riskler

### Avantajlar

- **Dağılmayı önler:** Tek şablon + 6 dosya kuralı + persona_pack.yaml = tek kaynak; “persona ekleye ekleye” spagetti azalır.
- **Sıra net:** L3 → L2 → L1 (yetki önce, ton en son) yanlış tasarımı azaltır.
- **Lint / gate:** P0/P1 kuralları otomasyonla uygulanabilir; tutarlılık korunur.
- **Persona Steward:** “Persona üreten persona” tek rol; süreç standardize olur, insanlar “nasıl ekliyoruz?” sorusuna tek cevap alır.
- **Uyum:** Policy/tool/audit versiyonları pack’te açık; denetim ve raporlama kolaylaşır.

### Riskler / dikkat

- **Erken karmaşıklık:** 1–2 persona ile başlarken 6 dosya + lint + steward fazla gelebilir. “Scaffold v0” ile iskelet kurup ilk persona’yı (örn. FIN_BASELINE_ASSISTANT_v1) minimal tutmak iyi olur.
- **Runtime entegrasyonu:** Scaffold şu an “tanım ve süreç”; runtime’da (Orchestrator’ın `agent_runtime`, API, CLI) persona pack’lerin nasıl yükleneceği, L2/L3’ün nasıl zorunlu kılınacağı ayrı tasarım konusu.
- **Çift yapı:** `config/agents.yaml` (mevcut) ile `personas/packs/` (yeni) birlikte yönetilmeli; “hangi istek hangi persona’ya gidecek?” eşlemesi net olmalı.

---

## 5. Bu repo’da nasıl konumlanır?

Üç makul seçenek:

| Seçenek | Açıklama | Ne zaman |
|--------|----------|----------|
| **A) Dokümantasyon / spec** | `personas/` sadece spec + şablon + örnek pack; runtime hâlâ `agents.yaml`. | Önce süreci ve standardı netleştirmek istiyorsan. |
| **B) Scaffold v0 + tek baseline pack** | `personas/_framework/` + `personas/packs/FIN_BASELINE_ASSISTANT_v1/` oluşturulur; runtime entegrasyonu sonra. | “İskelet hemen olsun, CFO-AI sonra genişler” diyorsan. |
| **C) v2 / Enterprise temeli** | Persona pack’ler, RBAC + audit roadmap’i ile birlikte v2’nin temeli yapılır. | Uzun vadede enterprise (RBAC, audit, multi-tenant) planlıyorsan. |

**Pratik öneri:** **B** — Scaffold v0’ı çıkar, tek baseline persona (FIN_BASELINE_ASSISTANT_v1) ile dene. Runtime’da önce “bu persona = şu agent” eşlemesi manuel bile olsa; lint + Persona Steward prompt’u ve süreç şablonu yerleşsin. İkinci persona’dan itibaren “aynı kalıptan paket” faydası görülür.

---

## 6. Lint ve Persona Steward hakkında

- **Lint (P0/P1):** Özellikle P0 (6 dosya, L3’te commit-class yasak, memory’de yasak alanlar, audit schema alanları) otomasyonla kontrol edilebilir. Başlangıçta basit bir script (örn. “tüm pack’lerde gerekli dosya var mı, persona_pack.yaml geçerli mi?”) bile yeterli; sonra P0/P1 kuralları eklenir.
- **Persona Steward:** `steward_persona.md` doğrudan “persona üreten/valid eden” rol için kullanılabilir (Cursor/Claude’da agent veya talimat olarak). Bu rolün **sadece persona üretim/validasyon** yapması, CFO işi yapmaması, spagettiyi önler.

---

## 7. Nihai öneri

- **Scaffold yaklaşımı mantıklı** — Özellikle birden fazla domain persona + governance + “tek kalıptan paket” hedefi varsa.
- **Mevcut repo ile çakışma yok** — Agent’lar orchestration katmanında kalır; persona pack’ler domain + governance katmanı olur; birlikte kullanılabilir.
- **Adım:** Scaffold v0 + tek baseline pack (FIN_BASELINE_ASSISTANT_v1) oluştur; süreç (registry → persona_pack.yaml → L3 → L2 → L1 → lint) ve Persona Steward’ı dokümante et. Runtime’ı tam entegre etmeden önce tanım ve süreç otursun; 2. persona’dan itibaren “paket” faydası netleşir.

İstersen bir sonraki adımda **Scaffold v0** (klasör yapısı + template’ler + `persona_registry.yaml` + `persona_lint_rules.md` + `steward_persona.md`) ve **FIN_BASELINE_ASSISTANT_v1** için 6 dosyanın iskeletini tek tek çıkaracak bir planı maddeler halinde yazabilirim.

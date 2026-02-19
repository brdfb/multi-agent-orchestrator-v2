# Toparlama / Commit Planı

`git status` çıktısına göre mantıksal commit grupları. Sırayla veya ihtiyaca göre kullan.

---

## 1. Çekirdek kod (Orchestrator plan değişiklikleri)

**Amaç:** Tier 1 modeller, Closer gatekeeper, Critic rubrik, refinement cap.

```
config/agents.yaml
core/agent_runtime.py
```

**Önerilen mesaj:**  
`feat: Tier 1 Closer gatekeeper, critic rubric, refinement cap (MAX_REFINEMENT_ITERATIONS=3)`

---

## 2. Dokümantasyon (README / env örneği)

```
README.md
.env.example
```

**Önerilen mesaj:**  
`docs: update README and .env.example`

---

## 3. Persona Scaffold UAT – prompt ve çıktılar

```
docs/UAT_PROMPT_PERSONA_SCAFFOLD.md
docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN.md
docs/UAT_OUTPUT_PERSONA_SCAFFOLD_CHAIN_V2_AFTER_PLAN.md
docs/UAT_PERSONA_SCAFFOLD_ANALIZ.md
docs/UAT_PERSONA_SCAFFOLD_ESKI_YENI_KIYAS.md
docs/UAT_REPORT_PERSONA_SCAFFOLD_ORCHESTRATOR.md
docs/PERSONA_FACTORY_SCAFFOLD_ANALIZ.md
```

**Not:** Eski Türkçe isimli dosya `UAT_PERSONA_SCAFFOLD_ESKİ_YENİ_KİYAS.md` → `UAT_PERSONA_SCAFFOLD_ESKI_YENI_KIYAS.md` olarak ASCII’ye çevrildi; artık sadece ASCII dosyayı ekle.

**Önerilen mesaj:**  
`docs: Persona Scaffold UAT prompt, chain outputs, analiz ve eski-yeni kıyas`

---

## 4. QA ve kullanım dokümanları

```
docs/qa/
docs/KULLANIM_DURUMLARI_VE_SENARYOLAR.md
docs/KULLANIM_ORNEGI_TAM_AKIS.md
```

**Önerilen mesaj:**  
`docs: QA (Executive Auditor) ve kullanım senaryoları`

---

## 5. Test

```
tests/test_two_topics_no_mix.py
```

**Önerilen mesaj:**  
`test: two topics no mix`  
(veya testin amacına uygun kısa bir mesaj)

---

## 6. Kişisel / yerel (commit etmeyebilirsin)

- **`.claude/settings.local.json`** — Yerel ayar; genelde commit edilmez. İsteyerek “defaults” için ekleyebilirsin.
- **`.claude/agents/`** — Agent tanımları; ekip paylaşacaksa bir commit, sadece senin kullanımınsa ignore veya ayrı branch.

---

## Hızlı komutlar (örnek)

```bash
# 1. Çekirdek
git add config/agents.yaml core/agent_runtime.py
git commit -m "feat: Tier 1 Closer gatekeeper, critic rubric, refinement cap"

# 2. README / env
git add README.md .env.example
git commit -m "docs: update README and .env.example"

# 3. UAT Persona Scaffold (ASCII kıyas dosyası; Türkçe isimli eski dosyayı silindiği için artık sadece bu)
git add docs/UAT_*.md docs/PERSONA_FACTORY_SCAFFOLD_ANALIZ.md
git commit -m "docs: Persona Scaffold UAT prompt, outputs, analiz, eski-yeni kıyas"

# 4. QA + kullanım
git add docs/qa/ docs/KULLANIM_*.md
git commit -m "docs: QA and usage scenarios"

# 5. Test
git add tests/test_two_topics_no_mix.py
git commit -m "test: two topics no mix"
```

---

**Türkçe karakterli dosya:** Kıyas dosyası `UAT_PERSONA_SCAFFOLD_ESKI_YENI_KIYAS.md` (ASCII) olarak kopyalanıp eski dosya silindi. (Eski dosya zaten ASCII isimli kopyaya tasinip silindi.)

Böylece `git status` artık escape’li isim göstermez; tek kıyas dokümanı ASCII isimle takip edilir.

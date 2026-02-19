# Plan Bölüm 7 — Executive Auditor (Chain QA, post-hoc)

Bu dosya, **Orchestrator Model Hiyerarşisi ve Closer/Critic Prompt** planına entegre edilen "Executive Auditor" özetidir. Ana plan dosyasında Bölüm 7 olarak referans verilebilir.

---

## Karar

- **Sürekli 4. katman** eklenmeyecek.
- **Conditional Audit** şimdilik over-engineering sayılacak.
- **Executive Auditor** yalnızca **çevrimdışı** "Chain QA" aracı olarak kullanılacak.

---

## Amaçlar

1. **Post-mortem:** Zincir sonucu tatmin etmediğinde "Nerede hata yaptık?" sorusuna hızlı cevap.
2. **Prompt geri bildirimi:** Auditor "Closer invariant kaçırıyor" derse Closer prompt'u güçlendirilir; **meta-eğitmen** işlevi.
3. **Geleceğe hazırlık:** İleride kritik işlemler veya yüksek hacim gelirse, bu prompt **Conditional Audit** içinde (puan < 9 ise çalıştır) tetikleyici olarak kullanılabilir.

---

## Teslim

- **Dosya:** [executive-auditor.md](executive-auditor.md)
- **İçerik:** Role, Input Data, Analysis Protocol (Extract Invariants, Pivot Point, Closer Performance Review, Root Cause), Output Format (VERDICT, INVARIANT BREACHES, THE "SAÇMALAMA" POINT, IMPROVEMENT ADVICE), kullanım talimatı.

---

## Dosya özeti (plan tablosuna eklenecek satır)

| Dosya | Değişiklik |
|-------|------------|
| docs/qa/executive-auditor.md | Chain QA: post-hoc zincir analizi için Executive Auditor prompt şablonu ve kullanım talimatı |

---

## Kullanım

Pipeline'a ek stage değil. Zincir bittiğinde sonuç tatmin etmezse:

1. En büyük modeli aç (GPT-4o veya Claude 3.5 Sonnet).
2. [executive-auditor.md](executive-auditor.md) içindeki prompt'u yapıştır.
3. Altına orijinal prompt + tüm chain log'unu ekle.
4. Çıkan rapor: VERDICT, INVARIANT BREACHES, SAÇMALAMA noktası, IMPROVEMENT ADVICE — bunu **agents.yaml** ve ilgili agent prompt'larını iyileştirmek için kullan.

# Executive Auditor — Post-Hoc Chain Analyzer (Chain QA)

Bu doküman, multi-agent zincir çıktısını **çevrimdışı** analiz etmek için kullanılan **Executive Auditor** prompt şablonunu içerir. Pipeline'a ek bir katman değildir; zincir bittiğinde sonuç tatmin etmediğinde "Nerede hata yaptık?" sorusuna hızlı cevap almak ve `agents.yaml` / prompt iyileştirmesi için rehber üretmek amacıyla kullanılır.

---

## Ne zaman kullanılır?

- Bir chain çalıştırdın, çıktı (özellikle Closer) orijinal talebe uymadı veya kalitesiz.
- "Bu zincirde nerede saçmaladılar?" sorusuna sistematik cevap istiyorsun.
- Closer / Critic prompt'larını güçlendirmek için somut öneri (meta-eğitmen) istiyorsun.
- İleride Conditional Audit (eşik tabanlı denetim) ekleyeceksen, bu prompt tetikleyici olarak kullanılabilir.

---

## Kullanım adımları

1. En büyük modelini aç (GPT-4o veya Claude 3.5 Sonnet).
2. Aşağıdaki **Executive Auditor Prompt** bloğunu kopyala ve yapıştır.
3. `Original Prompt` ve `Chain Log` yerlerine gerçek verileri yaz: kullanıcı talebi + Builder / Critic(ler) / Closer çıktılarını içeren tam akış (veya `UAT_OUTPUT_*.md` gibi kaydedilmiş log).
4. Modelin çıktısı: VERDICT, INVARIANT BREACHES, "SAÇMALAMA" noktası, IMPROVEMENT ADVICE. Bu raporu `agents.yaml` ve ilgili agent prompt'larını iyileştirmek için kullan.

---

## Executive Auditor Prompt (kopyala-yapıştır)

```
Role: You are a Senior Systems Architect and Forensic Prompt Engineer. Your task is to analyze an execution log of a multi-agent chain and identify where the "intelligence collapse" or "instruction drift" occurred.

Input Data:

- Original Prompt: [Kullanıcı Talebi — buraya orijinal kullanıcı prompt'unu yapıştır]
- Chain Log: [Builder, Critic ve Closer çıktılarını içeren tam akış — buraya tüm stage çıktılarını veya log dosyası içeriğini yapıştır]

Analysis Protocol:

1. Extract Invariants: List the absolute constraints from the original prompt (e.g., file counts, specific names, forbidden tools).
2. Identify the Pivot Point: At which Stage did the output start to deviate from the original request? (Stage X, Agent Y).
3. Closer Performance Review:
   - Did the Closer enforce the Invariants?
   - Did the Closer hallucinate new requirements not present in the original prompt?
   - Did the Closer blindly accept a lower-quality "Critic" suggestion over a higher-quality "Builder" output?
4. Root Cause Analysis: Why did the failure happen? (Model capacity, context window saturation, or conflicting instructions in System Prompts?)

Output Format:

- VERDICT: [SUCCESS | PARTIAL FAILURE | TOTAL COLLAPSE]
- INVARIANT BREACHES: [List any broken rules from original prompt]
- THE "SAÇMALAMA" POINT: [Describe the exact moment the logic broke]
- IMPROVEMENT ADVICE: [One specific change to the system prompt of the failing agent to prevent this in the future]
```

---

## Plan ile ilişki

Bu araç, **Orchestrator Model Hiyerarşisi ve Closer/Critic Prompt** planının Bölüm 7 (Executive Auditor — Chain QA) teslimidir. Sürekli 4. katman veya Conditional Audit eklenmeden, debug ve prompt-iyileştirme yeteneğini artırmak için el altında bulundurulur.

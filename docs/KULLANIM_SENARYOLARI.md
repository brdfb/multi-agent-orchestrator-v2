# Gerçek Dünya Kullanım Senaryoları

Bu dokümanda, Multi-Agent Orchestrator'ın kod yazmak dışında nasıl kullanılabileceğine
dair somut senaryolar yer almaktadır.

---

## Senaryo 1: Müşteri Destek Otomasyonu (E-ticaret)

### Problem
Bir online mağazaya günde 50-100 müşteri maili geliyor.
Hepsini okuyup cevaplamak zaman ve para alıyor.

### Çözüm

```
Müşteri mail atar
    → Mail sunucusu maili okur
    → HTTP POST /ask → Orchestrator
    → Claude cevabı yazar
    → Mail otomatik gönderilir
```

### Örnek Durumlar

| Müşteri Sorusu | Sistem Ne Yapar |
|---|---|
| "Siparişim nerede, 3 gündür gelmedi" | Kargo API'sine bakar, durumu bildirir |
| "İade etmek istiyorum" | İade politikasına göre adımları açıklar |
| "42 bedene uyar mı, 178 boyundayım" | Beden tablosuna göre öneri yapar |

### Sonuç
Günde 87 mail geldi → 81'i otomatik cevaplandı → Sen sadece 6 istisnaya bakıyorsun.

---

## Senaryo 2: İnsan Kaynakları — CV Tarama

### Problem
Pozisyon için 200 CV geldi, 5 kişi alınacak.
Tüm CV'leri elle okumak günler alıyor.

### Çözüm

```
HR sistemi yeni CV yükler
    → HTTP POST /chain → Orchestrator
    → builder:  CV'yi pozisyon kriterlerine göre analiz eder
    → critic:   Eksikleri, tutarsızlıkları işaretler
    → closer:   "Mülakata çağır / Reddet / Beklet" kararı + gerekçe verir
```

### Sonuç
Sabah geliyorsun → 200 CV yerine sıralanmış 12 aday listesi seni bekliyor.
Her adayın yanında neden seçildiği yazıyor.

---

## Neden Claude Code CLI Yetmiyor?

Bu senaryolarda ortak bir ihtiyaç var:

- **7/24 çalışma** — Sen klavye başında olmadan çalışması gerekiyor
- **Programatik erişim** — Başka bir uygulama veya script LLM'e HTTP ile bağlanıyor
- **Otomasyon** — İnsan müdahalesi olmadan tetikleniyor

Claude Code bunların hiçbirini karşılamıyor. İnteraktif bir terminal aracı.
Bu orchestrator ise bir **servis** — her zaman ayakta, her yerden erişilebilir.

---

## Kullanım Karar Tablosu

| Durum | Kullan |
|-------|--------|
| Kendi bilgisayarında kod yazıyorsun | Claude Code |
| Bir uygulama LLM'e HTTP ile bağlanacak | Bu repo |
| Gece otomatik çalışan script | Bu repo |
| Ekip olarak merkezi LLM kullanacaksınız | Bu repo |
| 7/24 müşteri/kullanıcı isteklerini karşılayacaksın | Bu repo |

---

*Son güncelleme: 2026-02-17*

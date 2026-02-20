# Ragip Aga E2E Senaryo Testi — Microsoft NCE Lisans Uyusmazligi

## OYUNCULAR

| Rol | Sirket | Detay |
|-----|--------|-------|
| **Biz** | Orka Teknoloji Ltd. Sti. | 45 kisilik IT firma, perakende sektore yazilim + bulut cozum satiyor |
| **Karsi taraf** | Yildiz Dagitim Tic. A.S. | Microsoft CSP Indirect Provider (distributor), MPN ID: 7891234 |
| **Arka plan** | Microsoft Turkiye | NCE kurallarini koyan, fiyatlari belirleyen, lisanslari saglayan |

---

## ARKA PLAN: Microsoft NCE Nedir?

**NCE (New Commerce Experience)** — Microsoft'un 2022'den itibaren uyguladigi yeni lisans modeli:

- **Yillik taahhut**: 12 ay kilitli. Donem icinde seat (lisans adedi) azaltilamaz, iptal edilemez.
- **7 gun iptal penceresi**: Yeni abonelik baslatildiktan sonra sadece 7 takvim gunu icinde iptal hakki var.
- **Aylik faturalamada +%5 prim**: Nisan 2025'ten itibaren, yillik taahhutlu aboneliklerde aylik odeme tercih edilirse +%5 ek ucret.
- **Aylik taahhütsüz: +%20 prim**: Esneklik icin %20 daha pahali.
- **USD bazli fiyat**: Microsoft liste fiyati USD cinsi. Distributor TL'ye cevirip faturalar.
- **Distributor marji**: Liste fiyat uzerine %5-15 arasi hizmet bedeli eklenir.

**Turkiye'deki zincir:**
```
Microsoft --> Yildiz Dagitim (Indirect Provider) --> Orka Teknoloji (Bayi/Son Kullanici)
                    |                                       |
              Lisansi temin eder,                    Lisansi kullanir,
              TL fatura keser,                       60 gun vadeli oder
              teknik destek saglar
```

---

## SENARYO

### Kronoloji

| Tarih | Olay |
|-------|------|
| 01.04.2024 | CSP Bayi Sozlesmesi imzalandi. Vade: 60 gun, vade farki: %2,5/ay, mutabakat zorunlu. |
| 01.04.2025 | NCE yillik taahhut baslatildi: 150 M365 Business Premium + 20 M365 E3 + 30 Power BI Pro = 200 seat yillik, 10 Windows 365 aylik. |
| 01.04.2025 | **Sorun 1**: Dagitici 15 seat'i 3 hafta gec aktive etti (sozlesme m.7.1: 2 is gunu). |
| Nisan-Ekim 2025 | Odemeler duzenli yapildi. Iliskiler normal. |
| 01.11.2025 | Kasim donemi faturasi: YD-2026-001412, 228.340,50 TL. Vade: 31.12.2025. |
| 01.12.2025 | Aralik donemi faturasi: YD-2026-001523, 239.615,03 TL. Vade: 30.01.2026. |
| 01.12.2025 | **Sorun 2**: Aralik faturasinda kur 39,85 TL/USD uygulanmis. TCMB doviz alis kuru o gun 37,42 TL. Sozlesme m.3.3: "TCMB kuru uzerine %2'yi asan kur farki uygulanamaz." %2 sinir = 38,17 TL. Uygulanan 39,85 TL → **%6,5 fazla.** |
| 31.12.2025 | Kasim faturasi vadesi doldu. Orka nakit sikintisi yasadi, ODEMEDI. |
| 30.01.2026 | Aralik faturasi vadesi doldu. Orka hala ODEMEDI. Toplam geciken: 467.955,53 TL. |
| 05.02.2026 | **Sorun 3**: Yildiz Dagitim, HICBIR YAZILI BILDIRIM yapmadan, mutabakat almadan, dogrudan vade farki faturasi kesti: YD-2026-001847, 49.135,33 TL (KDV dahil). Ustelik %3,5/ay oranla — sozlesmede %2,5/ay yaziyor. |
| 05.02.2026 | **Sorun 4**: Vade farki KDV dahil toplam (467.955,53 TL) uzerinden hesaplanmis. Dogru hesaplama KDV haric matrah uzerinden olmali. |
| 10.02.2026 | Dagitici, yeni lisans siparislerini durdurdugunu sozlu bildirdi. |
| 15.02.2026 | 30 seat (150'den 120'ye) azimsanmak isteniyor ama NCE yillik taahhut → azaltma Nisan 2026 yenilemede mumkun. Simdi bedeli odenmek ZORUNDA. |
| **BUGUN** | **20.02.2026** — Orka Teknoloji durumu analiz etmek ve aksiyona gecmek istiyor. |

---

### Uyusmazlik Katmanlari (5 Sorun)

#### SORUN 1: Gec Aktivasyon (Gecmis — Tazminat Hakki)
- 15 seat, siparis onayindan **15 is gunu** sonra aktive edildi
- Sozlesme m.7.1: "2 is gunu icinde aktive eder"
- Sozlesme m.7.1.b: Geciken her is gunu icin lisans bedelinin %0,5'i cezai sart
- **Hesaplama:** 15 seat × $22/ay × (13 is gunu gecikme) × %0,5 = ?
- Bu cezai sart hicbir zaman talep edilmedi — simdi koz olarak kullanilabilir

#### SORUN 2: Kur Farki Manipulasyonu (Aralik Faturasi)
- Uygulanan kur: 39,85 TL/USD
- TCMB doviz alis kuru (01.12.2025): 37,42 TL
- Sozlesmedeki sinir: TCMB + %2 = 38,17 TL
- **Fark:** 39,85 - 38,17 = 1,68 TL/USD × 5.010,77 USD = **8.418,09 TL fazla faturalanmis**
- Bu fatura 8 is gunu icinde itiraz edilmedi (TTK m.21/2 suresi kacti MI?)
- Fatura tarihi 01.12.2025, 8 is gunu = ~11.12.2025. Simdiye kadar itiraz yok.

#### SORUN 3: Vade Farki Orani Hatasi
- Faturada: %3,5/ay
- Sozlesmede (m.5.1): %2,5/ay
- **Fark:** 1 puan/ay → yillik %12 ek maliyet
- Dogru hesap (sozlesme oranıyla): 467.955,53 × 2,5% × 75/30 = 29.247,22 TL (KDV haric)
- Faturadaki: 40.946,11 TL (KDV haric)
- **Fazla kesilen:** 11.698,89 TL

#### SORUN 4: Prosedur Ihlali (Yazili Bildirim + Mutabakat)
- Sozlesme m.5.2: Yazili bildirim + 15 gun ek sure ZORUNLU → yapilmadi
- Sozlesme m.5.3: Mutabakat olmadan fatura gecersiz → alinmadi
- **Sonuc:** Vade farki faturasi sozlesmeye gore tamamen GECERSIZ

#### SORUN 5: KDV Dahil Tutar Uzerinden Hesaplama
- Vade farki, KDV dahil toplam (467.955,53 TL) uzerinden hesaplanmis
- Dogru olan: KDV haric matrah uzerinden hesaplanmali
- KDV haric toplam: 467.955,53 / 1,20 = 389.962,94 TL
- **Fark:** KDV dahil vs haric → hesaplama bazinda ~%20 fazla

---

### Ek Komplikasyon: NCE Taahhut Tuzagi

- 200 seat yillik taahhut Nisan 2025'te basladi → Nisan 2026'ya kadar kilitli
- Gercekte 120 seat aktif kullaniliyor, 30 seat bos (calisanlar ayrildi)
- Aylik ~5.100 USD ($61.200/yil) odeniyor, gercek ihtiyac ~4.000 USD
- **Yillik israf:** ~$13.200 (~508.000 TL) kullanilmayan lisans icin
- NCE kurali geregi azaltma ancak Nisan 2026 yenilemede yapilabilir
- Bu durum **dagitici sorumluluğunda degil** (Microsoft NCE kurali) ama bilgilendirme yukümlülügü var mi?

---

### Orka Teknoloji'nin Mali Durumu

| Kalem | Tutar |
|-------|-------|
| Geciken 2 fatura (KDV dahil) | 467.955,53 TL |
| Vade farki faturasi (KDV dahil) | 49.135,33 TL |
| Toplam talep | 517.090,86 TL |
| Nakit mevcudu (tahmini) | ~350.000 TL |
| Aylik NCE lisans gideri | ~200.000 TL |
| Aylik diger giderler | ~400.000 TL |
| Aylik gelir | ~700.000 TL |

**Nakit sikintisi nedeni:** Buyuk bir proje odemesi 45 gun gecikti (musteri: kamu kurumu).

---

### Orka'nin Elindeki Kozlar (Tespit Edilmesi Gereken)

1. **Vade farki faturasi prosedur hatasi** — m.5.2 + m.5.3 ihlali → fatura gecersiz
2. **Oran hatasi** — %3,5 vs %2,5 → 11.698,89 TL fazla
3. **Kur manipulasyonu** — %6,5 fark vs sozlesme siniri %2 → 8.418,09 TL fazla (ama itiraz suresi gecmis olabilir)
4. **Gec aktivasyon cezai sarti** — 15 seat × 13 gun × %0,5 → karsi alacak olarak kullanilabilir
5. **KDV dahil hesaplama hatasi** — matrah hatasi
6. **NCE seat israfi** — dagitici bilgilendirme sorumluluğunu yerine getirdi mi?

### Orka'nin Zayif Yonleri

1. **Odeme yapilmadigi gercegi** — Gercekten 75 gun gecikme var
2. **Kur itiraz suresi** — TTK m.21/2 kapsaminda 8 is gunu gecmis olabilir
3. **Nakit yetersizligi** — Tam odeme yapacak nakit yok
4. **NCE taahhut** — Dagitici ile iliskiyi bozarsa baska distributore gecis zor (transfer sureci var)

---

## TEST DOSYALARI

| Dosya | Aciklama |
|-------|----------|
| `sozlesme_yildiz_dagitim.txt` | CSP Bayi Sozlesmesi (11 madde + EK-1 abonelik listesi) |
| `fatura_nce_lisans.txt` | Aralik 2025 NCE lisans faturasi (kur problemi iceren) |
| `fatura_vade_farki.txt` | Vade farki faturasi (3 hata iceren: oran, prosedur, matrah) |
| `cari_hesap_listesi.csv` | 6 firmali cari hesap listesi (Parasut formati) |

---

## 8 ADIMLI TEST PLANI (Sub-Agent Mimarisi v3)

**Mimari:** ragip-aga (orchestrator) → 3 sub-agent (ragip-hesap, ragip-arastirma, ragip-veri)

Her adimda ragip-aga orchestrator ilgili sub-agent'a Task tool ile yonlendirir.
Dogrudan skill cagirmak yerine dogal dil kullanilir.

### FAZ 1: VERI TOPLAMA (PARALEL)

#### ADIM 1: ragip-aga → ragip-veri → /ragip-firma
```
Karsi tarafi kaydet: Yildiz Dagitim Ticaret A.S., vergi no 4820137695, vade 60 gun, vade farki orani %2.5, risk notu yuksek
```

#### ADIM 2: ragip-aga → ragip-arastirma → /ragip-dis-veri
```
Yildiz Dagitim Ticaret A.S. hakkinda kamuya acik kaynaklardan bilgi topla. Vergi no: 4820137695
```

> **Not:** Adim 1 ve 2 PARALEL calistirilabilir (bagimsiz islemler)

### FAZ 2: ANALIZ (PARALEL)

#### ADIM 3: ragip-aga → ragip-hesap → /ragip-vade-farki
```
Vade farki hesapla: 389.963 TL anapara, aylik %2.5 oran, 75 gun gecikme
```
(Not: KDV haric matrah uzerinden, sozlesmedeki oranla)

#### ADIM 4: ragip-aga → ragip-arastirma → /ragip-analiz
```
Su dosyalari analiz et: tests/e2e_ragip_scenario/sozlesme_yildiz_dagitim.txt tests/e2e_ragip_scenario/fatura_nce_lisans.txt tests/e2e_ragip_scenario/fatura_vade_farki.txt
```

> **Not:** Adim 3 ve 4 PARALEL calistirilabilir (bagimsiz islemler)

### FAZ 3: STRATEJI (SIRALI — Faz 1+2 sonuclarini bekler)

#### ADIM 5: ragip-aga → ragip-arastirma → /ragip-strateji
```
Yildiz Dagitim (Microsoft CSP distributor) 2 aydir odenemyen NCE lisans faturalari icin 49.135 TL vade farki faturasi kesti. Sozlesmedeki oran %2.5 ama %3.5 uyguladi, yazili bildirim yapmadi, mutabakat almadi. Toplam borcumuz 517.000 TL, nakit mevcudumuz 350.000 TL. 200 seat yillik NCE taahhudumuz var Nisan 2026'ya kadar.
```

### FAZ 4: UYGULAMA (SIRALI)

#### ADIM 6: ragip-aga → ragip-arastirma → /ragip-ihtar
```
Fatura hatasi icin ihtar taslagi hazirla
```

#### ADIM 7: ragip-aga → ragip-veri → /ragip-gorev
```
Su gorevleri ekle:
1. Yildiz Dagitim vade farki faturasina 8 is gunu icinde yazili itiraz gonder (konu=Yildiz_NCE, oncelik=yuksek, son_tarih=2026-02-25)
2. Avukata sozlesme fatura ve kur hesabini gonder (konu=Yildiz_NCE, oncelik=yuksek, son_tarih=2026-02-24)
3. Gec aktivasyon cezai sart hesabi cikart - karsi alacak dosyasi (konu=Yildiz_NCE, oncelik=orta, son_tarih=2026-03-01)
4. NCE yenileme oncesi seat optimizasyonu plani hazirla - Nisan 2026 (konu=NCE_Yenileme, oncelik=orta, son_tarih=2026-03-15)
Sonra gorevleri listele.
```

#### ADIM 8: ragip-aga → ragip-veri → /ragip-import
```
Su CSV dosyasini ice aktar: tests/e2e_ragip_scenario/cari_hesap_listesi.csv
```

---

## HER ADIMDA KONTROL EDILECEKLER

| # | Kontrol Sorusu |
|---|----------------|
| 1 | Bash hesaplamalari matematiksel olarak dogru mu? |
| 2 | TCMB orani gercek veri mi (ragip_rates.py)? |
| 3 | Sozlesme maddeleri dogru alintilanip referans verildi mi? |
| 4 | Yasal referanslar dogru mu (TBK, TTK, IIK, 3095 s.K.)? |
| 5 | JSONL dosyalari atomic write ile yazildi mi? |
| 6 | "Avukata danisin" / "hukuki gorus degildir" disclaimer var mi? |
| 7 | WebSearch sadece kamuya acik kaynaklari taradi mi? |
| 8 | NCE kurallarini (taahhut, 7 gun iptal, seat azaltma) dogru anladi mi? |
| 9 | Kur farki hesabinda TCMB referansi kullanildi mi? |
| 10 | Doviz forward / ithalat maliyet hesaplari senaryoya uygun mu? |

---

## BEKLENEN CIKTILAR OZETI

Tum adimlar tamamlandiginda Ragip Aga'nin ortaya koymasi gereken tablo:

**Orka'nin gercek borcu (duzeltilmis):**
- 2 fatura KDV haric toplam: ~389.963 TL
- Dogru vade farki (%2,5 × 75 gun): ~24.373 TL
- Toplam gercek borc: ~414.336 TL (vs talep edilen 517.091 TL)
- **Fazla talep:** ~102.755 TL

**Muzakere pozisyonu:**
- Vade farki faturasi iptal edilmeli (prosedur hatasi)
- Kur farkinin duzeltilmesi talep edilmeli (~8.418 TL)
- Gec aktivasyon cezai sarti karsi alacak olarak one surulmeli
- Kalan gercek borca 3 taksitle odeme planı teklif edilmeli
- NCE yenileme (Nisan 2026) icin seat optimizasyonu planlanmali

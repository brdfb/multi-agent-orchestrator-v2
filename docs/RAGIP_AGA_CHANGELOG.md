# Ragıp Aga — Changelog

Ragıp Aga'ya özgü değişiklik geçmişi. Ana orchestrator CHANGELOG.md'den bağımsızdır.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [2.3.0] - 2026-02-22

### Changed — Standalone Taşınabilir Modül

**`ragip_rates.py` artık tek dosya, sıfır bağımlılık, herhangi bir repoya kopyala-yapıştır ile taşınabilir.**

- **Cache path'leri taşınabilir**: `ROOT = Path(__file__).parent.parent` kaldırıldı → `RAGIP_CACHE_DIR` env var (varsayılan: `scripts/.ragip_cache/`)
- **`.env` parser kaldırıldı**: `get_env_key()` fonksiyonu silindi → `os.environ.get()` ile değiştirildi. Çağıran uygulama kendi `.env`'ini yükler.
- **`__all__` export listesi** eklendi — API yüzeyini netleştir
- **Portability docstring** eklendi — 4 adımda taşıma talimatı

### Fixed — Tutarsız Fallback Değerler

- `ragip_aga.py`: Kendi fallback dict'i (42.5, 52.0) kaldırıldı → `ragip_rates.FALLBACK_RATES` import edildi
- `ragip_aga.py`: 8 adet inline `.get("key", HARDCODED)` çağrısı → `_FB["key"]` referanslarıyla değiştirildi
- 3 skill dosyası (arbitraj, vade-farki, strateji): Hardcoded fallback sabitleri kaldırıldı → `ragip_rates.py` JSON çıktısından alınıyor

### Security

- Git geçmişinden 5 yanlışlıkla commit edilmiş dosya tamamen silindi (`git-filter-repo`)
- `.gitignore`'a eklendi: `data/NOTES/`, `scripts/.ragip_cache/`

### Docs

- `RAGIP_AGA.md` v2.3.0: Standalone modül bölümü, env var tablosu, cache dizini bilgisi
- `RAGIP_AGA_TASIMA_REHBERI.md`: "Sadece ragip_rates.py" hızlı başlangıç bölümü eklendi

### Tests

- `get_env_key` mock'ları kaldırıldı → `os.environ` mock'ları
- 5 yeni test: `TestCacheDir` (3), `TestAllExports` (2)
- Toplam: 19/19 test, full suite 300/300

---

## [2.2.0] - 2026-02-21

### Added — Firma Profili (ragip-profil)

- Yeni skill: `/ragip-profil kaydet firma_adi=X sektor=Y is_tipi=Z`
- Sektöre duyarlı KOBİ profili — döviz riski, stok durumu, vade bilgisi
- Profil verisi tüm Ragıp Aga yanıtlarına otomatik context olarak eklenir
- CRUD: goster / kaydet / guncelle / sil

---

## [2.1.0] - 2026-02-21

### Added — Arbitraj Hesaplamaları

- **CIP faiz paritesi arbitrajı**: Teorik vs piyasa forward kuru karşılaştırması
- **Üçgen kur arbitrajı**: EUR-USD-TRY döngüsünde tutarsızlık tespiti
- **Vade farkı vs mevduat arbitrajı**: Geç öde mi, mevduata yatır mı?
- **Carry trade analizi**: USD borç → TL mevduat → başabaş kur
- Yeni skill: `/ragip-arbitraj [cip|ucgen|vade-mevduat|carry-trade]`

### Changed — TCMB EVDS2 → EVDS3 Migration

- Tüm API URL'leri `evds2.tcmb.gov.tr` → `evds3.tcmb.gov.tr/igmevdsms-dis/` olarak güncellendi
- Seri kodları güncellendi (TP.APF.* → TP.APIFON4, TP.REESAVANS.*)

---

## [2.0.0] - 2026-02-19

### Changed — Sub-Agent Mimarisi

- `ragip-aga` tek agent → orchestrator hub'a dönüştürüldü
- 3 sub-agent eklendi: `ragip-hesap` (haiku), `ragip-arastirma` (sonnet), `ragip-veri` (haiku)
- 11 skill 3 sub-agent'a dağıtıldı
- Hardcoded `~/.orchestrator` path'leri → `git rev-parse --show-toplevel` ile dinamik

### Added

- `ragip-ozet`: Günlük brifing özeti skill'i
- `ragip-import`: CSV/Excel veri aktarımı (cari hesap listeleri)
- Output persistence layer: Sub-agent'lar `data/RAGIP_AGA/ciktilar/` altına yazar

### Fixed

- Shell injection koruması (skill Bash bloklarında)
- Undefined `df` variable (ragip-import)
- Atomic write (cache dosyaları için `*.tmp → rename`)

### Tests

- `test_ragip_subagents.py`: Portability (7), skill dağılımı (5), dosya varlığı (4)
- Toplam: 16 yeni yapısal test

---

## [1.1.0] - 2026-02-17

### Fixed — Kritik Bug'lar

- **ZeroDivisionError**: `vade_farki()` gun=0 durumu
- **Türkçe sayı parse**: `45.000` (binlik ayırıcı) vs `45.000` (ondalık) ayrımı
- **Falsy-zero**: `if not value` → `if value is None` (0.0 geçerli değer)
- Invoice regex: TR/EN fatura formatları için iyileştirme

### Added

- Input validation: Negatif anapara, 0-1000 oran aralığı, negatif gün kontrolü
- Atomic write: Cache dosyaları için `*.tmp → rename` pattern
- Path traversal guard: Dosya okuma fonksiyonlarında

### Tests

- `test_ragip_finansal.py`: FinansalHesap sınıfı unit testleri
- `test_ragip_rates.py`: TCMB oran çekici testleri

---

## [1.0.0] - 2026-02-15

### Added — İlk Sürüm

- **CLI**: `ragip "soru"`, `ragip --calc`, `ragip --tcmb`, `ragip --interactive`
- **Hesap motoru**: Vade farkı, TVM, erken ödeme iskontosu, indiferans, NCD, döviz forward, ithalat maliyet
- **Dosya okuma**: PDF (pdfplumber/pypdf), DOCX, TXT, CSV — fatura meta çıkarımı
- **TCMB entegrasyonu**: EVDS API'den canlı faiz/kur verisi, 4 saat cache, fallback
- **CollectAPI**: Banka mevduat ve kredi oranları
- **Claude Code agent**: `.claude/agents/ragip-aga.md` — WebSearch, Read, Bash
- **6 skill**: vade-farki, analiz, dis-veri, strateji, ihtar, firma, gorev
- **LLM fallback**: claude-sonnet-4-5 → gpt-4o → gemini-2.5-flash
- **Rich output**: Terminal'de renkli tablo, syntax highlighting
- **Geçmiş**: `data/RAGIP_AGA/history.jsonl`

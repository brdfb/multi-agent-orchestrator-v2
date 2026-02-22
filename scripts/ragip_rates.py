#!/usr/bin/env python3
"""
Ragıp Aga — Canlı Faiz & Piyasa Veri Çekici
Kaynaklar: TCMB EVDS (resmi) + CollectAPI (banka mevduat/kredi oranları)

Taşınabilir tek dosya modülü — herhangi bir repoya kopyala-yapıştır ile taşınabilir.
Sıfır bağımlılık (sadece stdlib), tek dosya.

Taşıma:
  1. Bu dosyayı kopyala:  cp ragip_rates.py /yeni-repo/scripts/
  2. API key tanımla:     export TCMB_API_KEY=xxx
  3. (Opsiyonel) Cache:   export RAGIP_CACHE_DIR=/yeni-repo/data/cache
  4. Test:                python3 ragip_rates.py --pretty

Kullanım:
  python3 ragip_rates.py              → JSON çıktı (skill'ler için)
  python3 ragip_rates.py --pretty     → Okunabilir tablo
  python3 ragip_rates.py --refresh    → Cache'i zorla yenile
  python3 ragip_rates.py --mevduat    → Banka mevduat oranları tablosu
  python3 ragip_rates.py --kredi      → Banka kredi oranları tablosu
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path

__all__ = [
    "FALLBACK_RATES", "SERIES", "CACHE_DIR",
    "get_rates", "get_mevduat", "get_kredi",
    "fetch_tcmb", "fetch_series", "fetch_collectapi",
    "eur_usd_cross", "en_yuksek_mevduat",
    "format_pretty", "format_mevduat", "format_kredi",
    "load_cache", "save_cache",
]

CACHE_DIR = Path(os.environ.get("RAGIP_CACHE_DIR", str(Path(__file__).parent / ".ragip_cache")))
CACHE_FILE       = CACHE_DIR / "rates_cache.json"
MEVDUAT_CACHE    = CACHE_DIR / "mevduat_cache.json"
KREDI_CACHE      = CACHE_DIR / "kredi_cache.json"
CACHE_TTL_HOURS  = 4    # Faiz oranları 4 saatte bir yenile
MARKET_TTL_HOURS = 12   # Mevduat/kredi oranları 12 saatte bir yenile

# ─── TCMB EVDS3 Seri Kodları ─────────────────────────────────────────────────
# EVDS3 migration (Şubat 2026): evds2 → evds3.tcmb.gov.tr/igmevdsms-dis/
# Eski TP.APF.* serileri kaldırıldı, yeni karşılıklar:
SERIES = {
    "politika_faizi":       "TP.APIFON4",      # TCMB Ağırlıklı Ort. Fonlama Maliyeti
    "reeskont_orani":       "TP.REESAVANS.RIO", # Reeskont iskonto oranı
    "avans_faizi":          "TP.REESAVANS.AFO", # Avans faiz oranı (yasal gecikme ref.)
    "usd_kuru":             "TP.DK.USD.A.YTL",  # USD/TRY
    "eur_kuru":             "TP.DK.EUR.A.YTL",  # EUR/TRY
}

# ─── CollectAPI Endpoints ─────────────────────────────────────────────────────
COLLECTAPI_BASE = "https://api.collectapi.com/credit"
COLLECTAPI_ENDPOINTS = {
    "mevduat":      f"{COLLECTAPI_BASE}/mevduat",
    "ihtiyacKredi": f"{COLLECTAPI_BASE}/ihtiyacKredi",
}

# ─── Fallback Değerler ────────────────────────────────────────────────────────
FALLBACK_RATES = {
    "politika_faizi":       37.00,
    "reeskont_orani":       38.75,
    "avans_faizi":          39.75,
    "yasal_gecikme_faizi":  39.75,
    "usd_kuru":             43.69,
    "eur_kuru":             51.48,
    "kaynak":               "fallback",
    "guncelleme":           "Manuel — 21 Şubat 2026",
    "uyari":                "TCMB_API_KEY eksik. Kayıt: https://evds3.tcmb.gov.tr"
}


# ─── Cache yardımcıları ───────────────────────────────────────────────────────

def load_cache(path: Path, ttl_hours: int) -> dict | None:
    if not path.exists():
        return None
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        updated = datetime.datetime.fromisoformat(cached.get("guncelleme", "2000-01-01"))
        if (datetime.datetime.now() - updated).total_seconds() / 3600 < ttl_hours:
            return cached
    except Exception:
        pass
    return None


def save_cache(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(path)


# ─── TCMB EVDS ───────────────────────────────────────────────────────────────

def fetch_series(series_code: str, api_key: str) -> float | None:
    """EVDS3 API'den tek seri verisi çek. Son 30 günün en güncel değerini döndür."""
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=30)).strftime("%d-%m-%Y")
    end = today.strftime("%d-%m-%Y")
    url = (
        f"https://evds3.tcmb.gov.tr/igmevdsms-dis/"
        f"series={series_code}&startDate={start}&endDate={end}&type=json"
    )
    try:
        req = urllib.request.Request(url, headers={"key": api_key})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        for item in reversed(data.get("items", [])):
            for k, v in item.items():
                if k in ("Tarih", "UNIXTIME") or v is None:
                    continue
                try:
                    return float(str(v).replace(",", "."))
                except (ValueError, TypeError):
                    continue
    except Exception as e:
        print(f"[rates] EVDS3 hata ({series_code}): {e}", file=sys.stderr)
    return None


def fetch_tcmb(api_key: str) -> dict:
    rates = {}
    errors = []
    for name, code in SERIES.items():
        val = fetch_series(code, api_key)
        if val is not None:
            rates[name] = val
        else:
            errors.append(name)
    # Yasal gecikme faizi = avans faizi (3095 s.K. referansı)
    if "avans_faizi" in rates:
        rates["yasal_gecikme_faizi"] = rates["avans_faizi"]
    else:
        rates["yasal_gecikme_faizi"] = FALLBACK_RATES["yasal_gecikme_faizi"]
        rates["yasal_gecikme_notu"] = "Fallback: avans faizi alınamadı"
    rates["kaynak"] = "TCMB EVDS3"
    rates["guncelleme"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if errors:
        rates["eksik_seriler"] = errors
    return rates


# ─── CollectAPI ───────────────────────────────────────────────────────────────

def fetch_collectapi(endpoint: str, api_key: str) -> list | None:
    try:
        req = urllib.request.Request(
            endpoint,
            headers={"authorization": f"apikey {api_key}", "content-type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("success"):
            return data.get("result", [])
    except Exception:
        pass
    return None


def get_mevduat(force_refresh: bool = False) -> dict:
    """Banka mevduat oranlarını çek."""
    if not force_refresh:
        cached = load_cache(MEVDUAT_CACHE, MARKET_TTL_HOURS)
        if cached:
            cached["_cache_hit"] = True
            return cached

    api_key = os.environ.get("COLLECTAPI_KEY", "").strip() or None
    if not api_key:
        return {"hata": "COLLECTAPI_KEY eksik", "kaynak": "fallback"}

    result = fetch_collectapi(COLLECTAPI_ENDPOINTS["mevduat"], api_key)
    if result:
        data = {
            "mevduat": result,
            "kaynak": "CollectAPI",
            "guncelleme": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save_cache(MEVDUAT_CACHE, data)
        return data
    return {"hata": "CollectAPI mevduat verisi alınamadı", "kaynak": "hata"}


def get_kredi(force_refresh: bool = False) -> dict:
    """Banka ihtiyaç kredi oranlarını çek."""
    if not force_refresh:
        cached = load_cache(KREDI_CACHE, MARKET_TTL_HOURS)
        if cached:
            cached["_cache_hit"] = True
            return cached

    api_key = os.environ.get("COLLECTAPI_KEY", "").strip() or None
    if not api_key:
        return {"hata": "COLLECTAPI_KEY eksik", "kaynak": "fallback"}

    result = fetch_collectapi(COLLECTAPI_ENDPOINTS["ihtiyacKredi"], api_key)
    if result:
        data = {
            "kredi": result,
            "kaynak": "CollectAPI",
            "guncelleme": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save_cache(KREDI_CACHE, data)
        return data
    return {"hata": "CollectAPI kredi verisi alınamadı", "kaynak": "hata"}


def en_yuksek_mevduat(mevduat_list: list, vade_gun: int = 32) -> dict | None:
    """Verilen vadeye en yakın en yüksek mevduat oranını bul."""
    best = None
    best_rate = 0.0
    for m in mevduat_list:
        try:
            rate = float(str(m.get("oran", "0")).replace(",", "."))
            vade = int(m.get("int", "0"))
            if abs(vade - vade_gun) <= 30 and rate > best_rate:
                best_rate = rate
                best = m
        except (ValueError, TypeError):
            continue
    return best


def eur_usd_cross(rates: dict = None) -> float:
    """EUR/USD = EUR/TRY / USD/TRY (TCMB verilerinden)."""
    if rates is None:
        rates = get_rates()
    eur_try = rates.get("eur_kuru", FALLBACK_RATES["eur_kuru"])
    usd_try = rates.get("usd_kuru", FALLBACK_RATES["usd_kuru"])
    if usd_try <= 0:
        return 0.0
    return round(eur_try / usd_try, 4)


# ─── Ana Faiz Çekici ─────────────────────────────────────────────────────────

def get_rates(force_refresh: bool = False) -> dict:
    """TCMB oranları: cache → API → fallback."""
    if not force_refresh:
        cached = load_cache(CACHE_FILE, CACHE_TTL_HOURS)
        if cached:
            cached["_cache_hit"] = True
            return cached

    api_key = os.environ.get("TCMB_API_KEY", "").strip() or None
    if api_key:
        try:
            rates = fetch_tcmb(api_key)
            if rates.get("politika_faizi"):
                save_cache(CACHE_FILE, rates)
                return rates
        except Exception:
            pass

    fallback = FALLBACK_RATES.copy()
    fallback["guncelleme"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return fallback


# ─── Formatlama ──────────────────────────────────────────────────────────────

def format_pretty(rates: dict) -> str:
    lines = ["=" * 52, "  TCMB FAİZ VE KUR ORANLARI"]
    cache = " [önbellekten]" if rates.get("_cache_hit") else ""
    lines.append(f"  Kaynak: {rates.get('kaynak','?')}{cache} | {rates.get('guncelleme','?')}")
    lines.append("=" * 52)

    def flt(key, label, prefix="%", suffix=""):
        v = rates.get(key)
        if isinstance(v, float):
            lines.append(f"  {label:<28}: {prefix}{v:.2f}{suffix}")
        elif v:
            lines.append(f"  {label:<28}: {v}")

    flt("politika_faizi",       "Politika Faizi (TCMB fonlama)")
    flt("reeskont_orani",       "Reeskont Oranı")
    flt("avans_faizi",          "Avans Faizi")
    flt("yasal_gecikme_faizi",  "Yasal Gecikme Faizi")
    flt("usd_kuru",             "USD/TRY", prefix=" ")
    flt("eur_kuru",             "EUR/TRY", prefix=" ")

    if rates.get("uyari"):
        lines.append(f"\n  ⚠️  {rates['uyari']}")
    lines.append("=" * 52)
    return "\n".join(lines)


def format_mevduat(data: dict) -> str:
    if data.get("hata"):
        return f"⚠️  Mevduat verisi: {data['hata']}\n   COLLECTAPI_KEY gerekli: https://collectapi.com"
    lines = ["=" * 60, "  BANKA MEVDUAT ORANLARI (CollectAPI)"]
    cache = " [önbellekten]" if data.get("_cache_hit") else ""
    lines.append(f"  Güncelleme: {data.get('guncelleme','?')}{cache}")
    lines.append("=" * 60)
    lines.append(f"  {'Ürün':<30} {'Vade':>6} {'Oran':>8} {'Net Getiri':>12}")
    lines.append("  " + "-" * 56)
    for m in data.get("mevduat", [])[:15]:
        ad   = str(m.get("name", m.get("bank-code", "?")))[:28]
        vade = str(m.get("int", "?"))
        oran = str(m.get("oran", "?"))
        net  = str(m.get("net_gelir", ""))
        try:
            net_fmt = f"{float(net):.2f} TL" if net else "-"
        except ValueError:
            net_fmt = net or "-"
        lines.append(f"  {ad:<30} {vade:>6} gün  %{oran:>5}   {net_fmt:>12}")
    lines.append("=" * 60)
    lines.append("  * Net getiri 1.000 TL anapara üzerinden hesaplanmıştır")
    return "\n".join(lines)


def format_kredi(data: dict) -> str:
    if data.get("hata"):
        return f"⚠️  Kredi verisi: {data['hata']}\n   COLLECTAPI_KEY gerekli: https://collectapi.com"
    lines = ["=" * 60, "  BANKA İHTİYAÇ KREDİSİ ORANLARI (CollectAPI)"]
    cache = " [önbellekten]" if data.get("_cache_hit") else ""
    lines.append(f"  Güncelleme: {data.get('guncelleme','?')}{cache}")
    lines.append("=" * 60)
    lines.append(f"  {'Banka':<20} {'Faiz/ay':>8} {'Min Vade':>10} {'Max Vade':>10}")
    lines.append("  " + "-" * 52)
    for k in data.get("kredi", [])[:15]:
        banka = str(k.get("bank", "?"))[:18]
        faiz  = str(k.get("faiz", "?"))
        mn    = str(k.get("min", "?"))
        mx    = str(k.get("max", "?"))
        lines.append(f"  {banka:<20} {faiz:>8}  {mn:>10}  {mx:>10}")
    lines.append("=" * 60)
    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    force    = "--refresh"  in sys.argv
    pretty   = "--pretty"   in sys.argv
    mevduat  = "--mevduat"  in sys.argv
    kredi    = "--kredi"    in sys.argv
    eur_usd  = "--eur-usd"  in sys.argv

    if eur_usd:
        rates = get_rates(force_refresh=force)
        out = {k: v for k, v in rates.items() if not k.startswith("_")}
        out["eur_usd"] = eur_usd_cross(rates)
        print(json.dumps(out, ensure_ascii=False, indent=2))

    elif mevduat:
        data = get_mevduat(force_refresh=force)
        if pretty or True:  # mevduat always pretty
            print(format_mevduat(data))
        else:
            print(json.dumps({k: v for k, v in data.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))

    elif kredi:
        data = get_kredi(force_refresh=force)
        if pretty or True:
            print(format_kredi(data))
        else:
            print(json.dumps({k: v for k, v in data.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))

    else:
        rates = get_rates(force_refresh=force)
        if pretty:
            print(format_pretty(rates))
        else:
            print(json.dumps({k: v for k, v in rates.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))

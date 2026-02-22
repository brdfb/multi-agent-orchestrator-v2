#!/usr/bin/env python3
"""
Ragıp Aga - Nakit Akışı & Ticari Müzakere Danışmanı CLI
Kullanım: ragip "soru"
         ragip "soru" --file sozlesme.pdf
         ragip --calc vade-farki --anapara 100000 --oran 3 --gun 45
         ragip --tcmb
"""

import os
import sys
import json
import argparse
import datetime
import math
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from ragip_rates import FALLBACK_RATES as _FB
except ImportError:
    _FB = {"politika_faizi": 37.0, "usd_kuru": 43.69, "eur_kuru": 51.48}


# ─── TCMB Faiz Verisi ────────────────────────────────────────────────────────

def get_tcmb_rates_with_search(force_refresh: bool = False) -> dict:
    """
    TCMB oranlarını ragip_rates.py üzerinden çek (cache + API + fallback).
    ragip_rates.py bağımsız çalışır: API key varsa EVDS'den, yoksa fallback.
    """
    rates_script = ROOT / "scripts" / "ragip_rates.py"
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(rates_script)] + (["--refresh"] if force_refresh else []),
            capture_output=True, text=True, timeout=12
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        print(f"[UYARI] Rate fetcher hatası: {e}", file=sys.stderr)

    # Son çare fallback — ragip_rates.py'deki tek kaynak kullan
    try:
        from ragip_rates import FALLBACK_RATES
        fallback = FALLBACK_RATES.copy()
        fallback["guncelleme"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return fallback
    except ImportError:
        return {
            "politika_faizi": 37.00,
            "yasal_gecikme_faizi": 39.75,
            "kaynak": "fallback",
            "guncelleme": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "uyari": "TCMB_API_KEY eksik. Kayıt: https://evds3.tcmb.gov.tr"
        }


# ─── Finansal Hesap Motoru ────────────────────────────────────────────────────

class FinansalHesap:
    """Ragıp Aga'nın finansal hesap motoru."""

    @staticmethod
    def _validate_positive(value: float, name: str) -> None:
        if value <= 0:
            raise ValueError(f"{name} sifir veya negatif olamaz: {value}")

    @staticmethod
    def _validate_non_negative_int(value: int, name: str) -> None:
        if value < 0:
            raise ValueError(f"{name} negatif olamaz: {value}")

    @staticmethod
    def _validate_rate(value: float, name: str) -> None:
        if value < 0 or value > 1000:
            raise ValueError(f"{name} 0-1000 arasinda olmali: {value}")

    @staticmethod
    def vade_farki(anapara: float, aylik_oran_pct: float, gun: int) -> dict:
        """
        Vade farkı hesapla.
        anapara: TL cinsinden
        aylik_oran_pct: aylık oran yüzde olarak (örn: 3.0 = %3/ay)
        gun: vade gün sayısı
        """
        FinansalHesap._validate_positive(anapara, "anapara")
        FinansalHesap._validate_rate(aylik_oran_pct, "aylik_oran_pct")
        FinansalHesap._validate_non_negative_int(gun, "gun")
        aylik_oran = aylik_oran_pct / 100
        vade_farki = anapara * aylik_oran * gun / 30
        toplam = anapara + vade_farki
        return {
            "anapara": anapara,
            "aylik_oran_pct": aylik_oran_pct,
            "gun": gun,
            "vade_farki_tl": round(vade_farki, 2),
            "toplam_tl": round(toplam, 2),
            "gunluk_maliyet_tl": round(vade_farki / gun, 2) if gun > 0 else 0.0,
        }

    @staticmethod
    def tvm_gunluk_maliyet(tutar: float, yillik_oran_pct: float, gun: int) -> dict:
        """
        Paranın zaman değeri - belirtilen süre için fırsat maliyeti.
        yillik_oran_pct: yıllık oran % (örn: TCMB politika faizi, 42.5)
        """
        FinansalHesap._validate_positive(tutar, "tutar")
        FinansalHesap._validate_rate(yillik_oran_pct, "yillik_oran_pct")
        FinansalHesap._validate_non_negative_int(gun, "gun")
        yillik_oran = yillik_oran_pct / 100
        maliyet = tutar * yillik_oran * gun / 365
        return {
            "tutar": tutar,
            "yillik_oran_pct": yillik_oran_pct,
            "gun": gun,
            "firsatmaliyeti_tl": round(maliyet, 2),
            "gunluk_tl": round(maliyet / gun, 2) if gun > 0 else 0.0,
        }

    @staticmethod
    def erken_odeme_iskonto(tutar: float, aylik_oran_pct: float, kazanilan_gun: int) -> dict:
        """
        Erken ödeme için kabul edilebilir maksimum iskonto.
        Mantık: erken ödersen vade farkından kurtulursun, o kadar indirim isteyebilirsin.
        """
        FinansalHesap._validate_positive(tutar, "tutar")
        FinansalHesap._validate_rate(aylik_oran_pct, "aylik_oran_pct")
        FinansalHesap._validate_non_negative_int(kazanilan_gun, "kazanilan_gun")
        aylik_oran = aylik_oran_pct / 100
        max_iskonto = tutar * aylik_oran * kazanilan_gun / 30
        iskonto_pct = (max_iskonto / tutar) * 100
        return {
            "tutar": tutar,
            "kazanilan_gun": kazanilan_gun,
            "max_iskonto_tl": round(max_iskonto, 2),
            "iskonto_pct": round(iskonto_pct, 2),
            "aciklama": f"{kazanilan_gun} gün erken ödersen en fazla %{iskonto_pct:.2f} iskonto isteyebilirsin",
        }

    @staticmethod
    def indiferans_iskonto(
        tutar: float,
        aylik_vade_farki_pct: float,
        yillik_firsat_oran_pct: float,
        erken_gun: int,
    ) -> dict:
        """
        Indiferans (break-even) iskonto hesabi.
        Karsi tarafin erken odeme karsiliginda kabul edebilecegi minimum iskonto.
        Mantik: Karsi taraf erken odeme yaparsa, o parayi bankada/mevduatta
        tutarak kazanacagi faizden vazgeciyor. Indiferans noktasi =
        karsi tarafin firsat maliyeti.

        tutar: fatura tutari
        aylik_vade_farki_pct: sozlesmedeki aylik vade farki orani %
        yillik_firsat_oran_pct: karsi tarafin alternatif getiri orani (yillik %)
        erken_gun: kac gun erken odenecek
        """
        FinansalHesap._validate_positive(tutar, "tutar")
        FinansalHesap._validate_rate(aylik_vade_farki_pct, "aylik_vade_farki_pct")
        FinansalHesap._validate_rate(yillik_firsat_oran_pct, "yillik_firsat_oran_pct")
        FinansalHesap._validate_non_negative_int(erken_gun, "erken_gun")

        # Senin max iskonto tavan = vade farki tasarrufu
        aylik_oran = aylik_vade_farki_pct / 100
        max_iskonto = tutar * aylik_oran * erken_gun / 30

        # Karsi tarafin firsat maliyeti = erken odeme ile kaybedecegi faiz geliri
        yillik_oran = yillik_firsat_oran_pct / 100
        karsi_taraf_maliyeti = tutar * yillik_oran * erken_gun / 365

        # Indiferans = karsi tarafin kabul edebilecegi minimum
        indiferans_pct = (karsi_taraf_maliyeti / tutar) * 100

        # Muzakere araliGi = indiferans ile max iskonto arasi
        max_iskonto_pct = (max_iskonto / tutar) * 100

        return {
            "tutar": tutar,
            "erken_gun": erken_gun,
            "max_iskonto_tl": round(max_iskonto, 2),
            "max_iskonto_pct": round(max_iskonto_pct, 2),
            "indiferans_tl": round(karsi_taraf_maliyeti, 2),
            "indiferans_pct": round(indiferans_pct, 2),
            "muzakere_araligi_tl": f"{round(karsi_taraf_maliyeti, 2)} - {round(max_iskonto, 2)}",
            "yorum": (
                f"Sen en fazla {max_iskonto:,.0f} TL (%{max_iskonto_pct:.2f}) iskonto isteyebilirsin. "
                f"Karsi taraf en az {karsi_taraf_maliyeti:,.0f} TL (%{indiferans_pct:.2f}) altina inmez. "
                f"Muzakere araligi: {karsi_taraf_maliyeti:,.0f} - {max_iskonto:,.0f} TL."
            ),
        }

    @staticmethod
    def odeme_plani_karsilastir(
        tutar: float,
        secenekler: list[dict],
        yillik_repo: float
    ) -> list[dict]:
        """
        Birden fazla ödeme seçeneğini TVM ile karşılaştır.
        secenekler: [{"ad": "30 gün", "gun": 30, "tutar": 102000}, ...]
        """
        bugunki_deger = []
        for s in secenekler:
            yillik_oran = yillik_repo / 100
            bugun = s["tutar"] / (1 + yillik_oran * s["gun"] / 365)
            bugunki_deger.append({
                "secenek": s["ad"],
                "odeme_tutari": s["tutar"],
                "gun": s["gun"],
                "bugunki_degeri_tl": round(bugun, 2),
                "fark_tl": round(bugun - tutar, 2),
            })
        # En düşük bugünkü değere göre sırala
        bugunki_deger.sort(key=lambda x: x["bugunki_degeri_tl"])
        return bugunki_deger

    @staticmethod
    def nakit_cevrim_dongusu(dio: int, dso: int, dpo: int) -> dict:
        """
        Nakit çevrim döngüsü: DIO + DSO - DPO
        DIO: Stokta kalma süresi (Days Inventory Outstanding)
        DSO: Tahsilat süresi (Days Sales Outstanding)
        DPO: Ödeme süresi (Days Payable Outstanding)
        """
        ncd = dio + dso - dpo
        return {
            "dio": dio,
            "dso": dso,
            "dpo": dpo,
            "nakit_cevrim_dongusu": ncd,
            "yorum": (
                "Nakit bağlanıyor" if ncd > 30
                else "Sağlıklı" if ncd > 0
                else "Tedarikçiler seni finanse ediyor (iyi)"
            ),
        }

    @staticmethod
    def doviz_forward(spot: float, r_tl_pct: float, r_usd_pct: float, gun: int) -> dict:
        """
        Forward kur tahmini (faiz orani paritesi).
        F = S x (1 + r_TL x t) / (1 + r_USD x t)
        spot: Guncel doviz kuru (ornek: 38.50)
        r_tl_pct: TL yillik faiz orani % (ornek: 42.5)
        r_usd_pct: USD yillik faiz orani % (ornek: 4.5)
        gun: Vade gun sayisi
        """
        FinansalHesap._validate_positive(spot, "spot")
        FinansalHesap._validate_rate(r_tl_pct, "r_tl_pct")
        FinansalHesap._validate_rate(r_usd_pct, "r_usd_pct")
        FinansalHesap._validate_non_negative_int(gun, "gun")
        t = gun / 365
        r_tl = r_tl_pct / 100
        r_usd = r_usd_pct / 100
        denominator = 1 + r_usd * t
        if denominator == 0:
            raise ValueError("Payda sifir: r_usd ve gun kombinasyonu gecersiz")
        forward = spot * (1 + r_tl * t) / denominator
        prim_pct = ((forward - spot) / spot) * 100
        return {
            "spot_kur": spot,
            "r_tl_pct": r_tl_pct,
            "r_usd_pct": r_usd_pct,
            "gun": gun,
            "forward_kur": round(forward, 4),
            "prim_pct": round(prim_pct, 2),
            "yorum": f"{gun} gun sonra beklenen kur: {forward:.4f} TL (% {prim_pct:.1f} prim)",
        }

    @staticmethod
    def ithalat_maliyet(
        usd_tutar: float,
        spot_kur: float,
        navlun_usd: float = 0,
        gtip_vergi_pct: float = 0,
        kdv_pct: float = 20.0,
    ) -> dict:
        """
        Ithalat toplam maliyet hesabi.
        CIF = FOB + navlun
        Gumruk vergisi = CIF x gtip_vergi_pct
        KDV matrah = CIF + gumruk vergisi
        KDV = matrah x kdv_pct
        """
        FinansalHesap._validate_positive(usd_tutar, "usd_tutar")
        FinansalHesap._validate_positive(spot_kur, "spot_kur")
        if navlun_usd < 0:
            raise ValueError(f"navlun_usd negatif olamaz: {navlun_usd}")
        if gtip_vergi_pct < 0 or gtip_vergi_pct > 100:
            raise ValueError(f"gtip_vergi_pct 0-100 arasinda olmali: {gtip_vergi_pct}")
        if kdv_pct < 0 or kdv_pct > 100:
            raise ValueError(f"kdv_pct 0-100 arasinda olmali: {kdv_pct}")
        cif_usd = usd_tutar + navlun_usd
        cif_tl = cif_usd * spot_kur
        gumruk_vergisi = cif_tl * (gtip_vergi_pct / 100)
        kdv_matrah = cif_tl + gumruk_vergisi
        kdv = kdv_matrah * (kdv_pct / 100)
        toplam = cif_tl + gumruk_vergisi + kdv
        birim_maliyet_tl = toplam / usd_tutar if usd_tutar > 0 else 0
        return {
            "fob_usd": usd_tutar,
            "navlun_usd": navlun_usd,
            "cif_usd": cif_usd,
            "spot_kur": spot_kur,
            "cif_tl": round(cif_tl, 2),
            "gumruk_vergisi_tl": round(gumruk_vergisi, 2),
            "kdv_matrah_tl": round(kdv_matrah, 2),
            "kdv_tl": round(kdv, 2),
            "toplam_tl": round(toplam, 2),
            "birim_maliyet_tl_usd": round(birim_maliyet_tl, 4),
            "yorum": f"1 USD mal = {birim_maliyet_tl:.4f} TL toplam maliyet",
        }

    # ─── Arbitraj Hesaplamalari ─────────────────────────────────────────────

    @staticmethod
    def covered_interest_arbitrage(
        spot: float,
        market_forward: float,
        r_tl_pct: float,
        r_usd_pct: float,
        gun: int,
        islem_maliyeti_pct: float = 0.1,
    ) -> dict:
        """
        Covered Interest Parity (CIP) arbitraji.
        Teorik forward kuru ile piyasa forward kurunu karsilastir.

        spot: Guncel doviz kuru
        market_forward: Piyasadaki gercek forward kuru
        r_tl_pct: TL yillik faiz orani %
        r_usd_pct: USD yillik faiz orani %
        gun: Vade gun sayisi
        islem_maliyeti_pct: Islem maliyeti % (spread+komisyon, varsayilan 0.1)
        """
        FinansalHesap._validate_positive(spot, "spot")
        FinansalHesap._validate_positive(market_forward, "market_forward")
        FinansalHesap._validate_rate(r_tl_pct, "r_tl_pct")
        FinansalHesap._validate_rate(r_usd_pct, "r_usd_pct")
        FinansalHesap._validate_non_negative_int(gun, "gun")

        t = gun / 365
        r_tl = r_tl_pct / 100
        r_usd = r_usd_pct / 100
        denom = 1 + r_usd * t
        if denom == 0:
            raise ValueError("Payda sifir: r_usd ve gun kombinasyonu gecersiz")
        teorik = spot * (1 + r_tl * t) / denom
        sapma_pct = ((market_forward - teorik) / teorik) * 100 if teorik != 0 else 0.0
        arbitraj_var = abs(sapma_pct) > islem_maliyeti_pct
        tahmini_kar_pct = round(abs(sapma_pct) - islem_maliyeti_pct, 4) if arbitraj_var else 0.0

        if sapma_pct > 0:
            yon = "TL'ye yatir, forward sat"
        elif sapma_pct < 0:
            yon = "USD'ye yatir, forward al"
        else:
            yon = "Denge — yon yok"

        return {
            "spot_kur": spot,
            "market_forward": market_forward,
            "teorik_forward": round(teorik, 4),
            "sapma_pct": round(sapma_pct, 4),
            "islem_maliyeti_pct": islem_maliyeti_pct,
            "arbitraj_var": arbitraj_var,
            "yon": yon,
            "tahmini_kar_pct": tahmini_kar_pct,
            "yorum": (
                f"Piyasa forward ({market_forward:.4f}) teorikten "
                f"{'yuksek' if sapma_pct > 0 else 'dusuk'} (%{abs(sapma_pct):.3f} sapma). "
                + (f"Arbitraj firsati: {yon}, tahmini kar %{tahmini_kar_pct:.3f}" if arbitraj_var
                   else f"Sapma islem maliyetinden (%{islem_maliyeti_pct}) kucuk — arbitraj yok")
            ),
        }

    @staticmethod
    def ucgen_kur_arbitraji(
        usd_try: float,
        eur_try: float,
        eur_usd: float,
        islem_maliyeti_pct: float = 0.15,
    ) -> dict:
        """
        Ucgen kur arbitraji: EUR-USD-TRY ucgeninde tutarsizlik tespiti.

        usd_try: USD/TRY kuru
        eur_try: EUR/TRY kuru
        eur_usd: EUR/USD kuru
        islem_maliyeti_pct: Bacak basina islem maliyeti % (varsayilan 0.15)
        """
        FinansalHesap._validate_positive(usd_try, "usd_try")
        FinansalHesap._validate_positive(eur_try, "eur_try")
        FinansalHesap._validate_positive(eur_usd, "eur_usd")

        dolayli_eur_try = eur_usd * usd_try
        sapma_pct = ((eur_try - dolayli_eur_try) / dolayli_eur_try) * 100

        baslangic = 1_000_000  # 1M EUR
        # Yol A: EUR→USD→TRY→EUR
        usd_a = baslangic * eur_usd
        tl_a = usd_a * usd_try
        son_eur_a = tl_a / eur_try
        kar_a_pct = ((son_eur_a - baslangic) / baslangic) * 100

        # Yol B: EUR→TRY→USD→EUR
        tl_b = baslangic * eur_try
        usd_b = tl_b / usd_try
        son_eur_b = usd_b / eur_usd
        kar_b_pct = ((son_eur_b - baslangic) / baslangic) * 100

        toplam_islem_maliyeti = islem_maliyeti_pct * 3  # 3 bacak
        if kar_a_pct >= kar_b_pct:
            brut_kar = kar_a_pct
            en_iyi_yol = "EUR→USD→TRY→EUR"
        else:
            brut_kar = kar_b_pct
            en_iyi_yol = "EUR→TRY→USD→EUR"

        net_kar_pct = brut_kar - toplam_islem_maliyeti
        arbitraj_var = net_kar_pct > 0

        return {
            "usd_try": usd_try,
            "eur_try": eur_try,
            "eur_usd": eur_usd,
            "dolayli_eur_try": round(dolayli_eur_try, 4),
            "sapma_pct": round(sapma_pct, 4),
            "yol_a_kar_pct": round(kar_a_pct, 4),
            "yol_b_kar_pct": round(kar_b_pct, 4),
            "en_iyi_yol": en_iyi_yol,
            "brut_kar_pct": round(brut_kar, 4),
            "islem_maliyeti_toplam_pct": round(toplam_islem_maliyeti, 4),
            "net_kar_pct": round(net_kar_pct, 4),
            "arbitraj_var": arbitraj_var,
            "yorum": (
                f"Dogrudan EUR/TRY ({eur_try:.4f}) vs dolayli ({dolayli_eur_try:.4f}): "
                f"%{abs(sapma_pct):.3f} sapma. "
                + (f"Arbitraj firsati: {en_iyi_yol}, net kar %{net_kar_pct:.3f}"
                   if arbitraj_var
                   else f"Net kar ({net_kar_pct:.3f}%) islem maliyetini karsilamiyor")
            ),
        }

    @staticmethod
    def vade_mevduat_arbitraji(
        anapara: float,
        vade_farki_oran_pct: float,
        gun: int,
        mevduat_oran_pct: float,
    ) -> dict:
        """
        Vade farki vs mevduat arbitraji.
        Tedarikciye vade farkiyla gec ode mi, yoksa parayi mevduata yatirip
        erken ode mi daha karli?

        anapara: Fatura tutari TL
        vade_farki_oran_pct: Aylik vade farki orani % (ornek: 3.0)
        gun: Vade gun sayisi
        mevduat_oran_pct: Yillik mevduat faiz orani % (ornek: 45.0)
        """
        FinansalHesap._validate_positive(anapara, "anapara")
        FinansalHesap._validate_rate(vade_farki_oran_pct, "vade_farki_oran_pct")
        FinansalHesap._validate_non_negative_int(gun, "gun")
        FinansalHesap._validate_rate(mevduat_oran_pct, "mevduat_oran_pct")

        vade_farki = anapara * (vade_farki_oran_pct / 100) * gun / 30
        mevduat_getiri = anapara * (mevduat_oran_pct / 100) * gun / 365
        net_fark = mevduat_getiri - vade_farki
        vade_farki_yillik = vade_farki_oran_pct * 12
        karar = (
            "Parayi mevduata yatir, tedarikciye gec ode"
            if net_fark > 0
            else "Erken ode, vade farkindan kurtul"
        )

        return {
            "anapara": anapara,
            "gun": gun,
            "vade_farki_oran_aylik_pct": vade_farki_oran_pct,
            "vade_farki_yillik_pct": round(vade_farki_yillik, 2),
            "mevduat_oran_yillik_pct": mevduat_oran_pct,
            "vade_farki_maliyeti_tl": round(vade_farki, 2),
            "mevduat_getirisi_tl": round(mevduat_getiri, 2),
            "net_fark_tl": round(net_fark, 2),
            "karar": karar,
            "yorum": (
                f"Vade farki maliyeti: {vade_farki:,.2f} TL (~%{vade_farki_yillik:.0f}/yil), "
                f"Mevduat getirisi: {mevduat_getiri:,.2f} TL (%{mevduat_oran_pct}/yil). "
                f"Net fark: {net_fark:,.2f} TL → {karar}"
            ),
        }

    @staticmethod
    def carry_trade_analizi(
        spot: float,
        r_tl_pct: float,
        r_usd_pct: float,
        gun: int,
        beklenen_kur: float | None = None,
    ) -> dict:
        """
        Carry trade analizi: USD borc al, TL'ye cevir, TL mevduata yatir.

        spot: Guncel USD/TRY kuru
        r_tl_pct: TL yillik faiz orani %
        r_usd_pct: USD yillik borc maliyeti %
        gun: Yatirim suresi (gun)
        beklenen_kur: Kullanicinin beklenen kur tahmini (opsiyonel)
        """
        FinansalHesap._validate_positive(spot, "spot")
        FinansalHesap._validate_rate(r_tl_pct, "r_tl_pct")
        FinansalHesap._validate_rate(r_usd_pct, "r_usd_pct")
        FinansalHesap._validate_non_negative_int(gun, "gun")

        t = gun / 365
        r_tl = r_tl_pct / 100
        r_usd = r_usd_pct / 100

        # 1 USD borc al, TL'ye cevir, mevduata yatir
        tl_yatirim = spot * (1 + r_tl * t)  # gun sonra TL birikimi
        usd_borc = 1 + r_usd * t             # gun sonra USD borcu

        # Basabas kur = TL'yi USD'ye cevirdikde borcu tam karsilayan kur
        basabas_kur = tl_yatirim / usd_borc if usd_borc > 0 else spot

        # Unhedged: kur spot'ta kalirsa
        unhedged_usd = tl_yatirim / spot if spot > 0 else 0
        unhedged_kar_pct = ((unhedged_usd - usd_borc) / 1) * 100

        result = {
            "spot_kur": spot,
            "r_tl_pct": r_tl_pct,
            "r_usd_pct": r_usd_pct,
            "gun": gun,
            "tl_birikim": round(tl_yatirim, 4),
            "usd_borc": round(usd_borc, 6),
            "basabas_kur": round(basabas_kur, 4),
            "unhedged_kar_pct": round(unhedged_kar_pct, 4),
            "beklenen_kur_kar_pct": None,
            "yorum": "",
        }

        yorum_parts = [
            f"1 USD borc al ({spot:.2f} TL), {gun} gun sonra {tl_yatirim:.2f} TL birikir. "
            f"Basabas kur: {basabas_kur:.4f}. "
            f"Kur sabit kalirsa kar: %{unhedged_kar_pct:.2f}."
        ]

        if beklenen_kur is not None and beklenen_kur > 0:
            beklenen_usd = tl_yatirim / beklenen_kur
            beklenen_kar_pct = ((beklenen_usd - usd_borc) / 1) * 100
            result["beklenen_kur_kar_pct"] = round(beklenen_kar_pct, 4)
            yorum_parts.append(
                f" Beklenen kur ({beklenen_kur:.2f}) ile kar: %{beklenen_kar_pct:.2f}."
            )

        if basabas_kur > spot * 1.15:
            yorum_parts.append(" UYARI: Basabas kuru spot'tan %15+ yukarda — kur riski yuksek.")

        result["yorum"] = "".join(yorum_parts)
        return result


# ─── Dosya Okuma ─────────────────────────────────────────────────────────────

def _parse_turkish_number(s: str) -> float:
    """
    Turkce/Ingilizce sayi formatini parse et.
    TR: 45.000,00 -> 45000.00
    EN: 45,000.00 -> 45000.00
    Basit: 9000 -> 9000.0
    """
    s = s.strip()
    # Son nokta/virgulun pozisyonuna bak
    last_dot = s.rfind('.')
    last_comma = s.rfind(',')

    if last_dot > last_comma:
        # Belirsizlik kontrolu: noktadan sonra tam 3 basamak varsa TR binlik ayirici
        after_dot = s[last_dot + 1:]
        if last_comma == -1 and len(after_dot) == 3 and after_dot.isdigit():
            # TR format: 45.000 -> 45000 (binlik ayirici)
            return float(s.replace('.', ''))
        # EN format: 45,000.00 — virgul binlik, nokta ondalik
        return float(s.replace(',', ''))
    elif last_comma > last_dot:
        # TR format: 45.000,00 — nokta binlik, virgul ondalik
        return float(s.replace('.', '').replace(',', '.'))
    else:
        # Sadece rakam veya tek ayirici
        return float(s.replace(',', '').replace('.', '') if ',' not in s and '.' not in s else s.replace(',', ''))


def extract_invoice_data(text: str) -> dict:
    """Fatura metninden regex ile anahtar verileri cikar."""
    import re
    meta = {}

    # Fatura numarasi
    m = re.search(r'(?:Fatura\s*(?:No|Numaras[ıi])|Invoice\s*No)[:\s]*([A-Z0-9\-/]+)', text, re.IGNORECASE)
    if m:
        meta["fatura_no"] = m.group(1).strip()

    # Tarih (GG.AA.YYYY veya GG/AA/YYYY)
    m = re.search(r'(?:Fatura\s*Tarihi|Tarih|Date)[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})', text, re.IGNORECASE)
    if m:
        meta["tarih"] = m.group(1).strip()

    # KDV toplam — "KDV" veya "KDV Tutari" ile baslayan
    m = re.search(r'KDV\s*(?:\(%?\d+\)|Tutar[ıi]?)?[:\s]*([\d.,]+)\s*(?:TL)?', text, re.IGNORECASE)
    if m:
        try:
            meta["kdv_toplam"] = _parse_turkish_number(m.group(1))
        except ValueError:
            pass

    # Genel toplam — "Genel Toplam" oncelikli, sonra tek basina "Toplam" (ama "Ara Toplam" degil)
    m = re.search(r'Genel\s*Toplam[:\s]*([\d.,]+)\s*(?:TL)?', text, re.IGNORECASE)
    if not m:
        m = re.search(r'Grand\s*Total[:\s]*([\d.,]+)\s*(?:TL)?', text, re.IGNORECASE)
    if not m:
        # "Toplam" tek basina — ama "Ara Toplam" olmamali
        m = re.search(r'(?<!Ara\s)Toplam[:\s]*([\d.,]+)\s*(?:TL)?', text, re.IGNORECASE)
    if m:
        try:
            meta["genel_toplam"] = _parse_turkish_number(m.group(1))
        except ValueError:
            pass

    # Vade tarihi
    m = re.search(r'(?:Vade\s*Tarihi|Due\s*Date)[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})', text, re.IGNORECASE)
    if m:
        meta["vade_tarihi"] = m.group(1).strip()

    return meta


def read_file_content(filepath: str) -> str | dict:
    """
    Sozlesme/fatura dosyasini oku. PDF, TXT, DOCX destekler.
    PDF icin pdfplumber varsa tablo cikarma da yapar ve dict doner.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadi: {filepath}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        # pdfplumber oncelikli (tablo cikarma destegi)
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                pages_text = []
                all_tables = []
                for page in pdf.pages:
                    pages_text.append(page.extract_text() or "")
                    tables = page.extract_tables()
                    if tables:
                        for tbl in tables:
                            all_tables.append(tbl)

                text = "\n".join(pages_text)[:8000]
                fatura_meta = extract_invoice_data(text)

                if all_tables or fatura_meta:
                    return {
                        "metin": text,
                        "tablolar": all_tables[:10],  # Maks 10 tablo
                        "fatura_meta": fatura_meta,
                    }
                return text
        except ImportError:
            pass

        # pypdf fallback (sadece metin)
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:8000]
        except ImportError:
            raise ImportError(
                "PDF okumak icin: pip install pdfplumber\n"
                "veya: pip install pypdf"
            )

    elif suffix in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs)
            return text[:8000]
        except ImportError:
            raise ImportError("DOCX okumak icin: pip install python-docx")

    elif suffix in (".txt", ".md", ".csv"):
        return path.read_text(encoding="utf-8", errors="ignore")[:8000]

    else:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:8000]
        except Exception:
            raise ValueError(f"Desteklenmeyen dosya formati: {suffix}")


# ─── LLM Çağrısı ─────────────────────────────────────────────────────────────

def load_config():
    config_path = ROOT / "config" / "ragip_aga.yaml"
    if not config_path.exists():
        print(f"[HATA] Config bulunamadı: {config_path}", file=sys.stderr)
        sys.exit(1)
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        print("[HATA] PyYAML kurulu değil: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


def ensure_log_dir(config):
    log_dir = ROOT / config["standalone"]["log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def save_to_history(log_dir, prompt, response, model, duration_ms, tokens):
    history_file = log_dir / "history.jsonl"
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt": prompt[:500],
        "response": response,
        "model": model,
        "duration_ms": duration_ms,
        "tokens": tokens,
    }
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def call_llm(config, prompt):
    try:
        import litellm
        import time
    except ImportError:
        print("[HATA] litellm kurulu değil: pip install litellm", file=sys.stderr)
        sys.exit(1)

    agent_cfg = config["agent"]
    model = agent_cfg["model"]
    system_prompt = agent_cfg["system_prompt"]
    temperature = agent_cfg.get("temperature", 0.4)
    max_tokens = agent_cfg.get("max_tokens", 4000)
    fallbacks = agent_cfg.get("fallback_order", [])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    models_to_try = [model] + fallbacks
    last_error = None

    for attempt_model in models_to_try:
        try:
            t0 = time.time()
            response = litellm.completion(
                model=attempt_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            duration_ms = int((time.time() - t0) * 1000)
            content = response.choices[0].message.content
            usage = response.usage
            tokens = {
                "prompt": getattr(usage, "prompt_tokens", 0),
                "completion": getattr(usage, "completion_tokens", 0),
                "total": getattr(usage, "total_tokens", 0),
            }
            if attempt_model != model:
                print(f"[FALLBACK] {model} → {attempt_model}", file=sys.stderr)
            return content, attempt_model, duration_ms, tokens
        except Exception as e:
            last_error = e
            provider = attempt_model.split("/")[0] if "/" in attempt_model else attempt_model
            print(f"[UYARI] {provider} başarısız: {e}", file=sys.stderr)
            continue

    print(f"[HATA] Tüm modeller başarısız. Son hata: {last_error}", file=sys.stderr)
    sys.exit(1)


# ─── Çıktı ───────────────────────────────────────────────────────────────────

def display_response(response_text, model, duration_ms, tokens):
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown
        from rich.text import Text

        console = Console()
        console.print()
        console.print(Panel(
            Markdown(response_text),
            title="[bold yellow]Ragıp Aga[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        ))
        console.print(Text(
            f"  {model} | {duration_ms}ms | "
            f"tokens: {tokens.get('total','?')} "
            f"(prompt:{tokens.get('prompt','?')} yanıt:{tokens.get('completion','?')})",
            style="dim"
        ))
        console.print()
    except ImportError:
        print("\n" + "=" * 60)
        print("RAGIP AGA:")
        print("=" * 60)
        print(response_text)
        print(f"\n[{model} | {duration_ms}ms | tokens:{tokens.get('total','?')}]")


def display_calc_result(title: str, data: dict):
    try:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title=f"[bold yellow]{title}[/bold yellow]", border_style="yellow")
        table.add_column("", style="dim")
        table.add_column("Değer", style="bold")
        for k, v in data.items():
            if isinstance(v, float):
                table.add_row(k, f"{v:,.2f}")
            else:
                table.add_row(k, str(v))
        console.print()
        console.print(table)
        console.print()
    except ImportError:
        print(f"\n{title}")
        print("-" * 40)
        for k, v in data.items():
            print(f"  {k}: {v}")


# ─── Geçmiş ──────────────────────────────────────────────────────────────────

def show_history(log_dir, limit=5):
    history_file = log_dir / "history.jsonl"
    if not history_file.exists():
        print("Henüz konuşma geçmişi yok.")
        return

    lines = [l for l in history_file.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
    recent = lines[-limit:]

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        for i, line in enumerate(recent, 1):
            entry = json.loads(line)
            ts = entry["timestamp"][:16].replace("T", " ")
            console.print(Panel(
                f"[bold cyan]Soru:[/bold cyan] {entry['prompt']}\n\n"
                f"[bold green]Ragıp Aga:[/bold green] {entry['response'][:400]}"
                f"{'...' if len(entry['response']) > 400 else ''}",
                title=f"[dim]#{i} | {ts}[/dim]",
                border_style="dim"
            ))
    except ImportError:
        for i, line in enumerate(recent, 1):
            entry = json.loads(line)
            print(f"\n--- #{i} [{entry['timestamp'][:16]}] ---")
            print(f"SORU: {entry['prompt']}")
            print(f"RAGIP AGA: {entry['response'][:400]}...")


# ─── İnteraktif Mod ──────────────────────────────────────────────────────────

def interactive_mode(config, log_dir):
    try:
        from rich.console import Console
        console = Console()
        console.print(
            "\n[bold yellow]Ragıp Aga[/bold yellow] [dim]- Nakit Akışı & Ticari Müzakere Danışmanı[/dim]"
        )
        console.print("[dim]Çıkmak için: 'çık' veya Ctrl+C[/dim]\n")
    except ImportError:
        print("\nRagıp Aga - Nakit Akışı & Ticari Müzakere Danışmanı")
        print("Çıkmak için: 'çık' veya Ctrl+C\n")

    while True:
        try:
            prompt = input("Sen: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGörüşürüz.")
            break

        if not prompt:
            continue
        if prompt.lower() in ("çık", "cik", "exit", "quit", "q"):
            print("Görüşürüz.")
            break

        response, model, duration_ms, tokens = call_llm(config, prompt)
        display_response(response, model, duration_ms, tokens)

        if config["standalone"].get("log_to_file", True):
            save_to_history(log_dir, prompt, response, model, duration_ms, tokens)


# ─── Ana Program ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="ragip",
        description="Ragıp Aga - Nakit Akışı & Ticari Müzakere Danışmanı",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  ragip "Disti vade farkı faturası kesti, ne yapmalıyım?"
  ragip "Fatura itirazı" --file sozlesme.pdf
  ragip --calc vade-farki --anapara 100000 --oran 3 --gun 45
  ragip --calc tvm --anapara 100000 --repo-orani 42.5 --gun 30
  ragip --calc iskonto --anapara 100000 --oran 3 --gun 30
  ragip --calc indiferans --anapara 100000 --oran 3 --gun 30 --firsat-orani 42.5
  ragip --calc ncd --dio 45 --dso 30 --dpo 60
  ragip --calc doviz --usd-tutar 10000 --gun 90
  ragip --calc ithalat --usd-tutar 50000 --navlun 3000 --gtip-vergi 10
  ragip --calc cip-arbitraj --market-forward 45.50 --gun 90
  ragip --calc ucgen-arbitraj
  ragip --calc vade-mevduat --anapara 500000 --oran 3 --gun 60
  ragip --calc carry-trade --gun 90 --beklenen-kur 46.0
  ragip --tcmb
  ragip --interactive
  ragip --history
        """
    )

    parser.add_argument("prompt", nargs="?", default=None,
                        help="Ragıp Aga'ya soracağın soru")
    parser.add_argument("--file", "-f", type=str,
                        help="Sözleşme/fatura dosyası (PDF, DOCX, TXT)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Etkileşimli sohbet modu")
    parser.add_argument("--history", action="store_true",
                        help="Son konuşmaları göster")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--model", type=str, help="Model override")
    parser.add_argument("--save-to", type=str, help="Yanıtı dosyaya kaydet")
    parser.add_argument("--tcmb", action="store_true",
                        help="Güncel TCMB faiz oranlarını göster")
    parser.add_argument("--profil", action="store_true",
                        help="Firma profilini göster")

    # Hesaplama modu
    parser.add_argument("--calc", type=str,
                        choices=["vade-farki", "tvm", "iskonto", "indiferans", "ncd", "doviz", "ithalat",
                                 "cip-arbitraj", "ucgen-arbitraj", "vade-mevduat", "carry-trade"],
                        help="Finansal hesaplama: vade-farki | tvm | iskonto | indiferans | ncd | doviz | ithalat | cip-arbitraj | ucgen-arbitraj | vade-mevduat | carry-trade")
    parser.add_argument("--anapara", type=float, help="Ana para tutarı (TL)")
    parser.add_argument("--oran", type=float, help="Aylık faiz oranı (%%)")
    parser.add_argument("--gun", type=int, help="Gün sayısı")
    parser.add_argument("--repo-orani", type=float, help="Yıllık politika faizi (%%)")
    parser.add_argument("--firsat-orani", type=float, help="Karşı tarafın yıllık fırsat oranı (%%) (indiferans hesabı)")
    parser.add_argument("--dio", type=int, help="Stokta kalma süresi (gün)")
    parser.add_argument("--dso", type=int, help="Tahsilat süresi (gün)")
    parser.add_argument("--dpo", type=int, help="Ödeme süresi (gün)")

    # Doviz hesaplama argumanlari
    parser.add_argument("--usd-tutar", type=float, help="USD tutarı")
    parser.add_argument("--usd-faiz", type=float, default=4.5, help="USD yıllık faiz %% (varsayılan: 4.5)")
    parser.add_argument("--navlun", type=float, default=0, help="Navlun USD")
    parser.add_argument("--gtip-vergi", type=float, default=0, help="GTIP gümrük vergisi %%")

    # Arbitraj argumanlari
    parser.add_argument("--market-forward", type=float, help="Piyasa forward kuru (CIP arbitraj)")
    parser.add_argument("--eur-usd", type=float, help="EUR/USD kuru (ucgen arbitraj)")
    parser.add_argument("--mevduat-oran", type=float, help="Yillik mevduat faiz orani %%")
    parser.add_argument("--beklenen-kur", type=float, help="Beklenen kur (carry trade)")
    parser.add_argument("--islem-maliyeti", type=float, default=0.1, help="Islem maliyeti %% (varsayilan: 0.1)")

    args = parser.parse_args()
    config = load_config()
    if args.model:
        config["agent"]["model"] = args.model
    log_dir = ensure_log_dir(config)

    # ── TCMB oranları ──
    if args.tcmb:
        rates = get_tcmb_rates_with_search()
        display_calc_result("TCMB Faiz Oranları", rates)

        # CollectAPI banka oranları — COLLECTAPI_KEY varsa ekrana bas
        import subprocess
        rates_script = ROOT / "scripts" / "ragip_rates.py"
        for flag in ("--mevduat", "--kredi"):
            try:
                result = subprocess.run(
                    [sys.executable, str(rates_script), flag],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0 and result.stdout.strip():
                    print(result.stdout)
            except Exception:
                pass
        return

    # ── Firma profili ──
    if args.profil:
        profil_file = ROOT / "data" / "RAGIP_AGA" / "profil.json"
        if not profil_file.exists():
            print("Firma profili tanımlanmamış.")
            print("Oluşturmak için: /ragip-profil kaydet firma_adi=X sektor=Y is_tipi=Z")
            return
        p = json.loads(profil_file.read_text(encoding="utf-8"))
        doviz = p.get("doviz_riski", {})
        doviz_str = ", ".join(doviz.get("para_birimleri", [])) if doviz.get("var") else "Yok"
        stok = p.get("stok", {})
        stok_str = stok.get("tur", "-") if stok.get("var") else "Yok"
        print("=== FİRMA PROFİLİ ===")
        print()
        print(f"Firma     : {p.get('firma_adi', '-')}")
        print(f"Sektör    : {p.get('sektor', '-')}")
        print(f"İş Tipi   : {p.get('is_tipi', '-')}")
        print(f"Gelir     : {p.get('gelir_modeli', '-')}")
        print(f"Büyüklük  : {p.get('firma_buyuklugu', '-')}")
        print(f"Müşteri   : {p.get('musteri_tipi', '-')}")
        print()
        print(f"Döviz Riski: {doviz_str}" + (f" ({doviz.get('yon', '-')})" if doviz.get("var") else ""))
        print(f"Stok       : {stok_str}")
        print(f"Vade Alıcı : {p.get('vade_alici', '-')} gün")
        print(f"Vade Satıcı: {p.get('vade_satici', '-')} gün")
        if p.get("notlar"):
            print(f"Notlar     : {p['notlar']}")
        print(f"Güncelleme : {p.get('guncelleme', '-')}")
        return

    # ── Finansal hesaplama modu ──
    if args.calc:
        hesap = FinansalHesap()

        if args.calc == "vade-farki":
            if any(v is None for v in [args.anapara, args.oran, args.gun]):
                print("Gerekli: --anapara --oran --gun")
                sys.exit(1)
            sonuc = hesap.vade_farki(args.anapara, args.oran, args.gun)
            display_calc_result("Vade Farkı Hesabı", sonuc)

        elif args.calc == "tvm":
            if any(v is None for v in [args.anapara, args.gun]):
                print("Gerekli: --anapara --gun [--repo-orani (varsayılan: TCMB)]")
                sys.exit(1)
            repo = args.repo_orani or get_tcmb_rates_with_search()["politika_faizi"]
            sonuc = hesap.tvm_gunluk_maliyet(args.anapara, repo, args.gun)
            display_calc_result("TVM - Fırsat Maliyeti", sonuc)

        elif args.calc == "iskonto":
            if any(v is None for v in [args.anapara, args.oran, args.gun]):
                print("Gerekli: --anapara --oran --gun")
                sys.exit(1)
            sonuc = hesap.erken_odeme_iskonto(args.anapara, args.oran, args.gun)
            display_calc_result("Erken Ödeme Maksimum İskonto", sonuc)

        elif args.calc == "indiferans":
            if any(v is None for v in [args.anapara, args.oran, args.gun]):
                print("Gerekli: --anapara --oran --gun [--firsat-orani (varsayılan: TCMB)]")
                sys.exit(1)
            firsat = args.firsat_orani or get_tcmb_rates_with_search()["politika_faizi"]
            sonuc = hesap.indiferans_iskonto(args.anapara, args.oran, firsat, args.gun)
            display_calc_result("İndiferans (Break-Even) İskonto", sonuc)

        elif args.calc == "ncd":
            if not all([args.dio is not None, args.dso is not None, args.dpo is not None]):
                print("Gerekli: --dio --dso --dpo")
                sys.exit(1)
            sonuc = hesap.nakit_cevrim_dongusu(args.dio, args.dso, args.dpo)
            display_calc_result("Nakit Çevrim Döngüsü", sonuc)

        elif args.calc == "doviz":
            if not args.usd_tutar or not args.gun:
                print("Gerekli: --usd-tutar --gun [--usd-faiz (varsayilan: 4.5)]")
                sys.exit(1)
            rates = get_tcmb_rates_with_search()
            spot = rates.get("usd_kuru", _FB["usd_kuru"])
            r_tl = rates.get("politika_faizi", _FB["politika_faizi"])
            r_usd = args.usd_faiz
            sonuc = hesap.doviz_forward(spot, r_tl, r_usd, args.gun)
            display_calc_result("Doviz Forward Kur Tahmini", sonuc)

        elif args.calc == "ithalat":
            if not args.usd_tutar:
                print("Gerekli: --usd-tutar [--navlun --gtip-vergi]")
                sys.exit(1)
            rates = get_tcmb_rates_with_search()
            spot = rates.get("usd_kuru", _FB["usd_kuru"])
            sonuc = hesap.ithalat_maliyet(
                usd_tutar=args.usd_tutar,
                spot_kur=spot,
                navlun_usd=args.navlun,
                gtip_vergi_pct=args.gtip_vergi,
            )
            display_calc_result("Ithalat Maliyet Hesabi", sonuc)

        # ── Arbitraj hesaplamalari ──

        elif args.calc == "cip-arbitraj":
            if not args.market_forward or not args.gun:
                print("Gerekli: --market-forward --gun [--usd-faiz --islem-maliyeti]")
                sys.exit(1)
            rates = get_tcmb_rates_with_search()
            spot = rates.get("usd_kuru", _FB["usd_kuru"])
            r_tl = rates.get("politika_faizi", _FB["politika_faizi"])
            sonuc = hesap.covered_interest_arbitrage(
                spot, args.market_forward, r_tl, args.usd_faiz, args.gun, args.islem_maliyeti
            )
            display_calc_result("CIP Faiz Paritesi Arbitraji", sonuc)

        elif args.calc == "ucgen-arbitraj":
            rates = get_tcmb_rates_with_search()
            usd_try = rates.get("usd_kuru", _FB["usd_kuru"])
            eur_try = rates.get("eur_kuru", _FB["eur_kuru"])
            eur_usd = args.eur_usd or (eur_try / usd_try if usd_try > 0 else 1.18)
            sonuc = hesap.ucgen_kur_arbitraji(usd_try, eur_try, eur_usd, args.islem_maliyeti)
            display_calc_result("Ucgen Kur Arbitraji", sonuc)

        elif args.calc == "vade-mevduat":
            if any(v is None for v in [args.anapara, args.oran, args.gun]):
                print("Gerekli: --anapara --oran --gun [--mevduat-oran]")
                sys.exit(1)
            mevduat_oran = args.mevduat_oran
            if mevduat_oran is None:
                mevduat_oran = get_tcmb_rates_with_search().get("politika_faizi", _FB["politika_faizi"])
            sonuc = hesap.vade_mevduat_arbitraji(args.anapara, args.oran, args.gun, mevduat_oran)
            display_calc_result("Vade Farki vs Mevduat Arbitraji", sonuc)

        elif args.calc == "carry-trade":
            if args.gun is None:
                print("Gerekli: --gun [--usd-faiz --beklenen-kur]")
                sys.exit(1)
            rates = get_tcmb_rates_with_search()
            spot = rates.get("usd_kuru", _FB["usd_kuru"])
            r_tl = rates.get("politika_faizi", _FB["politika_faizi"])
            sonuc = hesap.carry_trade_analizi(spot, r_tl, args.usd_faiz, args.gun, args.beklenen_kur)
            display_calc_result("Carry Trade / Faiz Arbitraji", sonuc)

        return

    # ── Geçmiş ──
    if args.history:
        show_history(log_dir, args.history_limit)
        return

    # ── İnteraktif mod ──
    if args.interactive:
        interactive_mode(config, log_dir)
        return

    # ── Tek soru ──
    if not args.prompt:
        parser.print_help()
        sys.exit(0)

    # Dosya varsa oku ve prompt'a ekle
    full_prompt = args.prompt
    if args.file:
        try:
            file_content = read_file_content(args.file)
            filename = Path(args.file).name

            if isinstance(file_content, dict):
                # pdfplumber ile zengin icerik dondu
                metin = file_content.get("metin", "")
                tablolar = file_content.get("tablolar", [])
                fatura_meta = file_content.get("fatura_meta", {})

                dosya_blok = f"--- DOSYA: {filename} ---\n{metin}\n"
                if fatura_meta:
                    dosya_blok += "\n--- FATURA VERILERI ---\n"
                    for k, v in fatura_meta.items():
                        dosya_blok += f"  {k}: {v}\n"
                if tablolar:
                    dosya_blok += f"\n--- TABLOLAR ({len(tablolar)} adet) ---\n"
                    for i, tbl in enumerate(tablolar[:3], 1):
                        dosya_blok += f"Tablo {i}:\n"
                        for row in tbl[:20]:  # Maks 20 satir/tablo
                            dosya_blok += "  | " + " | ".join(str(c or "") for c in row) + " |\n"
                dosya_blok += "--- DOSYA SONU ---"
                full_prompt = f"{args.prompt}\n\n{dosya_blok}"
                print(f"[OK] {filename} okundu ({len(metin)} karakter, {len(tablolar)} tablo)", file=sys.stderr)
            else:
                full_prompt = (
                    f"{args.prompt}\n\n"
                    f"--- DOSYA: {filename} ---\n"
                    f"{file_content}\n"
                    f"--- DOSYA SONU ---"
                )
                print(f"[OK] {filename} okundu ({len(file_content)} karakter)", file=sys.stderr)
        except Exception as e:
            print(f"[HATA] Dosya okunamadi: {e}", file=sys.stderr)
            sys.exit(1)

    # Güncel TCMB oranını prompt'a otomatik ekle
    rates = get_tcmb_rates_with_search()
    rate_context = (
        f"\n[Güncel Piyasa Verileri: TCMB Politika Faizi %{rates['politika_faizi']}, "
        f"Yasal Gecikme Faizi %{rates['yasal_gecikme_faizi']}, "
        f"Kaynak: {rates['kaynak']}]"
    )
    full_prompt = full_prompt + rate_context

    # Firma profili varsa prompt'a ekle
    profil_file = ROOT / "data" / "RAGIP_AGA" / "profil.json"
    if profil_file.exists():
        try:
            p = json.loads(profil_file.read_text(encoding="utf-8"))
            doviz = p.get("doviz_riski", {})
            doviz_str = ", ".join(doviz.get("para_birimleri", [])) if doviz.get("var") else "yok"
            profil_ctx = (
                f"\n[Firma Profili: {p.get('firma_adi', '-')}, "
                f"Sektor: {p.get('sektor', '-')}, "
                f"Is: {p.get('is_tipi', '-')}, "
                f"Doviz: {doviz_str}, "
                f"Buyukluk: {p.get('firma_buyuklugu', '-')}]"
            )
            full_prompt = full_prompt + profil_ctx
        except (json.JSONDecodeError, KeyError):
            pass

    response, model, duration_ms, tokens = call_llm(config, full_prompt)
    display_response(response, model, duration_ms, tokens)

    if config["standalone"].get("log_to_file", True):
        save_to_history(log_dir, args.prompt, response, model, duration_ms, tokens)

    if args.save_to:
        Path(args.save_to).write_text(response, encoding="utf-8")
        print(f"Yanıt kaydedildi: {args.save_to}")


if __name__ == "__main__":
    main()

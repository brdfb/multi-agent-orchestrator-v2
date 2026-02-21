"""
Ragip Aga - FinansalHesap sinifi unit testleri.
"""
import sys
from pathlib import Path

# scripts/ dizinini import path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ragip_aga import FinansalHesap


class TestVadeFarki:
    def test_basit_hesap(self):
        """100K x %3/ay x 30 gun = 3000 TL vade farki"""
        sonuc = FinansalHesap.vade_farki(100_000, 3.0, 30)
        assert sonuc["vade_farki_tl"] == 3000.0
        assert sonuc["toplam_tl"] == 103_000.0

    def test_45_gun(self):
        """100K x %3/ay x 45 gun = 4500 TL"""
        sonuc = FinansalHesap.vade_farki(100_000, 3.0, 45)
        assert sonuc["vade_farki_tl"] == 4500.0

    def test_sifir_gun(self):
        """0 gun = 0 vade farki"""
        sonuc = FinansalHesap.vade_farki(100_000, 3.0, 0)
        assert sonuc["vade_farki_tl"] == 0.0
        assert sonuc["toplam_tl"] == 100_000.0

    def test_gunluk_maliyet(self):
        """Gunluk maliyet = vade_farki / gun"""
        sonuc = FinansalHesap.vade_farki(100_000, 3.0, 30)
        assert sonuc["gunluk_maliyet_tl"] == 100.0


class TestTvmGunlukMaliyet:
    def test_basit(self):
        """100K x %42.5/yil x 30 gun"""
        sonuc = FinansalHesap.tvm_gunluk_maliyet(100_000, 42.5, 30)
        beklenen = 100_000 * 0.425 * 30 / 365
        assert abs(sonuc["firsatmaliyeti_tl"] - round(beklenen, 2)) < 0.01

    def test_365_gun(self):
        """Tam yil = anapara x oran"""
        sonuc = FinansalHesap.tvm_gunluk_maliyet(100_000, 42.5, 365)
        assert abs(sonuc["firsatmaliyeti_tl"] - 42_500.0) < 0.01

    def test_gunluk_deger(self):
        sonuc = FinansalHesap.tvm_gunluk_maliyet(100_000, 42.5, 30)
        assert sonuc["gunluk_tl"] > 0


class TestErkenOdemeIskonto:
    def test_basit(self):
        """100K x %3/ay x 30 gun kazanim = 3000 TL max iskonto"""
        sonuc = FinansalHesap.erken_odeme_iskonto(100_000, 3.0, 30)
        assert sonuc["max_iskonto_tl"] == 3000.0
        assert sonuc["iskonto_pct"] == 3.0

    def test_kisa_vade(self):
        """15 gun erken odeme = yarisinda iskonto"""
        sonuc = FinansalHesap.erken_odeme_iskonto(100_000, 3.0, 15)
        assert sonuc["max_iskonto_tl"] == 1500.0


class TestNakitCevrimDongusu:
    def test_pozitif(self):
        """DIO=45, DSO=30, DPO=20 -> NCD=55 (nakit baglaniyor)"""
        sonuc = FinansalHesap.nakit_cevrim_dongusu(45, 30, 20)
        assert sonuc["nakit_cevrim_dongusu"] == 55
        assert "bağlanıyor" in sonuc["yorum"].lower()

    def test_negatif(self):
        """DIO=10, DSO=15, DPO=60 -> NCD=-35 (tedarikciler finanse ediyor)"""
        sonuc = FinansalHesap.nakit_cevrim_dongusu(10, 15, 60)
        assert sonuc["nakit_cevrim_dongusu"] == -35
        assert "finanse" in sonuc["yorum"].lower()

    def test_saglikli(self):
        """DIO=20, DSO=15, DPO=25 -> NCD=10 (saglikli)"""
        sonuc = FinansalHesap.nakit_cevrim_dongusu(20, 15, 25)
        assert sonuc["nakit_cevrim_dongusu"] == 10
        assert "Sağlıklı" in sonuc["yorum"]


class TestOdemePlaniKarsilastir:
    def test_siralama(self):
        """Bugunki deger artan siralamayla doner"""
        secenekler = [
            {"ad": "Hemen", "gun": 1, "tutar": 100_000},
            {"ad": "60 gun", "gun": 60, "tutar": 105_000},
            {"ad": "90 gun", "gun": 90, "tutar": 108_000},
        ]
        sonuc = FinansalHesap.odeme_plani_karsilastir(100_000, secenekler, 42.5)
        # Artan siralama kontrolu
        for i in range(len(sonuc) - 1):
            assert sonuc[i]["bugunki_degeri_tl"] <= sonuc[i + 1]["bugunki_degeri_tl"]

    def test_iki_secenek(self):
        secenekler = [
            {"ad": "A", "gun": 30, "tutar": 102_000},
            {"ad": "B", "gun": 60, "tutar": 105_000},
        ]
        sonuc = FinansalHesap.odeme_plani_karsilastir(100_000, secenekler, 42.5)
        assert len(sonuc) == 2
        for s in sonuc:
            assert "bugunki_degeri_tl" in s


class TestDovizForward:
    def test_forward_buyuk(self):
        """TL faizi > USD faizi iken forward > spot olmali"""
        sonuc = FinansalHesap.doviz_forward(38.50, 42.5, 4.5, 90)
        assert sonuc["forward_kur"] > sonuc["spot_kur"]

    def test_prim_pozitif(self):
        """Pozitif faiz farki pozitif prim uretmeli"""
        sonuc = FinansalHesap.doviz_forward(38.50, 42.5, 4.5, 90)
        assert sonuc["prim_pct"] > 0

    def test_sifir_gun(self):
        """0 gun icin forward = spot"""
        sonuc = FinansalHesap.doviz_forward(38.50, 42.5, 4.5, 0)
        assert abs(sonuc["forward_kur"] - 38.50) < 0.001

    def test_esit_faiz(self):
        """Faizler esitken forward = spot"""
        sonuc = FinansalHesap.doviz_forward(38.50, 10.0, 10.0, 180)
        assert abs(sonuc["forward_kur"] - 38.50) < 0.01

    def test_formul_dogrulama(self):
        """F = S * (1 + r_TL * t) / (1 + r_USD * t)"""
        spot = 38.50
        r_tl = 42.5
        r_usd = 4.5
        gun = 90
        t = gun / 365
        beklenen = spot * (1 + r_tl / 100 * t) / (1 + r_usd / 100 * t)
        sonuc = FinansalHesap.doviz_forward(spot, r_tl, r_usd, gun)
        assert abs(sonuc["forward_kur"] - round(beklenen, 4)) < 0.001


class TestIthalatMaliyet:
    def test_basit(self):
        """Sadece FOB, gumruk ve KDV yok"""
        sonuc = FinansalHesap.ithalat_maliyet(10_000, 38.50, 0, 0, 20.0)
        cif_tl = 10_000 * 38.50
        kdv = cif_tl * 0.20
        assert sonuc["cif_tl"] == cif_tl
        assert sonuc["gumruk_vergisi_tl"] == 0
        assert abs(sonuc["kdv_tl"] - kdv) < 0.01
        assert abs(sonuc["toplam_tl"] - (cif_tl + kdv)) < 0.01

    def test_navlun_dahil(self):
        """FOB + navlun = CIF"""
        sonuc = FinansalHesap.ithalat_maliyet(10_000, 38.50, 2_000, 0)
        assert sonuc["cif_usd"] == 12_000
        assert sonuc["cif_tl"] == 12_000 * 38.50

    def test_gumruk_vergisi(self):
        """%10 gumruk vergisi"""
        sonuc = FinansalHesap.ithalat_maliyet(10_000, 38.50, 0, 10.0)
        cif_tl = 10_000 * 38.50
        gumruk = cif_tl * 0.10
        assert abs(sonuc["gumruk_vergisi_tl"] - gumruk) < 0.01

    def test_tam_hesap(self):
        """FOB 50K + navlun 3K, %10 gumruk, %20 KDV"""
        sonuc = FinansalHesap.ithalat_maliyet(50_000, 38.50, 3_000, 10.0, 20.0)
        cif_usd = 53_000
        cif_tl = cif_usd * 38.50
        gumruk = cif_tl * 0.10
        kdv_matrah = cif_tl + gumruk
        kdv = kdv_matrah * 0.20
        toplam = cif_tl + gumruk + kdv
        assert sonuc["cif_usd"] == cif_usd
        assert abs(sonuc["toplam_tl"] - round(toplam, 2)) < 0.01

    def test_birim_maliyet(self):
        """Birim maliyet = toplam / usd_tutar"""
        sonuc = FinansalHesap.ithalat_maliyet(10_000, 38.50, 0, 0, 20.0)
        assert abs(sonuc["birim_maliyet_tl_usd"] - sonuc["toplam_tl"] / 10_000) < 0.001


class TestIndiferansIskonto:
    def test_basit(self):
        """Indiferans = karsi tarafin firsat maliyeti"""
        sonuc = FinansalHesap.indiferans_iskonto(100_000, 3.0, 42.5, 30)
        # Max iskonto = 100K x 3% x 30/30 = 3000
        assert sonuc["max_iskonto_tl"] == 3000.0
        # Indiferans = 100K x 42.5% x 30/365
        beklenen = 100_000 * 0.425 * 30 / 365
        assert abs(sonuc["indiferans_tl"] - round(beklenen, 2)) < 0.01

    def test_muzakere_araligi(self):
        """Dusuk firsat orani ile indiferans < max iskonto olmali"""
        # 3%/ay = ~36% yillik; firsat orani 25% < 36% -> indiferans < max_iskonto
        sonuc = FinansalHesap.indiferans_iskonto(100_000, 3.0, 25.0, 30)
        assert sonuc["indiferans_tl"] < sonuc["max_iskonto_tl"]

    def test_yuksek_firsat_orani(self):
        """Yuksek firsat orani ile indiferans > max iskonto (muzakere zor)"""
        # 3%/ay = ~36% yillik; firsat orani 42.5% > 36% -> indiferans > max_iskonto
        sonuc = FinansalHesap.indiferans_iskonto(100_000, 3.0, 42.5, 30)
        assert sonuc["indiferans_tl"] > sonuc["max_iskonto_tl"]

    def test_sifir_gun(self):
        """0 gun erken odeme = her iki taraf 0"""
        sonuc = FinansalHesap.indiferans_iskonto(100_000, 3.0, 42.5, 0)
        assert sonuc["max_iskonto_tl"] == 0.0
        assert sonuc["indiferans_tl"] == 0.0

    def test_negatif_tutar_reddedilir(self):
        import pytest as pt
        with pt.raises(ValueError, match="negatif"):
            FinansalHesap.indiferans_iskonto(-100_000, 3.0, 42.5, 30)


import pytest


class TestInputValidation:
    """Negatif ve sinir disi degerler icin validation testleri."""

    def test_vade_farki_negatif_anapara(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.vade_farki(-100_000, 3.0, 30)

    def test_vade_farki_negatif_gun(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.vade_farki(100_000, 3.0, -10)

    def test_vade_farki_oran_sinir_disi(self):
        with pytest.raises(ValueError, match="0-1000"):
            FinansalHesap.vade_farki(100_000, 1500.0, 30)

    def test_tvm_negatif_tutar(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.tvm_gunluk_maliyet(-50_000, 42.5, 30)

    def test_erken_odeme_negatif(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.erken_odeme_iskonto(-100_000, 3.0, 30)

    def test_doviz_forward_negatif_spot(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.doviz_forward(-38.50, 42.5, 4.5, 90)

    def test_doviz_forward_oran_sinir_disi(self):
        with pytest.raises(ValueError, match="0-1000"):
            FinansalHesap.doviz_forward(38.50, -5.0, 4.5, 90)

    def test_ithalat_negatif_tutar(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.ithalat_maliyet(-10_000, 38.50, 0, 0)

    def test_ithalat_negatif_navlun(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.ithalat_maliyet(10_000, 38.50, -500, 0)

    def test_ithalat_kdv_sinir_disi(self):
        with pytest.raises(ValueError, match="0-100"):
            FinansalHesap.ithalat_maliyet(10_000, 38.50, 0, 0, 150.0)

    def test_sifir_anapara_reddedilir(self):
        """0 anapara gecersiz — sifir tutarla finansal hesap anlamsiz"""
        with pytest.raises(ValueError, match="sifir veya negatif"):
            FinansalHesap.vade_farki(0, 3.0, 30)


# ═══════════════════════════════════════════════════════════════════════
# Arbitraj Hesaplamalari
# ═══════════════════════════════════════════════════════════════════════


class TestCoveredInterestArbitrage:
    def test_cip_dengede(self):
        """Teorik forward = piyasa forward ise arbitraj yok"""
        spot = 43.69
        r_tl, r_usd, gun = 37.0, 4.5, 90
        t = gun / 365
        teorik = spot * (1 + r_tl / 100 * t) / (1 + r_usd / 100 * t)
        sonuc = FinansalHesap.covered_interest_arbitrage(spot, round(teorik, 4), r_tl, r_usd, gun)
        assert sonuc["arbitraj_var"] is False

    def test_cip_arbitraj_var(self):
        """Piyasa forward yuksekse arbitraj firsati olmali"""
        spot = 43.69
        r_tl, r_usd, gun = 37.0, 4.5, 90
        t = gun / 365
        teorik = spot * (1 + r_tl / 100 * t) / (1 + r_usd / 100 * t)
        market_forward = teorik * 1.005  # %0.5 sapma
        sonuc = FinansalHesap.covered_interest_arbitrage(spot, market_forward, r_tl, r_usd, gun)
        assert sonuc["arbitraj_var"] is True
        assert sonuc["tahmini_kar_pct"] > 0

    def test_cip_islem_maliyeti_filtresi(self):
        """Sapma islem maliyetinden kucukse arbitraj yok"""
        spot = 43.69
        r_tl, r_usd, gun = 37.0, 4.5, 90
        t = gun / 365
        teorik = spot * (1 + r_tl / 100 * t) / (1 + r_usd / 100 * t)
        market_forward = teorik * 1.0005  # %0.05 sapma < %0.1
        sonuc = FinansalHesap.covered_interest_arbitrage(spot, market_forward, r_tl, r_usd, gun, 0.1)
        assert sonuc["arbitraj_var"] is False

    def test_cip_negatif_spot_reddedilir(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.covered_interest_arbitrage(-43.69, 45.0, 37.0, 4.5, 90)


class TestUcgenKurArbitraji:
    def test_tutarli_kurlar_arbitraj_yok(self):
        """EUR/USD = EUR/TRY / USD/TRY ise arbitraj yok"""
        usd_try = 43.69
        eur_try = 51.48
        eur_usd = eur_try / usd_try
        sonuc = FinansalHesap.ucgen_kur_arbitraji(usd_try, eur_try, eur_usd)
        assert sonuc["arbitraj_var"] is False
        assert abs(sonuc["sapma_pct"]) < 0.01

    def test_tutarsiz_kurlar_sapma(self):
        """Tutarsiz kurlarda sapma tespiti"""
        sonuc = FinansalHesap.ucgen_kur_arbitraji(43.69, 51.48, 1.20)
        # Dolayli: 1.20 * 43.69 = 52.428 vs dogrudan 51.48
        assert abs(sonuc["sapma_pct"]) > 0.1

    def test_negatif_kur_reddedilir(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.ucgen_kur_arbitraji(-43.69, 51.48, 1.18)


class TestVadeMevduatArbitraji:
    def test_mevduat_karli(self):
        """Mevduat orani > vade farki yillik orani ise mevduat karli"""
        sonuc = FinansalHesap.vade_mevduat_arbitraji(100_000, 3.0, 30, 45.0)
        assert sonuc["mevduat_getirisi_tl"] > sonuc["vade_farki_maliyeti_tl"]
        assert "mevduat" in sonuc["karar"].lower()

    def test_erken_odeme_karli(self):
        """Vade farki yillik orani > mevduat orani ise erken odeme karli"""
        sonuc = FinansalHesap.vade_mevduat_arbitraji(100_000, 5.0, 30, 37.0)
        assert sonuc["vade_farki_maliyeti_tl"] > sonuc["mevduat_getirisi_tl"]
        assert "erken" in sonuc["karar"].lower()

    def test_net_fark_hesabi(self):
        """Net fark = mevduat - vade farki"""
        sonuc = FinansalHesap.vade_mevduat_arbitraji(100_000, 3.0, 30, 45.0)
        beklenen = sonuc["mevduat_getirisi_tl"] - sonuc["vade_farki_maliyeti_tl"]
        assert abs(sonuc["net_fark_tl"] - beklenen) < 0.01

    def test_sifir_gun(self):
        """0 gun = her iki taraf 0"""
        sonuc = FinansalHesap.vade_mevduat_arbitraji(100_000, 3.0, 0, 45.0)
        assert sonuc["vade_farki_maliyeti_tl"] == 0.0
        assert sonuc["mevduat_getirisi_tl"] == 0.0

    def test_negatif_anapara_reddedilir(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.vade_mevduat_arbitraji(-100_000, 3.0, 30, 45.0)


class TestCarryTradeAnalizi:
    def test_basabas_kur_forward(self):
        """Basabas kuru = CIP forward kuru olmali"""
        spot = 43.69
        r_tl, r_usd, gun = 37.0, 4.5, 90
        t = gun / 365
        beklenen = spot * (1 + r_tl / 100 * t) / (1 + r_usd / 100 * t)
        sonuc = FinansalHesap.carry_trade_analizi(spot, r_tl, r_usd, gun)
        assert abs(sonuc["basabas_kur"] - round(beklenen, 4)) < 0.01

    def test_unhedged_pozitif(self):
        """TL faizi > USD faizi iken unhedged kar pozitif olmali"""
        sonuc = FinansalHesap.carry_trade_analizi(43.69, 37.0, 4.5, 90)
        assert sonuc["unhedged_kar_pct"] > 0

    def test_beklenen_kur_etkisi(self):
        """Beklenen kur verilmisse hesaplanmali"""
        sonuc = FinansalHesap.carry_trade_analizi(43.69, 37.0, 4.5, 90, beklenen_kur=50.0)
        assert sonuc["beklenen_kur_kar_pct"] is not None

    def test_beklenen_kur_none(self):
        """Beklenen kur verilmezse None olmali"""
        sonuc = FinansalHesap.carry_trade_analizi(43.69, 37.0, 4.5, 90)
        assert sonuc["beklenen_kur_kar_pct"] is None

    def test_sifir_gun(self):
        """0 gun = basabas spot, kar 0"""
        sonuc = FinansalHesap.carry_trade_analizi(43.69, 37.0, 4.5, 0)
        assert abs(sonuc["basabas_kur"] - 43.69) < 0.01
        assert abs(sonuc["unhedged_kar_pct"]) < 0.01

    def test_negatif_spot_reddedilir(self):
        with pytest.raises(ValueError, match="negatif"):
            FinansalHesap.carry_trade_analizi(-43.69, 37.0, 4.5, 90)

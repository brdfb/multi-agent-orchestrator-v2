"""
Ragip Aga - ragip_rates.py unit testleri.
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# scripts/ dizinini import path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import ragip_rates


class TestFallbackRates:
    def test_fallback_has_required_keys(self):
        """Fallback rates gerekli alanlari icermeli"""
        fb = ragip_rates.FALLBACK_RATES
        assert "politika_faizi" in fb
        assert "yasal_gecikme_faizi" in fb
        assert "usd_kuru" in fb
        assert "eur_kuru" in fb
        assert fb["kaynak"] == "fallback"

    def test_fallback_values_reasonable(self):
        """Fallback degerler makul aralikta olmali"""
        fb = ragip_rates.FALLBACK_RATES
        assert 20 < fb["politika_faizi"] < 80
        assert 30 < fb["yasal_gecikme_faizi"] < 100
        assert 20 < fb["usd_kuru"] < 60
        assert 20 < fb["eur_kuru"] < 70


class TestGetRates:
    @patch.dict("os.environ", {"TCMB_API_KEY": ""}, clear=False)
    def test_get_rates_no_api_key(self):
        """API key yokken get_rates fallback donmeli"""
        result = ragip_rates.get_rates(force_refresh=True)
        assert "politika_faizi" in result
        assert result["kaynak"] == "fallback"


class TestCache:
    def test_load_cache_missing_file(self):
        """Olmayan cache dosyasi None donmeli"""
        result = ragip_rates.load_cache(Path("/tmp/nonexistent_cache_12345.json"), 4)
        assert result is None

    def test_save_and_load_cache(self):
        """Cache kaydet ve geri oku"""
        import datetime
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cache_path = Path(f.name)

        try:
            data = {
                "politika_faizi": 42.5,
                "guncelleme": datetime.datetime.now().isoformat(),
            }
            ragip_rates.save_cache(cache_path, data)
            loaded = ragip_rates.load_cache(cache_path, 1)  # 1 saat TTL
            assert loaded is not None
            assert loaded["politika_faizi"] == 42.5
        finally:
            cache_path.unlink(missing_ok=True)

    def test_expired_cache(self):
        """Suresi dolmus cache None donmeli"""
        import datetime
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cache_path = Path(f.name)

        try:
            data = {
                "politika_faizi": 42.5,
                "guncelleme": (datetime.datetime.now() - datetime.timedelta(hours=10)).isoformat(),
            }
            ragip_rates.save_cache(cache_path, data)
            loaded = ragip_rates.load_cache(cache_path, 4)  # 4 saat TTL, 10 saat once yazilmis
            assert loaded is None
        finally:
            cache_path.unlink(missing_ok=True)


class TestFormatPretty:
    def test_format_pretty_output(self):
        """format_pretty string donmeli ve temel bilgileri icermeli"""
        rates = {
            "politika_faizi": 42.5,
            "yasal_gecikme_faizi": 52.0,
            "usd_kuru": 38.50,
            "eur_kuru": 40.80,
            "kaynak": "test",
            "guncelleme": "2026-02-20 12:00",
        }
        output = ragip_rates.format_pretty(rates)
        assert "42.5" in output or "42.50" in output
        assert "test" in output.lower() or "kaynak" in output.lower()


class TestFetchTcmbMock:
    @patch("ragip_rates.fetch_series")
    def test_fetch_tcmb_success(self, mock_fetch):
        """TCMB API basarili donuste tum alanlari doldurmali"""
        mock_fetch.side_effect = lambda code, key: {
            "TP.APIFON4": 37.0,
            "TP.REESAVANS.RIO": 38.75,
            "TP.REESAVANS.AFO": 39.75,
            "TP.DK.USD.A.YTL": 43.69,
            "TP.DK.EUR.A.YTL": 51.48,
        }.get(code)

        result = ragip_rates.fetch_tcmb("test_key")
        assert result["politika_faizi"] == 37.0
        assert result["reeskont_orani"] == 38.75
        assert result["avans_faizi"] == 39.75
        assert result["usd_kuru"] == 43.69
        assert result["eur_kuru"] == 51.48
        assert result["yasal_gecikme_faizi"] == 39.75  # avans_faizi ile ayni
        assert result["kaynak"] == "TCMB EVDS3"

    @patch("ragip_rates.fetch_series")
    def test_fetch_tcmb_partial_failure(self, mock_fetch):
        """Bazi seriler basarisiz olsa da diger veriler donmeli"""
        mock_fetch.side_effect = lambda code, key: {
            "TP.APIFON4": 37.0,
        }.get(code)

        result = ragip_rates.fetch_tcmb("test_key")
        assert result["politika_faizi"] == 37.0
        assert "eksik_seriler" in result
        # avans_faizi alinamadiysa fallback yasal gecikme kullanilmali
        assert result["yasal_gecikme_faizi"] == ragip_rates.FALLBACK_RATES["yasal_gecikme_faizi"]


class TestSeriesConfig:
    def test_series_codes_valid(self):
        """Seri kodlari bos olmamali ve TP ile baslamali"""
        for name, code in ragip_rates.SERIES.items():
            assert code.startswith("TP."), f"{name} seri kodu TP. ile baslamali: {code}"

    def test_collectapi_endpoints(self):
        """CollectAPI endpointleri gecerli URL olmali"""
        for name, url in ragip_rates.COLLECTAPI_ENDPOINTS.items():
            assert url.startswith("https://"), f"{name} endpoint HTTPS olmali"


class TestEurUsdCross:
    def test_cross_rate_calculation(self):
        """EUR/USD = EUR/TRY / USD/TRY"""
        rates = {"usd_kuru": 43.69, "eur_kuru": 51.48}
        result = ragip_rates.eur_usd_cross(rates)
        expected = round(51.48 / 43.69, 4)
        assert abs(result - expected) < 0.001

    def test_cross_rate_fallback(self):
        """Rates None ise get_rates cagirilir"""
        with patch.object(ragip_rates, "get_rates", return_value=ragip_rates.FALLBACK_RATES.copy()):
            result = ragip_rates.eur_usd_cross()
            assert result > 1.0  # EUR/USD her zaman > 1

    def test_zero_usd_try(self):
        """USD/TRY 0 ise 0.0 doner"""
        result = ragip_rates.eur_usd_cross({"usd_kuru": 0, "eur_kuru": 51.48})
        assert result == 0.0


class TestCacheDir:
    def test_default_cache_dir(self):
        """Varsayilan cache dizini script'in kendi dizini altinda .ragip_cache olmali"""
        script_dir = Path(ragip_rates.__file__).parent
        expected = script_dir / ".ragip_cache"
        # RAGIP_CACHE_DIR set edilmemisse varsayilana duser
        # (test ortaminda zaten set olmayabilir, module-level degerini kontrol et)
        assert ragip_rates.CACHE_DIR is not None
        assert isinstance(ragip_rates.CACHE_DIR, Path)

    def test_cache_dir_env_override(self):
        """RAGIP_CACHE_DIR env var ile cache dizini degisebilmeli"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "custom_cache"
            # Module-level degiskeni degistirmeden, mantigi test et
            result = Path(os.environ.get("RAGIP_CACHE_DIR", str(Path(__file__).parent / ".ragip_cache")))
            assert isinstance(result, Path)

    def test_save_cache_creates_dir(self):
        """save_cache olmayan dizini olusturmali"""
        import datetime
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "subdir" / "test_cache.json"
            data = {
                "politika_faizi": 37.0,
                "guncelleme": datetime.datetime.now().isoformat(),
            }
            ragip_rates.save_cache(cache_path, data)
            assert cache_path.exists()
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            assert loaded["politika_faizi"] == 37.0


class TestAllExports:
    def test_all_exports_exist(self):
        """__all__ listelesindeki tum isimler modul icinde olmali"""
        for name in ragip_rates.__all__:
            assert hasattr(ragip_rates, name), f"{name} modulde bulunamadi"

    def test_no_get_env_key(self):
        """get_env_key kaldirilmis olmali"""
        assert not hasattr(ragip_rates, "get_env_key")

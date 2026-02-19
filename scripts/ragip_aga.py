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

    # Son çare fallback
    return {
        "politika_faizi": 42.5,
        "yasal_gecikme_faizi": 52.0,
        "kaynak": "fallback",
        "guncelleme": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "uyari": "TCMB_API_KEY eksik. Kayıt: https://evds2.tcmb.gov.tr"
    }


# ─── Finansal Hesap Motoru ────────────────────────────────────────────────────

class FinansalHesap:
    """Ragıp Aga'nın finansal hesap motoru."""

    @staticmethod
    def vade_farki(anapara: float, aylik_oran_pct: float, gun: int) -> dict:
        """
        Vade farkı hesapla.
        anapara: TL cinsinden
        aylik_oran_pct: aylık oran yüzde olarak (örn: 3.0 = %3/ay)
        gun: vade gün sayısı
        """
        aylik_oran = aylik_oran_pct / 100
        vade_farki = anapara * aylik_oran * gun / 30
        toplam = anapara + vade_farki
        return {
            "anapara": anapara,
            "aylik_oran_pct": aylik_oran_pct,
            "gun": gun,
            "vade_farki_tl": round(vade_farki, 2),
            "toplam_tl": round(toplam, 2),
            "gunluk_maliyet_tl": round(vade_farki / gun, 2),
        }

    @staticmethod
    def tvm_gunluk_maliyet(tutar: float, yillik_oran_pct: float, gun: int) -> dict:
        """
        Paranın zaman değeri - belirtilen süre için fırsat maliyeti.
        yillik_oran_pct: yıllık oran % (örn: repo oranı, 42.5)
        """
        yillik_oran = yillik_oran_pct / 100
        maliyet = tutar * yillik_oran * gun / 365
        return {
            "tutar": tutar,
            "yillik_oran_pct": yillik_oran_pct,
            "gun": gun,
            "firsatmaliyeti_tl": round(maliyet, 2),
            "gunluk_tl": round(maliyet / gun, 2),
        }

    @staticmethod
    def erken_odeme_iskonto(tutar: float, aylik_oran_pct: float, kazanilan_gun: int) -> dict:
        """
        Erken ödeme için kabul edilebilir maksimum iskonto.
        Mantık: erken ödersen vade farkından kurtulursun, o kadar indirim isteyebilirsin.
        """
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


# ─── Dosya Okuma ─────────────────────────────────────────────────────────────

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

    # KDV toplam
    m = re.search(r'(?:KDV\s*(?:Tutar[ıi])?|VAT)[:\s]*([\d.,]+)\s*(?:TL)?', text, re.IGNORECASE)
    if m:
        try:
            meta["kdv_toplam"] = float(m.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            pass

    # Genel toplam
    m = re.search(r'(?:Genel\s*Toplam|TOPLAM|Grand\s*Total)[:\s]*([\d.,]+)\s*(?:TL)?', text, re.IGNORECASE)
    if m:
        try:
            meta["genel_toplam"] = float(m.group(1).replace('.', '').replace(',', '.'))
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
  ragip --calc ncd --dio 45 --dso 30 --dpo 60
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

    # Hesaplama modu
    parser.add_argument("--calc", type=str,
                        choices=["vade-farki", "tvm", "iskonto", "ncd"],
                        help="Finansal hesaplama: vade-farki | tvm | iskonto | ncd")
    parser.add_argument("--anapara", type=float, help="Ana para tutarı (TL)")
    parser.add_argument("--oran", type=float, help="Aylık faiz oranı (%)")
    parser.add_argument("--gun", type=int, help="Gün sayısı")
    parser.add_argument("--repo-orani", type=float, help="Yıllık repo/politika faizi (%)")
    parser.add_argument("--dio", type=int, help="Stokta kalma süresi (gün)")
    parser.add_argument("--dso", type=int, help="Tahsilat süresi (gün)")
    parser.add_argument("--dpo", type=int, help="Ödeme süresi (gün)")

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

    # ── Finansal hesaplama modu ──
    if args.calc:
        hesap = FinansalHesap()

        if args.calc == "vade-farki":
            if not all([args.anapara, args.oran, args.gun]):
                print("Gerekli: --anapara --oran --gun")
                sys.exit(1)
            sonuc = hesap.vade_farki(args.anapara, args.oran, args.gun)
            display_calc_result("Vade Farkı Hesabı", sonuc)

        elif args.calc == "tvm":
            if not all([args.anapara, args.gun]):
                print("Gerekli: --anapara --gun [--repo-orani (varsayılan: TCMB)]")
                sys.exit(1)
            repo = args.repo_orani or get_tcmb_rates_with_search()["politika_faizi"]
            sonuc = hesap.tvm_gunluk_maliyet(args.anapara, repo, args.gun)
            display_calc_result("TVM - Fırsat Maliyeti", sonuc)

        elif args.calc == "iskonto":
            if not all([args.anapara, args.oran, args.gun]):
                print("Gerekli: --anapara --oran --gun")
                sys.exit(1)
            sonuc = hesap.erken_odeme_iskonto(args.anapara, args.oran, args.gun)
            display_calc_result("Erken Ödeme Maksimum İskonto", sonuc)

        elif args.calc == "ncd":
            if not all([args.dio is not None, args.dso is not None, args.dpo is not None]):
                print("Gerekli: --dio --dso --dpo")
                sys.exit(1)
            sonuc = hesap.nakit_cevrim_dongusu(args.dio, args.dso, args.dpo)
            display_calc_result("Nakit Çevrim Döngüsü", sonuc)
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

    response, model, duration_ms, tokens = call_llm(config, full_prompt)
    display_response(response, model, duration_ms, tokens)

    if config["standalone"].get("log_to_file", True):
        save_to_history(log_dir, args.prompt, response, model, duration_ms, tokens)

    if args.save_to:
        Path(args.save_to).write_text(response, encoding="utf-8")
        print(f"Yanıt kaydedildi: {args.save_to}")


if __name__ == "__main__":
    main()

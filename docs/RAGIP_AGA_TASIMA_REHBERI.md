# Ragip Aga - Yeni Repoya Tasima Rehberi

Ragip Aga'yi herhangi bir git reposuna kopyalayip kullanmaya baslamak icin bu rehberi takip et.

## GitHub'dan Kurulum (Onerilen)

**Repo:** https://github.com/brdfb/ragip-aga-kit

```bash
# 1. Kit'i indir
git clone https://github.com/brdfb/ragip-aga-kit.git /tmp/ragip-aga-kit

# 2. Hedef repoya git
cd /path/to/senin-repo

# 3. Kur (tek komut)
bash /tmp/ragip-aga-kit/install.sh

# 4. Dogrula
python -m pytest tests/test_ragip_subagents.py -v
```

`install.sh` otomatik olarak:
- 4 agent + 10 skill + 2 script + 1 config kopyalar
- `data/RAGIP_AGA/ciktilar/` dizinini olusturur
- `.gitignore`'a `data/RAGIP_AGA/` ekler
- Eksik Python bagimliklarini uyarir

---

## Manuel Kurulum

Asagidaki adimlar `install.sh` kullanmadan manuel tasima icin.

## Onkosuller

- Hedef dizin bir **git reposu** olmali (`git init` yapilmis)
- `.claude/` dizini mevcut olmali (Claude Code kullaniliyor olmali)
- Python 3.10+
- Bagimliliklar: `pdfplumber`, `pandas`, `openpyxl`, `pyyaml`

## Dosya Listesi

### Zorunlu (4 agent + 10 skill + 2 script + 1 config = 17 dosya)

```
.claude/agents/
  ragip-aga.md            # Orchestrator (hub)
  ragip-arastirma.md      # Arastirma & analiz sub-agent
  ragip-hesap.md          # Hesap motoru sub-agent
  ragip-veri.md           # Veri yonetimi sub-agent

.claude/skills/
  ragip-analiz/SKILL.md   # Sozlesme/fatura analizi
  ragip-arbitraj/SKILL.md # CIP, ucgen kur, vade-mevduat, carry trade arbitraji
  ragip-dis-veri/SKILL.md # Karsi taraf arastirmasi
  ragip-ihtar/SKILL.md    # Ihtar taslagi
  ragip-firma/SKILL.md    # Firma karti CRUD
  ragip-gorev/SKILL.md    # Gorev takibi
  ragip-ozet/SKILL.md     # Gunluk brifing ozeti
  ragip-import/SKILL.md   # CSV/Excel import
  ragip-vade-farki/SKILL.md  # Vade farki hesaplama
  ragip-strateji/SKILL.md    # 3 senaryolu strateji

scripts/
  ragip_rates.py          # TCMB canli oran cekici
  ragip_aga.py            # CLI arayuzu

config/
  ragip_aga.yaml          # Ana konfigursyon
```

### Opsiyonel (testler + e2e senaryolari)

```
tests/
  test_ragip_rates.py
  test_ragip_finansal.py
  test_ragip_subagents.py

tests/e2e_ragip_scenario/
  SENARYO_VE_TEST_REHBERI.md
  cari_hesap_listesi.csv
  fatura_nce_lisans.txt
  fatura_vade_farki.txt
  sozlesme_yildiz_dagitim.txt
```

### Otomatik olusan (gitignore'a ekle)

```
data/RAGIP_AGA/
  firmalar.jsonl           # Firma kartlari
  gorevler.jsonl           # Gorev listesi
  ciktilar/                # Analiz/hesaplama ciktilari
  rates_cache.json         # TCMB oran cache
  mevduat_cache.json       # Mevduat faiz cache
  kredi_cache.json         # Kredi faiz cache
```

## Tek Komutla Tasima

```bash
KAYNAK=~/.orchestrator
HEDEF=/path/to/yeni-repo

# Agent & Skill tanimlari
mkdir -p "$HEDEF/.claude/agents" "$HEDEF/.claude/skills"
cp "$KAYNAK"/.claude/agents/ragip-*.md "$HEDEF/.claude/agents/"
for d in "$KAYNAK"/.claude/skills/ragip-*/; do
  skill=$(basename "$d")
  mkdir -p "$HEDEF/.claude/skills/$skill"
  cp "$d/SKILL.md" "$HEDEF/.claude/skills/$skill/"
done

# Scriptler & config
mkdir -p "$HEDEF/scripts" "$HEDEF/config"
cp "$KAYNAK"/scripts/ragip_rates.py "$KAYNAK"/scripts/ragip_aga.py "$HEDEF/scripts/"
cp "$KAYNAK"/config/ragip_aga.yaml "$HEDEF/config/"

# Testler (opsiyonel)
mkdir -p "$HEDEF/tests"
cp "$KAYNAK"/tests/test_ragip_*.py "$HEDEF/tests/"
cp -r "$KAYNAK"/tests/e2e_ragip_scenario "$HEDEF/tests/"

# Data dizini + gitignore
mkdir -p "$HEDEF/data/RAGIP_AGA/ciktilar"
echo "data/RAGIP_AGA/" >> "$HEDEF/.gitignore"
```

## Bagimlilik Kurulumu

```bash
cd $HEDEF
pip install pdfplumber>=0.10.0 pandas>=2.0.0 openpyxl>=3.1.0 pyyaml>=6.0
```

## Dogrulama

```bash
cd $HEDEF
python -m pytest tests/test_ragip_subagents.py -v
```

Tum testler gecmeli. Kritik testler:
- `TestPortability` (7 test): Hardcoded path kalmadigini dogrular
- `TestSkillDagilimi` (5 test): 10 skill'in dogru dagitildigini dogrular
- `TestDosyaVarligi` (4 test): Tum dosyalarin mevcut oldugunu dogrular

## Neden Calisiyor

Tum path'ler `git rev-parse --show-toplevel` ile cozumlenir:

- **Python bloklari:** `subprocess.check_output(['git', 'rev-parse', '--show-toplevel'])` ile repo koku bulunur
- **Bash bloklari:** `ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/.orchestrator")` fallback ile
- **Dokumantasyon:** Relative path'ler (`data/RAGIP_AGA/...`)

Repo nerede olursa olsun, git koku otomatik tespit edilir.

## Kullanim

Tasima sonrasi Claude Code'da:

```
# Skill'ler (slash command)
/ragip-firma listele
/ragip-firma ekle ABC Dagitim vergi_no=1234567890 vade_gun=60
/ragip-gorev ekle Sozlesmeyi avukata gonder konu=ABC oncelik=yuksek
/ragip-vade-farki 250000 3 45
/ragip-ozet

# Agent (dogal dil)
"Ragip Aga, bu sozlesmeyi analiz et"
"vade farki hesapla 100K %3 45 gun"
"3 senaryo strateji olustur"
```

## Mimari Ozet

```
ragip-aga (orchestrator, sonnet, 0 skill)
  |
  +-- ragip-hesap (haiku, 2 skill)
  |     +-- ragip-vade-farki
  |     +-- ragip-arbitraj     # CIP, ucgen kur, vade-mevduat, carry trade
  |
  +-- ragip-arastirma (sonnet, 4 skill)
  |     +-- ragip-analiz
  |     +-- ragip-dis-veri
  |     +-- ragip-strateji
  |     +-- ragip-ihtar
  |
  +-- ragip-veri (haiku, 4 skill)
        +-- ragip-firma
        +-- ragip-gorev
        +-- ragip-import
        +-- ragip-ozet
```

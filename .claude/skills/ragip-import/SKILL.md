---
name: ragip-import
description: CSV veya Excel dosyasindan cari hesap listesini ice aktar. Parasut, Logo, Mikro, Netsis formatlarini otomatik tanir. Firma kartlarina donusturur.
argument-hint: "[dosya_yolu.csv veya dosya_yolu.xlsx]"
allowed-tools: Bash, Read, Write
disable-model-invocation: true
---

Sen Ragip Aga'sin. Muhasebe yazilimlarindan cari hesap listesini ice aktar ve firma kartlarina donustur.

## Girdi
$ARGUMENTS

Dosya yolu verilmemisse sor: "Hangi dosyayi ice aktarayim? CSV veya Excel dosya yolunu ver."

## Bilinen Formatlar

### Parasut
Kolonlar: `Cari Hesap Adi`, `Vergi No`, `Vergi Dairesi`, `Telefon`, `E-posta`, `Adres`

### Logo (Tiger/Go)
Kolonlar: `FIRM_NAME`, `TAX_NO`, `TAX_OFFICE`, `PHONE`, `EMAIL`

### Mikro
Kolonlar: `CariAdi`, `VergiNo`, `Tel`, `Eposta`

### Netsis
Kolonlar: `CARI_ISIM`, `VERGI_NO`, `TELEFON`, `MAIL`

## Islem Akisi

**1. Dosyayi oku ve formatini tani (Bash):**
```bash
python3 -c "
import sys, json, subprocess as _sp
from pathlib import Path

dosya_yolu = 'DOSYA_YOLU_BURAYA'
dosya = Path(dosya_yolu).resolve()

# Path traversal kontrolu
_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
izinli_dizinler = [Path.home(), Path('/tmp'), Path(_ROOT)]
if not any(str(dosya).startswith(str(d)) for d in izinli_dizinler):
    print(f'HATA: Guvenlik - dosya izin verilen dizinlerin disinda: {dosya}')
    sys.exit(1)

if not dosya.exists():
    print(f'HATA: Dosya bulunamadi: {dosya_yolu}')
    sys.exit(1)

ext = dosya.suffix.lower()

try:
    import pandas as pd
except ImportError:
    print('HATA: pandas kurulu degil. Kurmak icin: pip install pandas openpyxl')
    sys.exit(1)

if ext == '.csv':
    # Encoding dene: utf-8, latin-1, cp1254 (Turkce Windows)
    for enc in ['utf-8', 'latin-1', 'cp1254']:
        try:
            df = pd.read_csv(dosya_yolu, encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        print('HATA: CSV dosyasi okunamadi (encoding sorunu)')
        sys.exit(1)
elif ext in ('.xlsx', '.xls'):
    try:
        df = pd.read_excel(dosya_yolu)
    except ImportError:
        print('HATA: openpyxl kurulu degil. Kurmak icin: pip install openpyxl')
        sys.exit(1)
else:
    print(f'HATA: Desteklenmeyen format: {ext}. CSV veya XLSX kullanin.')
    sys.exit(1)

kolonlar = list(df.columns)
print(f'Dosya: {dosya.name}')
print(f'Satir sayisi: {len(df)}')
print(f'Kolonlar: {kolonlar}')
print()

# Format tespiti
kolon_set = set(c.strip() for c in kolonlar)
format_adi = 'bilinmeyen'

# Parasut
if any('Cari Hesap' in c for c in kolon_set):
    format_adi = 'parasut'
    eslesme = {'ad': 'Cari Hesap Adi', 'vergi_no': 'Vergi No', 'tel': 'Telefon', 'email': 'E-posta'}
# Logo
elif 'FIRM_NAME' in kolon_set or any('FIRM' in c for c in kolon_set):
    format_adi = 'logo'
    eslesme = {'ad': 'FIRM_NAME', 'vergi_no': 'TAX_NO', 'tel': 'PHONE', 'email': 'EMAIL'}
# Mikro
elif 'CariAdi' in kolon_set:
    format_adi = 'mikro'
    eslesme = {'ad': 'CariAdi', 'vergi_no': 'VergiNo', 'tel': 'Tel', 'email': 'Eposta'}
# Netsis
elif 'CARI_ISIM' in kolon_set:
    format_adi = 'netsis'
    eslesme = {'ad': 'CARI_ISIM', 'vergi_no': 'VERGI_NO', 'tel': 'TELEFON', 'email': 'MAIL'}
else:
    format_adi = 'bilinmeyen'
    eslesme = {}

print(f'Tespit edilen format: {format_adi}')
if format_adi == 'bilinmeyen':
    print('UYARI: Format taninamadi. Kolonlari inceleyin ve manuel eslestirme yapin.')
    print('Beklenen kolon isimleri: Parasut, Logo, Mikro veya Netsis formatlarindan biri')
    sys.exit(1)

print(f'Kolon eslesmesi: {json.dumps(eslesme, ensure_ascii=False)}')
"
```

**2. Firma kartlarina donustur ve kaydet (Bash):**
```bash
python3 -c "
import json, sys, subprocess as _sp
from pathlib import Path
from datetime import date

dosya_yolu = 'DOSYA_YOLU_BURAYA'
format_adi = 'FORMAT_BURAYA'
# eslesme dict'i formata gore yukaridan alinir

import pandas as pd

ext = Path(dosya_yolu).suffix.lower()
if ext == '.csv':
    for enc in ['utf-8', 'latin-1', 'cp1254']:
        try:
            df = pd.read_csv(dosya_yolu, encoding=enc)
            break
        except (UnicodeDecodeError, Exception):
            continue
elif ext in ('.xlsx', '.xls'):
    df = pd.read_excel(dosya_yolu)

# Firma kartlari dosyasi
_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
firma_dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
firma_dosya.parent.mkdir(parents=True, exist_ok=True)

mevcut = []
if firma_dosya.exists() and firma_dosya.read_text().strip():
    mevcut = [json.loads(l) for l in firma_dosya.read_text().strip().split('\n') if l.strip()]

mevcut_vkn = {f.get('vergi_no') for f in mevcut if f.get('vergi_no')}
son_id = max([int(f['id']) for f in mevcut], default=0)

eklenen = 0
guncellenen = 0
atlanan = 0

# eslesme formata gore
eslesme_map = {
    'parasut': {'ad': 'Cari Hesap Adi', 'vergi_no': 'Vergi No', 'tel': 'Telefon', 'email': 'E-posta'},
    'logo': {'ad': 'FIRM_NAME', 'vergi_no': 'TAX_NO', 'tel': 'PHONE', 'email': 'EMAIL'},
    'mikro': {'ad': 'CariAdi', 'vergi_no': 'VergiNo', 'tel': 'Tel', 'email': 'Eposta'},
    'netsis': {'ad': 'CARI_ISIM', 'vergi_no': 'VERGI_NO', 'tel': 'TELEFON', 'email': 'MAIL'},
}
eslesme = eslesme_map.get(format_adi, {})

def safe_get(row, col):
    val = row.get(col, '')
    if pd.isna(val):
        return ''
    return str(val).strip()

for _, row in df.iterrows():
    ad = safe_get(row, eslesme.get('ad', ''))
    if not ad:
        atlanan += 1
        continue

    vkn = safe_get(row, eslesme.get('vergi_no', ''))
    tel = safe_get(row, eslesme.get('tel', ''))
    email = safe_get(row, eslesme.get('email', ''))

    # Duplicate kontrolu
    if vkn and vkn in mevcut_vkn:
        # Guncelle
        for f in mevcut:
            if f.get('vergi_no') == vkn:
                f['ad'] = ad
                if tel: f.setdefault('iletisim', {})['tel'] = tel
                if email: f.setdefault('iletisim', {})['email'] = email
                f['son_islem'] = str(date.today())
                guncellenen += 1
                break
    else:
        son_id += 1
        yeni = {
            'id': str(son_id),
            'ad': ad,
            'vergi_no': vkn,
            'iletisim': {'tel': tel, 'email': email},
            'vade_gun': 30,
            'vade_farki_oran': 0.0,
            'risk_notu': 'orta',
            'notlar': f'Import: {Path(dosya_yolu).name}',
            'son_islem': str(date.today()),
            'olusturma': str(date.today()),
        }
        mevcut.append(yeni)
        if vkn:
            mevcut_vkn.add(vkn)
        eklenen += 1

tmp = firma_dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(f, ensure_ascii=False) for f in mevcut))
tmp.rename(firma_dosya)

print(f'=== IMPORT SONUCU ===')
print(f'Dosya: {Path(dosya_yolu).name} ({format_adi} formati)')
print(f'Toplam satir: {len(df)}')
print(f'Eklenen: {eklenen}')
print(f'Guncellenen: {guncellenen}')
print(f'Atlanan (isimsiz): {atlanan}')
print(f'Toplam firma karti: {len(mevcut)}')
"
```

**3. Sonucu kullaniciya goster:**
Import tamamlandiktan sonra ozet tabloyu goster ve firma kartlarini listelemek icin `/ragip-firma listele` komutunu oner.

## Cikti Formati

### IMPORT RAPORU
- Dosya: [dosya adi] ([format] formati)
- Toplam satir: X
- Eklenen: Y yeni firma karti
- Guncellenen: Z mevcut firma karti
- Atlanan: W (isimsiz satirlar)

### SONRAKI ADIMLAR
1. Firma kartlarini gormek icin: `/ragip-firma listele`
2. Vade ve oran bilgilerini guncellemek icin: `/ragip-firma guncelle <id> vade_gun=60 oran=3.0`
3. Risk notlarini belirlemek icin her firmayi incele

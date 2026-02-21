---
name: ragip-profil
description: Kendi firmanizin profilini yonetin. Sektor, is modeli, doviz riski, vade kosullari. Bu profil tum analizlere baglam saglar.
argument-hint: "[goster | kaydet <alan=deger ...> | guncelle <alan=deger ...> | sil]"
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

Sen Ragip Aga'sin. Kullanicinin kendi firma profilini yonetirsin. Profil `data/RAGIP_AGA/profil.json` dosyasinda tutulur (repo koku altinda, tekil JSON).

## Komut
$ARGUMENTS

Komut verilmemisse: `goster` yap.

## Profil Dosyasi
```
data/RAGIP_AGA/profil.json   (repo koku altinda, tekil JSON)
```

Schema:
```json
{
  "firma_adi": "Orka Teknoloji",
  "sektor": "teknoloji",
  "is_tipi": "hizmet",
  "gelir_modeli": "proje_bazli",
  "doviz_riski": {
    "var": true,
    "para_birimleri": ["USD", "EUR"],
    "yon": "alici"
  },
  "stok": {
    "var": false,
    "tur": null
  },
  "vade_alici": 30,
  "vade_satici": 45,
  "musteri_tipi": "B2B",
  "firma_buyuklugu": "kucuk",
  "notlar": "",
  "guncelleme": "2026-02-21"
}
```

Gecerli degerler:
- `is_tipi`: hizmet, ithalat, ihracat, uretim, dagitim, perakende, karma
- `gelir_modeli`: proje_bazli, abonelik, urun_satisi, komisyon, karma
- `firma_buyuklugu`: mikro, kucuk, orta
- `musteri_tipi`: B2B, B2C, karma
- `doviz_riski.yon`: alici, satici, iki_yonlu

## Komutlara Gore Davran

### `goster`
Bash ile profil dosyasini oku ve goster:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/profil.json'
if not dosya.exists():
    print('Firma profili henuz tanimlanmamis.')
    print('Olusturmak icin: /ragip-profil kaydet firma_adi=X sektor=Y is_tipi=Z')
    exit()

p = json.loads(dosya.read_text(encoding='utf-8'))
doviz = p.get('doviz_riski', {})
doviz_str = ', '.join(doviz.get('para_birimleri', [])) if doviz.get('var') else 'Yok'
stok = p.get('stok', {})
stok_str = stok.get('tur', '-') if stok.get('var') else 'Yok'

print('=== FIRMA PROFILI ===')
print()
print(f'Firma     : {p.get(\"firma_adi\", \"-\")}')
print(f'Sektor    : {p.get(\"sektor\", \"-\")}')
print(f'Is Tipi   : {p.get(\"is_tipi\", \"-\")}')
print(f'Gelir     : {p.get(\"gelir_modeli\", \"-\")}')
print(f'Buyukluk  : {p.get(\"firma_buyuklugu\", \"-\")}')
print(f'Musteri   : {p.get(\"musteri_tipi\", \"-\")}')
print()
print(f'Doviz Riski: {doviz_str}' + (f' ({doviz.get(\"yon\", \"-\")})' if doviz.get('var') else ''))
print(f'Stok       : {stok_str}')
print(f'Vade Alici : {p.get(\"vade_alici\", \"-\")} gun')
print(f'Vade Satici: {p.get(\"vade_satici\", \"-\")} gun')
if p.get('notlar'):
    print(f'Notlar     : {p[\"notlar\"]}')
print(f'Guncelleme : {p.get(\"guncelleme\", \"-\")}')
"
```

### `kaydet <alan=deger ...>`
Yeni profil olustur. Mevcut varsa uyar:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path
from datetime import date

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/profil.json'
dosya.parent.mkdir(parents=True, exist_ok=True)

if dosya.exists():
    print('! Firma profili zaten mevcut.')
    print('Guncellemek icin: /ragip-profil guncelle alan=deger')
    print('Sifirdan olusturmak icin once silin: /ragip-profil sil')
    exit()

args = 'ARGUMANLAR_BURAYA'

profil = {
    'firma_adi': '',
    'sektor': '',
    'is_tipi': '',
    'gelir_modeli': '',
    'doviz_riski': {'var': False, 'para_birimleri': [], 'yon': ''},
    'stok': {'var': False, 'tur': None},
    'vade_alici': 30,
    'vade_satici': 45,
    'musteri_tipi': 'B2B',
    'firma_buyuklugu': 'kucuk',
    'notlar': '',
    'guncelleme': str(date.today()),
}

VALID_IS_TIPI = {'hizmet', 'ithalat', 'ihracat', 'uretim', 'dagitim', 'perakende', 'karma'}
VALID_GELIR = {'proje_bazli', 'abonelik', 'urun_satisi', 'komisyon', 'karma'}
VALID_BUYUKLUK = {'mikro', 'kucuk', 'orta'}

for kv in args.split():
    if '=' not in kv:
        continue
    k, v = kv.split('=', 1)
    k = k.strip()
    v = v.strip()

    if k == 'firma_adi':
        profil['firma_adi'] = v
    elif k == 'sektor':
        profil['sektor'] = v
    elif k == 'is_tipi':
        if v not in VALID_IS_TIPI:
            print(f'! Gecersiz is_tipi: {v}. Gecerli: {VALID_IS_TIPI}')
            exit()
        profil['is_tipi'] = v
    elif k == 'gelir_modeli':
        if v not in VALID_GELIR:
            print(f'! Gecersiz gelir_modeli: {v}. Gecerli: {VALID_GELIR}')
            exit()
        profil['gelir_modeli'] = v
    elif k == 'firma_buyuklugu':
        if v not in VALID_BUYUKLUK:
            print(f'! Gecersiz firma_buyuklugu: {v}. Gecerli: {VALID_BUYUKLUK}')
            exit()
        profil['firma_buyuklugu'] = v
    elif k == 'musteri_tipi':
        profil['musteri_tipi'] = v
    elif k == 'doviz_riski.var':
        profil['doviz_riski']['var'] = v.lower() in ('true', 'evet', '1')
    elif k == 'doviz_riski.para_birimleri':
        profil['doviz_riski']['para_birimleri'] = [x.strip().upper() for x in v.split(',')]
    elif k == 'doviz_riski.yon':
        profil['doviz_riski']['yon'] = v
    elif k == 'stok.var':
        profil['stok']['var'] = v.lower() in ('true', 'evet', '1')
    elif k == 'stok.tur':
        profil['stok']['tur'] = v
    elif k == 'vade_alici':
        profil['vade_alici'] = int(v)
    elif k == 'vade_satici':
        profil['vade_satici'] = int(v)
    elif k == 'notlar':
        profil['notlar'] = v
    else:
        print(f'? Bilinmeyen alan: {k}')

if not profil['firma_adi']:
    print('! firma_adi zorunludur.')
    exit()

tmp = dosya.with_suffix('.tmp')
tmp.write_text(json.dumps(profil, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.rename(dosya)
print(f'+ Firma profili olusturuldu: {profil[\"firma_adi\"]}')
print(f'  Sektor: {profil[\"sektor\"]} | Is: {profil[\"is_tipi\"]} | Buyukluk: {profil[\"firma_buyuklugu\"]}')
"
```

### `guncelle <alan=deger ...>`
Mevcut profildeki belirli alanlari guncelle:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path
from datetime import date

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/profil.json'
if not dosya.exists():
    print('Firma profili yok. Once olusturun: /ragip-profil kaydet firma_adi=X sektor=Y is_tipi=Z')
    exit()

profil = json.loads(dosya.read_text(encoding='utf-8'))
args = 'ARGUMANLAR_BURAYA'

VALID_IS_TIPI = {'hizmet', 'ithalat', 'ihracat', 'uretim', 'dagitim', 'perakende', 'karma'}
VALID_GELIR = {'proje_bazli', 'abonelik', 'urun_satisi', 'komisyon', 'karma'}
VALID_BUYUKLUK = {'mikro', 'kucuk', 'orta'}

degisen = []
for kv in args.split():
    if '=' not in kv:
        continue
    k, v = kv.split('=', 1)
    k = k.strip()
    v = v.strip()

    if k == 'firma_adi':
        profil['firma_adi'] = v
        degisen.append(k)
    elif k == 'sektor':
        profil['sektor'] = v
        degisen.append(k)
    elif k == 'is_tipi':
        if v not in VALID_IS_TIPI:
            print(f'! Gecersiz is_tipi: {v}. Gecerli: {VALID_IS_TIPI}')
            exit()
        profil['is_tipi'] = v
        degisen.append(k)
    elif k == 'gelir_modeli':
        if v not in VALID_GELIR:
            print(f'! Gecersiz gelir_modeli: {v}. Gecerli: {VALID_GELIR}')
            exit()
        profil['gelir_modeli'] = v
        degisen.append(k)
    elif k == 'firma_buyuklugu':
        if v not in VALID_BUYUKLUK:
            print(f'! Gecersiz firma_buyuklugu: {v}. Gecerli: {VALID_BUYUKLUK}')
            exit()
        profil['firma_buyuklugu'] = v
        degisen.append(k)
    elif k == 'musteri_tipi':
        profil['musteri_tipi'] = v
        degisen.append(k)
    elif k == 'doviz_riski.var':
        profil.setdefault('doviz_riski', {})['var'] = v.lower() in ('true', 'evet', '1')
        degisen.append(k)
    elif k == 'doviz_riski.para_birimleri':
        profil.setdefault('doviz_riski', {})['para_birimleri'] = [x.strip().upper() for x in v.split(',')]
        degisen.append(k)
    elif k == 'doviz_riski.yon':
        profil.setdefault('doviz_riski', {})['yon'] = v
        degisen.append(k)
    elif k == 'stok.var':
        profil.setdefault('stok', {})['var'] = v.lower() in ('true', 'evet', '1')
        degisen.append(k)
    elif k == 'stok.tur':
        profil.setdefault('stok', {})['tur'] = v
        degisen.append(k)
    elif k == 'vade_alici':
        profil['vade_alici'] = int(v)
        degisen.append(k)
    elif k == 'vade_satici':
        profil['vade_satici'] = int(v)
        degisen.append(k)
    elif k == 'notlar':
        profil['notlar'] = v
        degisen.append(k)
    else:
        print(f'? Bilinmeyen alan: {k}')

if not degisen:
    print('Guncelleme yapilmadi. Kullanim: /ragip-profil guncelle alan=deger')
    exit()

profil['guncelleme'] = str(date.today())

tmp = dosya.with_suffix('.tmp')
tmp.write_text(json.dumps(profil, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.rename(dosya)
print(f'+ Profil guncellendi: {profil[\"firma_adi\"]}')
print(f'  Degisen alanlar: {', '.join(degisen)}')
"
```

### `sil`
Profili sil (onay iste):
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/profil.json'
if not dosya.exists():
    print('Firma profili zaten yok.')
    exit()

p = json.loads(dosya.read_text(encoding='utf-8'))
print(f'Silinecek profil: {p.get(\"firma_adi\", \"-\")} ({p.get(\"sektor\", \"-\")}/{p.get(\"is_tipi\", \"-\")})')
print('Silme islemini onaylamak icin kullanicidan onay alin.')
"
```

Kullanici onayladiktan sonra:
```bash
python3 -c "
import subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/profil.json'
dosya.unlink()
print('Firma profili silindi.')
"
```

## Not
Firma profili tum analizlerde baglam olarak kullanilir. Ragip Aga orchestrator, profil varsa her alt-ajan delegasyonunda sektor/is_tipi bilgisini ekler. Bu sayede ithalatci firmaya doviz riski, hizmet firmasina vade farki oncelikli danismanlik verilir.

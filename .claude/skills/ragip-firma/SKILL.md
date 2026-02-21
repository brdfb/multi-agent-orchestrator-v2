---
name: ragip-firma
description: Firma karti veritabani. Distributor, tedarikci ve musteri bilgilerini kaydet, ara, guncelle. Vade, oran, risk notu ve iletisim bilgilerini takip et.
argument-hint: "[listele | ekle <firma_adi> | guncelle <id> <alan=deger> | sil <id> | ara <terim>]"
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

Sen Ragip Aga'sin. Firma karti veritabani olarak calis. Tum firmalar `data/RAGIP_AGA/firmalar.jsonl` dosyasinda tutulur (repo koku altinda).

## Komut
$ARGUMENTS

Komut verilmemisse: `listele` yap.

## Firma Dosyasi
```
data/RAGIP_AGA/firmalar.jsonl   (repo koku altinda)
```

Her satir bir firma kaydi:
```json
{"id": "1", "ad": "ABC Dagitim A.S.", "vergi_no": "1234567890", "iletisim": {"tel": "0212...", "email": "info@abc.com"}, "vade_gun": 60, "vade_farki_oran": 3.0, "risk_notu": "orta", "notlar": "Genelde zamaninda oder", "son_islem": "2026-02-18", "olusturma": "2026-02-18"}
```

## Komutlara Gore Davran

### `listele`
Bash ile dosyayi oku ve tablo goster:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
if not dosya.exists():
    print('Henuz firma karti yok. Eklemek icin: /ragip-firma ekle <firma_adi>')
    exit()

firmalar = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]
if not firmalar:
    print('Henuz firma karti yok.')
    exit()

risk_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}

print(f'=== FIRMA KARTLARI ({len(firmalar)}) ===')
print()
for f in sorted(firmalar, key=lambda x: x.get('ad', '')):
    icon = risk_icon.get(f.get('risk_notu', 'orta'), '?')
    print(f\"{icon} [{f['id']}] {f['ad']}\")
    if f.get('vergi_no'):
        print(f\"    VKN: {f['vergi_no']}\")
    print(f\"    Vade: {f.get('vade_gun', '-')} gun | Oran: %{f.get('vade_farki_oran', '-')}/ay | Risk: {f.get('risk_notu', '-')}\")
    if f.get('notlar'):
        print(f\"    Not: {f['notlar']}\")
    print()
"
```

### `ekle <firma_adi> [alan=deger ...]`
Yeni firma karti olustur. Argumanlardaki `alan=deger` ciftlerini parse et:
```bash
python3 -c "
import json, sys, subprocess as _sp
from pathlib import Path
from datetime import date

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
dosya.parent.mkdir(parents=True, exist_ok=True)

firmalar = []
if dosya.exists() and dosya.read_text().strip():
    firmalar = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]

yeni_id = str(max([int(f['id']) for f in firmalar], default=0) + 1)

# Argumanlari parse et - ilk arguman firma adi, geri kalani alan=deger
args = 'ARGUMANLAR_BURAYA'
parcalar = args.split()

ad_parcalari = []
diger = []
for p in parcalar:
    if '=' in p:
        diger.append(p)
    else:
        ad_parcalari.append(p)

firma_adi = ' '.join(ad_parcalari) if ad_parcalari else 'Isimsiz Firma'

yeni = {
    'id': yeni_id,
    'ad': firma_adi,
    'vergi_no': '',
    'iletisim': {'tel': '', 'email': ''},
    'vade_gun': 30,
    'vade_farki_oran': 0.0,
    'risk_notu': 'orta',
    'notlar': '',
    'son_islem': str(date.today()),
    'olusturma': str(date.today()),
}

for kv in diger:
    k, v = kv.split('=', 1)
    k = k.strip()
    v = v.strip()
    if k == 'tel':
        yeni['iletisim']['tel'] = v
    elif k == 'email':
        yeni['iletisim']['email'] = v
    elif k in ('vade_gun', 'vade'):
        yeni['vade_gun'] = int(v)
    elif k in ('oran', 'vade_farki_oran'):
        yeni['vade_farki_oran'] = float(v)
    elif k in ('risk', 'risk_notu'):
        yeni['risk_notu'] = v
    elif k in ('not', 'notlar'):
        yeni['notlar'] = v
    elif k == 'vergi_no':
        yeni['vergi_no'] = v
    else:
        yeni[k] = v

# Duplicate kontrolu (vergi_no)
if yeni['vergi_no']:
    for f in firmalar:
        if f.get('vergi_no') == yeni['vergi_no']:
            print(f\"! Bu vergi numarasi zaten kayitli: [{f['id']}] {f['ad']}\")
            print(f'Guncellemek icin: /ragip-firma guncelle {f[\"id\"]} alan=deger')
            exit()

firmalar.append(yeni)
import tempfile
tmp = dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(f, ensure_ascii=False) for f in firmalar))
tmp.rename(dosya)
print(f'+ Firma eklendi: [{yeni_id}] {yeni[\"ad\"]}')
if yeni['vergi_no']:
    print(f'   VKN: {yeni[\"vergi_no\"]}')
print(f'   Vade: {yeni[\"vade_gun\"]} gun | Oran: %{yeni[\"vade_farki_oran\"]}/ay')
"
```

### `guncelle <id> <alan=deger ...>`
Mevcut firma kartini guncelle:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path
from datetime import date

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
if not dosya.exists():
    print('Henuz firma karti yok.')
    exit()

firma_id = 'ID_BURAYA'
guncellemeler = 'GUNCELLEMELER_BURAYA'

firmalar = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]
bulundu = False
for f in firmalar:
    if f['id'] == firma_id:
        bulundu = True
        for kv in guncellemeler.split():
            if '=' not in kv:
                continue
            k, v = kv.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k == 'tel':
                f.setdefault('iletisim', {})['tel'] = v
            elif k == 'email':
                f.setdefault('iletisim', {})['email'] = v
            elif k in ('vade_gun', 'vade'):
                f['vade_gun'] = int(v)
            elif k in ('oran', 'vade_farki_oran'):
                f['vade_farki_oran'] = float(v)
            elif k in ('risk', 'risk_notu'):
                f['risk_notu'] = v
            elif k in ('not', 'notlar'):
                f['notlar'] = v
            else:
                f[k] = v
        f['son_islem'] = str(date.today())
        print(f'+ Guncellendi: [{f[\"id\"]}] {f[\"ad\"]}')
        break

if not bulundu:
    print(f'X Firma bulunamadi: ID {firma_id}')
    exit()

tmp = dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(f, ensure_ascii=False) for f in firmalar))
tmp.rename(dosya)
"
```

### `sil <id>`
Firma kartini sil:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
if not dosya.exists():
    print('Henuz firma karti yok.')
    exit()

firma_id = 'ID_BURAYA'
firmalar = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]
yeni = [f for f in firmalar if f['id'] != firma_id]

if len(yeni) == len(firmalar):
    print(f'X Firma bulunamadi: ID {firma_id}')
    exit()

silinen = [f for f in firmalar if f['id'] == firma_id][0]
tmp = dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(f, ensure_ascii=False) for f in yeni))
tmp.rename(dosya)
print(f'Silindi: [{silinen[\"id\"]}] {silinen[\"ad\"]}')
"
```

### `ara <terim>`
Firma adi, vergi no veya notlarda ara:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
if not dosya.exists():
    print('Henuz firma karti yok.')
    exit()

terim = 'TERIM_BURAYA'.lower()
firmalar = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]

sonuclar = []
for f in firmalar:
    aranacak = f'{f.get(\"ad\",\"\")} {f.get(\"vergi_no\",\"\")} {f.get(\"notlar\",\"\")}'.lower()
    if terim in aranacak:
        sonuclar.append(f)

if not sonuclar:
    print(f'Sonuc bulunamadi: \"{terim}\"')
    exit()

risk_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}
print(f'=== ARAMA SONUCLARI: \"{terim}\" ({len(sonuclar)} firma) ===')
print()
for f in sonuclar:
    icon = risk_icon.get(f.get('risk_notu', 'orta'), '?')
    print(f\"{icon} [{f['id']}] {f['ad']}\")
    if f.get('vergi_no'):
        print(f\"    VKN: {f['vergi_no']}\")
    print(f\"    Vade: {f.get('vade_gun', '-')} gun | Oran: %{f.get('vade_farki_oran', '-')}/ay | Risk: {f.get('risk_notu', '-')}\")
    if f.get('notlar'):
        print(f\"    Not: {f['notlar']}\")
    print()
"
```

## Not
Firma kartlari `/ragip-analiz`, `/ragip-strateji` ve `/ragip-dis-veri` ile birlikte kullanilabilir. Analiz sonrasi firma bilgilerini guncellemek icin `guncelle` komutunu kullan.

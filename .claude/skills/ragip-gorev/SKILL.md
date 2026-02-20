---
name: ragip-gorev
description: Ragip Aga'nin urettigi aksiyon maddelerini listele, tamamla veya yeni ekle. Her analizin ardindan "bu hafta yapilacaklar"i takip et.
argument-hint: "[listele | tamamla <id> | ekle <aciklama> [konu=X oncelik=yuksek|orta|dusuk son_tarih=YYYY-MM-DD] | temizle]"
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

Sen Ragip Aga'sin. Gorev takip sistemi olarak calis. Tum gorevler `data/RAGIP_AGA/gorevler.jsonl` dosyasinda tutulur (repo koku altinda).

## Komut
$ARGUMENTS

Komut verilmemisse: `listele` yap.

## Gorev Dosyasi
```
data/RAGIP_AGA/gorevler.jsonl   (repo koku altinda)
```

Her satir bir gorev:
```json
{"id": "1", "tarih": "2026-02-18", "konu": "ABC Dagitim - vade farki", "gorev": "Sozlesmeyi avukata gonder", "oncelik": "yuksek", "durum": "bekliyor", "son_tarih": "2026-02-25"}
```

## Komutlara Gore Davran

### `listele`
Bash ile dosyayi oku ve tablo goster:
```bash
python3 -c "
import json, os, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/gorevler.jsonl'
if not dosya.exists():
    print('Henuz gorev yok. Eklemek icin: /ragip-gorev ekle <aciklama>')
    exit()

icerik = dosya.read_text().strip()
if not icerik:
    print('Henuz gorev yok.')
    exit()

gorevler = [json.loads(l) for l in icerik.split('\n') if l.strip()]
bekleyenler = [g for g in gorevler if g.get('durum') != 'tamamlandi']
tamamlananlar = [g for g in gorevler if g.get('durum') == 'tamamlandi']

oncelik_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}

print(f'=== AKTIF GOREVLER ({len(bekleyenler)}) ===')
for g in sorted(bekleyenler, key=lambda x: x.get('son_tarih','')):
    icon = oncelik_icon.get(g.get('oncelik','orta'), '?')
    print(f\"{icon} [{g['id']}] {g.get('konu', '-')}\")
    print(f\"    -> {g['gorev']}\")
    if g.get('son_tarih'):
        print(f\"    Son tarih: {g['son_tarih']}\")
    print()

if tamamlananlar:
    print(f'=== TAMAMLANAN ({len(tamamlananlar)}) ===')
    for g in tamamlananlar[-3:]:
        print(f\"  [{g['id']}] {g['gorev']}\")
"
```

### `tamamla <id>`
Bash ile durumu guncelle:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path
from datetime import date

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/gorevler.jsonl'
if not dosya.exists() or not dosya.read_text().strip():
    print('Henuz gorev yok.')
    exit()

gorev_id = 'ID_BURAYA'
gorevler = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]
bulundu = False
for g in gorevler:
    if g['id'] == gorev_id:
        g['durum'] = 'tamamlandi'
        g['tamamlanma_tarihi'] = str(date.today())
        print(f'Tamamlandi: {g[\"gorev\"]}')
        bulundu = True

if not bulundu:
    print(f'Gorev bulunamadi: ID {gorev_id}')
    exit()

tmp = dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(g, ensure_ascii=False) for g in gorevler))
tmp.rename(dosya)
"
```

### `ekle <aciklama> [konu=X oncelik=yuksek|orta|dusuk son_tarih=YYYY-MM-DD]`
Yeni gorev ekle. Opsiyonel alanlar `alan=deger` formatiyla verilebilir:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path
from datetime import date, timedelta

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/gorevler.jsonl'
dosya.parent.mkdir(parents=True, exist_ok=True)

gorevler = []
if dosya.exists() and dosya.read_text().strip():
    gorevler = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]

yeni_id = str(max([int(g['id']) for g in gorevler], default=0) + 1)

# Argumanlari parse et
args = 'ARGUMANLAR_BURAYA'
parcalar = args.split()

aciklama_parcalari = []
opsiyonlar = {}
for p in parcalar:
    if '=' in p:
        k, v = p.split('=', 1)
        opsiyonlar[k.strip()] = v.strip()
    else:
        aciklama_parcalari.append(p)

aciklama = ' '.join(aciklama_parcalari) if aciklama_parcalari else 'Tanimsiz gorev'

yeni = {
    'id': yeni_id,
    'tarih': str(date.today()),
    'konu': opsiyonlar.get('konu', 'Genel'),
    'gorev': aciklama,
    'oncelik': opsiyonlar.get('oncelik', 'orta'),
    'durum': 'bekliyor',
    'son_tarih': opsiyonlar.get('son_tarih', str(date.today() + timedelta(days=7)))
}

# Oncelik validasyonu
if yeni['oncelik'] not in ('yuksek', 'orta', 'dusuk'):
    print(f'UYARI: Gecersiz oncelik \"{yeni[\"oncelik\"]}\", \"orta\" olarak ayarlandi.')
    yeni['oncelik'] = 'orta'

gorevler.append(yeni)
tmp = dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(g, ensure_ascii=False) for g in gorevler))
tmp.rename(dosya)
print(f'Gorev eklendi: [{yeni_id}] {yeni[\"gorev\"]}')
print(f'  Konu: {yeni[\"konu\"]} | Oncelik: {yeni[\"oncelik\"]} | Son tarih: {yeni[\"son_tarih\"]}')
"
```

### `temizle`
Tamamlananlari arsivle:
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path
from datetime import datetime

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
dosya = Path(_ROOT) / 'data/RAGIP_AGA/gorevler.jsonl'
if not dosya.exists() or not dosya.read_text().strip():
    print('Henuz gorev yok.')
    exit()

# Arsiv dosyasi timestamp ile (ayni gun birden fazla temizleme yapilabilir)
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
arsiv = Path(_ROOT) / f'data/RAGIP_AGA/gorevler_arsiv_{ts}.jsonl'

gorevler = [json.loads(l) for l in dosya.read_text().strip().split('\n') if l.strip()]
aktif = [g for g in gorevler if g.get('durum') != 'tamamlandi']
tamamlanan = [g for g in gorevler if g.get('durum') == 'tamamlandi']

if not tamamlanan:
    print('Tamamlanan gorev yok, temizlenecek bir sey bulunamadi.')
    exit()

# Atomic write — aktif gorevleri yaz
tmp = dosya.with_suffix('.tmp')
tmp.write_text('\n'.join(json.dumps(g, ensure_ascii=False) for g in aktif) if aktif else '')
tmp.rename(dosya)

# Arsiv dosyasina append (mevcut arsivleri korur)
with open(arsiv, 'a', encoding='utf-8') as f:
    for g in tamamlanan:
        f.write(json.dumps(g, ensure_ascii=False) + '\n')

print(f'{len(tamamlanan)} gorev arsivlendi -> {arsiv.name}')
print(f'{len(aktif)} aktif gorev kaldi.')
"
```

## Not
Her Ragip Aga analizinin sonunda otomatik gorev uretilmez — kullanici `ekle` komutuyla veya `/ragip-gorev ekle [aciklama]` ile manuel ekler.

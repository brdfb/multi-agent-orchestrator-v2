---
name: ragip-ozet
description: Ragip Aga dashboard — firma kartlari, aktif gorevler, son hesaplamalar ve nakit durum ozetini tek ekranda goster. Gunluk sabah brifingi icin ideal.
argument-hint: "[firma_id veya bos=tum ozet]"
allowed-tools: Bash, Read
disable-model-invocation: true
---

Sen Ragip Aga'sin. Gunluk brifing olarak tum acik konularin ozetini goster.

## Girdi
$ARGUMENTS

Firma ID verilmisse sadece o firmanin ozetini goster. Bos ise tum ozet.

## Yapilacaklar

### Tam Ozet (arguman yok)

**1. Firma Kartlari Ozeti (Bash):**
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
firma_dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
gorev_dosya = Path(_ROOT) / 'data/RAGIP_AGA/gorevler.jsonl'
profil_dosya = Path(_ROOT) / 'data/RAGIP_AGA/profil.json'

# --- PROFIL ---
if profil_dosya.exists():
    p = json.loads(profil_dosya.read_text(encoding='utf-8'))
    doviz = p.get('doviz_riski', {})
    doviz_str = ', '.join(doviz.get('para_birimleri', [])) if doviz.get('var') else 'Yok'
    print(f'FIRMA PROFILI: {p.get(\"firma_adi\", \"-\")}')
    print(f'  Sektor: {p.get(\"sektor\", \"-\")} | Is: {p.get(\"is_tipi\", \"-\")} | Doviz: {doviz_str}')
    print(f'  Buyukluk: {p.get(\"firma_buyuklugu\", \"-\")} | Musteri: {p.get(\"musteri_tipi\", \"-\")}')
    print()
else:
    print('FIRMA PROFILI: Tanimlanmamis (/ragip-profil kaydet)')
    print()

# --- FIRMALAR ---
firmalar = []
if firma_dosya.exists() and firma_dosya.read_text().strip():
    firmalar = [json.loads(l) for l in firma_dosya.read_text().strip().split('\n') if l.strip()]

risk_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}
risk_sayac = {'yuksek': 0, 'orta': 0, 'dusuk': 0}
for f in firmalar:
    r = f.get('risk_notu', 'orta')
    risk_sayac[r] = risk_sayac.get(r, 0) + 1

print('=' * 56)
print('  RAGIP AGA — GUNLUK BRIFING')
print('=' * 56)
print()

print(f'FIRMA KARTLARI ({len(firmalar)})')
print(f'  Yuksek risk: {risk_sayac[\"yuksek\"]}  |  Orta: {risk_sayac[\"orta\"]}  |  Dusuk: {risk_sayac[\"dusuk\"]}')
print('-' * 40)
for f in sorted(firmalar, key=lambda x: (0 if x.get('risk_notu')=='yuksek' else 1 if x.get('risk_notu')=='orta' else 2, x.get('ad',''))):
    icon = risk_icon.get(f.get('risk_notu', 'orta'), '?')
    vade = f.get('vade_gun', '-')
    oran = f.get('vade_farki_oran', 0)
    oran_str = f'%{oran}/ay' if oran else '-'
    print(f'  {icon} [{f[\"id\"]}] {f[\"ad\"]:<35} {vade:>3}g  {oran_str}')
print()

# --- GOREVLER ---
gorevler = []
if gorev_dosya.exists() and gorev_dosya.read_text().strip():
    gorevler = [json.loads(l) for l in gorev_dosya.read_text().strip().split('\n') if l.strip()]

aktif = [g for g in gorevler if g.get('durum') != 'tamamlandi']
tamamlanan = [g for g in gorevler if g.get('durum') == 'tamamlandi']

oncelik_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}

from datetime import date
bugun = str(date.today())

geciken = 0
print(f'AKTIF GOREVLER ({len(aktif)})')
if not aktif:
    print('  Aktif gorev yok.')
else:
    print('-' * 40)
    for g in sorted(aktif, key=lambda x: x.get('son_tarih', '')):
        icon = oncelik_icon.get(g.get('oncelik', 'orta'), '?')
        st = g.get('son_tarih', '')
        gecikme = ' ** GECIKTI' if st and st < bugun else ''
        if gecikme:
            geciken += 1
        konu = g.get('konu', '')
        konu_str = f' [{konu}]' if konu else ''
        print(f'  {icon} [{g[\"id\"]}]{konu_str} {g[\"gorev\"]}')
        print(f'       Son: {st}{gecikme}')
    if geciken:
        print(f'  --- {geciken} gorev gecikti! ---')
print()

if tamamlanan:
    print(f'TAMAMLANAN ({len(tamamlanan)})')
    for g in tamamlanan[-3:]:
        print(f'  [{g[\"id\"]}] {g[\"gorev\"]}')
    print()

# --- OZET ISTATISTIKLER ---
print('OZET')
print('-' * 40)
print(f'  Toplam firma    : {len(firmalar)}')
print(f'  Yuksek riskli   : {risk_sayac[\"yuksek\"]}')
print(f'  Aktif gorev     : {len(aktif)}')
print(f'  Tamamlanan      : {len(tamamlanan)}')
print(f'  Geciken gorev   : {geciken}')
print()
print('HIZLI KOMUTLAR')
print('  /ragip-firma listele       — Tum firma kartlari')
print('  /ragip-gorev listele       — Tum gorevler')
print('  /ragip-vade-farki A O G    — Vade farki hesapla')
print('  /ragip-strateji [senaryo]  — 3 senaryo stratejisi')
"
```

### Firma Detay Ozeti (firma_id verilmisse)

**1. Firma Karti + Iliskili Gorevler (Bash):**
```bash
python3 -c "
import json, subprocess as _sp
from pathlib import Path

_ROOT = _sp.check_output(['git', 'rev-parse', '--show-toplevel'], text=True, stderr=_sp.DEVNULL).strip()
firma_dosya = Path(_ROOT) / 'data/RAGIP_AGA/firmalar.jsonl'
gorev_dosya = Path(_ROOT) / 'data/RAGIP_AGA/gorevler.jsonl'
firma_id = 'FIRMA_ID_BURAYA'

firmalar = []
if firma_dosya.exists() and firma_dosya.read_text().strip():
    firmalar = [json.loads(l) for l in firma_dosya.read_text().strip().split('\n') if l.strip()]

firma = None
for f in firmalar:
    if f['id'] == firma_id:
        firma = f
        break

if not firma:
    print(f'Firma bulunamadi: ID {firma_id}')
    exit()

risk_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}
icon = risk_icon.get(firma.get('risk_notu', 'orta'), '?')

print('=' * 56)
print(f'  FIRMA DETAY: {firma[\"ad\"]}')
print('=' * 56)
print()
print(f'  ID          : {firma[\"id\"]}')
print(f'  VKN         : {firma.get(\"vergi_no\", \"-\")}')
tel = firma.get('iletisim', {}).get('tel', '-')
email = firma.get('iletisim', {}).get('email', '-')
print(f'  Tel         : {tel}')
print(f'  E-posta     : {email}')
print(f'  Vade        : {firma.get(\"vade_gun\", \"-\")} gun')
oran = firma.get('vade_farki_oran', 0)
print(f'  Vade farki  : %{oran}/ay' if oran else '  Vade farki  : -')
print(f'  Risk        : {icon} {firma.get(\"risk_notu\", \"-\")}')
print(f'  Son islem   : {firma.get(\"son_islem\", \"-\")}')
if firma.get('notlar'):
    print(f'  Notlar      : {firma[\"notlar\"]}')
print()

# Iliskili gorevler (konu eslesmesi)
firma_ad_kisa = firma['ad'].split()[0].lower()  # Ilk kelime ile ara
gorevler = []
if gorev_dosya.exists() and gorev_dosya.read_text().strip():
    gorevler = [json.loads(l) for l in gorev_dosya.read_text().strip().split('\n') if l.strip()]

iliskili = [g for g in gorevler if firma_ad_kisa in g.get('konu', '').lower() or firma_ad_kisa in g.get('gorev', '').lower()]
aktif = [g for g in iliskili if g.get('durum') != 'tamamlandi']
tamamlanan = [g for g in iliskili if g.get('durum') == 'tamamlandi']

from datetime import date
bugun = str(date.today())

if aktif:
    print(f'AKTIF GOREVLER ({len(aktif)})')
    print('-' * 40)
    for g in sorted(aktif, key=lambda x: x.get('son_tarih', '')):
        st = g.get('son_tarih', '')
        gecikme = ' ** GECIKTI' if st and st < bugun else ''
        oncelik_icon = {'yuksek': '!', 'orta': '~', 'dusuk': '+'}
        oi = oncelik_icon.get(g.get('oncelik', 'orta'), '?')
        print(f'  {oi} [{g[\"id\"]}] {g[\"gorev\"]}')
        print(f'       Son: {st}{gecikme}')
    print()

if tamamlanan:
    print(f'TAMAMLANAN ({len(tamamlanan)})')
    for g in tamamlanan[-3:]:
        print(f'  [{g[\"id\"]}] {g[\"gorev\"]}')
    print()

if not aktif and not tamamlanan:
    print('Bu firma ile iliskili gorev bulunamadi.')
    print()

# Hizli hesaplama onerisi
if oran:
    print('HIZLI ISLEMLER')
    print(f'  /ragip-vade-farki [tutar] {oran} [gun]  — Vade farki hesapla')
    print(f'  /ragip-strateji [senaryo]               — Strateji olustur')
    print(f'  /ragip-ihtar [konu]                     — Ihtar taslagi')
    print(f'  /ragip-dis-veri {firma[\"ad\"]}            — Dis kaynak arastir')
"
```

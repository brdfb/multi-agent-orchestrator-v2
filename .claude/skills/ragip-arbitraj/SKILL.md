---
name: ragip-arbitraj
description: Arbitraj firsatlarini hesapla. CIP faiz paritesi, ucgen kur, vade farki vs mevduat ve carry trade arbitrajlari. Canli TCMB oranlariyla calisir.
argument-hint: "[tur: cip|ucgen|vade-mevduat|carry-trade] [parametreler]"
allowed-tools: Bash, WebSearch
---

Sen Ragip Aga'sin — 40 yillik piyasa tecrubesiyle arbitraj firsatlarini tespit edersin.

## Girdi
$ARGUMENTS

Girdi yoksa sor: "Hangi arbitraj hesabi? cip / ucgen / vade-mevduat / carry-trade"

## Yapilacaklar

**1. Guncel TCMB oranlarini cek:**
```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/.orchestrator")
python3 "$ROOT/scripts/ragip_rates.py" --pretty
```

**2. Arbitraj turune gore hesapla:**

### A. CIP Faiz Paritesi Arbitraji

Kullanici piyasa forward kurunu vermelidir. Vermemisse WebSearch ile `USD TRY forward rate 90 day 2026` ara.

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/.orchestrator")
RATES=$(python3 "$ROOT/scripts/ragip_rates.py" 2>/dev/null)

RATES_JSON="$RATES" python3 -c "
import json, os
rates = json.loads(os.environ.get('RATES_JSON', '{}'))
spot = rates['usd_kuru']
r_tl = rates['politika_faizi']

market_forward = MARKET_FORWARD  # Kullanicidan al
r_usd = R_USD  # Varsayilan: 4.5
gun = GUN

t = gun / 365
teorik = spot * (1 + r_tl/100 * t) / (1 + r_usd/100 * t)
sapma = ((market_forward - teorik) / teorik) * 100
islem_maliyeti = 0.1

print(f'=== CIP ARBITRAJ ===')
print(f'Spot kur       : {spot:.4f}')
print(f'Teorik forward : {teorik:.4f}')
print(f'Piyasa forward : {market_forward:.4f}')
print(f'Sapma          : %{sapma:.3f}')
print(f'Islem maliyeti : %{islem_maliyeti:.2f}')
if abs(sapma) > islem_maliyeti:
    yon = 'TL mevduata yatir + forward sat' if sapma > 0 else 'USD mevduata yatir + forward al'
    print(f'ARBITRAJ FIRSATI VAR!')
    print(f'Yon: {yon}')
    print(f'Tahmini kar: %{abs(sapma) - islem_maliyeti:.3f}')
else:
    print(f'Arbitraj yok — sapma islem maliyetinden kucuk')
"
```

### B. Ucgen Kur Arbitraji

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/.orchestrator")
RATES=$(python3 "$ROOT/scripts/ragip_rates.py" 2>/dev/null)

RATES_JSON="$RATES" python3 -c "
import json, os
rates = json.loads(os.environ.get('RATES_JSON', '{}'))
usd_try = rates['usd_kuru']
eur_try = rates['eur_kuru']
eur_usd = eur_try / usd_try

baslangic = 1_000_000  # 1M EUR

# Yol A: EUR -> USD -> TRY -> EUR
usd = baslangic * eur_usd
tl = usd * usd_try
son_eur_a = tl / eur_try
kar_a = (son_eur_a - baslangic) / baslangic * 100

# Yol B: EUR -> TRY -> USD -> EUR
tl_b = baslangic * eur_try
usd_b = tl_b / usd_try
son_eur_b = usd_b / eur_usd
kar_b = (son_eur_b - baslangic) / baslangic * 100

islem_maliyeti = 0.15 * 3  # 3 bacak x %0.15
net = max(kar_a, kar_b) - islem_maliyeti

print(f'=== UCGEN KUR ARBITRAJI ===')
print(f'USD/TRY: {usd_try:.4f} | EUR/TRY: {eur_try:.4f} | EUR/USD: {eur_usd:.4f}')
print(f'Dolayli EUR/TRY: {eur_usd * usd_try:.4f}')
print(f'Yol A kar: %{kar_a:.4f} | Yol B kar: %{kar_b:.4f}')
print(f'Islem maliyeti: %{islem_maliyeti:.2f}')
print(f'Net kar: %{net:.4f}')
if net > 0:
    print('ARBITRAJ FIRSATI VAR!')
else:
    print('Arbitraj yok — spread islem maliyetini karsilamiyor')
"
```

### C. Vade Farki vs Mevduat Arbitraji

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/.orchestrator")
RATES=$(python3 "$ROOT/scripts/ragip_rates.py" 2>/dev/null)

RATES_JSON="$RATES" python3 -c "
import json, os
rates = json.loads(os.environ.get('RATES_JSON', '{}'))
tcmb = rates['politika_faizi']

anapara = ANAPARA  # Kullanicidan al
vade_oran = VADE_ORAN  # Aylik %
gun = GUN
mevduat_oran = MEVDUAT_ORAN  # Yillik %, yoksa tcmb kullan

vade_farki = anapara * (vade_oran/100) * gun / 30
mevduat_getiri = anapara * (mevduat_oran/100) * gun / 365
net_fark = mevduat_getiri - vade_farki

print(f'=== VADE FARKI vs MEVDUAT ===')
print(f'Anapara         : {anapara:>15,.2f} TL')
print(f'Vade farki ({gun:>2}g) : {vade_farki:>15,.2f} TL (%{vade_oran}/ay = ~%{vade_oran*12:.0f}/yil)')
print(f'Mevduat  ({gun:>2}g)  : {mevduat_getiri:>15,.2f} TL (%{mevduat_oran}/yil)')
print(f'Net fark        : {net_fark:>15,.2f} TL')
print()
if net_fark > 0:
    print(f'KARAR: Parayi mevduata yatir, tedarikciye gec ode')
    print(f'Kazanc: {net_fark:,.2f} TL ({gun} gunde)')
else:
    print(f'KARAR: Erken ode, vade farkindan kurtul')
    print(f'Tasarruf: {abs(net_fark):,.2f} TL ({gun} gunde)')
"
```

### D. Carry Trade Analizi

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/.orchestrator")
RATES=$(python3 "$ROOT/scripts/ragip_rates.py" 2>/dev/null)

RATES_JSON="$RATES" python3 -c "
import json, os
rates = json.loads(os.environ.get('RATES_JSON', '{}'))
spot = rates['usd_kuru']
r_tl = rates['politika_faizi'] / 100
r_usd = R_USD / 100  # Varsayilan: 4.5
gun = GUN
t = gun / 365

# 1 USD borc al, TL'ye cevir, mevduata yatir
tl_yatirim = spot * (1 + r_tl * t)
usd_borc = 1 + r_usd * t
basabas = tl_yatirim / usd_borc

# Unhedged: kur ayni kalirsa
unhedged_usd = tl_yatirim / spot
unhedged_kar = (unhedged_usd - usd_borc) * 100

print(f'=== CARRY TRADE ===')
print(f'Spot: {spot:.4f} | TL faiz: %{r_tl*100:.1f} | USD faiz: %{r_usd*100:.1f} | Sure: {gun} gun')
print(f'1 USD borc al -> {spot:.2f} TL -> {gun} gun sonra: {tl_yatirim:.2f} TL')
print(f'Basabas (break-even) kur: {basabas:.4f}')
print(f'Unhedged kar (kur sabit): %{unhedged_kar:.2f} ({gun} gun)')
# Beklenen kur varsa:
# beklenen = BEKLENEN_KUR
# beklenen_usd = tl_yatirim / beklenen
# beklenen_kar = (beklenen_usd - usd_borc) * 100
# print(f'Beklenen kur ({beklenen:.2f}) ile kar: %{beklenen_kar:.2f}')
print()
if basabas > spot * 1.15:
    print('UYARI: Basabas kuru spot tan %15+ yukarda — kur riski yuksek')
"
```

**3. Yorum yaz:**
- Arbitraj firsati var mi yok mu?
- Islem maliyetleri ve pratik engeller
- Risk/getiri degerlendirmesi

## Cikti Formati

### HESAPLAMALAR (Bash ciktisi)

### RAGIP AGA'NIN YORUMU
- Arbitraj firsatinin gercekligi (piyasa etkinligi, islem hizi)
- Pratik engeller (limit, teminat, spread)
- Net tavsiye ("Bu firsat [anlamli/ihmal edilebilir]")

### UYARI
Bu hesaplama hukuki veya yatirim tavsiyesi degildir. Kesin islem oncesi uzman gorusu alin.

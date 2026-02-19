# Tam Kullanım Örneği – Bir Konuyu Tasarlama (Dummy Kullanıcı Rehberi)

Bu dokümanda **tek bir konu** üzerinden, projeyi hiç bilmeyen biri için baştan sona ne yapacağını ve arka planda ne olduğunu adım adım anlatıyorum.

> **Bu aracı ne zaman kullanmalıyım?** → [KULLANIM_DURUMLARI_VE_SENARYOLAR.md](KULLANIM_DURUMLARI_VE_SENARYOLAR.md) — Kullanım durumları, senaryolar, pipeline özeti ve Cursor/Claude ile fark.

---

## Örnek konumuz

**"Bir todo uygulaması için REST API tasarla: endpoint’ler, veritabanı şeması ve güvenlik notları olsun."**

Bu cümleyi sisteme verip **tasarlatma → inceleme → özet** akışının tamamını göreceğiz.

---

## 0. Ön hazırlık (bir kere)

### 0.1 Proje dizini ve sanal ortam

```bash
cd ~/.orchestrator
source .venv/bin/activate   # veya: .venv/bin/python kullan
```

(Venv yoksa: `make install`)

### 0.2 API anahtarları

En az bir provider’ın anahtarı olmalı. Örnek: `.env` dosyasında:

```bash
# .env (proje kökünde)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=...  (opsiyonel)
```

Anahtarlar yüklü mü diye komut çalıştırdığında ilk satırlarda "🔑 API keys: environment" veya "📁 API keys: .env" yazar.

### 0.3 CLI nasıl çalıştırılır?

- **Makefile ile:**  
  `make agent-ask AGENT=builder Q="soru"`  
  `make agent-chain Q="soru"`
- **Doğrudan Python ile (tercih edilen):**  
  `.venv/bin/python scripts/agent_runner.py builder "soru"`  
  `.venv/bin/python scripts/chain_runner.py "soru"`
- **Alias tanımlıysa:**  
  `mao builder "soru"`  
  `mao-chain "soru"`

Aşağıda **chain_runner** ile gideceğiz; yani **tam zincir** (builder → critic → closer).

---

## 1. Sen ne yazıyorsun?

Tek komut:

```bash
.venv/bin/python scripts/chain_runner.py "Bir todo uygulaması için REST API tasarla: endpoint'ler, veritabanı şeması ve güvenlik notları olsun."
```

İstersen çıktıyı dosyaya da kaydedebilirsin:

```bash
.venv/bin/python scripts/chain_runner.py "Bir todo uygulaması için REST API tasarla: endpoint'ler, veritabanı şeması ve güvenlik notları olsun." --save-to todo-api-rapor.md
```

---

## 2. Ekranda ne görürsün? (Sırayla)

Komutu verdikten sonra kabaca şunlar çıkar (metinler projedeki Rich çıktısına göre):

1. **Üst bilgi**
   - API key nereden yüklendi (environment / .env).
   - Çalışacak zincir: `builder → critic → closer` (veya config’e göre multi-critic ile birkaç critic).
   - Prompt’un kısa özeti veya ilk 100 karakteri.

2. **Stage 1 – Builder**
   - "🔄 Stage 1/3: Running BUILDER..."
   - Bittiğinde:
     - Hangi model kullanıldı (örn. `anthropic/claude-sonnet-4-5`).
     - Süre (ms), token sayıları.
     - **Uzun metin:** Problem → Çözüm → Kod örnekleri → Trade-off’lar.  
       Yani taslak: endpoint listesi, örnek şema, güvenlik notları, belki kısa kod parçaları (syntax highlighting ile).

3. **Stage 2 – Critic (veya birden fazla critic)**
   - "🔄 Stage 2/3: Running CRITIC..." (veya "Running CODE-QUALITY-CRITIC" vb.)
   - Bittiğinde:
     - Model (örn. `openai/gpt-4o-mini`).
     - **İnceleme metni:** Eksikler, riskler, iyileştirme önerileri (madde madde veya "Issue 1, Issue 2" tarzı).

4. **Stage 3 – Closer**
   - "🔄 Stage 3/3: Running CLOSER..."
   - Bittiğinde:
     - Model (örn. Gemini).
     - **Özet + aksiyon listesi:** Ne yapıldı, ne karar verildi, sıradaki adımlar (bullet list).

5. **En sonda – Özet kutu**
   - Kaç stage tamamlandı (örn. 3/3).
   - Toplam süre (saniye).
   - Toplam token.
   - "✅ Chain completed successfully!" veya hata varsa hangi stage’de koptuğu.

`--save-to todo-api-rapor.md` kullandıysan aynı çıktı (prompt + her stage’in cevabı) bu dosyaya da yazılır.

---

## 3. Arka planda ne oluyor? (Akış)

Aynı komutu verdiğinde sistem içeride şu adımları yapar (sen sadece tek cümle yazdın):

1. **Session**
   - CLI için oturum ID üretilir (örn. `cli-12345-20260214…`). Aynı terminal oturumunda yeni sorular bu session’a bağlanır; bellek bu oturuma göre “son konuşmalar”ı kullanır.

2. **Stage 1 – Builder**
   - **Girdi:** Senin prompt’un (+ varsa aynı session’daki önceki mesajlar + diğer session’lardan anlamsal olarak çekilen “bellek”).
   - **Agent:** Builder (config’teki system prompt: tasarım/kod odaklı, somut örnek ver, trade-off yaz).
   - **Model:** Varsayılan builder modeli (örn. Claude Sonnet). Başarısız olursa fallback (örn. GPT-4o-mini, sonra Gemini).
   - **Çıktı:** Uzun taslak metin (endpoint’ler, şema, güvenlik notları, kod parçaları).
   - **Kayıt:** Bu konuşma JSON log’a yazılır (`data/CONVERSATIONS/...`), memory açıksa SQLite’a da kaydedilir (ileride “daha önce todo API konuşmuştuk” diye kullanılsın diye).

3. **Stage 2 – Critic**
   - **Girdi:** Orijinal prompt’un + builder çıktısının bir kısmı (uzunsa sıkıştırılmış/semantik özet). Config’te multi-critic / dynamic selection varsa “todo, API, güvenlik” gibi kelimelere göre hangi critic’lerin çalışacağı seçilir (örn. sadece code-quality-critic).
   - **Agent:** Seçilen critic(ler) (kod kalitesi, güvenlik, performans vb.).
   - **Model:** Critic’in varsayılan modeli (örn. GPT-4o-mini).
   - **Çıktı:** İnceleme metni (sorunlar, öneriler).
   - **Kayıt:** Yine log + isteğe bağlı memory.

4. **Stage 3 – Closer**
   - **Girdi:** Orijinal prompt + builder’dan özet + critic’ten özet (config’e göre karakter limitleri var; tam metin değil, özetlenmiş hali).
   - **Agent:** Closer (system prompt: kararları netleştir, aksiyon listesi çıkar).
   - **Model:** Closer’ın varsayılan modeli (örn. Gemini).
   - **Çıktı:** Nihai özet ve “yapılacaklar” listesi.
   - **Kayıt:** Log + memory.

5. **Refinement (opsiyonel)**
   - Config’te refinement açıksa: critic “kritik” bir şey bulduysa (örn. güvenlik açığı) bir kez daha builder → critic dönebilir; belirli iterasyon sayısına kadar tekrarlanır. Sen ekstra bir şey yapmazsın; akış otomatik.

Tüm bu adımlar **senin yazdığın tek komuttan** tetiklenir; sen sadece konuyu (tasarlanacak şeyi) cümleyle veriyorsun.

---

## 4. Çıktılar nereye gidiyor?

| Nereye | Ne |
|--------|----|
| **Terminal** | Tüm stage’lerin cevapları (Rich ile renkli, kod vurgulu). |
| **`--save-to dosya.md`** | Aynı içerik: prompt, her stage’in başlığı ve cevabı, en sonda özet. |
| **`data/CONVERSATIONS/`** | Her LLM çağrısı için bir JSON dosyası (tarih-saat, agent, model, prompt, response, token, süre). |
| **Bellek (SQLite)** | Memory açık agent’lar için: prompt + response + session_id; ileride “benzer konu” sorduğunda bu konuşmalar bağlama enjekte edilir. |

Yani:
- **İnsan:** Terminal + isteğe bağlı `--save-to` ile rapor dosyası.
- **Makine:** Log’lar (debug/analiz) ve bellek (sonraki sorularda bağlam).

---

## 5. Aynı konuyu “sadece tasarlat” veya “sadece incelet” demek istersen

- **Sadece tasarım (builder):**  
  ```bash
  .venv/bin/python scripts/agent_runner.py builder "Bir todo uygulaması için REST API tasarla: endpoint'ler, şema, güvenlik."
  ```
  Sadece builder çalışır; critic ve closer yok.

- **Sadece inceleme (critic):**  
  Zaten elinde bir taslak metin varsa (örn. `taslak.md`):  
  ```bash
  .venv/bin/python scripts/agent_runner.py critic --file taslak.md
  ```
  Sadece critic çalışır; çıktıyı terminalde görürsün.

- **Tam zincir ama özel stage’ler:**  
  ```bash
  .venv/bin/python scripts/chain_runner.py "Aynı todo API konusu" builder critic
  ```
  Burada sadece builder → critic; closer çalışmaz.

Yani “konuyu tasarlat” = ya tek builder ya da chain (builder→critic→closer). Tam rapor istiyorsan chain + `--save-to` kullanmak en net yol.

---

## 6. Sonraki kullanım: bellek ve tekrar

- Aynı terminalde (aynı session’da) başka bir soru sorarsan (örn. “Bu API’ye auth ekle”), sistem **bu session’daki önceki mesajları** ve **diğer session’lardan anlamsal olarak benzer konuşmaları** (örn. “todo API”) builder/critic’e ek bağlam olarak verir. Böylece “az önce tasarladığımız API” referansı olur.
- Log’lara bakmak: `make agent-last` (son konuşma), `mao-last-chain` (son zincir), veya `data/CONVERSATIONS/` altındaki JSON’lar.
- İstatistik: `make stats` (veya `scripts/stats_cli.py`) ile token/maliyet özeti.

---

## 7. Tek cümleyle özet (dummy için)

- **Konuyu cümleyle yazıyorsun:** “Bir todo uygulaması için REST API tasarla: endpoint’ler, veritabanı şeması ve güvenlik notları olsun.”
- **Tek komut:** `chain_runner.py` ile bu cümleyi veriyorsun (istersen `--save-to rapor.md`).
- **Sistem:** Bu cümleyi alıp sırayla builder (tasarla) → critic (incele) → closer (özetle) yaptırıyor; çıktılar ekrana ve istersen dosyaya yazılıyor, log ve bellek de güncelleniyor.
- **Sen:** Sadece konuyu tasarlatmak istediğin cümleyi yazıyorsun; akışın tüm detayı (hangi model, ne kadar token, bellek enjeksiyonu, refinement) arka planda otomatik işliyor.

Bu akış, “bir konuyu tasarla” demenin bu projede tam karşılığıdır; Open WebUI’daki tek sohbetten farkı, burada **rol bazlı ve çok adımlı** bir pipeline’ın otomatik çalışmasıdır.


---

## 8. Başka bir konu tasarlayınca ikisi karışmaz mı?

Hayır; iki konu birbirine karışmaz. Sebepleri:

### 8.1 Asıl talimat hep senin yeni cümlen

Modele giden metin kabaca şöyle:

```
[MEMORY CONTEXT - Relevant past conversations]
Previous conversation (relevance: 0.xx):
Q: "Todo API tasarla..."
A: "..."
---
[Agent'ın asıl system prompt'u]

User: Bir kimlik doğrulama sistemi tasarla: JWT, refresh token, RBAC.
```

- **Ana görev:** Son satırdaki "User: ..." — yani **o an yazdığın cümle**. Model buna cevap verir.
- **Bellek bloğu:** Sadece "daha önce buna benzer konuşulmuştu" diye **referans**; cevabın konusu yine senin yeni cümlen (kimlik doğrulama). Todo API metni "bilgi" olarak durabilir, ama "şimdi ne tasarlanacak?" sorusunun cevabı **her zaman** yeni cümlen.

Yani: Farklı bir konu sorduğunda (örn. auth sistemi), çıktı **o konuya** (auth) dair olur; todo ile karışmaz.

### 8.2 Hangi eski konuşmalar gelir? (Anlamsal arama)

Bellek tarafı **senin o anki cümlene** göre çalışır:

- **"Todo API tasarla"** → Geçmişte "API", "endpoint", "şema" geçen konuşmalar daha çok çekilir.
- **"JWT ile auth sistemi tasarla"** → "auth", "JWT", "token" geçen konuşmalar daha çok çekilir.

Konular gerçekten farklıysa (todo vs auth), kelime/anlam örtüşmesi az olur; gelen eski bağlam da az olur veya hiç gelmez. Yani "başka konu" dediğinde zaten büyük ölçüde **o konuya** benzer geçmiş kullanılır.

### 8.3 Session: Aynı terminal vs yeni terminal

- **Aynı terminalde** art arda iki konu sorarsan (önce todo, sonra auth): Aynı **session** kullanılır; "son 5 mesaj" (session context) hem todo hem auth içerebilir. Ama yine de **son soru** "auth tasarla" olduğu için cevap auth'a dair olur; todo sadece "önceki konuşma" olarak kalır.

- **Tamamen ayrı olsun istersen:** Yeni bir terminal açıp komutu orada çalıştır. Yeni terminal = yeni process = **yeni session**. Eski terminaldeki "todo" session bu yeni oturumda hiç kullanılmaz; sadece anlamsal benzerlikle (knowledge) belki birkaç eski konuşma gelir, onlar da yeni cümlene (auth) benzer olanlardan seçilir.

### 8.4 Özet tablo

| Durum | Ne olur? |
|--------|----------|
| Aynı terminalde önce todo API, sonra auth tasarla | Cevap **auth**'a dair; todo sadece isteğe bağlı referans. |
| Yeni terminalde auth tasarla | Eski terminalin session'ı kullanılmaz; cevap yine **auth**'a dair. |
| Çok farklı konular (todo vs auth) | Anlamsal arama az örtüşme bulur; az veya sıfır eski bağlam. |
| Benzer konular (todo API → başka API) | İkinci konuda birinci tasarım referans olarak kullanılabilir; yine de **ana talimat** ikinci cümlen. |

**Kısa cevap:** Başka bir konuyu tasarlatırken karışmaz; çünkü modelin **asıl görevi** her zaman o an yazdığın cümle. Eski konuşmalar sadece yardımcı bağlam; "şimdi ne üretilecek?" her zaman senin yeni soruna göre belirlenir.

---

## 9. Aynı konu üzerinde konuşmaya devam edersek ne olur?

Aynı konuda art arda soru sorduğunda (takip sorusu / devam konuşması) sistem **session context** ile bu oturumdaki son konuşmaları modele verir; böylece “az önce ne tasarladık, şimdi ona ne ekliyoruz?” bağlamı korunur.

### 9.1 Nasıl çalışıyor?

- **Aynı terminal** = aynı **session_id** (örn. `cli-12345-...`). Her `run()` veya chain sonrası o oturumda yeni bir konuşma kaydı (prompt + response) belleğe yazılır.
- Sonraki soruda (örn. “Bu API’ye JWT auth ekle”) sistem:
  1. **Session context:** Bu session’daki **son N konuşmayı** (varsayılan **5**) veritabanından çeker; “önceki soru–cevap” metinleri system prompt’a eklenir.
  2. **Knowledge context:** İsteğe bağlı; diğer oturumlardan anlamsal arama ile benzer konuşmalar da eklenebilir.
  3. **Ana talimat:** Yine **senin yeni cümlen** user mesajı olarak gider: “Bu API’ye JWT auth ekle”.

Yani modele giden şey kabaca:

```
[MEMORY CONTEXT]
Session (son konuşmalar):
  Q: Todo uygulaması için REST API tasarla...
  A: [Builder’ın tasarım cevabı]
  ---
  (varsa daha eski mesajlar, en fazla 5 exchange)

[System prompt + yukarıdaki context]

User: Bu API'ye JWT auth ekle.
```

Model hem “daha önce ne tasarladık”ı görür hem de “şimdi ne istiyoruz”u (JWT auth ekle); cevabı aynı proje üzerinde devam eder.

### 9.2 Pratik örnek (aynı konu, aynı terminal)

1. **İlk komut:**  
   `mao-chain "Todo uygulaması için REST API tasarla: endpoint'ler, şema, güvenlik."`  
   → Builder tasarım yapar, critic inceler, closer özetler; hepsi bu session’a kaydedilir.

2. **İkinci komut (aynı terminalde):**  
   `mao-chain "Bu API'ye JWT ile kimlik doğrulama ekle; endpoint'leri ve şemayı güncelle."`  
   → Session context’te az önceki “Todo API” tasarımı gelir; builder/critic “bu API” derken o tasarımı referans alır, JWT ekleyerek günceller.

3. **Üçüncü komut (yine aynı terminal):**  
   `mao-chain "Rate limiting ve hata kodları (4xx/5xx) ekle."`  
   → Yine son N konuşma (ilk tasarım + JWT ekleme) bağlama girer; cevap aynı API tasarımı üzerinde devam eder.

### 9.3 Limitler

- **Session context:** Varsayılan **son 5 konuşma** (soru–cevap çifti). Config’te `session_context.limit` ile değiştirilebilir.
- **Token bütçesi:** Session + knowledge toplamı agent’ın `max_context_tokens` değerini aşmaz; gerekirse eski mesajlar kırpılır.
- **Session süresi (CLI):** Aynı terminal açık kaldığı sürece aynı session kullanılır; belirli süre (örn. 2 saat) kullanılmazsa session “eski” sayılıp yeni soruda yeni session da açılabilir (implementasyona bağlı).

### 9.4 Özet

| Ne yapıyorsun | Ne olur |
|----------------|--------|
| Aynı terminalde, aynı konuda takip sorusu | Session context ile **son N konuşma** modele gider; aynı tasarım/proje üzerinde devam edersin. |
| “Bu API’ye X ekle”, “Endpoint’leri detaylandır” | Model “bu API” = az önce konuştuğun tasarım; cevabı ona göre günceller. |
| Yeni terminal açarsan | Yeni session; o terminalde “önceki” konuşma yok (sadece knowledge ile benzer konuşmalar gelebilir). |

**Kısa cevap:** Aynı konu üzerinde konuşmaya devam edersen, aynı oturumdaki **son konuşmalar** (session context) otomatik olarak modele verilir; böylece tasarım/proje bağlamı korunur ve sohbet aynı konuda sürer.

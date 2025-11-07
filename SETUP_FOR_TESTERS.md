# 🧪 Multi-Agent Orchestrator - Test Setup Guide

**Bu dosya test kullanıcıları içindir.**

---

## 📋 Seninle Paylaşılma Sebebi

Bu sistemi test etmen için sana erişim verildi. **Amaç:**
- ✅ Kurulum dokümanlarını test etmek
- ✅ Hataları bulmak
- ✅ İyileştirme önerileri almak
- ✅ Gerçek kullanıcı deneyimini görmek

**Önemli:** Bu senin sandbox'ın - istediğin gibi oyna, bozabilirsin!

---

## 🔐 Güvenlik: Fork Kullanmalısın

### ❌ YAPMA: Direkt Clone
```bash
# Bu yöntemi KULLANMA:
git clone https://github.com/brdfb/multi-agent-orchestrator-v2.git
# Çünkü: Push yapamazsın, değişikliklerini kaybedersin
```

### ✅ YAP: Fork + Clone
```bash
# Adım 1: GitHub'da "Fork" butonuna bas
# → https://github.com/brdfb/multi-agent-orchestrator-v2
# → Sağ üstte "Fork" butonu
# → "Create fork" butonuna bas

# Adım 2: KENDI fork'unu clone et
git clone https://github.com/SENIN-KULLANICI-ADIN/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
```

**Neden fork?**
- ✅ Kendi repo'nda çalışırsın
- ✅ İstediğin gibi commit yapabilirsin
- ✅ Bozarsan sadece senin fork'un bozulur
- ✅ Orijinal repo güvende kalır

---

## 🪟 Windows Kullanıcıları: WSL Kurulumu (Adım 0)

**Windows kullanıcısıysan bu bölümü oku! macOS/Linux kullanıcıları [Adım 1'e](#adım-1-hızlı-kurulum-60-saniye) geçebilir.**

### Adım 0.1: WSL2 Kurulumu (İlk Kez İse)

**Windows PowerShell'i Administrator Olarak Aç:**
```
Windows tuşu + X → "Windows PowerShell (Admin)" veya "Terminal (Admin)"
```

**WSL2 Kur:**
```powershell
# WSL'i yükle (Windows 10 version 2004+ veya Windows 11)
wsl --install

# Bilgisayarı yeniden başlat
# (Gerekli - WSL çalışmaya başlamak için restart şart)
```

**Yeniden başlatma sonrası:**
- Ubuntu otomatik açılacak
- Kullanıcı adı iste: **küçük harf kullan** (örn: `ahmet`, `mehmet`)
- Şifre iste: **şifre yazarken ekranda görünmez** (normal)
- Şifreyi tekrar iste: Aynı şifreyi yaz

**✅ Kontrol Et:**
```powershell
# PowerShell'de (herhangi bir pencere, admin olmasına gerek yok)
wsl --list --verbose

# Görmek istediğin:
#   NAME      STATE           VERSION
# * Ubuntu    Running         2        ← VERSION: 2 olmalı!
```

### Adım 0.2: Git ve Python Kurulumu (WSL Ubuntu İçinde)

**Ubuntu terminalini aç:**
```
Windows tuşu → "Ubuntu" yaz → Enter
```

**Sistem paketlerini güncelle:**
```bash
# İlk komut (biraz zaman alır - 2-3 dk)
sudo apt update && sudo apt upgrade -y

# Şifre iste → Ubuntu şifreni yaz (Adım 0.1'de oluşturduğun)
```

**Git ve Python kur:**
```bash
# Tek komutla hepsini kur
sudo apt install -y git python3 python3-pip python3-venv make curl

# ✅ Kontrol et
python3 --version   # Python 3.10+ olmalı
git --version       # git version 2.x.x olmalı
```

**Git yapılandırması (önemli!):**
```bash
# Kendi bilgilerini yaz
git config --global user.name "Senin Adın"
git config --global user.email "senin@email.com"

# ✅ Kontrol et
git config --list | grep user
# user.name=Senin Adın
# user.email=senin@email.com
```

### Adım 0.3: SSH Key Oluştur (GitHub İçin)

**Neden SSH key?**
- ✅ GitHub'dan private repo clone edebilirsin
- ✅ Her seferinde şifre yazmana gerek yok
- ✅ Daha güvenli (şifre yerine key kullanır)

**SSH key oluştur:**
```bash
# Email'ini kendi email'inle değiştir
ssh-keygen -t ed25519 -C "senin@email.com"

# Soracaklar:
# "Enter file in which to save the key": [Enter'a bas - varsayılan yeri kullan]
# "Enter passphrase": [Enter'a bas - şifresiz (test için), veya şifre koy]
# "Enter same passphrase again": [Enter'a bas veya aynı şifreyi tekrar yaz]
```

**✅ Key oluşturuldu! Şimdi kopyala:**
```bash
# Public key'i göster
cat ~/.ssh/id_ed25519.pub

# Çıktı şuna benzer:
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHx... senin@email.com
#
# ← Bu TÜMÜNÜ kopyala (ssh-ed25519'den başlayıp email'e kadar)
```

### Adım 0.4: SSH Key'i GitHub'a Ekle

**GitHub'a git:**
```
https://github.com/settings/keys
```

**Key ekle:**
1. Sağ üstte "New SSH key" butonuna bas
2. **Title:** "WSL Ubuntu" (veya istediğin isim)
3. **Key:** Kopyaladığın key'i yapıştır (cat komutu çıktısı)
4. "Add SSH key" butonuna bas
5. GitHub şifreni iste → Yaz

**✅ Test et:**
```bash
# GitHub bağlantısını test et
ssh -T git@github.com

# Görmek istediğin:
# Hi KULLANICI-ADIN! You've successfully authenticated...
```

**❌ Hata aldıysan:**
```bash
# "Permission denied (publickey)" → SSH key eklenMEmiş
# → Adım 0.3 ve 0.4'ü tekrar kontrol et

# "Could not resolve hostname" → İnternet bağlantısı yok
# → WiFi/Ethernet bağlantını kontrol et
```

### Adım 0.5: Repository Clone (Fork Kullan!)

**GitHub'da fork yap:**
```
1. https://github.com/brdfb/multi-agent-orchestrator-v2 adresine git
2. Sağ üstte "Fork" butonuna bas
3. "Create fork" butonuna bas
4. Fork oluşturuldu! → Senin URL'in: https://github.com/SENIN-KULLANICI-ADIN/multi-agent-orchestrator-v2
```

**WSL Ubuntu'da clone et:**
```bash
# NOT: SENIN-KULLANICI-ADIN yerine kendi GitHub kullanıcı adını yaz!
git clone git@github.com:SENIN-KULLANICI-ADIN/multi-agent-orchestrator-v2.git

# Çıktı:
# Cloning into 'multi-agent-orchestrator-v2'...
# remote: Enumerating objects: ...
# ✅ Clone başarılı!

# Klasöre gir
cd multi-agent-orchestrator-v2

# ✅ Kontrol et
pwd
# /home/kullanici-adin/multi-agent-orchestrator-v2
```

### 🎯 WSL Kurulum Tamamlandı!

**Artık [Adım 1: Hızlı Kurulum](#adım-1-hızlı-kurulum-60-saniye)'a geçebilirsin.**

**WSL ile ilgili bilgiler:**
- 📁 Windows dosyalarına erişim: `/mnt/c/Users/SenınAdın/`
- 💻 WSL terminaline hızlı erişim: `Windows tuşu → "Ubuntu" → Enter`
- 🔄 WSL'i yeniden başlatma: `wsl --shutdown` (PowerShell'de)
- 📂 WSL dosyalarını Windows'tan görmek: `\\wsl$\Ubuntu\home\kullanici-adin\`

---

## 📦 Kurulum Talimatları

### Adım 1: Hızlı Kurulum (60 Saniye)

**QUICKSTART.md dosyasını takip et:**

```bash
cd multi-agent-orchestrator-v2

# 1. API key'lerini ekle
cp .env.example .env
nano .env  # Kendi API key'lerini yapıştır

# 2. Kurulum
make install

# 3. Test et
make test

# 4. Çalıştır
make run-api
# → http://localhost:5050
```

**Beklenen sonuç:**
- ✅ 29/29 test geçmeli
- ✅ API server başlamalı
- ✅ http://localhost:5050 açılmalı

### Adım 2: Takıldıysan

**TROUBLESHOOTING.md dosyasına bak:**
- Problem 1-8 arası yaygın hatalar
- Her hata için çözüm var

---

## 📝 Feedback: Ne Raporlamalısın?

### 1️⃣ Takıldığın Yerler (ÖNEMLI!)

**Her takıldığında şunları not et:**

```markdown
## Takıldığım Yer

**Hangi adım:** (örn: "make install")

**Hata mesajı:**
[Buraya kopyala veya screenshot]

**Ne yaptığımda oldu:**
[Adım adım açıkla]

**Beklediğim:**
[Ne olmasını bekliyordun?]

**Olan:**
[Ne oldu?]
```

### 2️⃣ Süre Takibi

```markdown
## Kurulum Süresi

- Python check: ___ dk
- Fork + clone: ___ dk
- make install: ___ dk
- API key setup: ___ dk
- make test: ___ dk
- make run-api: ___ dk

**Toplam:** ___ dk
```

### 3️⃣ Dokümantasyon Geribildirimi

```markdown
## Dokümantasyon

**Anlaşılmayan kısımlar:**
- [Hangi dosya, hangi satır?]

**Eksik olan:**
- [Ne anlatılmalıydı ama anlatılmamış?]

**Fazla olan:**
- [Hangi kısım gereksiz detay?]

**Öneriler:**
- [Nasıl daha iyi olabilir?]
```

---

## 📤 Feedback Gönderme

### Yöntem 1: GitHub Issues (Önerilen)
```bash
# Orijinal repo'da issue aç:
# https://github.com/brdfb/multi-agent-orchestrator-v2/issues/new

Başlık: [TEST] Kurulum hatası: make install fails
İçerik: [Yukarıdaki template'i kullan]
```

### Yöntem 2: Email/Message
```
Direkt bana feedback'i gönder:
- Screenshot'lar
- Hata mesajları
- Öneriler
```

### Yöntem 3: Pull Request
```bash
# Eğer düzeltme yaptıysan:
# Kendi fork'unda commit yap
git add .
git commit -m "Fix: INSTALLATION.md typo"
git push origin master

# Sonra GitHub'da PR aç:
# Senin fork → Orijinal repo
```

---

## 🎯 Test Senaryoları

### Senaryo 1: Basit Kurulum
**Amaç:** Sadece QUICKSTART.md'yi takip et, başka bir şey okuma.

**Soru:**
- Kurulum tamamlandı mı?
- Hangi adımda takıldın?
- Dokümantasyon yeterli miydi?

### Senaryo 2: Hata Simülasyonu
**Amaç:** Bilerek hata yap, TROUBLESHOOTING.md'nin çözümlerini test et.

**Örnek:**
- API key koymadan çalıştır → Hangi hata mesajı?
- Python 2 kullan (eğer varsa) → Ne diyor?
- Port 5050'yi başka bir şey kullanıyorken aç → Conflict?

### Senaryo 3: Gerçek Kullanım
**Amaç:** Kurulumdan sonra gerçekten kullan.

**Komutlar:**
```bash
# Basit test
mao auto "Merhaba, sistem testi"

# Kod yazdırma
mao builder "Python'da hesap makinesi yap"

# Chain workflow
mao-chain "E-ticaret sistemi tasarla"
```

**Soru:**
- Sistem beklediğin gibi çalıştı mı?
- Yanıtlar kaliteli miydi?
- Memory sistemi çalıştı mı? (İkinci conversation öncekini hatırladı mı?)

---

## ⚠️ Önemli Kurallar

### ✅ YAPMAN GEREKENLER:
- ✅ Kendi fork'unda çalış
- ✅ Kendi API key'lerini kullan
- ✅ Her hatayı not et
- ✅ Feedback gönder

### ❌ YAPMAMAN GEREKENLER:
- ❌ Orijinal repo'ya direkt commit yapma (yapamassın zaten)
- ❌ API key'lerini commit etme (.gitignore zaten engelliyor)
- ❌ data/CONVERSATIONS/ klasörünü commit etme
- ❌ Hata aldığında pes etme - hata raporla!

---

## 🪟 WSL Sorun Giderme (Yaygın Hatalar)

### Sorun 1: "wsl --install" Çalışmıyor

**Hata:** `wsl: command not found` veya `The term 'wsl' is not recognized`

**Sebep:** Windows versiyonu eski (Windows 10 build 19041'den eski)

**Çözüm:**
```powershell
# Windows versiyonu kontrol et
winver
# Build number 19041 veya üstü olmalı

# Eğer eski ise:
# 1. Windows Update → En son güncellemeleri yükle
# 2. Tekrar dene: wsl --install
```

**Alternatif (Eski Windows):**
```powershell
# Manuel WSL kurulumu (Windows 10 build 19041 öncesi)
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Bilgisayarı yeniden başlat
# Sonra: wsl --set-default-version 2
```

### Sorun 2: WSL2 Yerine WSL1 Kuruldu

**Hata:** `wsl --list --verbose` çıktısında `VERSION: 1`

**Çözüm:**
```powershell
# WSL2'ye geçiş yap
wsl --set-version Ubuntu 2

# Varsayılanı WSL2 yap (gelecekteki kurulumlar için)
wsl --set-default-version 2
```

### Sorun 3: "Permission denied" (SSH Key)

**Hata:** `git clone` yaparken `Permission denied (publickey)`

**Çözüm:**
```bash
# 1. SSH key oluşturuldu mu kontrol et
ls -la ~/.ssh/id_ed25519.pub

# Eğer dosya yoksa → Adım 0.3'ü tekrar yap
ssh-keygen -t ed25519 -C "senin@email.com"

# 2. Public key'i kopyala
cat ~/.ssh/id_ed25519.pub
# Çıktıyı TAMAMEN kopyala

# 3. GitHub'a ekle (Adım 0.4)
# https://github.com/settings/keys

# 4. Test et
ssh -T git@github.com
# "Hi KULLANICI-ADIN!" görmelisin
```

### Sorun 4: Python Versiyonu Eski

**Hata:** `python3 --version` → Python 3.8 veya daha eski

**Çözüm:**
```bash
# Ubuntu 22.04+ için (Python 3.10+ içerir)
# Sistem güncellendi mi?
sudo apt update
sudo apt upgrade -y

# Python 3.11 kurulumu (Ubuntu 20.04 için)
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# python3 → python3.11 alias
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### Sorun 5: "make: command not found"

**Hata:** `make install` → `make: command not found`

**Çözüm:**
```bash
# make yükle
sudo apt install -y make

# Kontrol et
make --version
```

### Sorun 6: WSL İnternet Bağlantısı Yok

**Hata:** `sudo apt update` → `Could not resolve 'archive.ubuntu.com'`

**Çözüm 1 (En kolay):**
```powershell
# PowerShell'de WSL'i yeniden başlat
wsl --shutdown

# Ubuntu'yu tekrar aç
# Windows tuşu → "Ubuntu" → Enter
```

**Çözüm 2 (DNS değiştir):**
```bash
# WSL içinde
sudo nano /etc/resolv.conf

# Dosya içeriğini şununla değiştir:
# nameserver 8.8.8.8
# nameserver 8.8.4.4

# Kaydet: Ctrl+X → Y → Enter

# Test et
ping google.com
```

**Çözüm 3 (Windows Firewall):**
```
Windows Defender Firewall → Advanced Settings
→ Inbound Rules → New Rule
→ Program: %SystemRoot%\system32\wsl.exe
→ Allow the connection
```

### Sorun 7: Windows'tan WSL Dosyalarına Erişemiyorum

**Çözüm:**
```
# Windows Explorer'da adres çubuğuna yaz:
\\wsl$\Ubuntu\home\kullanici-adin\

# Veya File Explorer'da:
# Network → \\wsl$ → Ubuntu → home → kullanici-adin
```

**Not:** WSL kapalıysa `\\wsl$` görünmez! Ubuntu terminalini önce aç.

### Sorun 8: "venv/bin/activate" Çalışmıyor

**Hata:** `.venv/bin/activate: No such file or directory`

**Çözüm:**
```bash
# venv oluşturuldu mu kontrol et
ls -la .venv/

# Eğer .venv yoksa:
python3 -m venv .venv

# Tekrar dene
source .venv/bin/activate
```

### Sorun 9: Windows ve WSL Arasında Kopyala-Yapıştır Çalışmıyor

**Çözüm:**
```bash
# WSL içinde Windows clipboard'a kopyala
cat dosya.txt | clip.exe

# Windows clipboard'dan WSL'e yapıştır
# → Sağ tık yeterli (WSL terminal'de)
```

**Windows Terminal kullanıyorsan:**
```
Settings → Defaults → Copy on select: ✅ AÇIK
```

---

## 🆘 Acil Yardım

### Tamamen Takıldım!
```bash
# Her şeyi sil, sıfırdan başla:
cd ..
rm -rf multi-agent-orchestrator-v2
git clone https://github.com/SENIN-KULLANICI-ADIN/multi-agent-orchestrator-v2.git
cd multi-agent-orchestrator-v2
```

### Bana Ulaş
```
GitHub: @brdfb
Repo: https://github.com/brdfb/multi-agent-orchestrator-v2
Issues: [Yukarıdaki link]/issues
```

---

## 🎉 Test Tamamlandı mı?

**Checklist (Windows/WSL Kullanıcıları):**
- [ ] WSL2 kurdum (Adım 0.1)
- [ ] Git ve Python kurdum (Adım 0.2)
- [ ] SSH key oluşturdum (Adım 0.3)
- [ ] SSH key'i GitHub'a ekledim (Adım 0.4)
- [ ] Fork yaptım ve clone ettim (Adım 0.5)
- [ ] Kurulumu tamamladım (make install)
- [ ] Testler geçti (make test)
- [ ] API server başladı (make run-api)
- [ ] UI açıldı (http://localhost:5050)
- [ ] En az 1 komut test ettim (mao auto "test")
- [ ] Feedback gönderdim

**Checklist (macOS/Linux Kullanıcıları):**
- [ ] Fork yaptım
- [ ] Clone ettim (SSH key varsa)
- [ ] Kurulumu tamamladım (make install)
- [ ] Testler geçti (make test)
- [ ] API server başladı (make run-api)
- [ ] UI açıldı (http://localhost:5050)
- [ ] En az 1 komut test ettim (mao auto "test")
- [ ] Feedback gönderdim

**Hepsi tamam mı? Tebrikler! 🎊**

Artık sistemi kullanabilirsin. Feedback'in proje için çok değerli!

---

## 📊 Neden Bu Test Önemli?

### Senin Perspektifin:
- ✅ Ücretsiz LLM orchestrator sistemi kullanıyorsun
- ✅ Kod, tasarım, analiz işlerinde asistan
- ✅ Öğrenme fırsatı (multi-agent architecture)

### Bizim Perspektifimiz:
- ✅ Gerçek kullanıcı feedback'i alıyoruz
- ✅ Dokümantasyon eksiklerini görüyoruz
- ✅ Edge case'leri yakalıyoruz
- ✅ Onboarding sürecini optimize ediyoruz

**Win-win!** 🤝

---

**Son Söz:** Rahat ol, test yap, boz, hata yap - bunun için buradayız! Her feedback değerli. 🚀

**Başlangıç komutu:**
```bash
# Fork → Clone → Install → Test → Feedback
```

İyi testler! 🧪

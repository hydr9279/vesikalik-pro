# Hayal Medya Vesikalık Pro 1.4.2

HAYDAR ALTINSABAN yapımıdır · Tüm hakları saklıdır · HAYAL MEDYA 0312 264 0 888

## Bu test sürümünde olanlar
- Biyometrik 5x6 ve 5x5, Vesikalık 4,5x6 ve 8 ülkenin vize ölçüleri
- Arka plan: BiRefNet (yedek: ISNet, U²-Net), gri hale temizliği, tıkla-düzelt (Kişiye ekle / Fon say), fırçalar, uçuşan saç temizleme
- Fonlar: biyometrik/vize için beyaz; vesikalıkta Orijinal fon (varsayılan), 12 degrade ve degrade ayarları
- Rötuş: LaMa ile leke onarımı ve leke fırçası, gözlük yansıması, cilt yumuşatma, parlama, göz altı, göz-diş beyazlatma (vesikalık), ışık-renk, stil öğrenme, profiller
- Ölçekleme: sizin örneklerinizden ölçülmüş şablonlar, kılavuzlar, şablon görseli, elle ölçek-eğim-kaydırma, uygunluk raporu
- Baskı: 10x15 referans dizimleri, Kaydet ve Yazdır / Sadece Kaydet, arşiv numaralı dosya adları, online başvuru çıktısı
- Yazıcı: sürücü ayarları, test sayfası, ölçek düzeltme (Ayarlar → Yazıcılar)
- Arşiv ve günlük rapor (F3), yönetici kilidi, hızlı mod, kamera klasörü izleme, ayar taşıma, hata kaydı, kısayol rehberi (F1)

**Sonraki test sürümünde:** Polaroid ve Serbest Baskı modülleri, Model Yöneticisi (paketle güncelleme).

## Kurulum (her bilgisayarda bir kez)
1. **Python 3.12** kurun: https://www.python.org/downloads/ — kurulumda **"Add python.exe to PATH"** kutusunu işaretleyin.
2. Bu klasörü örneğin `C:\VesikalikPro` içine çıkarın.
3. **`kurulum.bat`** dosyasına çift tıklayın. Program ekran kartını kendisi tanır (NVIDIA → CUDA, diğerleri → DirectML), paketleri ve yapay zeka modellerini (~1,6 GB) indirir. 10–30 dakika sürebilir.
4. **`baslat.bat`** ile programı açın.

**Tek dosyalık kurulum paketi (.exe):** `kurulum_paketi_olustur.bat` çalıştırın. Önce ücretsiz **Inno Setup 6** kurulu olmalı (https://jrsoftware.org/isdl.php). Sonuç: `kurulum\cikti\HayalMedya_VesikalikPro_1.3_Kurulum.exe` — masaüstü kısayollu, modeller dahil, internetsiz kurulur. Not: NVIDIA'lı bilgisayarda oluşturulan paket NVIDIA'lı bilgisayarlar içindir; 3. bilgisayar için paketi o bilgisayarda oluşturun (DirectML).

## İlk açılışta yapılacaklar
1. **Ayarlar → Yazıcılar:** her yazıcı için *Sürücü ayarları* (10x15, kenarsız; Epson'da genişletme EN AZ) → *Test sayfası yazdır* → cetvelleri ölçüp yazın → *Düzelt* → tekrar test.
2. **Ayarlar → Yönetici:** başlangıç arşiv numarasını girin (şifre gerekir).
3. **Ayarlar → Genel:** isterseniz varsayılan kayıt klasörü ve kamera klasörü.

## Sorun olursa
`baslat_hata_ayiklama.bat` ile açın; ya da **Ayarlar → Hata kaydı → klasörü aç** ve o günün `hata_YYYY-AA-GG.log` dosyasını gönderin.

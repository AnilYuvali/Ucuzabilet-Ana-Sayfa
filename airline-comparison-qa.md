# Havayolu karşılaştırması — doğrulama

## Özet

`#airline-flight-deals` hemen sonrasına `#airline-price-comparison` eklendi. H3 başlık, üç aramalı seçim alanı, 12 aylık çizgi grafik, dinamik öneri, beş rotalı karşılaştırma ve ortak disclaimer tasarımı doğrulandı. Mevcut bölümün HTML, CSS ve JS mantığı değiştirilmedi.

## Ortam

- Yerel sunucu: http://127.0.0.1:8000/index.html?v=airline-comparison-final#airline-price-comparison
- Codex uygulama içi tarayıcısı, CUA Playwright API.
- Masaüstü 1280×900 ve mobil 390×844 viewport override; inceleme sonunda override kaldırıldı.
- Ayrı Browser skill/plugin mevcut değil; mevcut CUA tarayıcı yüzeyi kullanıldı. Harici tarayıcı veya yeni bağımlılık kurulmadı.

## Kontroller

| Kontrol | Sonuç / kanıt |
|---|---|
| Sayfa kimliği | Doğru localhost URL, Ucuzabilet başlığı, doğru H3 |
| Boş sayfa / hata katmanı | Yok; başlık, filtreler, grafik ve fiyatlar görüntülendi |
| Varsayılan seçim | THY, Pegasus, İstanbul |
| Grafik | 2 çizgi, 24 fiyat etiketi, 12 odaklanabilir ay |
| Dönem | Eylül 2025–Ağustos 2026; son tamamlanan 12 ay |
| Arama ve seçim | AJet klavyeyle seçildi; `izmir` araması İzmir’i buldu |
| Dinamik güncelleme | İzmir seçilince beş rota, öneri, lejant ve disclaimer güncellendi |
| Tooltip | Eylül 2025 ve Ağustos 2026 fiyatları tıklamayla açıldı |
| Aynı firma | Diğer alanda seçili firma seçenek olarak devre dışı |
| Sonuçsuz arama | `zzzz` araması anlaşılır boş sonuç metni gösterdi |
| Yabancı firma | Lufthansa seçimi beş yurt dışı rotası ve değişen fiyatlar üretti |
| Veri yok | Aydın seçiminde eski grafik/fiyatlar temizlendi; boş durum göründü |
| Mobil | Uzun isimler için alanlar alt alta; fiyatlar yan yana; son aya yatay kaydırmayla erişim |
| Konsol | Yeni component hatası görülmedi; mevcut Google GSI/FedCM localhost origin/token hataları devam ediyor |
| Sözdizimi | `node --check` JS dosyalarında geçti |
| Veri modeli | 3.392 havayolu/şehir kombinasyonunda deterministik fiyat, pozitif/eksik değer ayrımı, 12 ay ve aynı rota ortalamaları geçti |
| Diff | `git diff --check` geçti |

## Görsel kanıt

CUA screenshot çıktıları masaüstünde üç filtreyi ve tüm 12 aylık çizgi grafiği; mobilde alt alta filtreleri, kaydırılabilir grafiği ve aynı satırda THY/Pegasus fiyatlarını gösterdi. Wireframe’in yapısı korundu; mevcut sayfanın panel, tipografi, renk ve disclaimer stilleri kullanıldı. Mobil tabloda okunabilirlik için her rota iki fiyatlı kompakt satır olarak düzenlendi.

## Kullanılan akış

Sayfa açılışı → ilk havayolunda AJet araması → ArrowDown/Enter → şehirde `izmir` araması → İzmir seçimi → güncellenen rota/fiyat/metin kontrolü → grafik ayı seçimi → tooltip kontrolü → ikinci havayolunda aynı-firma engeli / boş arama / Lufthansa seçimi → mobil Aydın boş durumu → İstanbul’a dönüş → son grafik ayı ve fiyat tablosu → varsayılan seçime dönüş.

Komutlar: `node --check airline-comparison.js`, `node --check airline-comparison-data.js`, geçici veri doğrulama betiği `/tmp/check-airline-comparison.cjs`, `git diff --check`. UI kontrolleri CUA `goto`, `reload`, scoped `locator`, `fill`, `press`, `click`, `textContent`, `count`, `screenshot`, `dev.logs` üzerinden yapıldı.

## Sınırlar

64 firma açık sayfalardan doğrulanabilen katalogdur; eksiksiz canlı satış envanteri iddiası yoktur. Fiyatlar ve popülerlik sıralaması örnektir; gerçek geçmiş fiyat veya sefer müsaitliği değildir. Gerçek API/rezervasyon ve diğer tarayıcı motorları test edilmedi. Veri kaynakları ve sağlayıcı sınırı `airline-comparison-sources.md` dosyasındadır.

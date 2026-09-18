# Havayolu karşılaştırması — veri ve entegrasyon notları

17 Eylül 2026 tarihinde hazırlanmıştır. `#airline-price-comparison`, `#airline-flight-deals` sonrasında bağımsız bir bölüm olarak eklenmiştir. Mevcut component kodu değiştirilmemiştir.

## Kaynak ve kapsam

- [Ucuzabilet tüm destinasyonlar / popüler havayolları](https://www.ucuzabilet.com/tum-destinasyonlar): 33 firmalık açık dizin başlangıç listesidir. Bu dizin **tam satış envanteri değildir**. Ek firmalar aşağıdaki açık rota sayfalarından ve projenin mevcut kampanya/rota içeriklerinden alınmıştır. Dropdown 64 havayolu içerir; tüm GDS/satış havayollarının eksiksiz listesi için Ucuzabilet'in yetkili envanter servisi gerekir. Kapalı servise erişilmemiştir.
- [DHMİ havalimanları](https://www.dhmi.gov.tr/Sayfalar/HavaLimanlari.aspx) ve [2026 Mayıs havalimanı trafik listesi](https://www.dhmi.gov.tr/Lists/Istatislikler/Attachments/436/T%C3%9CM%20U%C3%87AK.pdf): il bazında gruplama; Muğla altında BJV/DLM, Antalya altında AYT/GZP; Adana/Mersin COV, Ordu/Giresun OGU ve Rize/Artvin RZV ortak havalimanı kapsamı. Askeri meydanlar ve yapımı süren havalimanları kapsam dışıdır. Liste bir sefer müsaitlik listesi değildir.
- İl seçimi kalkış ilini ifade eder. Aydın, Kocaeli, Siirt, Tekirdağ ve Uşak için örnek fiyat üretilmez; dropdown seçilebilir, boş durum gösterilir. Bu boşluklar güncel operasyonel sefer durumuna ilişkin bir iddia değildir.

Ek havayolu kanıtları:
- [İzmir–Kuala Lumpur](https://www.ucuzabilet.com/izmir-kuala-lumpur-ucak-bileti): Thai Airways, Malaysia Airlines.
- [Londra–Tiran](https://www.ucuzabilet.com/londra-tiran-ucak-bileti): Croatia Airlines, SKY Express.
- [Basel–İzmir](https://www.ucuzabilet.com/basel-izmir-ucak-bileti): Austrian, Air Dolomiti, Swiss, Eurowings.
- [Göteborg–Antalya](https://www.ucuzabilet.com/goteborg-antalya-ucak-bileti): Scandinavian Airlines, Finnair.
- [Medine](https://www.ucuzabilet.com/medine-ucak-bileti): flyadeal.
- [Urgench](https://www.ucuzabilet.com/urgench-ucak-bileti): Uzbekistan Airways.
- [Hangzhou](https://www.ucuzabilet.com/hangzhou-ucak-bileti): Air China, Shandong Airlines.
- [Barselona–Porto](https://www.ucuzabilet.com/barselona-porto-ucak-bileti): Air Europa, TAP, Vueling.
- [Tenerife](https://www.ucuzabilet.com/tenerife-ucak-bileti): Binter, Condor, TUI fly Netherlands.
- [İstanbul–Zanzibar](https://www.ucuzabilet.com/istanbul-zanzibar-ucak-bileti) ve [Zanzibar–İstanbul](https://www.ucuzabilet.com/zanzibar-istanbul-ucak-bileti): flydubai, Gulf Air, Oman Air, Egyptair, Ethiopian, Precision Air, Air Tanzania.
- Mevcut `index.html` kampanya ve yurt dışı rota içerikleri: All Nippon Airways, Wizz Air (W6), Pobeda (DP), Centrum Air (C6).

## Fiyat modeli

Tüm fiyatlar **sentetik demo verisidir**; tarihsel fiyat arşivi ya da canlı bilet teklifi değildir. Havayolu/şehir/ay bazında deterministik hesaplanır; her yenilemede rastgele değişmez. Özellikle yabancı havayolları için aktarmalı/ortak uçuş ihtimalini temsil eden örneklerdir; doğrudan sefer veya biletlenebilir kombinasyon garantisi verilmez.

2026 fiyat ölçeği için [İstanbul–Ankara](https://www.ucuzabilet.com/istanbul-ankara-ucak-bileti), [Pegasus](https://www.ucuzabilet.com/Pegasus), [THY](https://www.ucuzabilet.com/thy), [Konya–Dalaman](https://www.ucuzabilet.com/konya-dalaman-ucak-bileti), [Gaziantep–Lisbon](https://www.ucuzabilet.com/gaziantep-lisbon-ucak-bileti) sayfaları incelendi. Bunlar model için büyüklük kontrolüdür; oluşturulan sayılar bu kaynakların ölçülmüş ortalamaları değildir.

- Referans tarih 17 Eylül 2026; son 12 tamamlanan ay Eylül 2025–Ağustos 2026.
- Yurt içi baz değerler 1.740–2.250 TL; kısa Avrupa rotaları 4.250–4.890 TL. Havayolu/il katsayısı, bağlantı maliyeti, mevsimsellik ve küçük deterministik farklılıklarla ölçeklenir.
- Grafik ve lejant, tabloda yer alan **aynı beş rota** için ay başına eşit ağırlıklı ortalamaları karşılaştırır. Lejant 12 aylık ortalamadır.
- Tablo, Eylül 2026 için ayrı örnek teklifleri gösterir. Aylık ortalama ile tek bilet fiyatı farklı ölçülerdir. Her rota için iki havayolu aynı tarihi kullanır.
- İlk öneri cümlesi, seçilen her havayolunun tabloda görülen en düşük teklifini karşılaştırır.
- Açıklamanın ilk cümlesi aynı beş rota için en düşük 12 aylık ortalamaya sahip firmayı, o firmanın en ucuz tablo teklifini verir. İkinci/üçüncü cümleler yurt içi/yurt dışı örnek havuzlarını ayrı değerlendirir.
- Yabancı firmalara Türkiye iç hat fiyatı üretilmez. Ukraine Int. Airlines katalogda bulunur fakat demo fiyatı yoktur. Eksik fiyatlar sıfır olarak değerlendirilmez.

## Entegrasyon sınırı

`airline-comparison-data.js`: katalog, kimlikler, referans tarih, demo katsayıları.
`airline-comparison.js`: `getComparison(selection)` tek veri sağlayıcı sınırıdır. API bağlantısında bu fonksiyonun şehir, havayolları, rota kayıtları ve 12 aylık serileri döndüren bir adaptörle değiştirilmesi yeterlidir. Gerçek envanter, uçuş kullanılabilirliği, geçmiş fiyatlar ve popülerlik sıralaması API'den sağlanmalıdır. Tarihler de API verisinden gelmelidir.

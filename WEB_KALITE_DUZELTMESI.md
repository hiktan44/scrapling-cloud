# Web kalite kontrolü ve Türkçe arayüz

F30: Web paketindeki `next lint` komutu doğrudan ESLint CLI ile değiştirildi. Next 16 / ESLint 9 için Core Web Vitals kurallarını kullanan düz yapılandırma eklendi. `.eslintrc.json` eski sürümler için depoda kalır; güncel kontrol `eslint.config.mjs` kullanır. Kural kapatılmadı ve bağımlılık sürümleri değiştirilmedi.

Çalışan kontrolün ortaya çıkardığı 12 hata ve 3 uyarı giderildi. Tarayıcı depolaması `useSyncExternalStore` ile okunur; sunucu renderi API anahtarını okumaz veya çıktıya taşımaz. Yönetici/kontrol panelinin ilk veri istekleri dış sistem cevabıyla durum günceller; ayrılan ekranların eski cevapları yok sayılır. Firma değiştirme sırasında form değerleri seçilen firmadan alınır.

Dil tercihi kaydedilmiş değerden veya çerezden okunur; varsayılan Türkçedir. İngilizce seçimi korunur. Depolama ve çerez kapalıyken seçim mevcut oturumda kullanılabilir. Dil değişimi aynı sayfadaki abonelere ve diğer sekmelere yansır. Otomatik IP ile ülke/dil belirleme kaldırıldı; kullanıcı seçimi uygulanır. Dil menüsünün erişilebilir açıklamaları Türkçeye çevrildi.

## Yerel doğrulama

- Node 22.23.3; Next 16.2.4, React 19.2.5 ve sabit npm kilit dosyası.
- 14 regresyon: 8 gerçek React DOM sunucu renderi ve 6 izole dil saklama/bildirim sözleşmesi. Son altı testte kanca bağdaştırıcısı ve kurgusal depolama/olay hedefi kullanılır.
- Tam web tür kontrolü geçti.
- ESLint 0 hata ve 0 uyarıyla geçti.
- Web üretim derlemesi `npm run build -- --webpack` ile geçti.

Testler dış ağ çağrısını reddeder. Gerçek müşteri anahtarı, üretim veritabanı veya ücretli iş başlatma kullanılmaz. Bunlar canlı tarayıcı hidrasyonu/tıklama, giriş, tarama işçisi veya Redis kabul testi değildir. F29 Redis kimlik doğrulaması ayrı ve açık kalır.

## GitHub ve Coolify

`Web kalite ve dil kontrolleri` iş akışı regresyon, tür, lint ve üretim derlemesini ayrı çalıştırır. Taslak PR Coolify dağıtımını değiştirmez. Birleştirme ve dağıtım sonrası kayıtlı anahtarla panel, firma seçimi, Türkçe/İngilizce seçimi ve sekmeler arası bildirim tarayıcıda ayrıca doğrulanmalıdır.

Yapılandırma [Next ESLint belgesindeki](https://nextjs.org/docs/app/api-reference/config/eslint) öneriyi uygular.

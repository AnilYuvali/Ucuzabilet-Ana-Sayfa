importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');

var firebaseConfig = {
	    apiKey: "AIzaSyDNz7oTp5xv79HY6U-Nhqln7cw6fkNWdqk",
	    authDomain: "ucuzabiletwebpush.firebaseapp.com",
	    databaseURL: "https://ucuzabiletwebpush.firebaseio.com",
	    projectId: "ucuzabiletwebpush",
	    storageBucket: "ucuzabiletwebpush.appspot.com",
	    messagingSenderId: "54700575270",
	    appId: "1:54700575270:web:189a862cd5ba430b70b4e7"
	  };
firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

self.addEventListener('error', function (e) {
    console.log('event error ', e);
});


self.addEventListener('notificationclick', function (event) {
    try {
        var payload = event.notification.data;
        payload.data.url = payload.data.url.trim() == '' ? 'www.ucuzabilet.com/kampanyalar?utm_source=webpush&utm_medium=kampanyalar' : payload.data.url;

        if (typeof (payload.data.url) != 'undefined') {
            event.waitUntil(
                self.clients.matchAll({
                    type: "window"
                })
                    .then(function () {
                        if (self.clients.openWindow) {
                            console.log('open window ', payload);
                            return self.clients.openWindow(payload.data.url);
                        }
                    })
            );
        }

        event.notification.close();
    } catch (e) {
        console.log('custom exception ', e);
    }
});

self.addEventListener('push', function(event) {
    try {
        const payload = event.data ? event.data.json() : {};
        console.log('payload', payload);
        const notificationTitle = payload.data?.title?.trim() || 'Bildirim';
        const notificationOptions = {
            body: payload.data?.body || '',
            image: payload.data?.attachment || '',
            icon: payload.data?.icon || '',
            click_action: payload.data?.url || '',
            data: payload,
            requireInteraction: true
        };

        //show duration
        event.waitUntil(self.registration.showNotification(notificationTitle, notificationOptions));
    } catch (e) {
        console.log('show notification error ', e);
    }
});


importScripts('https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js');

if (workbox) {
    const { precaching, routing, strategies, expiration, core } = workbox;

    core.skipWaiting();
    core.clientsClaim();

    const staticPages = [
        '/','/blog','/otobus-bileti','/bus-ticket', '/campaign','/kampanya','/kampanyalar', '/campaigns',
        '/arac-kiralama/','/onerileriniz', '/iletisim', '/populer-havalimanlari','/populer-havayollari', '/yurt-ici-populer-sehirler',
        '/yurt-disi-populer-sehirler', '/yurt-ici-populer-destinasyonlar','/yurt-disi-populer-destinasyonlar', '/populer-ulkeler',
        '/popular-airports','/popular-airlines','/popular-cities-domestic', '/popular-cities-international', '/popular-routes-domestic',
        '/popular-routes-international','/popular-countries','/bilet-iptal-sigortasi','/kart-puanlarinla-uc',
        '/kvkk-duyurular', '/salla-uc', '/shake-and-fly', '/hakkimizda', '/pnr-sorgulama', '/yardim', '/ucuz-ucak-bileti-nasil-alinir',
        '/how-to-buy-cheap-flight-ticket', '/ucuz-otel-rezervasyonu-nasil-yapilir', '/how-to-buy-cheap-hotel',
        '/ucuz-arac-nasil-kiralanir', '/how-to-buy-cheap-car', '/ucuz-transfer-rezervasyonu-nasil-yapilir',
        '/how-to-buy-cheap-transfer', '/ucuz-otobus-rezervasyonu-nasil-yapilir', '/how-to-buy-cheap-bus',
        '/kullanim-ve-gizlilik-sozlesmesi', '/cerez-politikasi', '/kisisel-verilerin-korunmasi-ve-gizlilik-politikasi',
        '/bilgi-toplumu-hizmetleri', '/bilgi-guvenligi-politikasi', '/membership'
    ];

    routing.registerRoute(
        ({ url }) => {
            return staticPages.some(page => {
                if (page === '/') {
                    return url.pathname === '/';
                }
                return url.pathname.startsWith(page);
            });
        },
        new strategies.NetworkFirst({
            cacheName: 'static-pages-cache',
            networkTimeoutSeconds: 7,
            plugins: [
                new expiration.ExpirationPlugin({
                    maxEntries: 20,
                    maxAgeSeconds: 7 * 24 * 60 * 60 // 7 gün
                })
            ]
        })
    );

    routing.registerRoute(
        ({ request }) => request.destination === 'script',
        new strategies.StaleWhileRevalidate({
            cacheName: 'js-cache',
            plugins: [
                new expiration.ExpirationPlugin({
                    maxEntries: 60,
                    maxAgeSeconds: 14 * 24 * 60 * 60, // 14 gün
                }),
            ],
        })
    );

    routing.registerRoute(
        ({ request }) => request.destination === 'style',
        new strategies.StaleWhileRevalidate({
            cacheName: 'css-cache',
            plugins: [
                new expiration.ExpirationPlugin({
                    maxEntries: 60,
                    maxAgeSeconds: 14 * 24 * 60 * 60,
                }),
            ],
        })
    );

    routing.registerRoute(
        ({ request, url }) => request.destination === 'image' && url.origin === 'https://images.ucuzabilet.com',
        new strategies.CacheFirst({
            cacheName: 'image-cache',
            plugins: [
                new expiration.ExpirationPlugin({
                    maxEntries: 100,
                    maxAgeSeconds: 90 * 24 * 60 * 60, // 90 gün
                }),
            ],
        })
    );


    routing.registerRoute(
        ({ url }) => url.pathname.startsWith('/special-days-list'),
        new strategies.StaleWhileRevalidate({
            cacheName: 'exact-api-cache',
            plugins: [
                new expiration.ExpirationPlugin({
                    maxEntries: 20,
                    maxAgeSeconds: 14 * 24 * 60 * 60,
                }),
            ],
        })
    );
} else {
    console.log("Workbox didn't load");
}

// -------------------- Service Worker Yaşam Döngüsü --------------------
self.addEventListener('install', function (event) {
    event.waitUntil(self.skipWaiting());
});
self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});

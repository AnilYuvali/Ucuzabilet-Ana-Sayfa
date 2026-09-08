# Ucuzabilet homepage snapshot

This project contains a local snapshot of the `https://www.ucuzabilet.com/` homepage captured on 1 September 2026.

The entry point is `index.html`. Its locally saved stylesheets, scripts, images, fonts, and captured data responses are under `assets/`; `assets/asset-manifest.json` records each resource's original URL and local path.

For the closest browser behavior, serve the directory over localhost instead of opening it with the `file://` protocol:

```sh
python3 -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/index.html`.

The page's live booking, authentication, analytics, and other server-backed POST actions still depend on Ucuzabilet or third-party services and are not emulated by this static copy.

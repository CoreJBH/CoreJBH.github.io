# CoreJBH.github.io

Static site for **CoreJBH** and **POCKETCORE**, served by GitHub Pages at
<https://corejbh.github.io/>.

No build step, no framework, no external host. Every page, stylesheet, script and
image is in this repository; there is no CDN, no web font, no analytics and no
cookie.

```
index.html                     CoreJBH — Verify, don't trust
pocketcore/index.html          POCKETCORE landing page
pocketcore/privacy/index.html  Privacy policy (canonical)
pocketcore/privacy.html        alias that redirects to the policy
404.html                       GitHub Pages not-found page
assets/css/site.css            the whole design system
assets/js/site.js              copy-to-clipboard for the release hash
assets/img/                    tesseract mark, mascot, app screenshots, PWA icons
manifest.webmanifest          install metadata: #030B27 theme, 192 and 512 icons
tools/check_site.py            offline link, tag and remote-resource check
.nojekyll                      serve files as-is, no Jekyll processing
```

## Local check

```sh
python3 -m http.server -d . 8080
# then open http://127.0.0.1:8080/

python3 tools/check_site.py   # links, tag balance, no remote resources
```

## Deploy

The repository is the site: commit to `main` and GitHub Pages publishes it
(Settings → Pages → Deploy from a branch → `main` / `/`).

## Facts that must stay in sync with the release

- APK version `v1.0.0`, size 17,216,155 bytes
- SHA-256 `872b8a6c406574ce15852ce0b1d895ffa08cb4b08f65f9e8f80b153379daabce`
- daemon Bitcoin Core 32.1, `arm64-v8a`, Android 8.0+ (API 26)
- source: <https://github.com/CoreJBH/pocketcore>

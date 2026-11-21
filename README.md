# CoreJBH.github.io

Static site for **CoreJBH** and **PocketCore**, served by GitHub Pages at
<https://corejbh.github.io/>.

No build step, no framework, no external host. Every page, stylesheet, script and
image is in this repository; there is no CDN, no web font, no analytics and no
cookie.

```
index.html                     CoreJBH — Verify, don't trust
pocketcore/index.html          PocketCore landing page
pocketcore/privacy/index.html  Privacy policy (canonical)
pocketcore/privacy.html        alias that redirects to the policy
404.html                       GitHub Pages not-found page
assets/css/site.css            the whole design system
assets/js/site.js              copy-to-clipboard for the release hash
assets/img/                    brand art, tesseract mark, PWA and app icons, screenshots
assets/img/favicon.svg         the master tesseract mark every install icon is rendered from
manifest.webmanifest          install metadata: #000000 field, standalone, any + maskable icons
sw.js                         service worker: lets the site install as a real app, caches nothing
tools/check_site.py            offline link, tag and remote-resource check
tools/make-icons.py            renders every install icon and the navbar mark from favicon.svg
.nojekyll                      serve files as-is, no Jekyll processing
```

## Local check

```sh
python3 -m http.server -d . 8080
# then open http://127.0.0.1:8080/

python3 tools/check_site.py   # links, tag balance, no remote resources
python3 tools/make-icons.py   # re-render the install icons (needs resvg-py)
```

## Install as an app

`manifest.webmanifest` plus `sw.js` make the site a real PWA: Chrome and Samsung
Internet build a WebAPK, so the home-screen entry opens without browser chrome
and shows `icon-512.png` — the tesseract wireframe on a pure `#000000` field —
instead of a white-framed shortcut. The worker caches nothing; it exists so the
install qualifies, and every request still goes to the network, so a deploy is
live on the next load.

A phone that already added the site keeps its old WebAPK until the entry is
removed and added again.

## Deploy

The repository is the site: commit to `main` and GitHub Pages publishes it
(Settings → Pages → Deploy from a branch → `main` / `/`).

## Facts that must stay in sync with the release

- APK version `v1.0.0`, size 17,216,155 bytes
- SHA-256 `872b8a6c406574ce15852ce0b1d895ffa08cb4b08f65f9e8f80b153379daabce`
- daemon Bitcoin Core 32.1, `arm64-v8a`, Android 8.0+ (API 26)
- source: <https://github.com/CoreJBH/pocketcore>

# CoreJBH.github.io

Static site for **CoreJBH**, **PocketCore** and **Hashes**, served by GitHub Pages at
<https://corejbh.github.io/>.

No build step, no framework, no external host. Every page, stylesheet, script and
image is in this repository; there is no CDN, no web font, no analytics and no
cookie.

```
index.html                     CoreJBH — Verify, don't trust
pocketcore/index.html          PocketCore landing page
pocketcore/privacy/index.html  Privacy policy (canonical)
pocketcore/privacy.html        alias that redirects to the policy
hashes/index.html              Hashes landing page
hashes/privacy/index.html      Hashes privacy policy
404.html                       GitHub Pages not-found page
assets/css/site.css            the whole design system
assets/js/site.js              copy-to-clipboard for the release hash
assets/img/                    brand art, tesseract mark, PWA and app icons, screenshots
assets/img/favicon.svg         the master tesseract mark every install icon is rendered from
manifest.webmanifest          install metadata: #000000 field, standalone, any + maskable icons
sw.js                         service worker: lets the site install as a real app, caches nothing
tools/check_site.py            offline link, tag and remote-resource check
tools/make-icons.py            renders every install icon and the navbar mark from favicon.svg
tools/update_l1_snapshot.py    refreshes nodepulse/l1-snapshot.json from bitnodes.io/api/v1
nodepulse/l1-snapshot.json     the current Bitnodes L1 round, the file NodePulse reads
nodepulse/entities.json        the verified entity table NodePulse adopts when it is newer
.nojekyll                      serve files as-is, no Jekyll processing
```

## The five projects

The home page names all five in PascalCase and shows the version each one ships.
When a release goes out, change the version on its card here and in the list below.

| Project | Version shown | Release link |
| --- | --- | --- |
| PocketCore | v1.0.0-vc22 | <https://github.com/CoreJBH/pocketcore/releases/latest> |
| Hashes | v1.0.0 | <https://github.com/CoreJBH/hashes/releases/latest> |
| ZeroWallet | v1.2.3 | <https://github.com/CoreJBH/zerowallet/releases/latest> |
| CleanSwap | v0.6.13 | <https://github.com/CoreJBH/cleanswap/releases/latest> |
| NodePulse | v1.2.0 | <https://github.com/CoreJBH/nodepulse/releases/tag/v1.2.0> |

PocketCore's card downloads the APK straight from
`releases/latest/download/pocketcore-1.0.0-release-vc22.apk`; the Hashes page uses
the same shape, `releases/latest/download/hashes-v1.0.0-arm64-release.apk`.

## Local check

```sh
python3 -m http.server -d . 8080
# then open http://127.0.0.1:8080/

python3 tools/check_site.py   # links, tag balance, no remote resources
python3 tools/make-icons.py   # re-render the install icons (needs resvg-py)
```

## The L1 snapshot NodePulse reads

`nodepulse/l1-snapshot.json` is the object `CoreJBH/nodepulse`'s `fetch_l1.py` writes —
the same keys in the same order — as a plain file the app can fetch from
<https://corejbh.github.io/nodepulse/l1-snapshot.json> instead of waiting for a new APK
build. It carries the Bitnodes round's node count, height, country split, unique
coordinates with their country, client versions and the clear-net/Tor/I2P split.

`tools/update_l1_snapshot.py` rebuilds it from `bitnodes.io/api/v1`. Every value is what
Bitnodes reported for that round; if any endpoint fails or the crawl rolls over mid-run
the script stops and the previous file stays, because a half-fresh snapshot would be a
lie about its date.

```sh
python3 tools/update_l1_snapshot.py   # needs the network; writes nodepulse/l1-snapshot.json
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

- APK version `v1.0.0-vc22` (versionCode 22), size 8,472,003 bytes
- SHA-256 `6715e22752446206095bb5daf7f2bddf375eea7e891bd46c67417753ef64f373`
- daemon Bitcoin Core 32.1, `arm64-v8a`, Android 8.0+ (API 26), built against API 36 (Android 16)
- source: <https://github.com/CoreJBH/pocketcore>
- Hashes `v1.0.0` (versionCode 1), `hashes-v1.0.0-arm64-release.apk`, size and
  SHA-256 copied from the release's `SHA256SUMS.txt`; the demo GIF
  (`assets/img/hashes-demo.gif`) shows an example payout address, never a real one

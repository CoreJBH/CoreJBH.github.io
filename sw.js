/* CoreJBH service worker — the piece that makes this site installable as a real app.
 *
 * Android Chrome and Samsung Internet only mint a WebAPK (a real app entry with
 * its own icon, launch screen and no home-screen shortcut frame) when the page
 * arrives with a manifest *and* a service worker that handles fetch. Without
 * this file the install falls back to a legacy shortcut, which One UI wraps in
 * a white border no icon can cover.
 *
 * So the job here is deliberately small: take over immediately, and let every
 * request go to the network. Nothing is precached and nothing is stored, so a
 * deploy is live on the next load and a visitor never gets a stale page that
 * looks like the release hash changed when it did not.
 */
const VERSION = "2026-11-22b";

self.addEventListener("install", () => {
  // No precache list: there is no copy of the site that could go out of date.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // Remove anything an earlier worker may have left behind, then control
      // the pages that are already open instead of waiting for a reload.
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return; // let the browser handle the rest

  // Pass-through: the network's answer is the only answer. There is no cache
  // fallback and no offline shell, because a stale copy of a page that states
  // an APK size and a SHA-256 would be worse than an honest error.
  event.respondWith(fetch(event.request));
});

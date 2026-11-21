/* CoreJBH site — local, dependency-free behaviour. */
(function () {
  "use strict";

  /* copy-to-clipboard for the release hash */
  document.querySelectorAll(".copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var el = document.getElementById(btn.getAttribute("data-copy"));
      if (!el) return;
      var text = (el.textContent || "").trim();
      var done = function () {
        var old = btn.textContent;
        btn.textContent = "copied";
        window.setTimeout(function () { btn.textContent = old; }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { legacy(text, done); });
      } else {
        legacy(text, done);
      }
    });
  });

  /* Install as a real app. Android Chrome and Samsung Internet only build a
     WebAPK — a proper app icon instead of a white-framed shortcut — when the
     page has a service worker that handles fetch. sw.js caches nothing, so this
     only enables the install; every visit still comes straight from the network. */
  if ("serviceWorker" in navigator) {
    var register = function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {
        /* No https, or a browser that blocks it: the site works either way. */
      });
    };
    if (document.readyState === "complete") register();
    else window.addEventListener("load", register);
  }

  function legacy(text, done) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { /* nothing to do */ }
    document.body.removeChild(ta);
  }
})();

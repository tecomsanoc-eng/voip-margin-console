/* Data loader for the console page.
 *
 * This file used to own a second login form, a second Supabase client, a
 * sign-out button, an injected sidebar and a floating import link — a complete
 * duplicate of the shell that portal.html already provides. All of that is
 * gone. The Operations Portal owns authentication and navigation; this file
 * does one thing: fetch the payload and hand it to bootConsole().
 *
 * Three ways in, in priority order:
 *   1. Embedded in portal.html  -> borrow the portal's access token
 *   2. localhost with ?local    -> read ./payload.json (offline dev)
 *   3. Opened directly          -> redirect to the portal to sign in
 */
(function () {
  'use strict';

  var cfg = window.SUPABASE_CONFIG || {};
  var appWrap = document.getElementById('appWrap');
  var msgEl = document.getElementById('loadMsg');

  function say(text, kind) {
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'load-msg' + (kind ? ' ' + kind : '');
    msgEl.style.display = text ? '' : 'none';
  }

  function reveal(data) {
    window.bootConsole(data);
    say('');
    appWrap.style.display = '';
    if (typeof window.vmAnnounceReady === 'function') window.vmAnnounceReady();
  }

  function isPortalFrame() {
    try {
      return !!(
        window.parent &&
        window.parent !== window &&
        window.parent.document &&
        window.parent.document.getElementById('portalApp')
      );
    } catch (e) {
      return false;
    }
  }

  var embedded = isPortalFrame();

  /* ---- 2. Offline dev ---------------------------------------------------- */

  var isLocalHost = ['localhost', '127.0.0.1', '[::1]', ''].indexOf(window.location.hostname) !== -1;

  if (isLocalHost && /(^|[?&])local(=|&|$)/.test(window.location.search)) {
    say('Local dev mode \u2014 loading payload.json\u2026');
    fetch('./payload.json').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(reveal).catch(function (err) {
      say('Local payload failed: ' + err.message, 'err');
    });
    return;
  }

  /* ---- 3. Opened directly ------------------------------------------------ */

  if (!embedded) {
    window.location.replace('./portal.html');
    return;
  }

  /* ---- 1. Embedded in the portal ----------------------------------------- */

  if (!cfg.url || !cfg.anonKey || cfg.url.indexOf('YOUR-PROJECT') !== -1) {
    say('config.js has not been filled in \u2014 set your Supabase URL and anon key.', 'err');
    return;
  }

  function portalSession() {
    try { return window.parent.__PORTAL_SESSION || null; } catch (e) { return null; }
  }

  /* One client, no session of its own. Every request carries the portal's
   * token, so there is exactly one session in the whole application. */
  var sb = window.supabase.createClient(cfg.url, cfg.anonKey, {
    auth: { autoRefreshToken: false, persistSession: false, detectSessionInUrl: false },
    global: {
      fetch: function (input, init) {
        init = init || {};
        var headers = new Headers(init.headers || {});
        var s = portalSession();
        if (s && s.access_token) headers.set('Authorization', 'Bearer ' + s.access_token);
        return window.fetch(input, Object.assign({}, init, { headers: headers }));
      }
    }
  });

  var booted = false;

  function load() {
    say('Loading margin data\u2026');
    sb.rpc('get_console_payload').then(function (res) {
      if (res.error) throw res.error;
      if (!res.data) throw new Error('The payload came back empty.');
      if (booted) return;
      booted = true;
      reveal(res.data);
    }).catch(function (err) {
      var m = (err && (err.message || err.error_description)) || String(err);
      if (/authentication required|jwt|unauthorized/i.test(m)) {
        say('Portal session unavailable. Refresh the portal once.', 'err');
      } else {
        say('Could not load data: ' + m, 'err');
      }
    });
  }

  /* The portal sets __PORTAL_SESSION before it points the frame here, but the
   * frame can win the race on a cold load. Wait, briefly, then give up loudly
   * rather than spinning forever. */
  var waited = 0;
  (function waitForSession() {
    if (portalSession()) { load(); return; }
    waited += 100;
    if (waited < 10000) setTimeout(waitForSession, 100);
    else say('Portal session not detected. Please refresh the portal.', 'err');
  })();
})();

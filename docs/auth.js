/* Login gate + data loader.
 *
 * The Operations Portal is the single authentication authority. When this
 * console is embedded by docs/portal.html, do NOT create a second persisted
 * Supabase auth session in the iframe. Instead, use the portal's current
 * access token as the Authorization header for each request.
 */
(function () {
  'use strict';

  var cfg = window.SUPABASE_CONFIG || {};
  var gate = document.getElementById('authGate');
  var form = document.getElementById('authForm');
  var emailEl = document.getElementById('authEmail');
  var passEl = document.getElementById('authPassword');
  var submitEl = document.getElementById('authSubmit');
  var msgEl = document.getElementById('authMsg');
  var appWrap = document.getElementById('appWrap');
  var signOutBtn = document.getElementById('signOutBtn');

  function say(text, kind) {
    msgEl.textContent = text || '';
    msgEl.className = 'auth-msg' + (kind ? ' ' + kind : '');
  }

  function addImportLink() {
    if (!appWrap || document.getElementById('excelImportLink')) return;
    var bar = document.createElement('div');
    bar.id = 'excelImportLink';
    bar.style.cssText = 'display:flex;justify-content:flex-end;margin:0 0 12px;';
    var a = document.createElement('a');
    a.href = './import.html';
    a.textContent = '📥 Upload Excel / CSV';
    a.target = '_self';
    a.rel = 'noopener';
    a.style.cssText = 'display:inline-block;padding:9px 14px;border-radius:9px;background:#4fd1c5;color:#08131a;text-decoration:none;font-weight:800;border:1px solid #4fd1c5;';
    bar.appendChild(a);
    appWrap.insertBefore(bar, appWrap.firstChild);
  }

  var isLocalHost = ['localhost', '127.0.0.1', '[::1]', ''].indexOf(window.location.hostname) !== -1;

  if (isLocalHost && /(^|[?&])local(=|&|$)/.test(window.location.search)) {
    say('Local dev mode — loading payload.json…', 'ok');
    fetch('./payload.json').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (data) {
      window.bootConsole(data);
      gate.style.display = 'none';
      appWrap.style.display = '';
      addImportLink();
      say('');
    }).catch(function (err) {
      say('Local payload failed: ' + err.message + ' — is scripts/serve_local.py running?', 'err');
    });
    return;
  }

  if (!cfg.url || !cfg.anonKey || cfg.url.indexOf('YOUR-PROJECT') !== -1) {
    say('config.js has not been filled in yet — set your Supabase URL and anon key.', 'err');
    submitEl.disabled = true;
    return;
  }

  /*
   * Detect the portal by its DOM, not by its session. This is important:
   * the iframe can execute before the parent has finished setting
   * __PORTAL_SESSION. We therefore choose embedded mode immediately and wait
   * for the parent's session below.
   */
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

  function getPortalSession() {
    if (!embedded) return null;
    try {
      return window.parent.__PORTAL_SESSION || null;
    } catch (e) {
      return null;
    }
  }

  var sb;

  if (embedded) {
    /*
     * No persistent auth session is created inside the iframe. Every Supabase
     * Data API request receives the latest access token from the portal.
     * This prevents refresh-token races between two GoTrue clients.
     */
    sb = window.supabase.createClient(cfg.url, cfg.anonKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
        detectSessionInUrl: false
      },
      global: {
        fetch: function (input, init) {
          init = init || {};
          var headers = new Headers(init.headers || {});
          var session = getPortalSession();
          if (session && session.access_token) {
            headers.set('Authorization', 'Bearer ' + session.access_token);
          }
          return window.fetch(input, Object.assign({}, init, { headers: headers }));
        }
      }
    });
  } else {
    /* Direct visit: retain the normal login/session behaviour. */
    sb = window.supabase.createClient(cfg.url, cfg.anonKey);
  }

  var booted = false;

  function showConsole() {
    gate.style.display = 'none';
    appWrap.style.display = '';
    signOutBtn.style.display = '';
    addImportLink();
    say('');
  }

  function loadAndRender() {
    say('Loading margin data…', 'ok');
    submitEl.disabled = true;

    return sb.rpc('get_console_payload').then(function (res) {
      if (res.error) throw res.error;
      if (!res.data) throw new Error('The payload came back empty.');

      if (!booted) {
        window.bootConsole(res.data);
        booted = true;
      }
      showConsole();
    }).catch(function (err) {
      submitEl.disabled = false;
      var m = (err && (err.message || err.error_description)) || String(err);
      if (/authentication required/i.test(m) || /jwt/i.test(m) || /unauthorized/i.test(m)) {
        say('Your portal session is not available to the dashboard. Refresh the portal once.', 'err');
      } else {
        say('Could not load data: ' + m, 'err');
      }
    });
  }

  function enterEmbeddedMode() {
    var session = getPortalSession();
    if (!session || !session.access_token) return false;
    /* Never display the child login form when the parent is authenticated. */
    emailEl.value = '';
    passEl.value = '';
    loadAndRender();
    return true;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    /* Embedded pages must never authenticate independently. */
    if (embedded) {
      say('Use the portal sign-in.', 'err');
      return;
    }

    submitEl.disabled = true;
    say('Signing in…', 'ok');

    sb.auth.signInWithPassword({
      email: emailEl.value.trim(),
      password: passEl.value
    }).then(function (res) {
      if (res.error) {
        submitEl.disabled = false;
        say(res.error.message, 'err');
        return;
      }
      passEl.value = '';
      loadAndRender();
    });
  });

  signOutBtn.addEventListener('click', function () {
    if (embedded) {
      try {
        if (window.parent && typeof window.parent.signOut === 'function') {
          window.parent.signOut();
          return;
        }
      } catch (e) {}
    }
    sb.auth.signOut().then(function () { window.location.reload(); });
  });

  if (embedded) {
    var attempts = 0;
    (function waitForPortalSession() {
      if (enterEmbeddedMode()) return;
      attempts += 1;
      if (attempts < 100) {
        setTimeout(waitForPortalSession, 100);
      } else {
        submitEl.disabled = false;
        say('Portal session not detected. Please refresh the portal.', 'err');
      }
    })();
    return;
  }

  sb.auth.getSession().then(function (res) {
    if (res.data && res.data.session) {
      loadAndRender();
    } else {
      submitEl.disabled = false;
      say('');
    }
  });
})();

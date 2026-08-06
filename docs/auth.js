/* Login gate + data loader.
 *
 * The page ships with no data in it. Nothing is rendered until Supabase hands
 * back a session, and the payload RPC is itself restricted to authenticated
 * users, so an unauthenticated visitor to the public URL sees a login box and
 * can obtain nothing else.
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

  /* Dev mode: serve_local.py exposes the dataset at /payload.json so the UI can
   * be exercised before a Supabase project exists. Deliberately gated on the
   * hostname rather than a flag — on the published GitHub Pages origin this
   * branch is unreachable no matter what query string a visitor supplies. */
  var isLocalHost = ['localhost', '127.0.0.1', '[::1]', ''].indexOf(
    window.location.hostname) !== -1;

  if (isLocalHost && /(^|[?&])local(=|&|$)/.test(window.location.search)) {
    say('Local dev mode — loading payload.json…', 'ok');
    fetch('./payload.json')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        window.bootConsole(data);
        gate.style.display = 'none';
        appWrap.style.display = '';
        say('');
      })
      .catch(function (err) {
        say('Local payload failed: ' + err.message +
            ' — is scripts/serve_local.py running?', 'err');
      });
    return;
  }

  if (!cfg.url || !cfg.anonKey || cfg.url.indexOf('YOUR-PROJECT') !== -1) {
    say('config.js has not been filled in yet — set your Supabase URL and ' +
        'anon key.', 'err');
    submitEl.disabled = true;
    return;
  }

  var sb = window.supabase.createClient(cfg.url, cfg.anonKey);
  var booted = false;

  function loadAndRender() {
    say('Loading margin data…', 'ok');
    submitEl.disabled = true;

    return sb.rpc('get_console_payload').then(function (res) {
      if (res.error) throw res.error;
      if (!res.data) throw new Error('The payload came back empty.');

      if (!booted) {
        // bootConsole wires up its own DOM listeners, so it must run exactly
        // once per page load even if the auth state changes again later.
        window.bootConsole(res.data);
        booted = true;
      }
      gate.style.display = 'none';
      appWrap.style.display = '';
      signOutBtn.style.display = '';
      say('');
    }).catch(function (err) {
      submitEl.disabled = false;
      var m = (err && (err.message || err.error_description)) || String(err);
      if (/authentication required/i.test(m)) {
        say('Signed in, but this account has no data access yet. Ask an ' +
            'admin to confirm your user is active.', 'err');
      } else {
        say('Could not load data: ' + m, 'err');
      }
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
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
    sb.auth.signOut().then(function () {
      // bootConsole cannot be cleanly unwound, so drop the in-memory dataset
      // by reloading rather than leaving it sitting behind a hidden div.
      window.location.reload();
    });
  });

  // Resume an existing session so a refresh does not force a re-login.
  sb.auth.getSession().then(function (res) {
    if (res.data && res.data.session) {
      loadAndRender();
    } else {
      submitEl.disabled = false;
      say('');
    }
  });
})();

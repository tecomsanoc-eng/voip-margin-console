/* Login gate + data loader. */
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

  var sb = window.supabase.createClient(cfg.url, cfg.anonKey);
  var booted = false;

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
      gate.style.display = 'none';
      appWrap.style.display = '';
      signOutBtn.style.display = '';
      addImportLink();
      say('');
    }).catch(function (err) {
      submitEl.disabled = false;
      var m = (err && (err.message || err.error_description)) || String(err);
      if (/authentication required/i.test(m)) {
        say('Signed in, but this account has no data access yet. Ask an admin to confirm your user is active.', 'err');
      } else {
        say('Could not load data: ' + m, 'err');
      }
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    submitEl.disabled = true;
    say('Signing in…', 'ok');
    sb.auth.signInWithPassword({email: emailEl.value.trim(), password: passEl.value}).then(function (res) {
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
    sb.auth.signOut().then(function () { window.location.reload(); });
  });

  sb.auth.getSession().then(function (res) {
    if (res.data && res.data.session) {
      loadAndRender();
    } else {
      submitEl.disabled = false;
      say('');
    }
  });
})();

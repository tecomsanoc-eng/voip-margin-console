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

  /* MAIN INDEX DASHBOARD UPLIFT
   * The navigation below is the dashboard's own navigation. It keeps the
   * existing tab IDs and click handlers, so all search/render/data logic stays
   * unchanged. portal.html hides this rail when embedded because the portal
   * already provides the same navigation on its left side.
   */
  function applyDashboardSidebar() {
    if (document.getElementById('vm-index-sidebar-style')) return;
    var style = document.createElement('style');
    style.id = 'vm-index-sidebar-style';
    style.textContent = `
      body { background:#f3f6fa !important; }
      .wrap {
        max-width:none !important;
        width:100% !important;
        min-height:100vh !important;
        margin:0 !important;
        padding:28px 34px 60px 278px !important;
        color:#172033 !important;
        background:#f3f6fa !important;
      }
      .wrap::before {
        content:'VoIP Margin Console\\A Operations Portal';
        white-space:pre;
        position:fixed;
        z-index:30;
        left:0; top:0; bottom:0;
        width:238px;
        padding:24px 18px;
        background:#0b1930;
        border-right:1px solid #1e3354;
        color:#fff;
        font-size:16px;
        font-weight:800;
        line-height:1.55;
        box-shadow:6px 0 20px rgba(15,23,42,.10);
      }
      .wrap::after {
        content:'WORKSPACE\\A\\A  Dashboard\\A  Data Import\\A\\A EXPLORE\\A\\A  Destinations\\A  Providers\\A  Customers\\A  Account Managers\\A  All Carriers\\A\\A TOOLS\\A\\A  Upload Excel / CSV';
        white-space:pre;
        position:fixed;
        z-index:31;
        left:0; top:102px;
        width:238px;
        padding:0 18px;
        color:#c9d6e8;
        font-size:12px;
        line-height:2.05;
        pointer-events:none;
      }
      .tabs {
        position:fixed !important;
        z-index:35 !important;
        left:0 !important;
        top:108px !important;
        bottom:auto !important;
        width:238px !important;
        height:auto !important;
        margin:0 !important;
        padding:0 10px !important;
        display:flex !important;
        flex-direction:column !important;
        gap:5px !important;
        background:transparent !important;
        border:0 !important;
        box-shadow:none !important;
      }
      .tab {
        width:218px !important;
        min-height:41px !important;
        padding:10px 12px !important;
        display:flex !important;
        align-items:center !important;
        border:1px solid transparent !important;
        border-radius:9px !important;
        background:transparent !important;
        color:#c9d6e8 !important;
        font-size:12.5px !important;
        font-weight:650 !important;
        text-align:left !important;
      }
      .tab::before { margin-right:10px; opacity:.9; }
      #tabDest::before { content:'◎'; }
      #tabProv::before { content:'▥'; }
      #tabCust::before { content:'♙'; }
      #tabAm::before { content:'◉'; }
      #tabAll::before { content:'▤'; }
      .tab:hover { background:#173566 !important; color:#fff !important; border-color:#294a7b !important; }
      .tab.active { background:#2563eb !important; color:#fff !important; border-color:#2563eb !important; box-shadow:0 3px 10px rgba(37,99,235,.24); }

      .wrap > h1 { color:#172033 !important; font-size:27px !important; margin-top:0 !important; }
      .wrap > .sub { color:#718096 !important; font-size:13px !important; margin-bottom:22px !important; }
      .searchbox input { background:#fff !important; color:#172033 !important; border-color:#dce4ef !important; box-shadow:0 2px 8px rgba(15,23,42,.03); }
      .searchbox input::placeholder { color:#8a98ad !important; }
      .legend { color:#718096 !important; }
      .table-wrap { background:#fff !important; border-color:#e1e7f0 !important; box-shadow:0 8px 24px rgba(15,23,42,.05); }
      th { background:#f7f9fc !important; color:#718096 !important; border-bottom-color:#e1e7f0 !important; }
      td { border-bottom-color:#edf1f6 !important; color:#263247 !important; }
      tr:hover td { background:#f8fafc !important; }
      .summary-bar .stat { background:#fff !important; border-color:#e1e7f0 !important; box-shadow:0 4px 12px rgba(15,23,42,.04); }
      .stat .l { color:#718096 !important; }
      .control-bar .fchip, .control-bar .am-select { background:#fff !important; border-color:#dce4ef !important; color:#52627a !important; }
      .control-bar .fchip.active { background:#2563eb !important; border-color:#2563eb !important; color:#fff !important; }
      .auth-gate { background:#f3f6fa !important; }
      .auth-card { background:#fff !important; border-color:#dce4ef !important; box-shadow:0 18px 50px rgba(15,23,42,.10); }
      .auth-card h2 { color:#172033 !important; }
      .auth-sub, .auth-msg.ok { color:#718096 !important; }
      .auth-card input { background:#f8fafc !important; color:#172033 !important; border-color:#dce4ef !important; }
      .auth-card button { background:#2563eb !important; color:#fff !important; }
      .signout { background:#fff !important; color:#52627a !important; border-color:#dce4ef !important; }
      @media(max-width:850px){
        .wrap { padding:20px 20px 80px !important; }
        .wrap::before,.wrap::after { display:none; }
        .tabs { position:sticky !important; top:0 !important; width:100% !important; padding:8px !important; flex-direction:row !important; overflow-x:auto !important; background:#0b1930 !important; border:1px solid #1e3354 !important; border-radius:12px !important; margin-bottom:16px !important; }
        .tab { width:auto !important; min-width:max-content !important; }
      }
    `;
    document.head.appendChild(style);
  }
  applyDashboardSidebar();

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

  function isPortalFrame() {
    try {
      return !!(window.parent && window.parent !== window && window.parent.document && window.parent.document.getElementById('portalApp'));
    } catch (e) { return false; }
  }

  var embedded = isPortalFrame();

  function getPortalSession() {
    if (!embedded) return null;
    try { return window.parent.__PORTAL_SESSION || null; } catch (e) { return null; }
  }

  var sb;

  if (embedded) {
    sb = window.supabase.createClient(cfg.url, cfg.anonKey, {
      auth: { autoRefreshToken:false, persistSession:false, detectSessionInUrl:false },
      global: { fetch:function(input, init){
        init = init || {};
        var headers = new Headers(init.headers || {});
        var session = getPortalSession();
        if (session && session.access_token) headers.set('Authorization','Bearer '+session.access_token);
        return window.fetch(input, Object.assign({}, init, {headers:headers}));
      }}
    });
  } else {
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
      if (!booted) { window.bootConsole(res.data); booted = true; }
      showConsole();
    }).catch(function (err) {
      submitEl.disabled = false;
      var m = (err && (err.message || err.error_description)) || String(err);
      if (/authentication required/i.test(m) || /jwt/i.test(m) || /unauthorized/i.test(m)) say('Your portal session is not available to the dashboard. Refresh the portal once.', 'err');
      else say('Could not load data: ' + m, 'err');
    });
  }

  function enterEmbeddedMode() {
    var session = getPortalSession();
    if (!session || !session.access_token) return false;
    emailEl.value = '';
    passEl.value = '';
    loadAndRender();
    return true;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (embedded) { say('Use the portal sign-in.', 'err'); return; }
    submitEl.disabled = true;
    say('Signing in…', 'ok');
    sb.auth.signInWithPassword({ email:emailEl.value.trim(), password:passEl.value }).then(function (res) {
      if (res.error) { submitEl.disabled=false; say(res.error.message,'err'); return; }
      passEl.value='';
      loadAndRender();
    });
  });

  signOutBtn.addEventListener('click', function () {
    if (embedded) {
      try { if (window.parent && typeof window.parent.signOut === 'function') { window.parent.signOut(); return; } } catch (e) {}
    }
    sb.auth.signOut().then(function () { window.location.reload(); });
  });

  if (embedded) {
    var attempts = 0;
    (function waitForPortalSession(){
      if (enterEmbeddedMode()) return;
      attempts += 1;
      if (attempts < 100) setTimeout(waitForPortalSession,100);
      else { submitEl.disabled=false; say('Portal session not detected. Please refresh the portal.','err'); }
    })();
    return;
  }

  sb.auth.getSession().then(function (res) {
    if (res.data && res.data.session) loadAndRender();
    else { submitEl.disabled=false; say(''); }
  });
})();

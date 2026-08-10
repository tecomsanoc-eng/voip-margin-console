/* Supabase connection settings.
 *
 * Both values below are safe to commit and to serve publicly. The anon key is
 * designed to be shipped in a browser — it grants no access on its own,
 * because every table in schema.sql is behind row level security that requires
 * an authenticated session.
 *
 * The service_role key is the opposite: it bypasses RLS entirely. Never put it
 * in this file. It belongs only in supabase/.env, which is gitignored.
 *
 * Find these under Supabase Dashboard > Project Settings > API.
 */

/* Public entry-point routing: the project root opens the Operations Portal.
 * The portal embeds index.html with ?embedded=1 so the dashboard can run
 * inside the portal without redirecting back to the portal.
 */
(function () {
  try {
    var path = window.location.pathname.replace(/\/+$/, '');
    var isProjectRoot = path === '/voip-margin-console' || path === '/voip-margin-console/index.html';
    var embedded = new URLSearchParams(window.location.search).get('embedded') === '1';
    if (isProjectRoot && !embedded) window.location.replace('./portal.html');
  } catch (e) {}
})();

window.SUPABASE_CONFIG = {
  url: 'https://skqawjqabuhrgzpypkrx.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrcWF3anFhYnVocmd6cHlwa3J4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMjk0NTgsImV4cCI6MjEwMTYwNTQ1OH0.VWfOY2tbA8esF-Qqc_gAO2xm1LYjo0Rd2yqX-OaZKZ4'
};

/* -------------------------------------------------------------------------
 * Dashboard visual uplift
 * -------------------------------------------------------------------------
 * The dashboard page is intentionally still powered by the existing index
 * logic. This only changes the presentation: on a standalone dashboard the
 * five dashboard modes become a proper left navigation rail instead of a
 * horizontal row across the top. When index.html is embedded by portal.html,
 * the portal's own navigation remains the single left rail.
 */
(function () {
  try {
    var embedded = new URLSearchParams(window.location.search).get('embedded') === '1';
    if (embedded) return;

    var css = document.createElement('style');
    css.id = 'vm-dashboard-uplift';
    css.textContent = `
      /* Standalone dashboard shell */
      body:has(#appWrap) { background:#f3f6fa; color:#172033; }
      #appWrap { display:none; }
      #appWrap.uplift-ready { display:block; }
      .wrap {
        max-width:none !important;
        width:100%;
        min-height:100vh;
        margin:0 !important;
        padding:28px 34px 60px 292px !important;
        background:#f3f6fa;
        color:#172033;
      }
      .wrap > h1 { color:#172033; font-size:27px; margin-top:2px; }
      .wrap > .sub { color:#718096; font-size:13px; margin-bottom:24px; }

      /* Left dashboard navigation */
      .tabs {
        position:fixed;
        z-index:40;
        left:0;
        top:0;
        bottom:0;
        width:250px;
        margin:0 !important;
        padding:22px 14px 24px;
        display:flex !important;
        flex-direction:column;
        justify-content:flex-start;
        gap:5px;
        background:#0b1930;
        border-right:1px solid #1e3354;
        box-shadow:8px 0 24px rgba(15,23,42,.08);
      }
      .tabs::before {
        content:'VOIP MARGIN CONSOLE';
        display:block;
        color:#fff;
        font-size:15px;
        font-weight:800;
        letter-spacing:-.01em;
        padding:4px 12px 24px;
      }
      .tabs::after {
        content:'DASHBOARD';
        order:-1;
        color:#6f86a7;
        font-size:10px;
        font-weight:800;
        letter-spacing:.09em;
        padding:0 12px 7px;
      }
      .tab {
        width:100%;
        padding:11px 13px !important;
        min-height:42px;
        display:flex;
        align-items:center;
        border:0 !important;
        border-radius:9px !important;
        background:transparent !important;
        color:#c9d6e8 !important;
        font-size:13px !important;
        font-weight:600 !important;
        text-align:left;
      }
      .tab::before { margin-right:10px; opacity:.9; font-size:13px; }
      #tabDest::before { content:'◎'; }
      #tabProv::before { content:'▥'; }
      #tabCust::before { content:'♙'; }
      #tabAm::before { content:'◉'; }
      #tabAll::before { content:'▤'; }
      .tab:hover { background:#173566 !important; color:#fff !important; }
      .tab.active {
        background:#2563eb !important;
        color:#fff !important;
        border-color:transparent !important;
        box-shadow:0 4px 12px rgba(37,99,235,.24);
      }

      /* Cleaner dashboard content */
      .searchbox input {
        background:#fff !important;
        color:#172033 !important;
        border-color:#dce4ef !important;
        box-shadow:0 2px 8px rgba(15,23,42,.03);
      }
      .searchbox input::placeholder { color:#8a98ad; }
      .legend { color:#718096 !important; }
      .table-wrap {
        background:#fff !important;
        border-color:#e1e7f0 !important;
        box-shadow:0 8px 24px rgba(15,23,42,.05);
      }
      th { background:#f7f9fc !important; color:#718096 !important; border-bottom-color:#e1e7f0 !important; }
      td { border-bottom-color:#edf1f6 !important; color:#263247; }
      tr:hover td { background:#f8fafc !important; }
      .summary-bar .stat { background:#fff !important; border-color:#e1e7f0 !important; box-shadow:0 4px 12px rgba(15,23,42,.04); }
      .stat .l { color:#718096 !important; }
      .control-bar .fchip, .control-bar .am-select { background:#fff !important; border-color:#dce4ef !important; color:#52627a !important; }
      .control-bar .fchip.active { background:#2563eb !important; border-color:#2563eb !important; color:#fff !important; }

      /* Keep authentication visually consistent with the new shell */
      .auth-gate { background:#f3f6fa !important; }
      .auth-card { background:#fff !important; border-color:#dce4ef !important; box-shadow:0 18px 50px rgba(15,23,42,.10); }
      .auth-card h2 { color:#172033; }
      .auth-sub, .auth-msg.ok { color:#718096; }
      .auth-card input { background:#f8fafc !important; color:#172033 !important; border-color:#dce4ef !important; }
      .auth-card button { background:#2563eb !important; color:#fff !important; }
      .signout { background:#fff !important; color:#52627a !important; border-color:#dce4ef !important; }

      @media (max-width: 850px) {
        .wrap { padding:24px 20px 80px 20px !important; }
        .tabs {
          position:sticky;
          top:0;
          left:auto;
          bottom:auto;
          width:100%;
          height:auto;
          padding:8px;
          flex-direction:row;
          overflow-x:auto;
          border:1px solid #1e3354;
          border-radius:12px;
          margin-bottom:18px !important;
        }
        .tabs::before,.tabs::after { display:none; }
        .tab { min-width:max-content; width:auto; }
      }
    `;
    document.head.appendChild(css);

    function markReady() {
      var app = document.getElementById('appWrap');
      if (app) app.classList.add('uplift-ready');
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', markReady, { once:true });
    } else {
      markReady();
    }
  } catch (e) {
    /* Never allow the visual enhancement to interfere with the console. */
  }
})();

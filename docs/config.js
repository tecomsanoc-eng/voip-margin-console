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

/*
 * Public entry-point routing.
 *
 * GitHub Pages serves docs/index.html at the project root. The Operations
 * Portal is the real application shell and owns the single Supabase session.
 * Therefore a normal visit to the project root/index is routed to portal.html.
 *
 * The portal embeds index.html with ?embedded=1 so the dashboard itself can
 * still run inside the portal without redirecting back to the portal.
 */
(function () {
  try {
    var path = window.location.pathname.replace(/\/+$/, '');
    var isProjectRoot = path === '/voip-margin-console' || path === '/voip-margin-console/index.html';
    var embedded = new URLSearchParams(window.location.search).get('embedded') === '1';

    if (isProjectRoot && !embedded) {
      window.location.replace('./portal.html');
    }
  } catch (e) {
    /* Routing failure must never prevent Supabase_CONFIG from loading. */
  }
})();

window.SUPABASE_CONFIG = {
  url: 'https://skqawjqabuhrgzpypkrx.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXAiLCJzdXAiLCJz'
};

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

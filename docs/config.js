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
window.SUPABASE_CONFIG = {
  url: 'https://skqawjqabuhrgzpypkrx.supabase.co',
  anonKey: 'sb_publishable_uWbs8DhlSGsUh-V8LwSRFQ_6j_9N3gD'
};

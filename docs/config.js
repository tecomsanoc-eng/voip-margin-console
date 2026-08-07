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
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrcWF3anFhYnVocmd6cHlwa3J4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMjk0NTgsImV4cCI6MjEwMTYwNTQ1OH0.VWfOY2tbA8esF-Qqc_gAO2xm1LYjo0Rd2yqX-OaZKZ4'
};

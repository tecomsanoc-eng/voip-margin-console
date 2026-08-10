import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.45.4'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

type Row = {
  id: number
  customer: string
  destination: string
  provider: string
  sell: number | null
  buy: number | null
  profit: number | null
  profit_pct: number | null
  asr: number | null
  acd: number | null
  calls: number
  dur: number | null
  rev: number | null
  exp: number | null
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })
  if (req.method !== 'POST') return json({ error: 'POST required' }, 405)

  const authHeader = req.headers.get('Authorization')
  if (!authHeader) return json({ error: 'Missing Authorization header' }, 401)

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  const anonKey = Deno.env.get('SUPABASE_ANON_KEY')!
  if (!supabaseUrl || !serviceRoleKey || !anonKey) return json({ error: 'Server Supabase secrets are not configured' }, 500)

  const admin = createClient(supabaseUrl, serviceRoleKey)
  const userClient = createClient(supabaseUrl, anonKey, {
    global: { headers: { Authorization: authHeader } },
  })
  const { data: { user }, error: userError } = await userClient.auth.getUser()
  if (userError || !user) return json({ error: 'Invalid session' }, 401)

  const body = await req.json()
  const rows = body.rows as Row[]
  const sourceFile = String(body.source_file || 'web-upload')
  const dryRun = body.dry_run === true

  if (!Array.isArray(rows) || rows.length === 0) return json({ error: 'rows must be a non-empty array' }, 400)
  if (rows.length > 50000) return json({ error: 'Maximum 50,000 rows per request' }, 400)

  const errors: string[] = []
  const seen = new Set<number>()
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i]
    if (!Number.isInteger(r.id) || r.id < 0) errors.push(`Row ${i + 1}: invalid id`)
    if (!r.customer?.trim()) errors.push(`Row ${i + 1}: customer is empty`)
    if (!r.destination?.trim()) errors.push(`Row ${i + 1}: destination is empty`)
    if (!r.provider?.trim()) errors.push(`Row ${i + 1}: provider is empty`)
    if (seen.has(r.id)) errors.push(`Row ${i + 1}: duplicate id ${r.id}`)
    seen.add(r.id)
  }
  if (errors.length) return json({ error: 'Validation failed', errors: errors.slice(0, 100) }, 400)
  if (dryRun) return json({ ok: true, dry_run: true, rows: rows.length }, 200)

  const batchId = crypto.randomUUID()

  // Use upsert rather than delete+insert. This is intentionally safe for the
  // first production test: existing IDs are updated and new IDs are inserted.
  // No production rows are deleted by this function.
  const cleanRows = rows.map(r => ({ ...r }))

  for (let i = 0; i < cleanRows.length; i += 500) {
    const { error } = await admin
      .from('customer_routes')
      .upsert(cleanRows.slice(i, i + 500), { onConflict: 'id' })
    if (error) {
      return json({
        error: 'Database upsert failed',
        details: error.message,
        batch_id: batchId,
        rows_attempted: Math.min(i + 500, cleanRows.length),
      }, 500)
    }
  }

  return json({ ok: true, batch_id: batchId, rows: rows.length, mode: 'upsert', source_file: sourceFile, user_id: user.id }, 200)
})

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
}

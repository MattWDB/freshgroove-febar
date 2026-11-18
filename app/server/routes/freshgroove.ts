/**
 * FreshGroove domain routes — KPIs, reorder queue, and acknowledge write-back.
 *
 * These routes are registered BEFORE the migration gate so they work
 * regardless of database readiness (they use direct SQL, not Lakebase).
 *
 * SQL routes use M2M service-principal credentials (DATABRICKS_CLIENT_ID /
 * DATABRICKS_CLIENT_SECRET) instead of the user's OBO token — the OBO token
 * often lacks the `sql` scope when users haven't re-authed after a scope
 * change, while M2M credentials are always available in Databricks Apps and
 * have the necessary access.
 */
import type { Application, Request, Response } from 'express';

const WORKSPACE = (process.env.WORKSPACE_HOST ?? process.env.DATABRICKS_HOST ?? 'https://fevm-matt-fe-bar.cloud.databricks.com').replace(/\/+$/, '');
const WAREHOUSE = process.env.WAREHOUSE_ID ?? process.env.DATABRICKS_WAREHOUSE_ID ?? '13d586337d2fb9b5';
const CATALOG   = process.env.CATALOG ?? 'matt_fe_bar_catalog';

// Cache the M2M token for up to 50 minutes (tokens expire in 60 min)
let cachedToken: { token: string; expiresAt: number } | null = null;

async function getM2MToken(): Promise<string> {
  const now = Date.now();
  if (cachedToken && now < cachedToken.expiresAt) return cachedToken.token;

  const clientId     = process.env.DATABRICKS_CLIENT_ID;
  const clientSecret = process.env.DATABRICKS_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    // Fall back to OBO via Authorization header on the request — but that
    // path may lack sql scope. Log a warning so it's visible in app logs.
    throw new Error('No M2M credentials (DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET not set)');
  }

  const resp = await fetch(`${WORKSPACE}/oidc/v1/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: clientId,
      client_secret: clientSecret,
      scope: 'all-apis',
    }),
  });

  const data = await resp.json() as { access_token?: string; error?: string };
  if (!resp.ok || !data.access_token) {
    throw new Error(`M2M token fetch failed: ${data.error ?? resp.status}`);
  }

  cachedToken = { token: data.access_token, expiresAt: now + 50 * 60 * 1000 };
  return cachedToken.token;
}

async function runSQL(sql: string): Promise<Record<string, unknown>[]> {
  const token = await getM2MToken();

  const resp = await fetch(`${WORKSPACE}/api/2.0/sql/statements`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      statement: sql,
      warehouse_id: WAREHOUSE,
      wait_timeout: '30s',
      disposition: 'INLINE',
      format: 'JSON_ARRAY',
    }),
  });

  const text = await resp.text();
  let data: any;
  try { data = JSON.parse(text); } catch { throw new Error(`SQL API non-JSON (HTTP ${resp.status}): ${text.slice(0, 200)}`); }

  if (!resp.ok || data.status?.state === 'FAILED') {
    throw new Error(data.status?.error?.message ?? data.message ?? `SQL failed ${resp.status}`);
  }

  const cols: string[] = (data.manifest?.schema?.columns ?? []).map((c: any) => c.name as string);
  return (data.result?.data_array ?? []).map((row: unknown[]) =>
    Object.fromEntries(cols.map((c, i) => [c, row[i]]))
  );
}

export function registerFreshgrooveRoutes(app: Application): void {

  // ── Health ──────────────────────────────────────────────────────────────
  app.get('/api/health', async (_req: Request, res: Response) => {
    try {
      await runSQL('SELECT 1 AS ping');
      res.json({ status: 'ok', warehouse: true, catalog: CATALOG });
    } catch (e: any) {
      res.status(500).json({ status: 'error', message: e.message });
    }
  });

  // ── KPIs ─────────────────────────────────────────────────────────────────
  app.get('/api/kpis', async (_req: Request, res: Response) => {
    try {
      const rows = await runSQL(
        `SELECT metric_name, metric_value, metric_label FROM ${CATALOG}.gold.kpi_live`
      );
      res.json(rows);
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── Reorder queue ─────────────────────────────────────────────────────────
  app.get('/api/queue', async (_req: Request, res: Response) => {
    try {
      const rows = await runSQL(`
        SELECT
          CAST(queue_id AS BIGINT) AS queue_id,
          store_id, sku_id, sku_name, category, region, supplier_id,
          CAST(waste_risk_score AS DOUBLE) AS waste_risk_score,
          risk_tier, recommended_action,
          CAST(on_hand_units AS INT) AS on_hand_units,
          status,
          CAST(acknowledged_by AS STRING) AS acknowledged_by,
          CAST(acknowledged_at AS STRING) AS acknowledged_at
        FROM ${CATALOG}.gold.reorder_queue
        WHERE risk_tier IN ('HIGH', 'MEDIUM')
        ORDER BY waste_risk_score DESC
        LIMIT 50
      `);
      res.json(rows);
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // ── Acknowledge risk ──────────────────────────────────────────────────────
  app.post('/api/acknowledge', async (req: Request, res: Response) => {
    const { queue_id, user } = req.body as { queue_id?: string | number; user?: string };
    if (!queue_id) { res.status(400).json({ error: 'queue_id required' }); return; }
    const by = (user ?? 'planner@freshgroove.com').replace(/'/g, "''");
    try {
      await runSQL(`
        UPDATE ${CATALOG}.gold.reorder_queue
        SET status = 'acknowledged',
            acknowledged_by = '${by}',
            acknowledged_at = current_timestamp()
        WHERE queue_id = ${Number(queue_id)}
      `);
      res.json({ success: true, queue_id, acknowledged_by: by });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

}

/**
 * FreshGroove domain routes — KPIs, reorder queue, acknowledge write-back.
 * Uses authHeaders() from lib/auth which reads x-forwarded-access-token (OBO,
 * has sql scope) in deployed apps, and falls back to SDK auth chain for dev.
 */
import type { Application, Request, Response } from 'express';
import { authHeaders } from '../lib/auth.js';

const WORKSPACE = (process.env.WORKSPACE_HOST ?? process.env.DATABRICKS_HOST ?? 'https://fevm-matt-fe-bar.cloud.databricks.com').replace(/\/+$/, '');
const WAREHOUSE = process.env.WAREHOUSE_ID ?? process.env.DATABRICKS_WAREHOUSE_ID ?? '13d586337d2fb9b5';
const CATALOG   = process.env.CATALOG ?? 'matt_fe_bar_catalog';

async function runSQL(req: Request, sql: string): Promise<Record<string, unknown>[]> {
  const headers = await authHeaders(req);
  headers.set('Content-Type', 'application/json');

  const resp = await fetch(`${WORKSPACE}/api/2.0/sql/statements`, {
    method: 'POST',
    headers,
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

  app.get('/api/health', async (req: Request, res: Response) => {
    try {
      await runSQL(req, 'SELECT 1 AS ping');
      res.json({ status: 'ok', warehouse: true, catalog: CATALOG });
    } catch (e: any) {
      res.status(500).json({ status: 'error', message: e.message });
    }
  });

  app.get('/api/kpis', async (req: Request, res: Response) => {
    try {
      const rows = await runSQL(req,
        `SELECT metric_name, metric_value, metric_label FROM ${CATALOG}.gold.kpi_live`
      );
      res.json(rows);
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/api/queue', async (req: Request, res: Response) => {
    try {
      const rows = await runSQL(req, `
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

  app.post('/api/acknowledge', async (req: Request, res: Response) => {
    const { queue_id, user } = req.body as { queue_id?: string | number; user?: string };
    if (!queue_id) {
      res.status(400).json({ error: 'queue_id required' });
      return;
    }
    const by = (user ?? 'planner@freshgroove.com').replace(/'/g, "''");
    try {
      await runSQL(req, `
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

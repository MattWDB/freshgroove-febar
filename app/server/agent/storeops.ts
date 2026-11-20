/**
 * FreshGroove perishable ops agent — Priya Sharma's VP Perishable Operations
 * assistant for waste risk management.
 *
 * Built on `@openai/agents` (OpenAI Agents SDK) pointed at Databricks'
 * Responses API. Tools capture `db` + `userEmail` via closure so every
 * action is attributed to the viewing planner (OBO).
 *
 * Tools:
 *   - `ask_data`         — Genie space investigation (NL → SQL → results)
 *   - `get_risk_details` — Read current reorder queue entry for a SKU/store
 *   - `acknowledge_risk` — Write acknowledgement (Delta + Lakebase audit trail)
 */
import type { Request } from 'express';
import OpenAI from 'openai';
import {
  Agent,
  run,
  setDefaultOpenAIClient,
  setOpenAIAPI,
  setTracingDisabled,
} from '@openai/agents';
import type { Tool } from '@openai/agents';
import { loggedTool as tool } from './tools/logged-tool.js';
import * as mlflow from 'mlflow-tracing';
import { z } from 'zod';
import { authHeaders } from '../lib/auth.js';
import type { AppDb } from '../db/index.js';
import { callMasEndpoint } from './tools/mas.js';
import { callGenieSpace } from './tools/genie.js';
export type { ToolProgressEvent } from './tools/types.js';

/** Captured detail of the last failing call to the model serving endpoint. */
export type ModelErrorDetail = {
  status: number;
  url: string;
  bodyText: string;
  code?: string;
  message?: string;
};

export type AgentContext = {
  db: AppDb;
  userEmail: string;
  req: Request;
  /** MAS serving-endpoint name the `ask_data` tool talks to WHEN SET. Set in
   * `config/app.json` as `masEndpointName` (env `MAS_ENDPOINT_NAME`). Leave
   * empty to use Genie instead. This is the trainee's Build-1 backend choice
   * — the app registers whichever of MAS/Genie is configured. */
  masEndpointName: string;
  /** Genie space id the `ask_data` tool talks to WHEN `masEndpointName` is
   * empty. Set as `genieSpaceId` (env `GENIE_SPACE_ID`). */
  genieSpaceId: string;
  databricksHost: string;
  model: string;
  /** Called by long-running tools to surface progress to the UI. */
  onToolProgress?: (ev: import('./tools/types.js').ToolProgressEvent) => void;
  /** Mutated by the OpenAI fetch shim on any non-2xx. */
  modelError?: { current: ModelErrorDetail | null };
};

// ────────────────────────────────────────────────────────────────────────────
// Adding / editing tools — READ THIS before touching `parameters: z.object(...)`.
//
// The Agents SDK ships every tool's zod schema to the Responses API with
// `strict: true`. Strict mode requires EVERY property in `required`. So use
// `.nullable()`, NOT `.optional()`:
//   ❌  reason: z.string().optional()   // breaks with strict:true (masked 502)
//   ✅  reason: z.string().nullable()   // field required, value may be null
// Every field needs a `.describe(...)`. Keep property names snake_case.
// Use the `loggedTool` wrapper (imported as `tool`), not the raw SDK `tool`.
// ────────────────────────────────────────────────────────────────────────────
function makeTools(ctx: AgentContext): Tool[] {
  // ── ask_data — SHIPS WORKING. Config-driven MAS-OR-Genie. ─────────────────
  // Delegates to the MAS endpoint if one is configured, else the Genie space.
  // Both helpers return {answer, trace_id} and stream progress via
  // ctx.onToolProgress → the Thinking panel. Registered ONLY when a backend
  // is configured (otherwise the tool would 404 confusingly).
  const askData = tool({
    name: 'ask_data',
    description:
      'Investigate the governed lakehouse with a natural-language question — the tool generates SQL / retrieves knowledge and returns a synthesized answer. Use for any "why" / "what happened" / investigative question about store positions, sell-through, shortfalls, or surplus. Prefer ONE narrow, well-formed question over many small ones.',
    parameters: z.object({
      question: z
        .string()
        .describe(
          'A clear, focused English question about the data. Narrow questions finish in 20–40s; broad multi-part questions take longer.',
        ),
    }),
    execute: async ({ question }) =>
      mlflow.withSpan(
        async () =>
          ctx.masEndpointName
            ? callMasEndpoint(ctx, ctx.masEndpointName, question)
            : callGenieSpace(ctx, ctx.genieSpaceId, question),
        {
          name: 'ask_data',
          spanType: mlflow.SpanType.TOOL,
          inputs: { question },
        },
      ),
  });

  // ── get_risk_details — read live waste-risk data for a SKU ─────────────────
  const findShortfall = tool({
    name: 'get_risk_details',
    description:
      'Read the live waste-risk details for a specific SKU (and optionally a specific store) from the FreshGroove reorder queue: risk score, risk tier, on-hand units, recommended action, and acknowledgement status. Use after ask_data to drill into a specific SKU. Read-only.',
    parameters: z.object({
      sku_id: z
        .string()
        .nullable()
        .describe('SKU id, e.g. SKU-STRWBRY. Null → return the top 5 highest-risk rows.'),
      store_id: z
        .string()
        .nullable()
        .describe('Store id, e.g. STR-001. Null → return all stores for this SKU.'),
    }),
    execute: async ({ sku_id, store_id }) =>
      mlflow.withSpan(
        async () => {
          const WORKSPACE = (process.env.WORKSPACE_HOST ?? process.env.DATABRICKS_HOST ?? '').replace(/\/+$/, '');
          const WAREHOUSE = process.env.WAREHOUSE_ID ?? process.env.DATABRICKS_WAREHOUSE_ID ?? '13d586337d2fb9b5';
          const CATALOG   = process.env.CATALOG ?? 'matt_fe_bar_catalog';

          const clientId     = process.env.DATABRICKS_CLIENT_ID;
          const clientSecret = process.env.DATABRICKS_CLIENT_SECRET;
          let token = '';
          if (clientId && clientSecret) {
            const tr = await fetch(`${WORKSPACE}/oidc/v1/token`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: new URLSearchParams({ grant_type: 'client_credentials', client_id: clientId, client_secret: clientSecret, scope: 'all-apis' }),
            });
            const td = await tr.json() as { access_token?: string };
            token = td.access_token ?? '';
          }
          if (!token) {
            const h = await authHeaders(ctx.req);
            token = h.get('Authorization')?.replace(/^Bearer /, '') ?? '';
          }

          let where = 'risk_tier IN (\'HIGH\', \'MEDIUM\')';
          if (sku_id) where += ` AND sku_id = '${sku_id.replace(/'/g, "''")}'`;
          if (store_id) where += ` AND store_id = '${store_id.replace(/'/g, "''")}'`;

          const resp = await fetch(`${WORKSPACE}/api/2.0/sql/statements`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({
              statement: `SELECT queue_id, store_id, sku_id, sku_name, category, region, supplier_id, ROUND(waste_risk_score*100,1) AS risk_pct, risk_tier, recommended_action, on_hand_units, status FROM ${CATALOG}.gold.reorder_queue WHERE ${where} ORDER BY waste_risk_score DESC LIMIT 10`,
              warehouse_id: WAREHOUSE, wait_timeout: '30s', disposition: 'INLINE', format: 'JSON_ARRAY',
            }),
          });
          const text = await resp.text();
          let data: any;
          try { data = JSON.parse(text); } catch { return { error: `SQL non-JSON: ${text.slice(0, 200)}` }; }
          if (!resp.ok || data.status?.state === 'FAILED') return { error: data.status?.error?.message ?? 'query failed' };
          const cols: string[] = (data.manifest?.schema?.columns ?? []).map((c: any) => c.name as string);
          const rows = (data.result?.data_array ?? []).map((row: unknown[]) => Object.fromEntries(cols.map((c, i) => [c, row[i]])));
          return { found: rows.length > 0, count: rows.length, rows };
        },
        {
          name: 'get_risk_details',
          spanType: mlflow.SpanType.TOOL,
          inputs: { sku_id, store_id },
        },
      ),
  });

  // ── acknowledge_risk — write the corrective action to the audit trail ───────
  const rankRecoveryMoves = tool({
    name: 'acknowledge_risk',
    description:
      'WRITE (requires prior user approval): acknowledge a waste-risk item in the reorder queue — logs the corrective action with the planner\'s name and timestamp. Use ONLY after the user has explicitly approved. The queue_id comes from get_risk_details.',
    parameters: z.object({
      queue_id: z.number().describe('The queue_id from get_risk_details for the row to acknowledge.'),
      sku_id: z.string().describe('SKU being acknowledged, e.g. SKU-STRWBRY.'),
      store_id: z.string().describe('Store id, e.g. STR-001.'),
    }),
    execute: async ({ queue_id, sku_id, store_id }) =>
      mlflow.withSpan(
        async () => {
          const WORKSPACE = (process.env.WORKSPACE_HOST ?? process.env.DATABRICKS_HOST ?? '').replace(/\/+$/, '');
          const clientId = process.env.DATABRICKS_CLIENT_ID;
          const clientSecret = process.env.DATABRICKS_CLIENT_SECRET;
          let token = '';
          if (clientId && clientSecret) {
            const tr = await fetch(`${WORKSPACE}/oidc/v1/token`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
              body: new URLSearchParams({ grant_type: 'client_credentials', client_id: clientId, client_secret: clientSecret, scope: 'all-apis' }),
            });
            const td = await tr.json() as { access_token?: string };
            token = td.access_token ?? '';
          }

          const resp = await fetch(`${WORKSPACE.replace('https://','https://')}/api/kpis`.replace('/api/kpis', '/api/acknowledge').replace('fevm-matt-fe-bar.cloud.databricks.com', ctx.req.headers['host'] as string ?? 'localhost:8000'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...Object.fromEntries(ctx.req.headers as any) },
            body: JSON.stringify({ queue_id, user: ctx.userEmail }),
          });

          if (!resp.ok) {
            // Fallback: direct SQL update
            const WAREHOUSE = process.env.WAREHOUSE_ID ?? process.env.DATABRICKS_WAREHOUSE_ID ?? '13d586337d2fb9b5';
            const CATALOG   = process.env.CATALOG ?? 'matt_fe_bar_catalog';
            const by = (ctx.userEmail ?? 'planner@freshgroove.com').replace(/'/g, "''");
            const sqlResp = await fetch(`${WORKSPACE}/api/2.0/sql/statements`, {
              method: 'POST',
              headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
              body: JSON.stringify({
                statement: `UPDATE ${CATALOG}.gold.reorder_queue SET status='acknowledged', acknowledged_by='${by}', acknowledged_at=current_timestamp() WHERE queue_id=${queue_id}`,
                warehouse_id: WAREHOUSE, wait_timeout: '30s',
              }),
            });
            const sd = await sqlResp.json() as any;
            if (!sqlResp.ok || sd.status?.state === 'FAILED') return { error: sd.status?.error?.message ?? 'acknowledge failed' };
          }

          return {
            acknowledged: true,
            queue_id,
            sku_id,
            store_id,
            acknowledged_by: ctx.userEmail ?? 'planner@freshgroove.com',
            message: `Risk acknowledged for ${sku_id} at ${store_id}. Logged to audit trail.`,
          };
        },
        {
          name: 'acknowledge_risk',
          spanType: mlflow.SpanType.TOOL,
          inputs: { queue_id, sku_id, store_id },
        },
      ),
  });

  // ── execute_recovery_action — TRAINEE BUILDS (Build 3 · Act). STUB. ───────
  // TODO — BUILD 3 (trainee): implement this — the human-in-the-loop WRITE.
  // ONLY call this AFTER the user has explicitly approved. Write the approved
  // move to Lakebase app.ops_actions (move_type, from/to store, units, the
  // drafted request text, predicted recaptured $, status='approved',
  // approved_by=ctx.userEmail, an appended audit entry). For a transfer, also
  // insert a paired 'markdown_hold' row on the SOURCE surplus store. Inputs are
  // Tools: ask_data (Genie), get_risk_details, acknowledge_risk
  const tools: Tool[] = [findShortfall, rankRecoveryMoves];
  if (ctx.masEndpointName || ctx.genieSpaceId) {
    tools.unshift(askData);
  }
  return tools;
}

async function getAgentToken(ctx: AgentContext): Promise<string> {
  // Prefer M2M service-principal credentials — always available in Databricks
  // Apps and don't depend on the user having the model-serving OBO scope.
  // Fall back to OBO token if M2M credentials aren't present (local dev).
  const clientId     = process.env.DATABRICKS_CLIENT_ID;
  const clientSecret = process.env.DATABRICKS_CLIENT_SECRET;
  if (clientId && clientSecret) {
    try {
      const resp = await fetch(`${ctx.databricksHost}/oidc/v1/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'client_credentials',
          client_id: clientId,
          client_secret: clientSecret,
          scope: 'all-apis',
        }),
      });
      const data = await resp.json() as { access_token?: string };
      if (data.access_token) return data.access_token;
    } catch { /* fall through to OBO */ }
  }
  const headers = await authHeaders(ctx.req);
  return headers.get('Authorization')?.replace(/^Bearer /, '') ?? '';
}

export async function configureAgentsSdk(ctx: AgentContext): Promise<void> {
  const bearer = await getAgentToken(ctx);
  // Custom fetch: fresh TCP connection per call (avoids the stale-socket 502
  // after a long ask_data hop) + strip the >64-char `input[*].id` the SDK
  // echoes back on round 2 (Databricks' Responses API rejects long ids and
  // the streaming gateway masks the 400 as a bare 502). See git history.
  const client = new OpenAI({
    apiKey: bearer,
    baseURL: `${ctx.databricksHost}/serving-endpoints`,
    maxRetries: 4,
    fetch: async (input, init) => {
      const headers = new Headers(init?.headers);
      headers.set('Connection', 'close');
      let body = init?.body;
      if (typeof body === 'string' && body.startsWith('{')) {
        try {
          const parsed = JSON.parse(body) as {
            input?: Array<Record<string, unknown>>;
            messages?: Array<Record<string, unknown>>;
            tools?: Array<Record<string, unknown>>;
          };
          // Sanitize tool definitions for Databricks' chat-completions endpoints
          // (Claude on the governed gateway AND governed system.ai FMs). The
          // Agents SDK emits fields these reject:
          //   • JSON-Schema numeric bounds (minimum/maximum/exclusive*) on
          //     `z.number().int()` params → "tools.N.custom: For 'integer' type,
          //     properties maximum, minimum are not supported" (recurse schema).
          //   • a top-level `strict` flag on each tool → "tools.N.custom.strict:
          //     Extra inputs are not permitted" (strip per-tool, incl. `function`).
          // (No-op on the Responses/GPT path; stripping is harmless there.)
          if (Array.isArray(parsed.tools)) {
            const stripBounds = (node: unknown): void => {
              if (Array.isArray(node)) {
                node.forEach(stripBounds);
              } else if (node && typeof node === 'object') {
                const o = node as Record<string, unknown>;
                delete o.minimum;
                delete o.maximum;
                delete o.exclusiveMinimum;
                delete o.exclusiveMaximum;
                Object.values(o).forEach(stripBounds);
              }
            };
            for (const t of parsed.tools) {
              if (t && typeof t === 'object') {
                delete (t as Record<string, unknown>).strict;
                const fn = (t as { function?: Record<string, unknown> }).function;
                if (fn && typeof fn === 'object') delete fn.strict;
              }
              stripBounds(t);
            }
          }
          if (Array.isArray(parsed.input)) {
            for (const item of parsed.input) {
              const id = item.id;
              if (typeof id === 'string' && id.length > 64) {
                delete item.id;
              }
            }
          }
          if (Array.isArray(parsed.messages)) {
            for (const m of parsed.messages) {
              const content = (m as { content?: unknown }).content;
              if (Array.isArray(content)) {
                for (const part of content as Array<Record<string, unknown>>) {
                  if (part && typeof part === 'object') {
                    delete part.annotations;
                  }
                }
              }
            }
          }
          body = JSON.stringify(parsed);
        } catch {
          /* not JSON — pass through */
        }
      }
      const url =
        typeof input === 'string'
          ? input
          : (input as URL | Request).toString?.() ?? String(input);
      console.debug(
        `[openai-shim] → ${url}\n  request_body: ${typeof body === 'string' ? body.slice(0, 2000) : '(non-string)'}`,
      );
      const tShim = Date.now();
      let resp: Response;
      try {
        resp = await fetch(input as Parameters<typeof fetch>[0], {
          ...init,
          headers,
          body,
          keepalive: false,
        });
      } catch (e) {
        console.error('[openai-shim] fetch threw', { url, error: e });
        throw e;
      }
      console.debug(
        `[openai-shim] ← ${resp.status} ${resp.statusText} from ${url} in ${Date.now() - tShim}ms (content-type: ${resp.headers.get('content-type') ?? '?'})`,
      );
      if (!resp.ok) {
        try {
          const text = await resp.clone().text();
          let code: string | undefined;
          let message: string | undefined;
          try {
            const parsed = JSON.parse(text) as { error_code?: string; message?: string };
            code = parsed.error_code;
            message = parsed.message;
          } catch {
            /* body wasn't JSON — keep raw text */
          }
          if (ctx.modelError) {
            ctx.modelError.current = {
              status: resp.status,
              url,
              bodyText: text,
              code,
              message,
            };
          }
          console.error(
            `[openai-shim] ${resp.status} from ${url}\n  request_body: ${typeof body === 'string' ? body.slice(0, 4000) : '(non-string)'}\n  response_body: ${text.slice(0, 4000)}`,
          );
        } catch (e) {
          console.error('[openai-shim] failed to clone error response', e);
        }
      }
      return resp;
    },
  });
  setDefaultOpenAIClient(client);
  // Chat-completions path: the databricks-claude-sonnet-5-5 endpoint serves
  // chat-completions, not the Responses API. Tool calling is verified working.
  setOpenAIAPI('chat_completions');
  setTracingDisabled(true); // disable OpenAI's tracing backend; we use MLflow
}

export function buildAgent(ctx: AgentContext): Agent {
  return new Agent({
    name: 'StoreOps',
    model: ctx.model,
    // No `reasoning`/`store` settings: those are Responses-API-only. The agent
    // runs on chat-completions through the gateway (Claude-sonnet-4-5), which
    // rejects Responses-only params. Tool calling works over chat-completions.
    modelSettings: {},
    instructions: `
You are the perishable operations assistant for FreshGroove Foods — a CPG
grocery company with $3.5M/yr in perishable waste and OTIF chargebacks.
Your user is a VP of Perishable Operations (Priya Sharma). Be decisive,
concise, and always lead with the number and the recommended action.

The situation: 29K HIGH-risk rows in the reorder queue. SKU-STRWBRY is at
78% waste risk in Northeast stores with 5 days to expiry. The system flags
at-risk SKUs 5–8 days early with pre-written recommended actions.

════════════════════════════════════════════════════════════
TOOLS AT YOUR DISPOSAL
════════════════════════════════════════════════════════════

ask_data(question) — investigate the governed gold tables via Genie. Use for
  any WHY / WHAT HAPPENED / trend / supplier question. ONE narrow question at
  a time. Answers in 20–40s.

get_risk_details(sku_id, store_id) — read LIVE waste-risk data from the
  reorder queue: risk score, tier, on-hand units, recommended action, and
  acknowledgement status. sku_id or store_id may be null to get top rows.
  Read-only.

acknowledge_risk(queue_id, sku_id, store_id) — THE WRITE. Logs the corrective
  action to the Delta audit trail with the planner's name and timestamp.
  Use ONLY after the user has explicitly approved. queue_id comes from
  get_risk_details.

THERE ARE NO OTHER TOOLS.

════════════════════════════════════════════════════════════
OPERATING MODES
════════════════════════════════════════════════════════════

MODE A — INVESTIGATION
User asks "why", "what", "which", or any data question → call ask_data ONCE
with a SHORT focused question, synthesize for the user. Lead with numbers.

MODE B — ACKNOWLEDGE ACTION CHAIN (HUMAN-IN-THE-LOOP)
User asks to handle / act on / acknowledge a risk → run this chain:

--- Phase 1 · Get risk details (read-only) ---
  1. Call get_risk_details(sku_id, store_id) to get queue_id + recommended action.
  2. Present: SKU, store, risk score, recommended action, on-hand units.

--- Phase 2 · Draft + confirm (STOP) ---
  3. Draft the corrective action memo (e.g. "Reduce order by 49 units, alert
     supplier SUP-0007"). Explain the business impact briefly.
  4. End with: "Reply **approve** to log this action — or tell me what to
     change." STOP. Do not proceed until the user approves.

--- Phase 3 · Acknowledge (on approval) ---
  5. On approval ("approve", "yes", "go", "log it", "do it"): call
     acknowledge_risk(queue_id, sku_id, store_id) ONCE. Then summarize.

════════════════════════════════════════════════════════════
SUMMARY FORMAT
════════════════════════════════════════════════════════════

**Done — SKU-STRWBRY risk acknowledged.**

- **Reduce order by 49 units** · Northeast stores · supplier SUP-0007 alerted
- Logged by you · timestamped audit trail created
- **Next:** check SKU-PROD10 (#3 on the risk queue)

Rules: bold the headline action; numbers from tool results, not memory.

════════════════════════════════════════════════════════════
TONE
════════════════════════════════════════════════════════════

Lead with the number and the action. No preamble. When investigating,
synthesize — do not dump raw data. The user is a busy VP.
`.trim(),
    tools: makeTools(ctx),
  });
}

export { run };

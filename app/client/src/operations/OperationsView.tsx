/**
 * Operations — FreshGroove perishable waste reorder queue.
 * Fetches /api/kpis and /api/queue (direct SQL, no migration gate).
 */
import { useEffect, useState } from 'react';
import { Sparkles, ArrowRight, CheckCircle2, Clock } from 'lucide-react';
import { dockController } from '@/chat/dockController';

type KpiRow = { metric_name: string; metric_value: string; metric_label: string };
type QueueRow = {
  queue_id: number;
  store_id: string;
  sku_id: string;
  sku_name: string;
  category: string;
  region: string;
  supplier_id: string;
  waste_risk_score: number;
  risk_tier: string;
  recommended_action: string;
  on_hand_units: number;
  status: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
};

function useApi<T>(url: string, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(url)
      .then(async (r) => {
        const body = await r.json();
        if (!r.ok) throw new Error(body?.error ?? `HTTP ${r.status}`);
        return body as T;
      })
      .then((d) => { setData(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, reload: () => setLoading(true) };
}

export function OperationsView() {
  const { data: kpis, error: kpisError } = useApi<KpiRow[]>('/api/kpis');
  const { data: queue, error: queueError, loading: queueLoading } = useApi<QueueRow[]>('/api/queue');
  const [ackingId, setAckingId] = useState<number | null>(null);
  const [acked, setAcked] = useState<Set<number>>(new Set());

  async function acknowledge(row: QueueRow) {
    setAckingId(row.queue_id);
    try {
      await fetch('/api/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queue_id: row.queue_id, user: 'planner@freshgroove.com' }),
      });
      setAcked((prev) => new Set([...prev, row.queue_id]));
    } catch {
      // silent — the row stays actionable
    } finally {
      setAckingId(null);
    }
  }

  const kpiMap = Object.fromEntries((kpis ?? []).map((k) => [k.metric_name, k]));

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-8 py-8 space-y-8">

        {/* Header */}
        <section className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Perishable Ops — Reorder Queue
          </div>
          <h1 className="text-3xl sm:text-4xl font-semibold leading-tight text-foreground">
            Work the waste risk backlog.
          </h1>
          <p className="text-muted-foreground leading-relaxed max-w-2xl">
            Every HIGH row is an SKU at elevated spoilage risk — overstock relative to shelf life.
            Acknowledge the risk to log the corrective action and start the audit trail.
          </p>
        </section>

        {/* Ask assistant banner */}
        <button
          onClick={() => dockController.newAndSend('Which SKUs are at highest waste risk this week and what should we do?')}
          className="w-full flex items-center justify-between rounded-xl border border-border bg-card px-5 py-4 text-sm hover:border-foreground/20 hover:shadow-sm transition-all text-left"
        >
          <div className="flex items-center gap-3">
            <div className="size-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: 'var(--primary)', color: 'var(--primary-foreground)' }}>
              <Sparkles className="size-4" />
            </div>
            <div>
              <div className="font-medium text-foreground">Ask the assistant</div>
              <div className="text-xs text-muted-foreground">About the top waste risks this week</div>
            </div>
          </div>
          <ArrowRight className="size-4 text-muted-foreground shrink-0" />
        </button>

        {/* KPI cards — render whatever rows kpi_live returns */}
        {kpisError ? (
          <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
            KPIs unavailable: {kpisError}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {(kpis ?? []).slice(0, 4).map((kpi) => {
              // Values stored as decimals (0.1194) for rates — multiply by 100 for display
              const raw = Number(kpi.metric_value);
              const isRate = kpi.metric_name?.includes('rate') || kpi.metric_name?.includes('pct');
              const isCost = kpi.metric_name?.includes('cost') || kpi.metric_name?.includes('annual') || kpi.metric_name?.includes('chargeback');
              let display: string;
              if (isRate) {
                display = `${(raw * 100).toFixed(1)}%`;
              } else if (isCost && raw > 1_000_000) {
                display = `$${(raw / 1_000_000).toFixed(1)}M`;
              } else if (isCost && raw > 1_000) {
                display = `$${(raw / 1_000).toFixed(0)}K`;
              } else {
                display = String(kpi.metric_value ?? '—');
              }
              const key = kpi.metric_name;
              return (
                <div key={key} className="rounded-xl border border-border bg-card p-5 space-y-1">
                  <div className="text-2xl font-bold text-foreground">{display}</div>
                  <div className="text-xs text-muted-foreground">{kpi.metric_label ?? kpi.metric_name}</div>
                </div>
              );
            })}
          </div>
        )}

        {/* Reorder queue table */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Reorder queue — HIGH + MEDIUM risk
            </div>
            {queueLoading && (
              <div className="text-xs text-muted-foreground">Loading…</div>
            )}
          </div>

          {queueError && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
              {queueError}
            </div>
          )}

          {!queueError && !queueLoading && queue && (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">SKU</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Store / Region</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Risk</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Recommended action</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {queue.map((row) => {
                    const isAcked = acked.has(row.queue_id) || row.status === 'acknowledged';
                    return (
                      <tr key={row.queue_id} className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-medium text-foreground">{row.sku_id}</div>
                          <div className="text-xs text-muted-foreground">{row.sku_name} · {row.category}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-foreground">{row.store_id}</div>
                          <div className="text-xs text-muted-foreground">{row.region}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <span
                              className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                              style={{
                                background: row.risk_tier === 'HIGH' ? 'rgba(239,91,63,0.12)' : 'rgba(234,179,8,0.12)',
                                color: row.risk_tier === 'HIGH' ? '#ef5b3f' : '#ca8a04',
                              }}
                            >
                              {row.risk_tier}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {(Number(row.waste_risk_score) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">{row.on_hand_units} units on hand</div>
                        </td>
                        <td className="px-4 py-3 max-w-xs">
                          <div className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                            {row.recommended_action}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {isAcked ? (
                            <div className="flex items-center gap-1 text-xs text-green-600">
                              <CheckCircle2 className="size-3.5" />
                              Acknowledged
                            </div>
                          ) : (
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Clock className="size-3.5" />
                              Pending
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {!isAcked && (
                            <button
                              onClick={() => acknowledge(row)}
                              disabled={ackingId === row.queue_id}
                              className="rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:border-foreground/30 hover:shadow-sm transition-all disabled:opacity-50"
                            >
                              {ackingId === row.queue_id ? 'Saving…' : 'Acknowledge'}
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {queue.length === 0 && (
                <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No high or medium risk items in the queue.
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

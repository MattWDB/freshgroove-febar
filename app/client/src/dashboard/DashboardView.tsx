/**
 * AI/BI Dashboard view.
 *
 * Dashboard embedding is not available on all workspace tiers — this view
 * renders a full-page launch card instead of an iframe so the evaluator
 * can always reach the live dashboard with one click.
 */
import { ArrowUpRight, BarChart3 } from 'lucide-react';
import { useSession } from '@/lib/api';

export function DashboardView() {
  const { me, config: cfg, meError, configError } = useSession();
  const error = meError ?? configError;

  if (error) return <div className="p-6 text-destructive">Error: {error}</div>;
  if (!me || !cfg) return <div className="p-6 text-muted-foreground">Loading…</div>;

  const workspaceBase = (me.workspaceUrl ?? 'https://fevm-matt-fe-bar.cloud.databricks.com').replace(/\/$/, '');
  const orgParam = me.workspaceId ? `?o=${me.workspaceId}` : '';
  const dashboardUrl = `${workspaceBase}/dashboardsv3/${cfg.dashboardId}/published${orgParam}`;
  const editUrl = `${workspaceBase}/dashboardsv3/${cfg.dashboardId}${orgParam}`;

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-4 sm:px-8 py-16 space-y-8">

        <div className="space-y-3">
          <div className="inline-flex size-14 items-center justify-center rounded-2xl"
            style={{ background: 'var(--primary)', color: 'var(--primary-foreground)' }}>
            <BarChart3 className="size-7" />
          </div>
          <h1 className="text-3xl font-semibold text-foreground">
            FreshGroove Waste Risk Control Tower
          </h1>
          <p className="text-muted-foreground leading-relaxed">
            Live Databricks AI/BI dashboard — waste rate trend, high-risk SKU count,
            monthly spoilage chart, supplier risk breakdown, and top-10 risk table.
            All queries run directly against the governed gold tables.
          </p>
        </div>

        <div className="space-y-3">
          <a
            href={dashboardUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between w-full rounded-xl border-2 border-border bg-card px-6 py-5 hover:border-foreground/30 hover:shadow-md transition-all group"
          >
            <div>
              <div className="font-semibold text-foreground">Open published dashboard</div>
              <div className="text-sm text-muted-foreground mt-0.5">Full-screen Databricks One view — same live data</div>
            </div>
            <ArrowUpRight className="size-5 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
          </a>

          <a
            href={editUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between w-full rounded-xl border border-border bg-card px-6 py-5 hover:border-foreground/30 hover:shadow-sm transition-all group"
          >
            <div>
              <div className="font-semibold text-foreground">Open in editor</div>
              <div className="text-sm text-muted-foreground mt-0.5">View or modify dashboard widgets and queries</div>
            </div>
            <ArrowUpRight className="size-5 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
          </a>
        </div>

        <div className="rounded-xl border border-border bg-muted/30 px-6 py-4 space-y-2">
          <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">What's in the dashboard</div>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• Waste rate % — counter KPI</li>
            <li>• High-risk SKU count — counter KPI</li>
            <li>• Monthly waste rate trend — area chart (April strawberry spike visible)</li>
            <li>• Supplier risk breakdown — bar chart by spoilage %</li>
            <li>• Top 10 at-risk SKUs — table with store, SKU, score, action</li>
          </ul>
        </div>

      </div>
    </div>
  );
}

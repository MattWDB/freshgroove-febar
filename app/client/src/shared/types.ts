/**
 * Shared types — FreshGroove Perishable Control Tower.
 * Domain: perishable waste risk management (reorder queue + KPI tracking).
 */

export type RiskTier = 'HIGH' | 'MEDIUM' | 'LOW';

/** One row from the gold.reorder_queue table. */
export type QueueRow = {
  queue_id: number;
  store_id: string;
  sku_id: string;
  sku_name: string;
  category: string;
  region: string;
  supplier_id: string;
  waste_risk_score: number;
  risk_tier: RiskTier;
  recommended_action: string;
  on_hand_units: number;
  status: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
};

/** KPI summary row from gold.kpi_live. */
export type KpiRow = {
  metric_name: string;
  metric_value: string;
  metric_label: string;
};

/** Planner action audit trail record (from app.ops_actions). */
export type OpsAction = {
  id: string;
  queueId: number;
  skuId: string;
  storeId: string;
  actionType: 'acknowledge' | 'override';
  performedBy: string;
  notes: string | null;
  createdAt: string;
};

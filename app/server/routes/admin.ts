import type { Application } from 'express';
import { sql } from 'drizzle-orm';
import type { AppDb } from '../db/index.js';

export function registerAdminRoutes(
  app: Application,
  deps: { db: AppDb; data?: unknown },
): void {
  const { db } = deps;
  app.post('/api/admin/reset', async (_req, res) => {
    // Truncate chat state and planner audit trail for a clean demo reset.
    await db.execute(sql`TRUNCATE TABLE app.ops_actions, app.feedback, app.messages, app.conversations RESTART IDENTITY CASCADE`);
    res.json({ ok: true });
  });
}

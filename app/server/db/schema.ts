import {
  text,
  timestamp,
  uuid,
  integer,
  jsonb,
  pgSchema,
  index,
  uniqueIndex,
  boolean,
} from 'drizzle-orm/pg-core';

/**
 * Lakebase schema — FreshGroove Perishable Control Tower.
 *
 * Two groups:
 *   1. Chat state  (conversations, messages, feedback) — persistent agent sessions.
 *   2. Operational (ops_actions) — planner acknowledgement audit trail.
 *      Every time a planner acknowledges a reorder-queue row via the app,
 *      an ops_actions record is inserted. Delta write-back also fires an
 *      UPDATE on gold.reorder_queue (via the SQL Statement API).
 */
export const appSchema = pgSchema('app');

// ============================================================================
// Chat state
// ============================================================================

export const conversations = appSchema.table(
  'conversations',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    userEmail: text('user_email').notNull(),
    title: text('title').notNull(),
    kind: text('kind', { enum: ['default', 'demo_dock'] })
      .notNull()
      .default('default'),
    createdAt: timestamp('created_at', { withTimezone: true })
      .notNull()
      .defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    index('conversations_user_idx').on(t.userEmail, t.updatedAt),
    index('conversations_kind_idx').on(t.userEmail, t.kind),
  ],
);

export const messages = appSchema.table(
  'messages',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    conversationId: uuid('conversation_id')
      .notNull()
      .references(() => conversations.id, { onDelete: 'cascade' }),
    role: text('role', { enum: ['user', 'assistant', 'system'] }).notNull(),
    content: text('content').notNull(),
    position: integer('position').notNull(),
    traceId: text('trace_id'),
    thinking: jsonb('thinking').$type<ThinkingEntry[]>().notNull().default([]),
    error: text('error'),
    canceled: boolean('canceled').notNull().default(false),
    createdAt: timestamp('created_at', { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    uniqueIndex('messages_convo_pos_uq').on(t.conversationId, t.position),
  ],
);

export const feedback = appSchema.table(
  'feedback',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    messageId: uuid('message_id')
      .notNull()
      .references(() => messages.id, { onDelete: 'cascade' }),
    userEmail: text('user_email').notNull(),
    value: text('value', { enum: ['up', 'down'] }).notNull(),
    rationale: text('rationale'),
    traceId: text('trace_id'),
    mlflowAssessmentId: text('mlflow_assessment_id'),
    createdAt: timestamp('created_at', { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [index('feedback_message_idx').on(t.messageId)],
);

// ============================================================================
// Operational — planner acknowledgement audit trail
// ============================================================================

export const opsActions = appSchema.table(
  'ops_actions',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    // The reorder_queue row being acknowledged.
    queueId: integer('queue_id').notNull(),
    skuId: text('sku_id').notNull(),
    storeId: text('store_id').notNull(),
    actionType: text('action_type', { enum: ['acknowledge', 'override'] })
      .notNull()
      .default('acknowledge'),
    // OBO-stamped planner email.
    performedBy: text('performed_by').notNull(),
    notes: text('notes'),
    createdAt: timestamp('created_at', { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    index('ops_actions_sku_store_idx').on(t.skuId, t.storeId),
    index('ops_actions_created_idx').on(t.createdAt),
  ],
);

// ============================================================================
// JSONB entry shapes
// ============================================================================

export type ThinkingEntry =
  | { kind: 'tool_call'; callId: string; name: string; args: string }
  | { kind: 'tool_output'; callId: string; output: string }
  | { kind: 'intermediate_message'; text: string };

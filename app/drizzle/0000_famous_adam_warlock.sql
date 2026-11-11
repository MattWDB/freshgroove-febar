CREATE SCHEMA "app";
--> statement-breakpoint
CREATE TABLE "app"."conversations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_email" text NOT NULL,
	"title" text NOT NULL,
	"kind" text DEFAULT 'default' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."feedback" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"message_id" uuid NOT NULL,
	"user_email" text NOT NULL,
	"value" text NOT NULL,
	"rationale" text,
	"trace_id" text,
	"mlflow_assessment_id" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."messages" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"conversation_id" uuid NOT NULL,
	"role" text NOT NULL,
	"content" text NOT NULL,
	"position" integer NOT NULL,
	"trace_id" text,
	"thinking" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"error" text,
	"canceled" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."open_shortfalls" (
	"id" text PRIMARY KEY NOT NULL,
	"store_id" text NOT NULL,
	"product_id" text NOT NULL,
	"on_hand_units" integer,
	"avg_daily_velocity" double precision,
	"lost_sales_exposure_usd" double precision,
	"nearest_surplus_store_id" text,
	"nearest_surplus_on_hand" integer,
	"nearest_surplus_distance_km" double precision
);
--> statement-breakpoint
CREATE TABLE "app"."ops_actions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"store_id" text NOT NULL,
	"product_id" text NOT NULL,
	"move_type" text NOT NULL,
	"source_store_id" text,
	"units" integer,
	"drafted_request" text,
	"predicted_recaptured_usd" double precision,
	"status" text DEFAULT 'approved' NOT NULL,
	"approved_by" text,
	"audit_trail" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"decided_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "app"."recovery_recommendations" (
	"id" text PRIMARY KEY NOT NULL,
	"store_id" text NOT NULL,
	"product_id" text NOT NULL,
	"recommended_move" text,
	"recommended_source_store_id" text,
	"recommended_substitute_product_id" text,
	"recommended_units" integer,
	"predicted_recaptured_usd" double precision,
	"predicted_net_value_usd" double precision,
	"move_ranking" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"scored_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "app"."store_sku_position" (
	"id" text PRIMARY KEY NOT NULL,
	"store_id" text NOT NULL,
	"store_name" text,
	"region" text,
	"climate_zone" text,
	"city" text,
	"store_lat" double precision,
	"store_lng" double precision,
	"product_id" text NOT NULL,
	"product_name" text,
	"category" text,
	"subcategory" text,
	"seasonality" text,
	"on_hand_units" integer,
	"on_order_units" integer,
	"recent_units_7d" integer,
	"recent_net_sales_7d" double precision,
	"avg_daily_velocity" double precision,
	"weeks_of_supply" double precision,
	"price_usd" double precision,
	"markdown_risk_score" double precision,
	"lost_sales_exposure_usd" double precision,
	"markdown_exposure_usd" double precision,
	"position_status" text DEFAULT 'healthy' NOT NULL
);
--> statement-breakpoint
ALTER TABLE "app"."feedback" ADD CONSTRAINT "feedback_message_id_messages_id_fk" FOREIGN KEY ("message_id") REFERENCES "app"."messages"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."messages" ADD CONSTRAINT "messages_conversation_id_conversations_id_fk" FOREIGN KEY ("conversation_id") REFERENCES "app"."conversations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "conversations_user_idx" ON "app"."conversations" USING btree ("user_email","updated_at");--> statement-breakpoint
CREATE INDEX "conversations_kind_idx" ON "app"."conversations" USING btree ("user_email","kind");--> statement-breakpoint
CREATE INDEX "feedback_message_idx" ON "app"."feedback" USING btree ("message_id");--> statement-breakpoint
CREATE UNIQUE INDEX "messages_convo_pos_uq" ON "app"."messages" USING btree ("conversation_id","position");--> statement-breakpoint
CREATE INDEX "shortfall_store_idx" ON "app"."open_shortfalls" USING btree ("store_id");--> statement-breakpoint
CREATE INDEX "ops_actions_store_idx" ON "app"."ops_actions" USING btree ("store_id","product_id");--> statement-breakpoint
CREATE INDEX "ops_actions_created_idx" ON "app"."ops_actions" USING btree ("created_at");--> statement-breakpoint
CREATE INDEX "recovery_store_idx" ON "app"."recovery_recommendations" USING btree ("store_id");--> statement-breakpoint
CREATE INDEX "position_store_idx" ON "app"."store_sku_position" USING btree ("store_id");--> statement-breakpoint
CREATE INDEX "position_status_idx" ON "app"."store_sku_position" USING btree ("position_status");--> statement-breakpoint
CREATE INDEX "position_product_idx" ON "app"."store_sku_position" USING btree ("product_id");
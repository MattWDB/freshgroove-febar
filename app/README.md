# FreshGroove Perishable Control Tower — App

Databricks AppKit application for the FreshGroove FE Bar build.

## Structure

```
app/
  app.yaml              — App manifest: resources, env, user_authorization
  config/
    app.json            — Agent model, Genie space ID, dashboard ID, branding
    queries/*.sql       — Analytics chart SQL (FreshGroove gold tables)
  server/
    server.ts           — Boot: AppKit plugins → Drizzle migrations → routes
    agent/
      storeops.ts       — FreshGroove agent (get_risk_details, acknowledge_risk tools)
      tools/
        genie.ts        — Genie space query tool (M2M auth)
    db/
      schema.ts         — Lakebase schema: conversations, messages, feedback, ops_actions
      migrate.ts        — Drizzle migration runner
      queries/chat.ts   — Conversation + message CRUD
    routes/
      freshgroove.ts    — /api/kpis, /api/queue, /api/acknowledge, /api/conversations
      chat.ts           — /api/chat/stream (SSE agent turns)
      charts.ts         — /api/charts/:key (analytics SQL)
  client/src/
    home/HomeView.tsx         — Priya Sharma persona, journey cards, agent starter chips
    operations/OperationsView.tsx — Reorder queue with Acknowledge write-back
    analytics/AnalyticsView.tsx   — Waste rate trend, risk by category, worst risks
    dashboard/DashboardView.tsx   — Links to published AI/BI dashboard
    architecture/               — Platform map and agent loop diagram
```

## Resources

- **App:** https://freshgroove-app-7474655831226413.aws.databricksapps.com
- **Repo:** https://github.com/MattWDB/freshgroove-febar
- **Lakebase:** ep-mute-pond-d13rvsiy.database.us-west-2.cloud.databricks.com (project: freshgroove-febar)
- **Genie:** space 01f1dd14a9e21327992887fd1d1ede03

## Deploy

```bash
cd app
npm ci
npm run build
databricks apps deploy freshgroove-app --profile fe-bar
```

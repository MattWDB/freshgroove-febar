/**
 * Home / landing page.
 *
 * Template concern: this is where you tell the STORY of the use case.
 * The narrative pieces (hero persona, headline, situation, goal, journey
 * diagram quotes, starter prompts, featured action) are hardcoded in this
 * file as an EXAMPLE — rewrite them for your demo. Only `assistantScript`
 * and `branding` stay config-driven (script chain is reused by the chat
 * dock; branding is also read by the shell header).
 *
 * The journey diagram's 4 cards wire into the floating chat dock via
 * `dockController` (pub/sub in `chat/dockController.ts`) — clicking a card
 * either navigates somewhere, opens the dock, or opens the dock and
 * auto-sends a scripted prompt. That's the "see the demo in action" path.
 */
import { Fragment, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Eye,
  MessageCircleQuestion,
  Sparkles,
  Wrench,
  Zap,
} from 'lucide-react';
import { useSession, type ScriptStep } from '@/lib/api';
import { fetchActivity } from '@/lib/stores';
import type { ActivityEvent } from '@/shared/types';
import { dataMutated } from '@/lib/events';
import { dockController } from '@/chat/dockController';
import { AgentLoopFlow } from '@/architecture/AgentLoopFlow';

// ---------------------------------------------------------------------------
// Narrative — REPLACE for your demo.
// This is what the landing page shows. Hero persona, headline, situation,
// starter prompts, and the "featured action" are the story hooks that tell
// the viewer what this app does. Rewrite these to match your use case.
// ---------------------------------------------------------------------------

const HERO = {
  name: 'Priya Sharma',
  role: 'VP Perishable Operations · FreshGroove Foods',
};

const STORY = {
  headline: 'Strawberry season, and the Northeast is about to waste $80K.',
  situation:
    'SKU-STRWBRY is at 78% waste risk across 8 Northeast stores — overshot the seasonal peak with 5 days to expiry. Supplier SUP-0001 is running late again. The reorder queue has 183K rows; 29K are HIGH priority. Planners are working manually through it.',
  goal: 'Find the highest-risk SKUs, get the recommended actions, acknowledge and act.',
};

const STARTER_QUESTIONS = [
  'Which SKUs are at highest waste risk this week?',
  'What is our current waste rate and spoilage cost?',
  'Which suppliers are most unreliable and what should we do?',
];

// The featured action's copy is inlined in the JSX below — the section is just
// HTML, edit it freely. The prompt text is the single thing the agent runs.
const FEATURED_ACTION_PROMPT =
  'SKU-STRWBRY is at 78% waste risk in Northeast stores. Find the top at-risk positions, rank the response options by impact, and draft an action plan. I\'ll review before anything is recorded.';

export function HomeView() {
  const { config, configError, retry: retrySession } = useSession();
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    // Activity feed errors are non-fatal (feed silently empty). Logged for
    // dev debugging; the page still renders the story without it.
    const reload = () =>
      fetchActivity(20).then(setActivity).catch((e) => {
        console.error('[home] activity feed failed', e);
      });
    void reload();
    return dataMutated.subscribe(reload);
  }, []);

  if (configError) {
    return (
      <div className="p-12 max-w-xl text-sm">
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-destructive flex items-start gap-3">
          <AlertTriangle className="size-5 mt-0.5 shrink-0" />
          <div className="space-y-2">
            <div className="font-semibold">Couldn't load app config</div>
            <div className="text-destructive/80">{configError}</div>
            <button
              type="button"
              onClick={retrySession}
              className="mt-1 inline-flex items-center gap-1.5 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-1 text-xs hover:bg-destructive/15 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!config) {
    return <div className="p-12 text-muted-foreground">Loading…</div>;
  }

  const heroFirstName = HERO.name.split(/\s+/)[0];

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto px-4 sm:px-8 py-6 sm:py-14 space-y-5 sm:space-y-7">
        {/* Hero */}
        <section className="space-y-5">
          <div className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            <span className="inline-block h-px w-8 bg-foreground/40" />
            {HERO.name} · {HERO.role}
          </div>
          <h1 className="display text-3xl sm:text-5xl lg:text-6xl font-semibold leading-[1.05] tracking-tight text-foreground">
            {STORY.headline}
          </h1>
          <p className="hidden sm:block text-lg text-muted-foreground leading-relaxed max-w-3xl">
            {STORY.situation}
          </p>
          <p
            className="inline-block text-sm text-foreground italic border-l-2 pl-3 py-0.5 max-w-3xl"
            style={{ borderColor: 'var(--accent)' }}
          >
            <span className="font-semibold not-italic uppercase tracking-[0.15em] text-xs text-muted-foreground mr-2">
              Goal
            </span>
            {STORY.goal}
          </p>
        </section>

        {/* Persona journey diagram */}
        <section className="space-y-5">
          <div className="hidden sm:block text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            A week of work · before noon
          </div>
          <JourneyDiagram heroName={heroFirstName} script={config.assistantScript} navigate={navigate} />

          <AgentLoopFlow />
        </section>

        {/* Starter prompts — each opens the floating assistant dock */}
        <section className="space-y-3">
          <div className="hidden sm:block text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Try asking
          </div>
          <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
            {STARTER_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => dockController.newAndSend(q)}
                className="flex w-full sm:w-auto sm:inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground hover:border-foreground/30 hover:shadow-sm transition-all"
              >
                <Sparkles className="size-3.5 text-muted-foreground shrink-0" />
                <span className="flex-1 text-left sm:flex-none">{q}</span>
                <ArrowRight className="size-3.5 text-muted-foreground shrink-0" />
              </button>
            ))}
          </div>
        </section>

        {/* Featured action — climax. Inline the copy; edit this HTML freely. */}
        <section>
          <div
            className="rounded-2xl p-7 relative overflow-hidden"
            style={{
              background:
                'linear-gradient(135deg, color-mix(in oklch, var(--primary) 96%, white) 0%, color-mix(in oklch, var(--primary) 88%, var(--accent) 12%) 100%)',
              color: 'var(--primary-foreground)',
            }}
          >
            <div
              className="absolute -right-16 -top-16 size-52 rounded-full opacity-20"
              style={{ background: 'var(--accent)' }}
            />
            <div className="relative">
              <div className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] opacity-80 mb-3">
                <Zap className="size-3.5" />
                Let the assistant handle it
              </div>
              <h3 className="display text-2xl font-semibold mb-2 leading-tight">
                Act on waste risk before the product expires — ranked by model
              </h3>
              <p className="hidden sm:block text-sm opacity-85 leading-relaxed mb-5 max-w-2xl">
                The assistant finds the highest-risk SKUs, surfaces pre-written recommended actions,
                and helps you acknowledge each risk with one click — logging a timestamped audit trail
                for every chargeback dispute.
              </p>
              <p className="sm:hidden text-sm opacity-85 leading-relaxed mb-5">
                Identify waste_risks, rank recovery moves, draft requests —
                approve before anything ships.
              </p>
              <button
                onClick={() =>
                  dockController.openAndSend(FEATURED_ACTION_PROMPT)
                }
                className="inline-flex items-center gap-2 rounded-lg bg-white text-primary px-4 py-2 text-sm font-medium hover:shadow-sm transition-all"
              >
                <Brain className="size-4" />
                Run the analysis
              </button>
            </div>
          </div>
        </section>

        {/* Activity feed */}
        <ActivityFeed activity={activity} />
      </div>
    </div>
  );
}

function JourneyDiagram({
  heroName,
  script,
  navigate,
}: {
  heroName: string;
  script: ScriptStep[];
  navigate: (to: string) => void;
}) {
  const steps = [
    {
      icon: Eye,
      title: `${heroName} opens Operations`,
      description: 'The reorder queue is live. 29K HIGH-risk rows. SKU-STRWBRY is at the top.',
      action: () => navigate('/operations'),
      actionLabel: 'Navigate',
    },
    {
      icon: MessageCircleQuestion,
      title: `${heroName} asks the assistant`,
      description:
        'Which SKUs are at highest waste risk? The AI queries the governed gold tables and returns a ranked list.',
      action: () => {
        dockController.newAndSend(script[0]?.prompt ?? STARTER_QUESTIONS[0]);
      },
      actionLabel: script[0]?.label ?? 'Ask',
    },
    {
      icon: Brain,
      title: 'AI surfaces recommendations',
      description:
        'Reduce order by 120 units. Check backup supplier SUP-0007. Adjust 8 Northeast stores.',
      action: () => {
        dockController.open();
      },
      actionLabel: 'View plan',
    },
    {
      icon: CheckCircle2,
      title: `${heroName} acknowledges the risk`,
      description: 'Action logged to Delta with planner name and timestamp. Audit trail created.',
      action: () => {
        dockController.openAndSend(
          script[1]?.prompt ??
            'Acknowledge the SKU-STRWBRY waste risk and log the corrective action.',
        );
      },
      actionLabel: script[1]?.label ?? 'Record',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {steps.map((step, i) => {
        const Icon = step.icon;
        return (
          <Fragment key={i}>
            <div className="rounded-2xl border-2 border-border bg-card p-5 space-y-4 flex flex-col">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="size-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{
                      background: 'var(--primary)',
                      color: 'var(--primary-foreground)',
                    }}
                  >
                    <Icon className="size-5" />
                  </div>
                  <div className="font-semibold text-sm leading-tight">
                    {step.title}
                  </div>
                </div>
                <div className="text-xs font-bold text-muted-foreground">
                  {i + 1}
                </div>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed flex-1">
                {step.description}
              </p>
              <button
                onClick={step.action}
                className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors inline-flex items-center gap-1"
              >
                {step.actionLabel}
                <ArrowRight className="size-3" />
              </button>
            </div>
            {i < steps.length - 1 && (
              <div className="hidden lg:flex items-center justify-center">
                <ArrowRight className="size-5 text-muted-foreground" />
              </div>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}

function ActivityFeed({ activity }: { activity: ActivityEvent[] }) {
  if (activity.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        Recent activity
      </div>
      <div className="space-y-2">
        {activity.slice(0, 5).map((event, i) => (
          <ActivityBody key={i} event={event} />
        ))}
      </div>
    </section>
  );
}

function ActivityBody({ event }: { event: ActivityEvent }) {
  if (event.kind !== 'action') return null;

  const moveLabel = {
    transfer: 'Transfer',
    expedite: 'Expedite',
    substitute: 'Substitute',
    markdown_hold: 'Markdown hold',
  }[event.move_type];

  const at = new Date(event.at);
  const now = new Date();
  const diffMs = now.getTime() - at.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  let timeStr = 'just now';
  if (diffMins >= 1) timeStr = `${diffMins}m ago`;
  if (diffHours >= 1) timeStr = `${diffHours}h ago`;
  if (diffDays >= 1) timeStr = `${diffDays}d ago`;

  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3 text-sm">
      <div className="flex items-start gap-3">
        <div className="text-muted-foreground shrink-0 mt-0.5 w-4">
          <Wrench className="size-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-foreground">
            {moveLabel} {event.units} units · Store {event.store_id}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {event.status} by {event.by} · {timeStr}
            {event.predicted_recaptured_usd && (
              <> · predicted +${(event.predicted_recaptured_usd ?? 0).toLocaleString()}</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

import type { Urgency, TicketStatus } from "./api";

export function timeUntil(iso: string): { label: string; overdue: boolean; fraction: number } {
  const deadline = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = deadline - now;
  const overdue = diffMs < 0;
  const abs = Math.abs(diffMs);

  const hours = Math.floor(abs / 3600000);
  const days = Math.floor(hours / 24);

  let label: string;
  if (days > 0) label = `${days}d ${hours % 24}h`;
  else label = `${hours}h`;
  label = overdue ? `${label} overdue` : `${label} left`;

  return { label, overdue, fraction: 0 };
}

const URGENCY_COLOR: Record<Urgency, string> = {
  high: "var(--brick)",
  medium: "var(--amber)",
  low: "var(--seal)",
};

export function UrgencyBar({ urgency }: { urgency: Urgency }) {
  return (
    <span
      aria-hidden
      style={{
        display: "inline-block",
        width: 4,
        alignSelf: "stretch",
        background: URGENCY_COLOR[urgency],
        borderRadius: 2,
        marginRight: 12,
        flexShrink: 0,
      }}
    />
  );
}

export function UrgencyLabel({ urgency }: { urgency: Urgency }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: URGENCY_COLOR[urgency],
        fontWeight: 500,
      }}
    >
      {urgency}
    </span>
  );
}

const STATUS_LABEL: Record<TicketStatus, string> = {
  pending_review: "Pending review",
  auto_routed: "Auto-routed",
  in_progress: "In progress",
  resolved: "Resolved",
  closed_no_action: "Closed — duplicate",
};

const STATUS_COLOR: Record<TicketStatus, { fg: string; bg: string }> = {
  pending_review: { fg: "var(--amber)", bg: "var(--amber-tint)" },
  auto_routed: { fg: "var(--slate)", bg: "var(--slate-tint)" },
  in_progress: { fg: "var(--slate)", bg: "var(--slate-tint)" },
  resolved: { fg: "var(--seal)", bg: "var(--seal-tint)" },
  closed_no_action: { fg: "var(--ink-faint)", bg: "var(--paper)" },
};

export function StatusChip({ status }: { status: TicketStatus }) {
  const c = STATUS_COLOR[status];
  return (
    <span
      style={{
        fontSize: 12,
        fontWeight: 500,
        color: c.fg,
        background: c.bg,
        padding: "3px 9px",
        borderRadius: "var(--radius-sm)",
        border: `1px solid ${c.fg}22`,
        whiteSpace: "nowrap",
      }}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

export function ConfidenceMeter({ value, threshold }: { value: number; threshold: number }) {
  const pct = Math.round(value * 100);
  const above = value >= threshold;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 120 }}>
      <div
        style={{
          position: "relative",
          flex: 1,
          height: 6,
          background: "var(--hairline)",
          borderRadius: 3,
          overflow: "visible",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: `${pct}%`,
            background: above ? "var(--seal)" : "var(--amber)",
            borderRadius: 3,
          }}
        />
        <div
          title={`Auto-route threshold: ${Math.round(threshold * 100)}%`}
          style={{
            position: "absolute",
            left: `${threshold * 100}%`,
            top: -2,
            bottom: -2,
            width: 2,
            background: "var(--ink)",
          }}
        />
      </div>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-soft)", width: 32 }}>
        {pct}%
      </span>
    </div>
  );
}

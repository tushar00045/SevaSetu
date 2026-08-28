import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, type Ticket, type Stats } from "./api";
import { UrgencyBar, UrgencyLabel, StatusChip, ConfidenceMeter, timeUntil } from "./components";

const DEPARTMENTS = [
  "Public Works Department (PWD)", "Water Board", "State Electricity Board",
  "Municipal Corporation - Sanitation", "Department of Health & Family Welfare",
  "Department of School Education", "State Transport Corporation", "Police Department",
  "Department of Food & Civil Supplies", "Department of Social Welfare",
  "Revenue Department", "State Pollution Control Board",
];

export default function OfficerDashboard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [t, s] = await Promise.all([
        api.listTickets({
          ...(statusFilter ? { status: statusFilter } : {}),
          ...(deptFilter ? { department: deptFilter } : {}),
        }),
        api.getStats(),
      ]);
      setTickets(t);
      setStats(s);
    } catch (e) {
      setError("Could not reach the SevaSetu backend. Is it running on port 4000?");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, deptFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ maxWidth: 1180, margin: "0 auto", padding: "32px 24px 64px" }}>
      <Header />

      {error && (
        <div style={{ background: "var(--brick-tint)", border: "1px solid var(--brick)", borderRadius: "var(--radius-md)", padding: "12px 16px", marginBottom: 24, color: "var(--brick)", fontSize: 14 }}>
          {error}
        </div>
      )}

      {stats && <StatsBar stats={stats} />}

      <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "28px 0 16px", flexWrap: "wrap" }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 600, margin: 0, marginRight: "auto" }}>
          Grievance queue
        </h2>
        <FilterSelect
          value={statusFilter}
          onChange={setStatusFilter}
          placeholder="All statuses"
          options={[
            ["pending_review", "Pending review"],
            ["auto_routed", "Auto-routed"],
            ["in_progress", "In progress"],
            ["resolved", "Resolved"],
            ["closed_no_action", "Closed — duplicate"],
          ]}
        />
        <FilterSelect
          value={deptFilter}
          onChange={setDeptFilter}
          placeholder="All departments"
          options={DEPARTMENTS.map((d) => [d, d])}
        />
      </div>

      {loading ? (
        <EmptyState text="Loading queue…" />
      ) : tickets.length === 0 ? (
        <EmptyState text="No grievances match these filters." />
      ) : (
        <div style={{ background: "var(--paper-raised)", border: "1px solid var(--hairline)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
          <TicketRowHeader threshold={stats?.config.AUTO_ROUTE_CONFIDENCE_THRESHOLD ?? 0.6} />
          {tickets.map((t) => (
            <TicketRow key={t.id} ticket={t} threshold={stats?.config.AUTO_ROUTE_CONFIDENCE_THRESHOLD ?? 0.6} />
          ))}
        </div>
      )}
    </div>
  );
}

function Header() {
  return (
    <header style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 8, borderBottom: "2px solid var(--ink)", paddingBottom: 16 }}>
      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>
          SevaSetu · Officer Console
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 700, margin: 0 }}>
          Grievance Triage Dashboard
        </h1>
      </div>
      <Link to="/track" style={{ fontSize: 13, color: "var(--seal)", textDecoration: "none", fontWeight: 500 }}>
        Citizen tracker →
      </Link>
    </header>
  );
}

function StatsBar({ stats }: { stats: Stats }) {
  const total = stats.byStatus.reduce((s, x) => s + x.count, 0);
  const pending = stats.byStatus.find((x) => x.status === "pending_review")?.count ?? 0;
  const overdue = stats.overdue.count;

  const cells: Array<{ label: string; value: number; tone?: "amber" | "brick" }> = [
    { label: "Total tickets", value: total },
    { label: "Awaiting officer review", value: pending, tone: pending > 0 ? "amber" : undefined },
    { label: "Past SLA deadline", value: overdue, tone: overdue > 0 ? "brick" : undefined },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, background: "var(--hairline)", border: "1px solid var(--hairline)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
      {cells.map((c) => (
        <div key={c.label} style={{ background: "var(--paper-raised)", padding: "18px 20px" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 30, fontWeight: 600, color: c.tone === "brick" ? "var(--brick)" : c.tone === "amber" ? "var(--amber)" : "var(--ink)" }}>
            {c.value}
          </div>
          <div style={{ fontSize: 12, color: "var(--ink-soft)", marginTop: 2 }}>{c.label}</div>
        </div>
      ))}
    </div>
  );
}

function FilterSelect({ value, onChange, placeholder, options }: { value: string; onChange: (v: string) => void; placeholder: string; options: [string, string][] }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        fontFamily: "var(--font-body)",
        fontSize: 13,
        padding: "7px 10px",
        border: "1px solid var(--hairline-strong)",
        borderRadius: "var(--radius-sm)",
        background: "var(--paper-raised)",
        color: "var(--ink)",
      }}
    >
      <option value="">{placeholder}</option>
      {options.map(([v, l]) => (
        <option key={v} value={v}>{l}</option>
      ))}
    </select>
  );
}

function TicketRowHeader({ threshold }: { threshold: number }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "auto 2.2fr 1.3fr 130px 110px 100px", gap: 16, padding: "10px 20px", borderBottom: "1px solid var(--hairline)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--ink-faint)", fontWeight: 500 }}>
      <span></span>
      <span>Complaint</span>
      <span>Department</span>
      <span title={`Auto-routes above ${Math.round(threshold * 100)}% confidence`}>Confidence</span>
      <span>SLA</span>
      <span>Status</span>
    </div>
  );
}

function TicketRow({ ticket, threshold }: { ticket: Ticket; threshold: number }) {
  const sla = timeUntil(ticket.sla_deadline);
  return (
    <Link
      to={`/ticket/${ticket.id}`}
      style={{
        display: "grid",
        gridTemplateColumns: "auto 2.2fr 1.3fr 130px 110px 100px",
        gap: 16,
        alignItems: "center",
        padding: "14px 20px",
        borderBottom: "1px solid var(--hairline)",
        textDecoration: "none",
        color: "inherit",
      }}
      onMouseOver={(e) => (e.currentTarget.style.background = "var(--paper)")}
      onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
    >
      <UrgencyBar urgency={ticket.urgency} />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 14, color: "var(--ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {ticket.complaint_text}
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-faint)", marginTop: 3 }}>
          {ticket.id} · {ticket.location ?? "no location"}
        </div>
      </div>
      <div style={{ fontSize: 13, color: "var(--ink-soft)" }}>{ticket.department}</div>
      <ConfidenceMeter value={ticket.department_confidence} threshold={threshold} />
      <div>
        <UrgencyLabel urgency={ticket.urgency} />
        <div style={{ fontSize: 11, color: sla.overdue ? "var(--brick)" : "var(--ink-faint)", marginTop: 2 }}>
          {sla.label}
        </div>
      </div>
      <StatusChip status={ticket.status} />
    </Link>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={{ padding: "64px 20px", textAlign: "center", color: "var(--ink-faint)", border: "1px dashed var(--hairline-strong)", borderRadius: "var(--radius-md)", fontSize: 14 }}>
      {text}
    </div>
  );
}

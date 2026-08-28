import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api, ApiError, type TicketDetail, type TicketStatus } from "./api";
import { UrgencyLabel, StatusChip, ConfidenceMeter, timeUntil } from "./components";

const STATUS_OPTIONS: [TicketStatus, string][] = [
  ["in_progress", "Mark in progress"],
  ["resolved", "Mark resolved"],
  ["closed_no_action", "Close — no action needed"],
];

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actor, setActor] = useState("");
  const [note, setNote] = useState("");
  const [pendingStatus, setPendingStatus] = useState<TicketStatus | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const t = await api.getTicket(id);
      setTicket(t);
    } catch {
      setError("Could not load this ticket.");
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function handleSubmit(status: TicketStatus) {
    if (!id) return;
    setSubmitError(null);
    if (!actor.trim()) return setSubmitError("Enter your officer name/ID first.");
    if (note.trim().length < 5) return setSubmitError("Resolution note must be at least 5 characters — this becomes the permanent audit record.");

    setSubmitting(true);
    try {
      await api.updateStatus(id, { status, actor: actor.trim(), note: note.trim() });
      setNote("");
      setPendingStatus(null);
      await load();
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.message : "Failed to update status.");
    } finally {
      setSubmitting(false);
    }
  }

  if (error) return <Shell><p style={{ color: "var(--brick)" }}>{error}</p></Shell>;
  if (!ticket) return <Shell><p style={{ color: "var(--ink-faint)" }}>Loading…</p></Shell>;

  const sla = timeUntil(ticket.sla_deadline);
  const canUpdate = ticket.status !== "resolved" && ticket.status !== "closed_no_action";

  return (
    <Shell>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-faint)" }}>{ticket.id}</div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 24, margin: "4px 0 0" }}>{ticket.department}</h1>
        </div>
        <StatusChip status={ticket.status} />
      </div>

      <Section title="Complaint">
        <p style={{ fontSize: 15, lineHeight: 1.6, margin: 0 }}>{ticket.complaint_text}</p>
        <div style={{ display: "flex", gap: 20, marginTop: 12, fontSize: 13, color: "var(--ink-soft)" }}>
          {ticket.location && <span>📍 {ticket.location}</span>}
          {ticket.citizen_phone && <span>📞 {ticket.citizen_phone}</span>}
        </div>
      </Section>

      {ticket.duplicate_of && (
        <div style={{ background: "var(--amber-tint)", border: "1px solid var(--amber)", borderRadius: "var(--radius-md)", padding: "12px 16px", marginBottom: 20, fontSize: 13, color: "var(--amber)" }}>
          Flagged as a likely duplicate of ticket <Link to={`/ticket/${ticket.duplicate_of}`} style={{ color: "var(--amber)", fontWeight: 600 }}>{ticket.duplicate_of}</Link> — not auto-closed. Confirm or reject below.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
        <Section title="Classification confidence">
          <ConfidenceMeter value={ticket.department_confidence} threshold={0.6} />
          <p style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 8 }}>
            {ticket.route_type === "auto"
              ? "Above threshold — auto-routed without waiting for officer triage."
              : "Below threshold — held for human review rather than auto-closed."}
          </p>
        </Section>
        <Section title="SLA">
          <div style={{ fontSize: 20, fontFamily: "var(--font-display)", color: sla.overdue ? "var(--brick)" : "var(--ink)" }}>
            {sla.label}
          </div>
          <p style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 8 }}>
            Urgency: <UrgencyLabel urgency={ticket.urgency} /> · Deadline {new Date(ticket.sla_deadline).toLocaleDateString()}
          </p>
        </Section>
      </div>

      <Section title="Audit trail">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {ticket.events.map((e, i) => (
            <div key={i} style={{ display: "flex", gap: 12, fontSize: 13 }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-faint)", whiteSpace: "nowrap", paddingTop: 2 }}>
                {new Date(e.created_at).toLocaleString()}
              </div>
              <div>
                <span style={{ fontWeight: 600 }}>{e.actor}</span>{" "}
                <span style={{ color: "var(--ink-soft)" }}>{e.note}</span>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {canUpdate && (
        <Section title="Update status">
          <p style={{ fontSize: 12, color: "var(--ink-faint)", marginBottom: 12 }}>
            A resolution note is required for every status change — no ticket can be closed silently.
          </p>
          <input
            placeholder="Your officer name / ID"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            style={inputStyle}
          />
          <textarea
            placeholder="What was done? (required, min 5 characters)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            style={{ ...inputStyle, marginTop: 8, resize: "vertical" }}
          />
          {submitError && <p style={{ color: "var(--brick)", fontSize: 13, marginTop: 8 }}>{submitError}</p>}
          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            {STATUS_OPTIONS.map(([status, label]) => (
              <button
                key={status}
                disabled={submitting}
                onClick={() => { setPendingStatus(status); handleSubmit(status); }}
                style={{
                  padding: "8px 14px",
                  fontSize: 13,
                  fontWeight: 500,
                  border: "1px solid var(--seal)",
                  borderRadius: "var(--radius-sm)",
                  background: status === "resolved" ? "var(--seal)" : "var(--paper-raised)",
                  color: status === "resolved" ? "white" : "var(--seal)",
                  opacity: submitting && pendingStatus === status ? 0.6 : 1,
                }}
              >
                {submitting && pendingStatus === status ? "Saving…" : label}
              </button>
            ))}
          </div>
        </Section>
      )}
    </Shell>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  fontFamily: "var(--font-body)",
  fontSize: 14,
  padding: "9px 12px",
  border: "1px solid var(--hairline-strong)",
  borderRadius: "var(--radius-sm)",
  background: "var(--paper-raised)",
  color: "var(--ink)",
};

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px 64px" }}>
      <Link to="/" style={{ fontSize: 13, color: "var(--seal)", textDecoration: "none", fontWeight: 500 }}>
        ← Back to queue
      </Link>
      <div style={{ marginTop: 20 }}>{children}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--paper-raised)", border: "1px solid var(--hairline)", borderRadius: "var(--radius-md)", padding: "18px 20px", marginBottom: 16 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--ink-faint)", fontWeight: 500, marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

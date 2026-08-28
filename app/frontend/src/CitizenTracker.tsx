import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";

const STATUS_MESSAGE: Record<string, { title: string; body: string; tone: "seal" | "amber" | "slate" }> = {
  pending_review: { title: "Being reviewed by an officer", body: "Your complaint needs a closer look before it's assigned. An officer will route it shortly.", tone: "amber" },
  auto_routed: { title: "Sent to the right department", body: "Your complaint has been assigned and is being tracked against a response deadline.", tone: "slate" },
  in_progress: { title: "Work has started", body: "An officer has picked this up and is working on it.", tone: "slate" },
  resolved: { title: "Resolved", body: "This complaint has been marked resolved by the department.", tone: "seal" },
  closed_no_action: { title: "Closed as a duplicate", body: "This looked like a repeat of a complaint already being handled. If that's wrong, please submit again with more detail.", tone: "slate" },
};

export default function CitizenTracker() {
  const [mode, setMode] = useState<"submit" | "check">("submit");
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "40px 24px 64px" }}>
      <header style={{ marginBottom: 32 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 6 }}>
          SevaSetu
        </div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 30, fontWeight: 700, margin: 0 }}>
          File or track a complaint
        </h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 14, marginTop: 8 }}>
          Apni shikayat darj karein ya status check karein — kisi bhi language mein likh sakte hain.
        </p>
      </header>

      <div style={{ display: "flex", gap: 4, marginBottom: 24, borderBottom: "1px solid var(--hairline)" }}>
        <TabButton active={mode === "submit"} onClick={() => setMode("submit")}>File a complaint</TabButton>
        <TabButton active={mode === "check"} onClick={() => setMode("check")}>Check status</TabButton>
      </div>

      {mode === "submit" ? <SubmitForm /> : <StatusCheck />}

      <div style={{ marginTop: 40, textAlign: "center" }}>
        <Link to="/" style={{ fontSize: 12, color: "var(--ink-faint)", textDecoration: "none" }}>
          Officer console →
        </Link>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "10px 4px",
        marginRight: 24,
        background: "none",
        border: "none",
        borderBottom: active ? "2px solid var(--seal)" : "2px solid transparent",
        color: active ? "var(--ink)" : "var(--ink-faint)",
        fontSize: 14,
        fontWeight: active ? 600 : 400,
      }}
    >
      {children}
    </button>
  );
}

function SubmitForm() {
  const [text, setText] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ ticketId: string; department: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.submitComplaint({
        text,
        phone: phone.trim() || undefined,
        location: location.trim() || undefined,
      });
      setResult({ ticketId: res.ticketId, department: res.department });
    } catch (e) {
      setError(e instanceof ApiError ? formatApiError(e) : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div style={{ background: "var(--seal-tint)", border: "1px solid var(--seal)", borderRadius: "var(--radius-md)", padding: "24px" }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "var(--seal-dark)", marginBottom: 6 }}>
          Complaint filed
        </div>
        <p style={{ fontSize: 14, color: "var(--ink)", margin: "0 0 12px" }}>
          Sent to <strong>{result.department}</strong>. Save your ticket number to check status later:
        </p>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 600, background: "var(--paper-raised)", padding: "10px 14px", borderRadius: "var(--radius-sm)", display: "inline-block" }}>
          {result.ticketId}
        </div>
        <div style={{ marginTop: 16 }}>
          <button onClick={() => setResult(null)} style={{ fontSize: 13, color: "var(--seal)", background: "none", border: "none", padding: 0, fontWeight: 500 }}>
            File another complaint
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <label style={labelStyle}>What's the problem?</label>
      <textarea
        required
        minLength={10}
        rows={4}
        placeholder="Describe your complaint in your own words — e.g. Hamare area mein 3 din se paani nahi aa raha hai"
        value={text}
        onChange={(e) => setText(e.target.value)}
        style={{ ...inputStyle, resize: "vertical" }}
      />

      <label style={labelStyle}>Location</label>
      <input placeholder="Area, city" value={location} onChange={(e) => setLocation(e.target.value)} style={inputStyle} />

      <label style={labelStyle}>Phone number (optional)</label>
      <input placeholder="10-digit number" value={phone} onChange={(e) => setPhone(e.target.value)} style={inputStyle} />

      {error && <p style={{ color: "var(--brick)", fontSize: 13, marginTop: 8 }}>{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        style={{
          marginTop: 16,
          width: "100%",
          padding: "12px",
          fontSize: 14,
          fontWeight: 600,
          color: "white",
          background: "var(--seal)",
          border: "none",
          borderRadius: "var(--radius-sm)",
          opacity: submitting ? 0.7 : 1,
        }}
      >
        {submitting ? "Submitting…" : "Submit complaint"}
      </button>
    </form>
  );
}

function formatApiError(e: ApiError): string {
  const fieldErrors = e.body?.error?.fieldErrors;
  if (fieldErrors) {
    const first = Object.values(fieldErrors).flat()[0];
    if (typeof first === "string") return first;
  }
  return e.message;
}

function StatusCheck() {
  const [ticketId, setTicketId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ticket, setTicket] = useState<Awaited<ReturnType<typeof api.getTicket>> | null>(null);

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setTicket(null);
    try {
      const t = await api.getTicket(ticketId.trim());
      setTicket(t);
    } catch {
      setError("No complaint found with that ticket number. Double-check and try again.");
    } finally {
      setLoading(false);
    }
  }

  const status = ticket ? STATUS_MESSAGE[ticket.status] : null;

  return (
    <div>
      <form onSubmit={handleCheck} style={{ display: "flex", gap: 8 }}>
        <input
          required
          placeholder="Enter your ticket number"
          value={ticketId}
          onChange={(e) => setTicketId(e.target.value)}
          style={{ ...inputStyle, flex: 1 }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ padding: "0 20px", background: "var(--seal)", color: "white", border: "none", borderRadius: "var(--radius-sm)", fontWeight: 600, fontSize: 14 }}
        >
          {loading ? "…" : "Check"}
        </button>
      </form>

      {error && <p style={{ color: "var(--brick)", fontSize: 13, marginTop: 12 }}>{error}</p>}

      {ticket && status && (
        <div style={{ marginTop: 20, background: "var(--paper-raised)", border: "1px solid var(--hairline)", borderRadius: "var(--radius-md)", padding: 20 }}>
          <div style={{ fontSize: 13, color: "var(--ink-faint)", marginBottom: 4 }}>{ticket.department}</div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
            {status.title}
          </div>
          <p style={{ fontSize: 14, color: "var(--ink-soft)", margin: 0 }}>{status.body}</p>
          <p style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 12 }}>
            Filed {new Date(ticket.created_at).toLocaleDateString()}
          </p>
        </div>
      )}
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 500,
  color: "var(--ink-soft)",
  marginTop: 16,
  marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  fontFamily: "var(--font-body)",
  fontSize: 14,
  padding: "10px 12px",
  border: "1px solid var(--hairline-strong)",
  borderRadius: "var(--radius-sm)",
  background: "var(--paper-raised)",
  color: "var(--ink)",
};

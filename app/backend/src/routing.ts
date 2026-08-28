import { nanoid } from "nanoid";
import db from "./db.js";
import { findDuplicate } from "./duplicates.js";
import type { Classifier } from "./classifier.js";

// Below this department-classification confidence, a ticket goes to human
// review instead of being auto-routed. This is the direct fix for the
// Parliamentary Standing Committee's "resolved without action" finding:
// low-confidence tickets are never silently auto-closed, only auto-ROUTED
// tickets get an SLA clock, review tickets wait for a human decision.
const AUTO_ROUTE_CONFIDENCE_THRESHOLD = 0.6;

// SLA windows by urgency, in hours. Matches the "21-day standard SLA, faster
// for urgent cases" framing used in the pitch deck.
const SLA_HOURS: Record<"low" | "medium" | "high", number> = {
  high: 24,
  medium: 24 * 5,
  low: 24 * 15,
};

export interface IngestResult {
  ticketId: string;
  status: string;
  routeType: "auto" | "human_review";
  department: string;
  departmentConfidence: number;
  urgency: string;
  slaDeadline: string;
  duplicateOf: string | null;
}

export async function ingestComplaint(
  classifier: Classifier,
  input: { text: string; phone?: string; location?: string }
): Promise<IngestResult> {
  const classification = await classifier.classify(input.text);
  const duplicate = findDuplicate(input.text, classification.department);

  const id = nanoid(10);
  const now = new Date();
  const slaHours = SLA_HOURS[classification.urgency];
  const slaDeadline = new Date(now.getTime() + slaHours * 3600 * 1000).toISOString();

  const isAutoRoutable = classification.departmentConfidence >= AUTO_ROUTE_CONFIDENCE_THRESHOLD && !duplicate;
  const routeType: "auto" | "human_review" = isAutoRoutable ? "auto" : "human_review";
  const status = duplicate ? "closed_no_action" : isAutoRoutable ? "auto_routed" : "pending_review";

  db.prepare(
    `INSERT INTO tickets
      (id, complaint_text, citizen_phone, location, department, department_confidence,
       urgency, urgency_confidence, status, route_type, duplicate_of, sla_deadline)
     VALUES (@id, @text, @phone, @location, @department, @departmentConfidence,
             @urgency, @urgencyConfidence, @status, @routeType, @duplicateOf, @slaDeadline)`
  ).run({
    id,
    text: input.text,
    phone: input.phone ?? null,
    location: input.location ?? null,
    department: classification.department,
    departmentConfidence: classification.departmentConfidence,
    urgency: classification.urgency,
    urgencyConfidence: classification.urgencyConfidence,
    status,
    routeType,
    duplicateOf: duplicate?.ticketId ?? null,
    slaDeadline,
  });

  logEvent(id, duplicate ? "sent_to_review" : isAutoRoutable ? "auto_routed" : "sent_to_review", "system",
    duplicate
      ? `Flagged as likely duplicate of ${duplicate.ticketId} (similarity ${duplicate.similarity.toFixed(2)}) — not auto-closed, held for officer confirmation.`
      : isAutoRoutable
      ? `Auto-routed to ${classification.department} (confidence ${classification.departmentConfidence.toFixed(2)})`
      : `Below auto-route confidence threshold (${classification.departmentConfidence.toFixed(2)} < ${AUTO_ROUTE_CONFIDENCE_THRESHOLD}) — sent to human review, not auto-closed.`
  );

  return {
    ticketId: id,
    status,
    routeType,
    department: classification.department,
    departmentConfidence: classification.departmentConfidence,
    urgency: classification.urgency,
    slaDeadline,
    duplicateOf: duplicate?.ticketId ?? null,
  };
}

export function logEvent(ticketId: string, eventType: string, actor: string, note?: string) {
  db.prepare(
    `INSERT INTO ticket_events (ticket_id, event_type, actor, note) VALUES (?, ?, ?, ?)`
  ).run(ticketId, eventType, actor, note ?? null);
}

export function updateTicketStatus(ticketId: string, status: string, actor: string, note: string) {
  // Mandatory resolution note on every status change — this is what makes a
  // closure auditable instead of a silent "resolved without action".
  if (!note || note.trim().length < 5) {
    throw new Error("A resolution note (min 5 characters) is required to change ticket status.");
  }
  db.prepare(`UPDATE tickets SET status = ?, updated_at = datetime('now') WHERE id = ?`).run(status, ticketId);
  logEvent(ticketId, "status_changed", actor, `Status -> ${status}: ${note}`);
}

export const config = { AUTO_ROUTE_CONFIDENCE_THRESHOLD, SLA_HOURS };

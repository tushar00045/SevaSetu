import express from "express";
import cors from "cors";
import { z } from "zod";
import db from "./db.js";
import { RemoteClassifier } from "./classifier.js";

const classifier = new RemoteClassifier(process.env.CLASSIFIER_URL ?? "http://localhost:8000");
import { ingestComplaint, updateTicketStatus, config } from "./routing.js";

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT ? Number(process.env.PORT) : 4000;

// ---------------------------------------------------------------------------
// POST /api/complaints — citizen submits a grievance
// ---------------------------------------------------------------------------

const ComplaintInput = z.object({
  text: z.string().min(10, "Complaint text must be at least 10 characters.").max(2000),
  phone: z.string().regex(/^\d{10}$/, "Phone must be a 10-digit number.").optional(),
  location: z.string().max(200).optional(),
});

app.post("/api/complaints", async (req, res) => {
  const parsed = ComplaintInput.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }
  try {
    const result = await ingestComplaint(classifier, parsed.data);
    res.status(201).json(result);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to process complaint." });
  }
});

// ---------------------------------------------------------------------------
// GET /api/tickets — officer dashboard queue, filterable
// ---------------------------------------------------------------------------

app.get("/api/tickets", (req, res) => {
  const { status, department, urgency } = req.query;

  let query = "SELECT * FROM tickets WHERE 1=1";
  const params: unknown[] = [];

  if (status) { query += " AND status = ?"; params.push(status); }
  if (department) { query += " AND department = ?"; params.push(department); }
  if (urgency) { query += " AND urgency = ?"; params.push(urgency); }

  // Urgency-sorted queue: high first, then by how close the SLA deadline is.
  query += ` ORDER BY
    CASE urgency WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
    sla_deadline ASC`;

  const tickets = db.prepare(query).all(...params);
  res.json(tickets);
});

// ---------------------------------------------------------------------------
// GET /api/tickets/:id — full ticket detail + audit trail (for officer view
// and for the citizen tracker, without exposing other citizens' data)
// ---------------------------------------------------------------------------

app.get("/api/tickets/:id", (req, res) => {
  const ticket = db.prepare("SELECT * FROM tickets WHERE id = ?").get(req.params.id);
  if (!ticket) return res.status(404).json({ error: "Ticket not found." });

  const events = db
    .prepare("SELECT event_type, actor, note, created_at FROM ticket_events WHERE ticket_id = ? ORDER BY created_at ASC")
    .all(req.params.id);

  res.json({ ...ticket, events });
});

// ---------------------------------------------------------------------------
// PATCH /api/tickets/:id/status — officer changes status; note is mandatory
// ---------------------------------------------------------------------------

const StatusUpdate = z.object({
  status: z.enum(["in_progress", "resolved", "closed_no_action", "auto_routed", "pending_review"]),
  actor: z.string().min(1, "Officer name/id is required."),
  note: z.string().min(5, "A resolution note of at least 5 characters is required."),
});

app.patch("/api/tickets/:id/status", (req, res) => {
  const parsed = StatusUpdate.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }
  const ticket = db.prepare("SELECT id FROM tickets WHERE id = ?").get(req.params.id);
  if (!ticket) return res.status(404).json({ error: "Ticket not found." });

  try {
    updateTicketStatus(req.params.id, parsed.data.status, parsed.data.actor, parsed.data.note);
    res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ error: (err as Error).message });
  }
});

// ---------------------------------------------------------------------------
// GET /api/stats — dashboard summary counts
// ---------------------------------------------------------------------------

app.get("/api/stats", (_req, res) => {
  const byStatus = db.prepare("SELECT status, COUNT(*) as count FROM tickets GROUP BY status").all();
  const byDepartment = db.prepare("SELECT department, COUNT(*) as count FROM tickets GROUP BY department").all();
  const byUrgency = db.prepare("SELECT urgency, COUNT(*) as count FROM tickets GROUP BY urgency").all();
  const overdue = db
    .prepare("SELECT COUNT(*) as count FROM tickets WHERE sla_deadline < datetime('now') AND status NOT IN ('resolved', 'closed_no_action')")
    .get();

  res.json({ byStatus, byDepartment, byUrgency, overdue, config });
});

app.get("/api/health", (_req, res) => res.json({ ok: true }));

app.listen(PORT, () => {
  console.log(`SevaSetu backend running on http://localhost:${PORT}`);
});

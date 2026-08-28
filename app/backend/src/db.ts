import Database from "better-sqlite3";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, "..", "sevasetu.db");

export const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");
db.pragma("foreign_keys = ON");

db.exec(`
CREATE TABLE IF NOT EXISTS tickets (
  id TEXT PRIMARY KEY,
  complaint_text TEXT NOT NULL,
  citizen_phone TEXT,
  location TEXT,
  department TEXT NOT NULL,
  department_confidence REAL NOT NULL,
  urgency TEXT NOT NULL,
  urgency_confidence REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending_review', -- pending_review | auto_routed | in_progress | resolved | closed_no_action
  route_type TEXT NOT NULL, -- 'auto' | 'human_review'
  duplicate_of TEXT,        -- ticket id this was flagged as a near-duplicate of, if any
  sla_deadline TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (duplicate_of) REFERENCES tickets(id)
);

CREATE TABLE IF NOT EXISTS ticket_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id TEXT NOT NULL,
  event_type TEXT NOT NULL, -- 'created' | 'auto_routed' | 'sent_to_review' | 'reviewed' | 'status_changed' | 'resolution_note'
  actor TEXT,               -- officer name/id, or 'system'
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_department ON tickets(department);
CREATE INDEX IF NOT EXISTS idx_tickets_urgency ON tickets(urgency);
CREATE INDEX IF NOT EXISTS idx_events_ticket ON ticket_events(ticket_id);
`);

export default db;

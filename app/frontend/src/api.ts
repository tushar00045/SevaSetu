const API_BASE = "http://localhost:4000/api";

export type Urgency = "low" | "medium" | "high";
export type TicketStatus =
  | "pending_review"
  | "auto_routed"
  | "in_progress"
  | "resolved"
  | "closed_no_action";

export interface Ticket {
  id: string;
  complaint_text: string;
  citizen_phone: string | null;
  location: string | null;
  department: string;
  department_confidence: number;
  urgency: Urgency;
  urgency_confidence: number;
  status: TicketStatus;
  route_type: "auto" | "human_review";
  duplicate_of: string | null;
  sla_deadline: string;
  created_at: string;
  updated_at: string;
}

export interface TicketEvent {
  event_type: string;
  actor: string;
  note: string | null;
  created_at: string;
}

export interface TicketDetail extends Ticket {
  events: TicketEvent[];
}

export interface Stats {
  byStatus: Array<{ status: string; count: number }>;
  byDepartment: Array<{ department: string; count: number }>;
  byUrgency: Array<{ urgency: string; count: number }>;
  overdue: { count: number };
  config: {
    AUTO_ROUTE_CONFIDENCE_THRESHOLD: number;
    SLA_HOURS: Record<Urgency, number>;
  };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body);
  }
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, public body: any) {
    super(typeof body?.error === "string" ? body.error : "Request failed");
  }
}

export const api = {
  listTickets: (filters?: { status?: string; department?: string; urgency?: string }) => {
    const params = new URLSearchParams(filters as Record<string, string>);
    return request<Ticket[]>(`/tickets?${params}`);
  },
  getTicket: (id: string) => request<TicketDetail>(`/tickets/${id}`),
  submitComplaint: (data: { text: string; phone?: string; location?: string }) =>
    request<{ ticketId: string; status: string; department: string; departmentConfidence: number; routeType: string; slaDeadline: string; duplicateOf: string | null }>(
      "/complaints",
      { method: "POST", body: JSON.stringify(data) }
    ),
  updateStatus: (id: string, data: { status: TicketStatus; actor: string; note: string }) =>
    request<{ ok: true }>(`/tickets/${id}/status`, { method: "PATCH", body: JSON.stringify(data) }),
  getStats: () => request<Stats>("/stats"),
};

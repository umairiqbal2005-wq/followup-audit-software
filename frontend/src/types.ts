export type UserRole = "ADMIN" | "CENTRAL_TEAM" | "PROCESS_OWNER" | "AUDITOR" | "VIEWER";
export type ObservationStatus =
  | "DRAFT"
  | "PENDING_REVIEW"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "PENDING_VERIFICATION"
  | "CLOSED"
  | "REJECTED";
export type ObservationSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type ResponseType = "RESOLVED" | "NEED_MORE_TIME" | "COMMITTED_TIMELINE";

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  department?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuditReport {
  id: number;
  title: string;
  report_number: string;
  description?: string | null;
  file_name?: string | null;
  uploaded_by_id: number;
  audit_date?: string | null;
  created_at: string;
  observation_count: number;
}

export interface Observation {
  id: number;
  report_id: number;
  observation_number: string;
  title: string;
  description: string;
  category?: string | null;
  severity: ObservationSeverity;
  status: ObservationStatus;
  recommendation?: string | null;
  owner_id?: number | null;
  assigned_by_id?: number | null;
  due_date?: string | null;
  closed_at?: string | null;
  created_by_id: number;
  created_at: string;
  updated_at: string;
  owner_name?: string | null;
  report_title?: string | null;
}

export interface ObservationDetail extends Observation {
  responses: Array<{
    id: number;
    observation_id: number;
    responder_id: number;
    response_type: string;
    comments: string;
    committed_date?: string | null;
    evidence_file?: string | null;
    created_at: string;
  }>;
  history: Array<{
    id: number;
    action: string;
    from_status?: string | null;
    to_status?: string | null;
    notes?: string | null;
    actor_id: number;
    created_at: string;
  }>;
}

export interface DashboardStats {
  total: number;
  draft: number;
  pending_review: number;
  assigned: number;
  in_progress: number;
  pending_verification: number;
  closed: number;
  rejected: number;
  by_severity: Record<string, number>;
  overdue: number;
}

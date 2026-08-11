import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { ObservationDetail, ResponseType, User } from "../types";

export function ObservationDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [obs, setObs] = useState<ObservationDetail | null>(null);
  const [owners, setOwners] = useState<User[]>([]);
  const [ownerId, setOwnerId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [responseType, setResponseType] = useState<ResponseType>("RESOLVED");
  const [comments, setComments] = useState("");
  const [committedDate, setCommittedDate] = useState("");
  const [verifyNotes, setVerifyNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!id) return;
    const detail = await api.observation(Number(id));
    setObs(detail);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
    if (user?.role === "ADMIN" || user?.role === "CENTRAL_TEAM") {
      api.users({ role: "PROCESS_OWNER" }).then(setOwners).catch(() => undefined);
    }
  }, [id, user?.role]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!obs) {
    return error ? <div className="error">{error}</div> : <div className="empty">Loading observation…</div>;
  }

  const canSubmit =
    obs.status === "DRAFT" &&
    user &&
    ["ADMIN", "CENTRAL_TEAM", "AUDITOR"].includes(user.role);
  const canAssign =
    obs.status === "PENDING_REVIEW" &&
    user &&
    ["ADMIN", "CENTRAL_TEAM"].includes(user.role);
  const canRespond =
    ["ASSIGNED", "IN_PROGRESS"].includes(obs.status) &&
    user &&
    (user.role === "ADMIN" || (user.role === "PROCESS_OWNER" && obs.owner_id === user.id));
  const canVerify =
    obs.status === "PENDING_VERIFICATION" &&
    user &&
    ["ADMIN", "CENTRAL_TEAM"].includes(user.role);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{obs.observation_number}</h1>
          <p>{obs.title}</p>
        </div>
        <button className="btn secondary" onClick={() => navigate("/observations")}>
          Back
        </button>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="detail-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>Details</h2>
            <span className={`badge ${obs.status}`}>{obs.status.replaceAll("_", " ")}</span>
          </div>
          <div className="meta-list">
            <div>
              <span>Description</span>
              <strong>{obs.description}</strong>
            </div>
            <div>
              <span>Recommendation</span>
              <strong>{obs.recommendation || "—"}</strong>
            </div>
            <div>
              <span>Category / Severity</span>
              <strong>
                {obs.category || "Uncategorized"} · <span className={`badge ${obs.severity}`}>{obs.severity}</span>
              </strong>
            </div>
            <div>
              <span>Report</span>
              <strong>
                <Link to="/reports">{obs.report_title || `Report #${obs.report_id}`}</Link>
              </strong>
            </div>
          </div>

          <div className="form-grid" style={{ borderTop: "1px solid var(--line)" }}>
            {canSubmit && (
              <button className="btn" disabled={busy} onClick={() => run(() => api.submitObservation(obs.id))}>
                Submit for central review
              </button>
            )}

            {canAssign && (
              <form
                className="form-grid"
                style={{ padding: 0 }}
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  run(() =>
                    api.assignObservation(obs.id, {
                      owner_id: Number(ownerId),
                      due_date: dueDate ? new Date(dueDate).toISOString() : null,
                      notes: "Assigned via UI",
                    }),
                  );
                }}
              >
                <label>
                  Process owner
                  <select value={ownerId} onChange={(e) => setOwnerId(e.target.value)} required>
                    <option value="">Select owner</option>
                    {owners.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Due date
                  <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
                </label>
                <button className="btn" disabled={busy || !ownerId}>
                  Assign owner
                </button>
              </form>
            )}

            {canRespond && (
              <form
                className="form-grid"
                style={{ padding: 0 }}
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  run(() =>
                    api.respondObservation(obs.id, {
                      response_type: responseType,
                      comments,
                      committed_date: committedDate ? new Date(committedDate).toISOString() : null,
                    }),
                  );
                }}
              >
                <label>
                  Response
                  <select value={responseType} onChange={(e) => setResponseType(e.target.value as ResponseType)}>
                    <option value="RESOLVED">Resolved</option>
                    <option value="NEED_MORE_TIME">Need more time</option>
                    <option value="COMMITTED_TIMELINE">Committed timeline</option>
                  </select>
                </label>
                <label>
                  Comments
                  <textarea value={comments} onChange={(e) => setComments(e.target.value)} required />
                </label>
                {responseType !== "RESOLVED" && (
                  <label>
                    Committed date
                    <input
                      type="date"
                      value={committedDate}
                      onChange={(e) => setCommittedDate(e.target.value)}
                      required
                    />
                  </label>
                )}
                <button className="btn" disabled={busy}>
                  Submit response
                </button>
              </form>
            )}

            {canVerify && (
              <div className="form-grid" style={{ padding: 0 }}>
                <label>
                  Verification notes
                  <textarea value={verifyNotes} onChange={(e) => setVerifyNotes(e.target.value)} />
                </label>
                <div className="actions">
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() => run(() => api.verifyObservation(obs.id, { approved: true, notes: verifyNotes }))}
                  >
                    Approve & close
                  </button>
                  <button
                    className="btn danger"
                    disabled={busy}
                    onClick={() =>
                      run(() => api.verifyObservation(obs.id, { approved: false, notes: verifyNotes || "Returned" }))
                    }
                  >
                    Return to owner
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>History</h2>
          </div>
          <ul className="timeline">
            {obs.history
              .slice()
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((h) => (
                <li key={h.id}>
                  <strong>{h.action.replaceAll("_", " ")}</strong>
                  <div>
                    {h.from_status || "—"} → {h.to_status || "—"}
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                    {new Date(h.created_at).toLocaleString()}
                    {h.notes ? ` · ${h.notes}` : ""}
                  </div>
                </li>
              ))}
          </ul>
          <div className="panel-head" style={{ borderTop: "1px solid var(--line)" }}>
            <h2>Responses</h2>
          </div>
          {obs.responses.length === 0 ? (
            <div className="empty">No owner responses yet.</div>
          ) : (
            <ul className="timeline">
              {obs.responses.map((r) => (
                <li key={r.id}>
                  <strong>{r.response_type.replaceAll("_", " ")}</strong>
                  <div>{r.comments}</div>
                  <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
                    {new Date(r.created_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

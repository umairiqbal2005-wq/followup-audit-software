import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Observation } from "../types";

export function ObservationsPage() {
  const [rows, setRows] = useState<Observation[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params: Record<string, string> = { limit: "100" };
    if (status) params.status = status;
    api
      .observations(params)
      .then(setRows)
      .catch((err) => setError(err.message));
  }, [status]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Observations</h1>
          <p>Filter and manage the follow-up workflow.</p>
        </div>
        <Link className="btn" to="/observations/new">
          New observation
        </Link>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <div className="panel-head">
          <h2>All observations</h2>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {[
              "DRAFT",
              "PENDING_REVIEW",
              "ASSIGNED",
              "IN_PROGRESS",
              "PENDING_VERIFICATION",
              "CLOSED",
              "REJECTED",
            ].map((s) => (
              <option key={s} value={s}>
                {s.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </div>
        {rows.length === 0 ? (
          <div className="empty">No observations match this filter.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Title</th>
                <th>Report</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link to={`/observations/${o.id}`}>{o.observation_number}</Link>
                  </td>
                  <td>{o.title}</td>
                  <td>{o.report_title || o.report_id}</td>
                  <td>
                    <span className={`badge ${o.severity}`}>{o.severity}</span>
                  </td>
                  <td>
                    <span className={`badge ${o.status}`}>{o.status.replaceAll("_", " ")}</span>
                  </td>
                  <td>{o.due_date ? new Date(o.due_date).toLocaleDateString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

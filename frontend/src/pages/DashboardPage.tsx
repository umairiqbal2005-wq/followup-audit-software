import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { DashboardStats, Observation } from "../types";

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<Observation[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.dashboard(), api.observations({ limit: "8" })])
      .then(([dash, obs]) => {
        setStats(dash);
        setRecent(obs);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Observation pipeline across review, ownership, and verification.</p>
        </div>
        <Link className="btn" to="/observations/new">
          New observation
        </Link>
      </div>

      {error && <div className="error">{error}</div>}

      {stats && (
        <div className="stats">
          <div className="stat">
            <div className="label">Open pipeline</div>
            <div className="value">{stats.total - stats.closed - stats.rejected}</div>
          </div>
          <div className="stat">
            <div className="label">Pending review</div>
            <div className="value">{stats.pending_review}</div>
          </div>
          <div className="stat">
            <div className="label">Awaiting verify</div>
            <div className="value">{stats.pending_verification}</div>
          </div>
          <div className="stat">
            <div className="label">Overdue</div>
            <div className="value">{stats.overdue}</div>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-head">
          <h2>Recent observations</h2>
          <Link to="/observations">View all</Link>
        </div>
        {recent.length === 0 ? (
          <div className="empty">No observations yet. Upload a report and create the first item.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Title</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Owner</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link to={`/observations/${o.id}`}>{o.observation_number}</Link>
                  </td>
                  <td>{o.title}</td>
                  <td>
                    <span className={`badge ${o.severity}`}>{o.severity}</span>
                  </td>
                  <td>
                    <span className={`badge ${o.status}`}>{o.status.replaceAll("_", " ")}</span>
                  </td>
                  <td>{o.owner_name || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

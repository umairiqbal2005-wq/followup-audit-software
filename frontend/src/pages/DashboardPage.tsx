import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { DashboardStats, Observation } from "../types";

const pipelineStages: Array<{ key: keyof DashboardStats; label: string }> = [
  { key: "draft", label: "Draft" },
  { key: "pending_review", label: "Pending review" },
  { key: "assigned", label: "Assigned" },
  { key: "in_progress", label: "In progress" },
  { key: "pending_verification", label: "Verification" },
  { key: "closed", label: "Closed" },
];

function formatStatus(status: string) {
  return status.replaceAll("_", " ");
}

export function DashboardPage() {
  const { user } = useAuth();
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

  const openCount = stats ? stats.total - stats.closed - stats.rejected : 0;
  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="dashboard">
      <div className="page-header dashboard-header">
        <div>
          <p className="page-kicker">Operations overview</p>
          <h1>Dashboard</h1>
          <p>
            Welcome{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}. Track the audit
            observation pipeline from review through closure.
          </p>
          <p className="dashboard-date">{today}</p>
        </div>
        <div className="dashboard-header-actions">
          <Link className="btn secondary" to="/reports">
            Upload report
          </Link>
          <Link className="btn" to="/observations/new">
            New observation
          </Link>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {stats && (
        <>
          <div className="stats dashboard-stats">
            <div className="stat accent-open">
              <div className="label">Open pipeline</div>
              <div className="value">{openCount}</div>
              <div className="stat-note">Active items across all stages</div>
            </div>
            <div className="stat accent-review">
              <div className="label">Pending review</div>
              <div className="value">{stats.pending_review}</div>
              <div className="stat-note">Awaiting central team action</div>
            </div>
            <div className="stat accent-verify">
              <div className="label">Awaiting verification</div>
              <div className="value">{stats.pending_verification}</div>
              <div className="stat-note">Owner marked resolved</div>
            </div>
            <div className="stat accent-overdue">
              <div className="label">Overdue</div>
              <div className="value">{stats.overdue}</div>
              <div className="stat-note">Past committed due date</div>
            </div>
          </div>

          <div className="dashboard-secondary">
            <div className="panel">
              <div className="panel-head">
                <h2>Workflow stages</h2>
                <span className="panel-meta">{stats.total} total</span>
              </div>
              <div className="stage-list">
                {pipelineStages.map((stage) => {
                  const count = Number(stats[stage.key] ?? 0);
                  const pct = stats.total ? Math.round((count / stats.total) * 100) : 0;
                  return (
                    <div className="stage-row" key={stage.key}>
                      <div className="stage-row-top">
                        <span>{stage.label}</span>
                        <strong>{count}</strong>
                      </div>
                      <div className="stage-bar" aria-hidden="true">
                        <span style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h2>Severity mix</h2>
                <span className="panel-meta">Open portfolio risk</span>
              </div>
              <div className="severity-grid">
                {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((level) => (
                  <div className={`severity-tile ${level}`} key={level}>
                    <span className="label">{level}</span>
                    <strong>{stats.by_severity[level] ?? 0}</strong>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      <div className="panel">
        <div className="panel-head">
          <h2>Recent observations</h2>
          <Link className="panel-link" to="/observations">
            View all
          </Link>
        </div>
        {recent.length === 0 ? (
          <div className="empty">No observations yet. Upload a report and create the first item.</div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
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
                      <Link className="table-link" to={`/observations/${o.id}`}>
                        {o.observation_number}
                      </Link>
                    </td>
                    <td>
                      <div className="table-title">{o.title}</div>
                      {o.report_title && <div className="table-sub">{o.report_title}</div>}
                    </td>
                    <td>
                      <span className={`badge ${o.severity}`}>{o.severity}</span>
                    </td>
                    <td>
                      <span className={`badge ${o.status}`}>{formatStatus(o.status)}</span>
                    </td>
                    <td>{o.owner_name || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

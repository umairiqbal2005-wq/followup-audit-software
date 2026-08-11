import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Observation, Region, AuditSegment } from "../types";
import { REGION_LABELS, SEGMENT_LABELS } from "../types";

export function ObservationsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Observation[]>([]);
  const [status, setStatus] = useState("");
  const [region, setRegion] = useState("");
  const [segment, setSegment] = useState("");
  const [error, setError] = useState("");

  const regionOptions =
    user?.role === "ADMIN" || !user?.regions?.length ? (["NORTH", "SOUTH", "CENTRAL"] as Region[]) : user.regions;
  const segmentOptions =
    user?.role === "ADMIN" || !user?.segments?.length
      ? (["BRANCH_AUDIT", "SHARIAH", "MANAGEMENT", "OTHER"] as AuditSegment[])
      : user.segments;

  useEffect(() => {
    const params: Record<string, string> = { limit: "100" };
    if (status) params.status = status;
    if (region) params.region = region;
    if (segment) params.segment = segment;
    api
      .observations(params)
      .then(setRows)
      .catch((err) => setError(err.message));
  }, [status, region, segment]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Observations</h1>
          <p>Scoped to your assigned regions and segments.</p>
        </div>
        <Link className="btn" to="/observations/new">
          New observation
        </Link>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <div className="panel-head">
          <h2>All observations</h2>
          <div className="filter-bar">
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="">All regions</option>
              {regionOptions.map((r) => (
                <option key={r} value={r}>
                  {REGION_LABELS[r]}
                </option>
              ))}
            </select>
            <select value={segment} onChange={(e) => setSegment(e.target.value)}>
              <option value="">All segments</option>
              {segmentOptions.map((s) => (
                <option key={s} value={s}>
                  {SEGMENT_LABELS[s]}
                </option>
              ))}
            </select>
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
        </div>
        {rows.length === 0 ? (
          <div className="empty">No observations match this filter.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Number</th>
                <th>Title</th>
                <th>Region</th>
                <th>Segment</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link className="table-link" to={`/observations/${o.id}`}>
                      {o.observation_number}
                    </Link>
                  </td>
                  <td>
                    <div className="table-title">{o.title}</div>
                    <div className="table-sub">{o.report_title || `Report #${o.report_id}`}</div>
                  </td>
                  <td>{REGION_LABELS[o.region]}</td>
                  <td>{SEGMENT_LABELS[o.segment]}</td>
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

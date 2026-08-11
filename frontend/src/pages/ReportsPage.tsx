import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { AuditReport, AuditSegment, Region } from "../types";
import { REGION_LABELS, SEGMENT_LABELS } from "../types";

export function ReportsPage() {
  const { user } = useAuth();
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [title, setTitle] = useState("");
  const [reportNumber, setReportNumber] = useState("");
  const [description, setDescription] = useState("");
  const [region, setRegion] = useState<Region>("CENTRAL");
  const [segment, setSegment] = useState<AuditSegment>("BRANCH_AUDIT");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const regionOptions: Region[] =
    user?.role === "ADMIN" || !user?.regions?.length
      ? (["NORTH", "SOUTH", "CENTRAL"] as Region[])
      : user.regions;
  const segmentOptions: AuditSegment[] =
    user?.role === "ADMIN" || !user?.segments?.length
      ? (["BRANCH_AUDIT", "SHARIAH", "MANAGEMENT", "OTHER"] as AuditSegment[])
      : user.segments;

  async function load() {
    setReports(await api.reports());
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (regionOptions.length && !regionOptions.includes(region)) setRegion(regionOptions[0]);
    if (segmentOptions.length && !segmentOptions.includes(segment)) setSegment(segmentOptions[0]);
  }, [user]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("title", title);
      form.append("report_number", reportNumber);
      form.append("region", region);
      form.append("segment", segment);
      if (description) form.append("description", description);
      if (file) form.append("file", file);
      await api.createReport(form);
      setTitle("");
      setReportNumber("");
      setDescription("");
      setFile(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Audit reports</h1>
          <p>Upload PDF or Excel reports tagged by region and audit segment.</p>
        </div>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>Upload report</h2>
          </div>
          <form className="form-grid" onSubmit={onSubmit}>
            {error && <div className="error">{error}</div>}
            <label>
              Title
              <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </label>
            <label>
              Report number
              <input value={reportNumber} onChange={(e) => setReportNumber(e.target.value)} required />
            </label>
            <label>
              Region
              <select value={region} onChange={(e) => setRegion(e.target.value as Region)}>
                {regionOptions.map((r) => (
                  <option key={r} value={r}>
                    {REGION_LABELS[r]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Segment
              <select value={segment} onChange={(e) => setSegment(e.target.value as AuditSegment)}>
                {segmentOptions.map((s) => (
                  <option key={s} value={s}>
                    {SEGMENT_LABELS[s]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Description
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>
            <label>
              File (PDF / Excel)
              <input
                type="file"
                accept=".pdf,.xlsx,.xls,.csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <button className="btn" disabled={busy}>
              {busy ? "Uploading…" : "Upload"}
            </button>
          </form>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Library</h2>
          </div>
          {reports.length === 0 ? (
            <div className="empty">No reports in your assigned regions/segments.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Title</th>
                  <th>Region</th>
                  <th>Segment</th>
                  <th>Obs.</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td>{r.report_number}</td>
                    <td>
                      <strong>{r.title}</strong>
                      <div className="table-sub">{r.file_name || "No file"}</div>
                    </td>
                    <td>{REGION_LABELS[r.region]}</td>
                    <td>{SEGMENT_LABELS[r.segment]}</td>
                    <td>{r.observation_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

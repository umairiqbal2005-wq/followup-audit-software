import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditReport } from "../types";

export function ReportsPage() {
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [title, setTitle] = useState("");
  const [reportNumber, setReportNumber] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setReports(await api.reports());
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("title", title);
      form.append("report_number", reportNumber);
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
          <p>Upload PDF or Excel reports that observations attach to.</p>
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
            <div className="empty">No reports uploaded yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Title</th>
                  <th>Obs.</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td>{r.report_number}</td>
                    <td>
                      <strong>{r.title}</strong>
                      <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{r.file_name || "No file"}</div>
                    </td>
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

import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { AuditReport, ObservationSeverity } from "../types";

export function NewObservationPage() {
  const navigate = useNavigate();
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [reportId, setReportId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [severity, setSeverity] = useState<ObservationSeverity>("MEDIUM");
  const [recommendation, setRecommendation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .reports()
      .then((rows) => {
        setReports(rows);
        if (rows[0]) setReportId(String(rows[0].id));
      })
      .catch((err) => setError(err.message));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const obs = await api.createObservation({
        report_id: Number(reportId),
        title,
        description,
        category: category || null,
        severity,
        recommendation: recommendation || null,
      });
      navigate(`/observations/${obs.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>New observation</h1>
          <p>Capture a finding against an uploaded audit report.</p>
        </div>
      </div>
      <div className="panel" style={{ maxWidth: 720 }}>
        <form className="form-grid" onSubmit={onSubmit}>
          {error && <div className="error">{error}</div>}
          <label>
            Audit report
            <select value={reportId} onChange={(e) => setReportId(e.target.value)} required>
              <option value="">Select report</option>
              {reports.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.report_number} — {r.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} required />
          </label>
          <label>
            Category
            <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. ITGC, SOX" />
          </label>
          <label>
            Severity
            <select value={severity} onChange={(e) => setSeverity(e.target.value as ObservationSeverity)}>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            Recommendation
            <textarea value={recommendation} onChange={(e) => setRecommendation(e.target.value)} />
          </label>
          <div className="actions">
            <button className="btn" disabled={busy || !reportId}>
              {busy ? "Saving…" : "Create draft"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { AccessCatalog, AuditSegment, Region, User, UserRole } from "../types";
import { REGION_LABELS, SEGMENT_LABELS } from "../types";

function toggleValue<T extends string>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [catalog, setCatalog] = useState<AccessCatalog | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draftRole, setDraftRole] = useState<UserRole>("VIEWER");
  const [draftRegions, setDraftRegions] = useState<Region[]>([]);
  const [draftSegments, setDraftSegments] = useState<AuditSegment[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: "",
    email: "",
    full_name: "",
    password: "Pass@12345",
    role: "VIEWER" as UserRole,
    department: "",
    regions: [] as Region[],
    segments: [] as AuditSegment[],
  });

  const selected = useMemo(() => users.find((u) => u.id === selectedId) || null, [users, selectedId]);
  const isAdmin = me?.role === "ADMIN";

  async function load() {
    const [rows, cat] = await Promise.all([api.users(), api.accessCatalog()]);
    setUsers(rows);
    setCatalog(cat);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  function openEditor(u: User) {
    setSelectedId(u.id);
    setDraftRole(u.role);
    setDraftRegions([...(u.regions || [])]);
    setDraftSegments([...(u.segments || [])]);
    setError("");
  }

  async function saveAccess(e: FormEvent) {
    e.preventDefault();
    if (!selected || !isAdmin) return;
    setBusyId(selected.id);
    setError("");
    try {
      const updated = await api.updateUser(selected.id, {
        role: draftRole,
        regions: draftRegions,
        segments: draftSegments,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setSelectedId(updated.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  async function createUser(e: FormEvent) {
    e.preventDefault();
    if (!isAdmin) return;
    setBusyId(-1);
    setError("");
    try {
      const created = await api.createUser(createForm);
      setUsers((prev) => [...prev, created].sort((a, b) => a.full_name.localeCompare(b.full_name)));
      setShowCreate(false);
      openEditor(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Users & regional access</h1>
          <p>Assign functional roles plus North / South / Central windows across all audit segments.</p>
        </div>
        {isAdmin && (
          <button className="btn" onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "Close form" : "Add user"}
          </button>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      {showCreate && isAdmin && catalog && (
        <div className="panel" style={{ marginBottom: "1.25rem" }}>
          <div className="panel-head">
            <h2>Create user</h2>
          </div>
          <form className="form-grid" onSubmit={createUser}>
            <label>
              Full name
              <input
                value={createForm.full_name}
                onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                required
              />
            </label>
            <label>
              Username
              <input
                value={createForm.username}
                onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                required
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                required
              />
            </label>
            <label>
              Temporary password
              <input
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                required
                minLength={8}
              />
            </label>
            <label>
              Role
              <select
                value={createForm.role}
                onChange={(e) => setCreateForm({ ...createForm, role: e.target.value as UserRole })}
              >
                {catalog.roles.map((r) => (
                  <option key={r} value={r}>
                    {r.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="check-set">
              <legend>Regions</legend>
              {catalog.regions.map((r) => (
                <label key={r} className="check-inline">
                  <input
                    type="checkbox"
                    checked={createForm.regions.includes(r)}
                    onChange={() =>
                      setCreateForm({ ...createForm, regions: toggleValue(createForm.regions, r) })
                    }
                  />
                  {REGION_LABELS[r]}
                </label>
              ))}
            </fieldset>
            <fieldset className="check-set">
              <legend>Segments</legend>
              {catalog.segments.map((s) => (
                <label key={s} className="check-inline">
                  <input
                    type="checkbox"
                    checked={createForm.segments.includes(s)}
                    onChange={() =>
                      setCreateForm({ ...createForm, segments: toggleValue(createForm.segments, s) })
                    }
                  />
                  {SEGMENT_LABELS[s]}
                </label>
              ))}
            </fieldset>
            <button className="btn" disabled={busyId === -1}>
              {busyId === -1 ? "Creating…" : "Create user"}
            </button>
          </form>
        </div>
      )}

      <div className="detail-grid users-layout">
        <div className="panel">
          <div className="panel-head">
            <h2>Directory</h2>
            <span className="panel-meta">{users.length} users</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Regions</th>
                <th>Segments</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.id}
                  className={selectedId === u.id ? "row-selected" : undefined}
                  onClick={() => openEditor(u)}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    <div className="table-title">{u.full_name}</div>
                    <div className="table-sub">{u.username}</div>
                  </td>
                  <td>
                    <span className="badge">{u.role.replaceAll("_", " ")}</span>
                  </td>
                  <td>{u.role === "ADMIN" ? "All" : (u.regions || []).map((r) => REGION_LABELS[r]).join(", ") || "—"}</td>
                  <td>
                    {u.role === "ADMIN"
                      ? "All"
                      : (u.segments || []).map((s) => SEGMENT_LABELS[s]).join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Assign access</h2>
          </div>
          {!selected || !catalog ? (
            <div className="empty">Select a user to assign role, region, and segment access.</div>
          ) : (
            <form className="form-grid" onSubmit={saveAccess}>
              <div className="meta-list" style={{ padding: 0 }}>
                <div>
                  <span>User</span>
                  <strong>{selected.full_name}</strong>
                </div>
                <div>
                  <span>Username</span>
                  <strong>{selected.username}</strong>
                </div>
              </div>
              <label>
                Functional role
                <select
                  value={draftRole}
                  onChange={(e) => setDraftRole(e.target.value as UserRole)}
                  disabled={!isAdmin}
                >
                  {catalog.roles.map((r) => (
                    <option key={r} value={r}>
                      {r.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
              <fieldset className="check-set" disabled={!isAdmin}>
                <legend>Region windows</legend>
                <p className="help-text">User only sees North / South / Central data you tick here.</p>
                {catalog.regions.map((r) => (
                  <label key={r} className="check-inline">
                    <input
                      type="checkbox"
                      checked={draftRegions.includes(r)}
                      onChange={() => setDraftRegions((prev) => toggleValue(prev, r))}
                    />
                    {REGION_LABELS[r]}
                  </label>
                ))}
              </fieldset>
              <fieldset className="check-set" disabled={!isAdmin}>
                <legend>Audit segments</legend>
                <p className="help-text">Applies across Branch Audit, Shariah, Management, and Other.</p>
                {catalog.segments.map((s) => (
                  <label key={s} className="check-inline">
                    <input
                      type="checkbox"
                      checked={draftSegments.includes(s)}
                      onChange={() => setDraftSegments((prev) => toggleValue(prev, s))}
                    />
                    {SEGMENT_LABELS[s]}
                  </label>
                ))}
              </fieldset>
              {isAdmin ? (
                <button className="btn" disabled={busyId === selected.id}>
                  {busyId === selected.id ? "Saving…" : "Save access"}
                </button>
              ) : (
                <p className="help-text">Only ADMIN can change role and region assignments.</p>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

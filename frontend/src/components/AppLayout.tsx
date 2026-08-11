import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { REGION_LABELS, SEGMENT_LABELS, type Region, type AuditSegment } from "../types";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/observations", label: "Observations" },
  { to: "/reports", label: "Reports" },
];

function isAdminRole(role?: string | null) {
  return (role || "").toUpperCase() === "ADMIN";
}

function canManageUsers(role?: string | null) {
  const r = (role || "").toUpperCase();
  return r === "ADMIN" || r === "CENTRAL_TEAM";
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const role = (user?.role || "").toUpperCase();
  const regions = user?.regions || [];
  const segments = user?.segments || [];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          AOP
          <span>Audit Observations Platform</span>
        </div>
        <nav className="nav">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"}>
              {link.label}
            </NavLink>
          ))}
          {canManageUsers(role) && <NavLink to="/users">Users & roles</NavLink>}
        </nav>
        <div className="user-card">
          <strong>{user?.full_name || user?.username}</strong>
          <div>{role.replaceAll("_", " ") || "UNKNOWN"}</div>
          <div className="scope-chip-row">
            {isAdminRole(role) ? (
              <span className="scope-chip">All regions</span>
            ) : (
              regions.map((r) => (
                <span className="scope-chip" key={r}>
                  {REGION_LABELS[r as Region] || r}
                </span>
              ))
            )}
          </div>
          <div className="scope-chip-row">
            {isAdminRole(role) ? (
              <span className="scope-chip">All segments</span>
            ) : (
              segments.slice(0, 3).map((s) => (
                <span className="scope-chip" key={s}>
                  {SEGMENT_LABELS[s as AuditSegment] || s}
                </span>
              ))
            )}
          </div>
          <button className="btn secondary" style={{ marginTop: "0.9rem", width: "100%" }} onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

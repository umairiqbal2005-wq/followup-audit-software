import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { REGION_LABELS, SEGMENT_LABELS } from "../types";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/observations", label: "Observations" },
  { to: "/reports", label: "Reports" },
];

export function AppLayout() {
  const { user, logout } = useAuth();

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
          {(user?.role === "ADMIN" || user?.role === "CENTRAL_TEAM") && (
            <NavLink to="/users">Users</NavLink>
          )}
        </nav>
        <div className="user-card">
          <strong>{user?.full_name}</strong>
          <div>{user?.role.replaceAll("_", " ")}</div>
          <div className="scope-chip-row">
            {user?.role === "ADMIN" ? (
              <span className="scope-chip">All regions</span>
            ) : (
              (user?.regions || []).map((r) => (
                <span className="scope-chip" key={r}>
                  {REGION_LABELS[r]}
                </span>
              ))
            )}
          </div>
          <div className="scope-chip-row">
            {user?.role === "ADMIN" ? (
              <span className="scope-chip">All segments</span>
            ) : (
              (user?.segments || []).slice(0, 3).map((s) => (
                <span className="scope-chip" key={s}>
                  {SEGMENT_LABELS[s]}
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

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

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

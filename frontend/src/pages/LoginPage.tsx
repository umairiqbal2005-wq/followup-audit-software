import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState("umair");
  const [password, setPassword] = useState("Umair@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card form-grid" onSubmit={onSubmit}>
        <div>
          <p className="eyebrow">Internal audit follow-up</p>
          <h1>AOP</h1>
          <p>Track observations from report upload through closure.</p>
        </div>
        {error && <div className="error">{error}</div>}
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button className="btn" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <div style={{ margin: 0, fontSize: "0.9rem", color: "var(--muted)", lineHeight: 1.45 }}>
          <strong style={{ color: "var(--ink)" }}>Admin logins</strong>
          <div>
            <code>umair</code> / <code>Umair@123</code> — full admin (roles & regions)
          </div>
          <div>
            <code>admin</code> / <code>Admin@123</code> — full admin
          </div>
          <div style={{ marginTop: "0.45rem" }}>
            Regional demo: <code>khurrum</code> / <code>Pass@123</code> (North only)
          </div>
        </div>
      </form>
    </div>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { User } from "../types";

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .users()
      .then(setUsers)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Users</h1>
          <p>Role directory for assignment and access control.</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Username</th>
              <th>Role</th>
              <th>Department</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.username}</td>
                <td>
                  <span className="badge">{u.role.replaceAll("_", " ")}</span>
                </td>
                <td>{u.department || "—"}</td>
                <td>{u.is_active ? "Active" : "Inactive"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

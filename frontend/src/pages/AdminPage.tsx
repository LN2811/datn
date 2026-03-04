import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.tsx';

export function AdminPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <main className="dashboard-shell">
      <section className="dashboard-card">
        <h1 className="dashboard-title">Admin</h1>
        <p className="dashboard-text">Ban dang o khu vuc quan tri.</p>
        <p className="dashboard-text">
          Tai khoan hien tai: <strong>{user?.email ?? 'admin'}</strong>
        </p>
        <button
          className="dashboard-button dashboard-button--ghost"
          type="button"
          onClick={() => navigate('/dashboard')}
        >
          Ve dashboard
        </button>
        <button className="dashboard-button" type="button" onClick={handleLogout}>
          Dang xuat
        </button>
      </section>
    </main>
  );
}

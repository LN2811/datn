import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.tsx';

export function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <main className="dashboard-shell">
      <section className="dashboard-card">
        <h1 className="dashboard-title">Dashboard</h1>
        <p className="dashboard-text">Ban da dang nhap thanh cong.</p>
        <p className="dashboard-text">
          Xin chao <strong>{user?.email ?? 'nguoi dung'}</strong>
        </p>
        {user?.is_superuser ? (
          <button
            className="dashboard-button dashboard-button--ghost"
            type="button"
            onClick={() => navigate('/admin')}
          >
            Vao trang admin
          </button>
        ) : null}
        <button
          className="dashboard-button"
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
        >
          {isLoggingOut ? 'Dang xu ly...' : 'Dang xuat'}
        </button>
      </section>
    </main>
  );
}


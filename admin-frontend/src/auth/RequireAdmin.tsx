import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext.tsx';

export function RequireAdmin() {
  const { user, logout } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_superuser) {
    return (
      <main className="auth-shell">
        <section className="auth-card auth-card--compact">
          <h1 className="auth-title">Không có quyền truy cập</h1>
          <p className="auth-muted">Tài khoản này không có quyền quản trị hệ thống.</p>
          <button className="auth-button" type="button" onClick={() => void logout()}>
            Đăng xuất
          </button>
        </section>
      </main>
    );
  }

  return <Outlet />;
}

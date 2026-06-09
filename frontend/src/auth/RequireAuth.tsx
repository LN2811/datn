import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext.tsx';

export function RequireAuth() {
  const { user, isCheckingAuth } = useAuth();
  const location = useLocation();

  if (isCheckingAuth) {
    return (
      <main className="auth-shell">
        <section className="auth-card auth-card--compact">
          <p className="auth-muted">Đang kiểm tra phiên đăng nhập...</p>
        </section>
      </main>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  return <Outlet />;
}

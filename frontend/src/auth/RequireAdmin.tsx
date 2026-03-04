import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext.tsx';

export function RequireAdmin() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_superuser) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

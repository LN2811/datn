import { Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import { RequireAuth } from './auth/RequireAuth.tsx';
import { RequireAdmin } from './auth/RequireAdmin.tsx';
import { AdminPage } from './admin_fe/AdminPage.tsx';
import { LoginForm } from './components/login/LoginForm.tsx';
import { RegisterForm } from './components/register/RegisterForm.tsx';


function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/login" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/forgot_password" element={<Navigate to="/login" replace />} />
      <Route path="/forgot-password" element={<Navigate to="/login" replace />} />
      <Route path="/reset-password" element={<Navigate to="/login" replace />} />
      <Route element={<RequireAuth />}>
        <Route element={<RequireAdmin />}>
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/dashboard" element={<Navigate to="/admin" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

export default App;

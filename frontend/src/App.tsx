import { Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import { RequireAuth } from './auth/RequireAuth.tsx';
import { RequireAdmin } from './auth/RequireAdmin.tsx';
import { AdminPage } from './pages/AdminPage.tsx';
import { DashboardPage } from './pages/DashboardPage.tsx';
import { RegisterForm } from './components/register/RegisterForm.tsx';
import HomePage from './pages/HomePage.tsx';
import { LoginForm } from './components/LoginForm.tsx';
import ForgotPasswordPage from './pages/forgot_password/index.tsx';
import Project from './components/home/project.tsx';


function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/forgot_password" element={<ForgotPasswordPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ForgotPasswordPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/projects" element={<Project />} />
        <Route path="/projects/:projectId" element={<Project />} />
        <Route element={<RequireAdmin />}>
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

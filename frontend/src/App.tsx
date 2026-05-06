import { Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import { RequireAuth } from './auth/RequireAuth.tsx';
import { RequireAdmin } from './auth/RequireAdmin.tsx';
import { DashboardPage } from './pages/DashboardPage.tsx';
import { ProfilePage } from './pages/ProfilePage.tsx';
import { RegisterForm } from './components/register/RegisterForm.tsx';
import HomePage from './pages/HomePage.tsx';
import { LoginForm } from './components/LoginForm.tsx';
import ForgotPasswordPage from './pages/forgot_password/index.tsx';
import { QuizPage } from './pages/QuizPage.tsx';
import Project from './components/home/project.tsx';
import Lession from './components/home/lession.tsx';
import ProjectsPage from './components/home/projects.tsx';
import Upgrade from './components/upgared/upgrade.tsx'


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
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<Project />} />
        <Route path="/assignments/:assignmentId/quiz" element={<QuizPage />} />
        <Route path="/lession" element={<Navigate to="/projects" replace />} />
        <Route path="/lession/:moduleId" element={<Lession />} />
        <Route path="/lession/:moduleId/quiz" element={<QuizPage />} />
        <Route path="/upgrade" element={<Upgrade/>}/>

      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

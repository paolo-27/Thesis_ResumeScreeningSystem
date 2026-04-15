import React from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ApplicantLanding from './pages/applicant/ApplicantLanding';
import LoginPage from './pages/admin/auth/LoginPage';
import AdminLayout from './pages/admin/AdminLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminJobs from './pages/admin/AdminJobs';
import AdminCandidates from './pages/admin/AdminCandidates';
import ProfilePage from './pages/admin/ProfilePage';
import UserManagement from './pages/admin/UserManagement';
import { toast } from 'sonner';

/** Wraps any route that requires the user to be authenticated. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <Routes>
      {/* Public applicant page */}
      <Route path="/" element={<ApplicantLanding />} />

      {/* Login – redirect to /admin if already authenticated */}
      <Route
        path="/admin/login"
        element={
          token ? <Navigate to="/admin" replace /> : (
            <LoginPage
              onLogin={() => navigate('/admin', { replace: true })}
            />
          )
        }
      />

      {/* Protected admin area */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="jobs" element={<AdminJobs />} />
        <Route path="candidates" element={<AdminCandidates />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="users" element={<UserManagement />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

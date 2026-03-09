import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ApplicantLanding from './pages/applicant/ApplicantLanding';
import LoginPage from './pages/admin/auth/LoginPage';
import ResetPassword from './pages/admin/auth/ResetPassword';
import AdminLayout from './pages/admin/AdminLayout';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminJobs from './pages/admin/AdminJobs';
import AdminCandidates from './pages/admin/AdminCandidates';
import { toast } from 'sonner';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ApplicantLanding />} />
      <Route path="/admin/login" element={
        <LoginPage
          onLogin={() => window.location.href = '/admin'}
          onResetPassword={() => window.location.href = '/admin/reset-password'}
        />
      } />
      <Route path="/admin/reset-password" element={
        <ResetPassword
          onBack={() => window.location.href = '/admin/login'}
          onSuccess={() => {
            toast.success('Password reset successfully!');
            window.location.href = '/admin/login';
          }}
        />
      } />
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="jobs" element={<AdminJobs />} />
        <Route path="candidates" element={<AdminCandidates />} />
      </Route>
    </Routes>
  );
}

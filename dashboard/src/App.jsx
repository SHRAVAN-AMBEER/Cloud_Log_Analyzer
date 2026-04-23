import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';

import Login from './pages/Login';
import Register from './pages/Register';
import CustomerDashboard from './pages/CustomerDashboard';
import SuperAdminDashboard from './pages/SuperAdminDashboard';

import './styles/main.css';

// ── Route Guards ─────────────────────────────────────────────

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('siem_token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function AdminRoute({ children }) {
  const token = localStorage.getItem('siem_token');
  const role = localStorage.getItem('siem_role');
  if (!token) return <Navigate to="/login" replace />;
  if (role !== 'super_admin') return <Navigate to="/dashboard" replace />;
  return children;
}

// ── App ───────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <CustomerDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <SuperAdminDashboard />
            </AdminRoute>
          }
        />
        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

// ============================================================
// src/services/api.js — Centralized API service layer
// Base URL is driven by VITE_API_BASE_URL in .env
// ============================================================

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

function authHeaders() {
  const token = localStorage.getItem('siem_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('siem_token');
      window.location.href = '/login';
    }
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

// ── Auth ─────────────────────────────────────────────────────

export async function loginUser(companyId, password) {
  const res = await fetch(`${BASE}/api/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_id: companyId, password }),
  });
  return handleResponse(res);
}

export async function loginWithApiKey(apiKey) {
  const res = await fetch(`${BASE}/api/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  return handleResponse(res);
}

export async function registerCompany(data) {
  const res = await fetch(`${BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function fetchMe() {
  const res = await fetch(`${BASE}/api/me`, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Alerts ───────────────────────────────────────────────────

export async function fetchAlerts(companyId = null, limit = 50, offset = 0) {
  let url = `${BASE}/alerts?limit=${limit}&offset=${offset}`;
  if (companyId && companyId !== 'ALL') url += `&tenant=${companyId}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Dashboard Stats ──────────────────────────────────────────

export async function fetchDashboardStats(companyId) {
  const param = companyId ? `?company_id=${companyId}` : '';
  const res = await fetch(`${BASE}/api/dashboard-stats${param}`, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Timeline ─────────────────────────────────────────────────

export async function fetchAlertsTimeline(companyId) {
  const param = companyId ? `?company_id=${companyId}` : '';
  const res = await fetch(`${BASE}/api/alerts/timeline${param}`, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Companies (super admin) ───────────────────────────────────

export async function fetchCompanies() {
  const res = await fetch(`${BASE}/api/companies`, { headers: authHeaders() });
  return handleResponse(res);
}

export async function sendAlertReminder(companyId) {
  const res = await fetch(`${BASE}/api/companies/${companyId}/send-alert-reminder`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ── Report ───────────────────────────────────────────────────

export async function downloadReport(companyId = null) {
  const token = localStorage.getItem('siem_token');
  let url = `${BASE}/api/report`;
  if (companyId && companyId !== 'ALL') url += `?tenant=${companyId}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error('Failed to generate report');
  const blob = await res.blob();
  const link = document.createElement('a');
  link.href = window.URL.createObjectURL(blob);
  link.download = `${companyId || 'Enterprise'}_Security_Report.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export async function deleteCompany(companyId) {
  const res = await fetch(`${BASE}/api/companies/${companyId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse(res);
}
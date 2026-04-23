import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Tooltip, Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

import {
  fetchCompanies, fetchAlerts, fetchAlertsTimeline,
  sendAlertReminder, downloadReport,
} from '../services/api';
import '../styles/main.css';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// Assign a deterministic color per company
const COMPANY_COLORS = [
  '#3b82f6', '#ef4444', '#22c55e', '#f97316', '#a855f7',
  '#eab308', '#06b6d4', '#ec4899', '#14b8a6', '#f43f5e',
];
function companyColor(idx) { return COMPANY_COLORS[idx % COMPANY_COLORS.length]; }

function relativeTime(iso) {
  if (!iso) return 'Never';
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Toast system ──────────────────────────────────────────────
function Toast({ toasts }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>{t.msg}</div>
      ))}
    </div>
  );
}

// ── Live clock ────────────────────────────────────────────────
function LiveClock() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span style={{ color: '#94a3b8', fontSize: '0.9rem', fontFamily: 'monospace' }}>
      {time.toUTCString().slice(0, 25)}
    </span>
  );
}

// ── Overview metric card ──────────────────────────────────────
function OverviewCard({ label, value, icon, accent }) {
  return (
    <div className="metric-card" style={accent ? { borderColor: `${accent}40` } : {}}>
      <div className="metric-icon" style={{ background: `${accent || '#3b82f6'}22` }}>
        <span style={{ fontSize: '1.4rem' }}>{icon}</span>
      </div>
      <h3>{label}</h3>
      <p className="metric-value" style={{ color: accent || 'var(--text-main)' }}>{value ?? '—'}</p>
    </div>
  );
}

// ── Company Detail Modal (slide panel) ───────────────────────
function CompanyPanel({ company, onClose }) {
  const navigate = useNavigate();
  if (!company) return null;
  return (
    <div className="side-panel-overlay" onClick={onClose}>
      <div className="side-panel" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0, color: '#f8fafc' }}>{company.company_name}</h2>
          <button className="btn-ghost" onClick={onClose}>✕</button>
        </div>
        <p style={{ color: '#94a3b8' }}>Industry: <strong style={{ color: '#f8fafc' }}>{company.industry}</strong></p>
        <p style={{ color: '#94a3b8' }}>Company ID: <code style={{ color: '#60a5fa' }}>{company.company_id}</code></p>
        <p style={{ color: '#94a3b8' }}>Status: <span className={`badge badge-${company.status === 'active' ? 'LOW' : 'CRITICAL'}`}>{company.status}</span></p>
        <p style={{ color: '#94a3b8' }}>Last Login: {relativeTime(company.last_login)}</p>

        <button
          className="login-btn"
          style={{ marginTop: '1.5rem' }}
          onClick={() => {
            localStorage.setItem('siem_company', company.company_id);
            localStorage.setItem('siem_company_name', company.company_name);
            navigate(`/dashboard?company=${company.company_id}`);
          }}
        >
          📊 Open Dashboard →
        </button>
      </div>
    </div>
  );
}

// ── Global Threat Map ─────────────────────────────────────────
function GlobalThreatMap({ alertsByCompany, companyColorMap }) {
  const [tooltip, setTooltip] = useState(null);

  const allMarkers = Object.entries(alertsByCompany).flatMap(([cid, alerts], cidx) =>
    alerts
      .filter((a) => a.latitude && a.longitude)
      .map((a) => ({ ...a, _company: cid, _color: companyColorMap[cid] || companyColor(cidx) }))
  );

  return (
    <div className="chart-panel" style={{ gridColumn: '1 / -1' }}>
      <h2>🌍 Global Threat Map — All Companies</h2>
      <div style={{ position: 'relative', background: '#0a0f1e', borderRadius: 10, overflow: 'hidden' }}>
        <ComposableMap projectionConfig={{ scale: 140 }} style={{ width: '100%', height: 400 }}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography key={geo.rsmKey} geography={geo}
                  style={{ default: { fill: '#1e293b', stroke: '#334155', strokeWidth: 0.5, outline: 'none' }, hover: { fill: '#1e293b', outline: 'none' }, pressed: { outline: 'none' } }}
                />
              ))
            }
          </Geographies>
          {allMarkers.map((m, i) => (
            <Marker key={i} coordinates={[m.longitude, m.latitude]}
              onMouseEnter={() => setTooltip(m)} onMouseLeave={() => setTooltip(null)}>
              <circle r={m.risk_level === 'CRITICAL' ? 7 : 5}
                fill={m._color} opacity={0.85}
                className={m.risk_level === 'CRITICAL' ? 'pulse-marker' : ''} />
            </Marker>
          ))}
        </ComposableMap>

        {/* Company Legend */}
        <div className="map-legend" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
          {Object.entries(companyColorMap).map(([cid, color]) => (
            <span key={cid} className="legend-item">
              <span style={{ background: color }} className="legend-dot" /> {cid}
            </span>
          ))}
        </div>

        {tooltip && (
          <div className="map-tooltip">
            <div><strong>Company:</strong> {tooltip._company}</div>
            <div><strong>User:</strong> {tooltip.user_id}</div>
            <div>Risk: <span style={{ color: tooltip._color }}>{tooltip.risk_level}</span></div>
            <div>IP: {tooltip.ip}</div>
            <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>{tooltip.timestamp?.slice(0, 19).replace('T', ' ')}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Platform Timeline ─────────────────────────────────────────
function PlatformTimeline({ timelineByCompany, companyColorMap }) {
  const companies = Object.keys(timelineByCompany);
  if (!companies.length) return null;

  const labels = (timelineByCompany[companies[0]] || []).map((d) => d.date.slice(5));
  const datasets = companies.map((cid) => ({
    label: cid,
    data: (timelineByCompany[cid] || []).map((d) => d.total),
    borderColor: companyColorMap[cid] || '#3b82f6',
    backgroundColor: 'transparent',
    tension: 0.4, pointRadius: 2,
  }));

  const opts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
    scales: {
      x: { ticks: { color: '#94a3b8', maxTicksLimit: 10 }, grid: { color: '#ffffff08' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: '#ffffff08' } },
    },
  };

  return (
    <div className="chart-panel" style={{ gridColumn: '1 / -1' }}>
      <h2>📈 Platform-Wide Alert Timeline (30 days)</h2>
      <div className="chart-wrapper" style={{ height: 260 }}>
        <Line data={{ labels, datasets }} options={opts} />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SUPER ADMIN DASHBOARD
// ═══════════════════════════════════════════════════════════════
export default function SuperAdminDashboard() {
  const navigate = useNavigate();

  const [companies, setCompanies] = useState([]);
  const [alertsByCompany, setAlertsByCompany] = useState({});
  const [timelineByCompany, setTimelineByCompany] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedCompany, setSelectedCompany] = useState(null);  // for side panel
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((msg, type = 'success') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);

  const load = useCallback(async () => {
    try {
      const comps = await fetchCompanies();
      setCompanies(comps);

      // Per-company alerts + timeline in parallel
      const alertResults = await Promise.allSettled(
        comps.map((c) => fetchAlerts(c.company_id, 100, 0).then((d) => ({ id: c.company_id, data: d.alerts || [] })))
      );
      const timelineResults = await Promise.allSettled(
        comps.map((c) => fetchAlertsTimeline(c.company_id).then((d) => ({ id: c.company_id, data: d })))
      );

      const ab = {};
      alertResults.forEach((r) => { if (r.status === 'fulfilled') ab[r.value.id] = r.value.data; });
      const tb = {};
      timelineResults.forEach((r) => { if (r.status === 'fulfilled') tb[r.value.id] = r.value.data; });

      setAlertsByCompany(ab);
      setTimelineByCompany(tb);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!localStorage.getItem('siem_token')) { navigate('/login'); return; }
    if (localStorage.getItem('siem_role') !== 'super_admin') { navigate('/dashboard'); return; }
    load();
  }, [load, navigate]);

  const handleSendAlert = async (companyId) => {
    try {
      await sendAlertReminder(companyId);
      addToast(`✅ Alert reminder sent to ${companyId}`);
    } catch (err) {
      addToast(`❌ ${err.message}`, 'error');
    }
  };

  const handleLogout = () => { localStorage.clear(); navigate('/login'); };

  // Build color map
  const companyColorMap = Object.fromEntries(
    companies.map((c, i) => [c.company_id, companyColor(i)])
  );

  // Overview aggregates
  const totalCompanies = companies.length;
  const yesterday = new Date(Date.now() - 86400000).toISOString();
  const allAlerts = Object.values(alertsByCompany).flat();
  const alertsLast24h = allAlerts.filter((a) => (a.timestamp || '') > yesterday).length;
  const criticalLast24h = allAlerts.filter((a) => a.risk_level === 'CRITICAL' && (a.timestamp || '') > yesterday).length;
  const activeIPs = new Set(allAlerts.filter((a) => (a.timestamp || '') > yesterday).map((a) => a.ip)).size;

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p style={{ color: '#94a3b8' }}>Loading Super Admin Console…</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <Toast toasts={toasts} />

      {/* ── Top Bar ── */}
      <div className="topbar">
        <div>
          <h1 className="topbar-title">🛡️ Cloud Log Analyzer — Super Admin Console</h1>
          <p className="topbar-sub">Platform-wide threat intelligence & tenant management</p>
        </div>
        <div className="topbar-right">
          <LiveClock />
          <button className="btn-danger" onClick={handleLogout}>Logout</button>
        </div>
      </div>

      {/* ── Section 1: Platform Overview ── */}
      <div className="metrics-row">
        <OverviewCard label="Total Companies" value={totalCompanies} icon="🏢" accent="#3b82f6" />
        <OverviewCard label="Alerts (24h)" value={alertsLast24h} icon="📊" accent="#f97316" />
        <OverviewCard label="Critical (24h)" value={criticalLast24h} icon="🚨" accent="#ef4444" />
        <OverviewCard label="Active Attack IPs" value={activeIPs} icon="🌐" accent="#a855f7" />
      </div>

      {/* ── Section 2: Companies Table ── */}
      <div className="data-table-container" style={{ marginBottom: '2rem' }}>
        <div className="table-header">
          <h2>🏢 Registered Companies</h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="styled-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Industry</th>
                <th>Alerts (24h)</th>
                <th>Critical</th>
                <th>Last Login</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((c) => {
                const cAlerts = alertsByCompany[c.company_id] || [];
                const cnt24 = cAlerts.filter((a) => (a.timestamp || '') > yesterday).length;
                const crit24 = cAlerts.filter((a) => a.risk_level === 'CRITICAL' && (a.timestamp || '') > yesterday).length;
                return (
                  <tr key={c.company_id} title={`Email: ${c.email || 'N/A'}`}>
                    <td>
                      <div className="user-cell">
                        <div className="user-avatar" style={{ background: companyColorMap[c.company_id] }}>
                          {c.company_name?.[0]?.toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600 }}>{c.company_name}</div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{c.company_id}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ color: '#94a3b8' }}>{c.industry || '—'}</td>
                    <td>{cnt24}</td>
                    <td style={{ color: crit24 > 0 ? '#ef4444' : '#22c55e', fontWeight: 700 }}>{crit24}</td>
                    <td style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{relativeTime(c.last_login)}</td>
                    <td>
                      <span className={`badge badge-${c.status === 'active' ? 'LOW' : 'CRITICAL'}`}>
                        {c.status || 'unknown'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn-action" onClick={() => setSelectedCompany(c)}>📊 View</button>
                        <button className="btn-action btn-action-warn" onClick={() => handleSendAlert(c.company_id)}>📧 Alert</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Section 3: Global Threat Map ── */}
      <div className="charts-grid" style={{ marginBottom: '2rem' }}>
        <GlobalThreatMap alertsByCompany={alertsByCompany} companyColorMap={companyColorMap} />
      </div>

      {/* ── Section 4: Platform Timeline ── */}
      <div className="charts-grid" style={{ marginBottom: '2rem' }}>
        <PlatformTimeline timelineByCompany={timelineByCompany} companyColorMap={companyColorMap} />
      </div>

      {/* ── Section 5: Company Detail Side Panel ── */}
      <CompanyPanel company={selectedCompany} onClose={() => setSelectedCompany(null)} />
    </div>
  );
}

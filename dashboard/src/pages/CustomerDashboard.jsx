import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement,
} from 'chart.js';
import { Doughnut, Bar, Line } from 'react-chartjs-2';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

import {
  fetchAlerts, fetchDashboardStats, fetchAlertsTimeline, downloadReport
} from '../services/api';
import '../styles/main.css';

ChartJS.register(
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement
);

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

const RISK_COLORS = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
};

function riskColor(level) { return RISK_COLORS[level] || '#94a3b8'; }

// ── Metric Card ──────────────────────────────────────────────
function MetricCard({ label, value, icon, accent }) {
  return (
    <div className="metric-card" style={accent ? { borderColor: `${accent}40` } : {}}>
      <div className="metric-icon" style={{ background: `${accent || '#3b82f6'}22` }}>
        <span style={{ fontSize: '1.4rem' }}>{icon}</span>
      </div>
      <h3>{label}</h3>
      <p className="metric-value" style={{ color: accent || 'var(--text-main)' }}>
        {value ?? '—'}
      </p>
    </div>
  );
}

// ── Risk Distribution Doughnut ────────────────────────────────
function RiskChart({ distribution }) {
  const labels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
  const data = {
    labels,
    datasets: [{
      data: labels.map((l) => distribution?.[l] || 0),
      backgroundColor: ['#22c55e33', '#eab30833', '#f9731633', '#ef444433'],
      borderColor: ['#22c55e', '#eab308', '#f97316', '#ef4444'],
      borderWidth: 2,
    }],
  };
  return (
    <div className="chart-panel">
      <h2>🎯 Risk Distribution</h2>
      <div className="chart-wrapper" style={{ maxHeight: 260 }}>
        <Doughnut data={data} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } } }} />
      </div>
    </div>
  );
}

// ── Top Attack Types Bar ──────────────────────────────────────
function AttackChart({ topAttacks }) {
  const data = {
    labels: (topAttacks || []).map((a) => a.type),
    datasets: [{
      label: 'Count',
      data: (topAttacks || []).map((a) => a.count),
      backgroundColor: '#3b82f680',
      borderColor: '#3b82f6',
      borderWidth: 2,
      borderRadius: 6,
    }],
  };
  const opts = {
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#94a3b8' }, grid: { color: '#ffffff08' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: '#ffffff08' } },
    },
  };
  return (
    <div className="chart-panel">
      <h2>⚡ Top Attack Types</h2>
      <div className="chart-wrapper" style={{ maxHeight: 260 }}>
        <Bar data={data} options={opts} />
      </div>
    </div>
  );
}

// ── Timeline Line Chart ───────────────────────────────────────
function TimelineChart({ timeline }) {
  const data = {
    labels: (timeline || []).map((d) => d.date.slice(5)), // MM-DD
    datasets: [
      {
        label: 'Total', data: (timeline || []).map((d) => d.total),
        borderColor: '#3b82f6', backgroundColor: '#3b82f620',
        tension: 0.4, fill: true, pointRadius: 2,
      },
      {
        label: 'Critical', data: (timeline || []).map((d) => d.critical),
        borderColor: '#ef4444', backgroundColor: '#ef444420',
        tension: 0.4, fill: false, pointRadius: 2,
      },
      {
        label: 'High', data: (timeline || []).map((d) => d.high),
        borderColor: '#f97316', backgroundColor: 'transparent',
        tension: 0.4, fill: false, pointRadius: 2,
      },
    ],
  };
  const opts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
    scales: {
      x: { ticks: { color: '#94a3b8', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 }, grid: { color: '#ffffff08' } },
      y: { ticks: { color: '#94a3b8' }, grid: { color: '#ffffff08' } },
    },
  };
  return (
    <div className="chart-panel" style={{ gridColumn: '1 / -1' }}>
      <h2>📈 30-Day Alert Timeline</h2>
      <div className="chart-wrapper" style={{ height: 220 }}>
        <Line data={data} options={opts} />
      </div>
    </div>
  );
}

// ── Threat Map ────────────────────────────────────────────────
function ThreatMap({ alerts, showNormal, onToggleNormal }) {
  const [tooltip, setTooltip] = useState(null);

  const markers = alerts.filter((a) => {
    if (!a.latitude || !a.longitude) return false;
    if (!showNormal && a.risk_level === 'LOW' && a.login_status !== 'failure') return false;
    return true;
  });

  return (
    <div className="chart-panel" style={{ gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>🌍 Threat Origin Map</h2>
        <label className="toggle-label">
          <input type="checkbox" checked={showNormal} onChange={onToggleNormal} />
          <span style={{ marginLeft: '0.5rem', fontSize: '0.85rem', color: '#94a3b8' }}>Show Normal Logins</span>
        </label>
      </div>

      <div style={{ position: 'relative', background: '#0a0f1e', borderRadius: 10, overflow: 'hidden' }}>
        <ComposableMap projectionConfig={{ scale: 140 }} style={{ width: '100%', height: 380 }}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography key={geo.rsmKey} geography={geo}
                  style={{ default: { fill: '#1e293b', stroke: '#334155', strokeWidth: 0.5, outline: 'none' }, hover: { fill: '#1e293b', outline: 'none' }, pressed: { fill: '#1e293b', outline: 'none' } }}
                />
              ))
            }
          </Geographies>
          {markers.map((a, idx) => (
            <Marker key={idx} coordinates={[a.longitude, a.latitude]}
              onMouseEnter={() => setTooltip(a)} onMouseLeave={() => setTooltip(null)}>
              <circle r={a.risk_level === 'CRITICAL' ? 7 : 5}
                fill={riskColor(a.risk_level)} opacity={0.85}
                className={a.risk_level === 'CRITICAL' ? 'pulse-marker' : ''} />
            </Marker>
          ))}
        </ComposableMap>

        {/* Legend */}
        <div className="map-legend">
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <span key={level} className="legend-item">
              <span style={{ background: color }} className="legend-dot" /> {level}
            </span>
          ))}
        </div>

        {/* Tooltip */}
        {tooltip && (
          <div className="map-tooltip">
            <div><strong>{tooltip.user_id}</strong></div>
            <div>IP: {tooltip.ip}</div>
            <div>Risk: <span style={{ color: riskColor(tooltip.risk_level) }}>{tooltip.risk_level}</span></div>
            <div>Country: {tooltip.country}</div>
            <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>{tooltip.timestamp?.slice(0, 19).replace('T', ' ')}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Alerts Table ─────────────────────────────────────────────
function AlertsTable({ alerts, total, limit, offset, onPage }) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('timestamp');
  const [sortAsc, setSortAsc] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const filtered = alerts
    .filter((a) =>
      [a.user_id, a.ip, a.risk_level, a.alert_type, a.country]
        .join(' ').toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const av = a[sortKey] || '';
      const bv = b[sortKey] || '';
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });

  const SortIcon = ({ k }) => sortKey === k ? (sortAsc ? ' ↑' : ' ↓') : ' ⇅';

  return (
    <div className="data-table-container">
      <div className="table-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>🔍 Recent Alerts</h2>
        <input
          className="search-input"
          placeholder="Search user, IP, country, type…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="styled-table">
          <thead>
            <tr>
              {[
                ['timestamp', 'Timestamp'], ['user_id', 'User'], ['ip', 'IP'],
                ['country', 'Country'], ['risk_level', 'Risk'], ['alert_type', 'Type'],
              ].map(([k, label]) => (
                <th key={k} onClick={() => toggleSort(k)} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  {label}<SortIcon k={k} />
                </th>
              ))}
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>No alerts found</td></tr>
            )}
            {filtered.map((a, idx) => (
              <React.Fragment key={a.id || idx}>
                <tr
                  style={{ cursor: 'pointer' }}
                  onClick={() => setExpanded(expanded === idx ? null : idx)}
                >
                  <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{a.timestamp?.slice(0, 19).replace('T', ' ')}</td>
                  <td>
                    <div className="user-cell">
                      <div className="user-avatar">{(a.user_id || 'U')[0].toUpperCase()}</div>
                      {a.user_id}
                    </div>
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{a.ip}</td>
                  <td>{a.country || '—'}</td>
                  <td><span className={`badge badge-${a.risk_level}`}>{a.risk_level}</span></td>
                  <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{a.alert_type || '—'}</td>
                  <td>
                    {(a.reasons || []).slice(0, 2).map((r) => (
                      <span key={r} className="reason-tag">{r}</span>
                    ))}
                    {(a.reasons || []).length > 2 && <span className="reason-tag">+{a.reasons.length - 2}</span>}
                  </td>
                </tr>
                {expanded === idx && (
                  <tr>
                    <td colSpan={7} className="expanded-row">
                      <strong>Full Reasons:</strong>{' '}
                      {(a.reasons || []).map((r) => <span key={r} className="reason-tag">{r}</span>)}
                      <br />
                      <strong>Risk Score:</strong> {a.risk_score} &nbsp;|&nbsp;
                      <strong>Alert ID:</strong> <code style={{ fontSize: '0.75rem' }}>{a.id}</code>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="pagination-bar">
        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
          Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
        </span>
        <div className="pagination-btns">
          <button className="page-btn" disabled={offset === 0} onClick={() => onPage(offset - limit)}>← Prev</button>
          <button className="page-btn" disabled={offset + limit >= total} onClick={() => onPage(offset + limit)}>Next →</button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN CUSTOMER DASHBOARD
// ═══════════════════════════════════════════════════════════════
export default function CustomerDashboard() {
  const navigate = useNavigate();
  const companyId = localStorage.getItem('siem_company');
  const companyName = localStorage.getItem('siem_company_name') || companyId;

  const [stats, setStats] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [alertsData, setAlertsData] = useState({ alerts: [], total: 0 });
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;

  const [loading, setLoading] = useState(true);
  const [showNormal, setShowNormal] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [secAgo, setSecAgo] = useState(0);

  const load = useCallback(async () => {
    try {
      const [s, tl, al] = await Promise.all([
        fetchDashboardStats(companyId),
        fetchAlertsTimeline(companyId),
        fetchAlerts(companyId, LIMIT, offset),
      ]);
      setStats(s);
      setTimeline(tl);
      setAlertsData(al);
      setLastUpdated(Date.now());
      setSecAgo(0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [companyId, offset]);

  // Initial load + 30s auto-refresh
  useEffect(() => {
    if (!localStorage.getItem('siem_token')) { navigate('/login'); return; }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load, navigate]);

  // "X seconds ago" counter
  useEffect(() => {
    const t = setInterval(() => setSecAgo((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [lastUpdated]);

  const handleLogout = () => { localStorage.clear(); navigate('/login'); };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p style={{ color: '#94a3b8' }}>Loading intelligence layer…</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* ── Top Bar ── */}
      <div className="topbar">
        <div>
          <h1 className="topbar-title">🛡️ {companyName}</h1>
          <p className="topbar-sub">SIEM Dashboard · {companyId}</p>
        </div>
        <div className="topbar-right">
          <span className="live-badge">🔴 LIVE</span>
          <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
            Updated {secAgo}s ago
          </span>
          <button className="btn-secondary" onClick={() => downloadReport(companyId)}>
            📄 Report
          </button>
          <button className="btn-danger" onClick={handleLogout}>Logout</button>
        </div>
      </div>

      {/* ── Section 1: Metric Cards ── */}
      <div className="metrics-row">
        <MetricCard label="Total Alerts" value={stats?.total_alerts} icon="📊" accent="#3b82f6" />
        <MetricCard label="Critical" value={stats?.critical_alerts} icon="🔴" accent="#ef4444" />
        <MetricCard label="High Risk" value={stats?.high_alerts} icon="🟠" accent="#f97316" />
        <MetricCard label="Unique IPs" value={stats?.unique_ips} icon="🌐" accent="#8b5cf6" />
        <MetricCard label="Affected Users" value={stats?.unique_users_affected} icon="👤" accent="#eab308" />
      </div>

      {/* ── Section 2: Charts ── */}
      <div className="charts-grid">
        <RiskChart distribution={stats?.risk_distribution} />
        <AttackChart topAttacks={stats?.top_attack_types} />
        <TimelineChart timeline={timeline} />
      </div>

      {/* ── Section 3: Threat Map ── */}
      <div className="charts-grid" style={{ marginBottom: '2rem' }}>
        <ThreatMap
          alerts={alertsData.alerts}
          showNormal={showNormal}
          onToggleNormal={() => setShowNormal(!showNormal)}
        />
      </div>

      {/* ── Section 4: Alerts Table ── */}
      <AlertsTable
        alerts={alertsData.alerts}
        total={alertsData.total || 0}
        limit={LIMIT}
        offset={offset}
        onPage={(newOffset) => setOffset(Math.max(0, newOffset))}
      />
    </div>
  );
}

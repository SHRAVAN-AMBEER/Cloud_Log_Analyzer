import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement,
} from 'chart.js';
import { Doughnut, Bar, Line } from 'react-chartjs-2';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';
import { Target, Zap, TrendingUp, Globe, Search, Shield, Activity, AlertCircle, AlertTriangle, Network, Users, FileText, LogOut, Download } from 'lucide-react';

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
function MetricCard({ label, value, icon, accent, onClick, isActive }) {
  return (
    <div 
      className={`metric-card ${isActive ? 'active' : ''}`} 
      style={{ 
        '--card-accent': accent || 'var(--primary-color)',
        cursor: onClick ? 'pointer' : 'default'
      }}
      onClick={onClick}
    >
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
      <h2><Target size={20} /> Risk Distribution</h2>
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
      <h2><Zap size={20} /> Top Attack Types</h2>
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
      <h2><TrendingUp size={20} /> 30-Day Alert Timeline</h2>
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
        <h2 style={{ margin: 0 }}><Globe size={24} /> Threat Origin Map</h2>
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

// ── Threat Intel Feed ────────────────────────────────────────
function ThreatIntelFeed({ alerts }) {
  const criticalAlerts = alerts.filter(a => ['CRITICAL', 'HIGH'].includes(a.risk_level)).slice(0, 10);
  
  if (criticalAlerts.length === 0) return null;

  return (
    <div className="threat-feed-container" style={{ marginBottom: '2.5rem', background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '12px', padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden' }}>
      <div style={{ fontWeight: 'bold', color: '#ef4444', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '0.5rem', zIndex: 2, background: 'var(--bg-dark)', paddingRight: '1rem' }}>
        <Zap size={18} /> LIVE THREAT INTEL:
      </div>
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        <div className="marquee-scroll" style={{ display: 'flex', gap: '3rem', whiteSpace: 'nowrap' }}>
          {criticalAlerts.map((a, i) => (
            <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ color: '#fca5a5' }}>[{a.timestamp?.slice(11, 19)}]</span>
              <span style={{ color: '#f8fafc' }}>{a.alert_type} detected from</span>
              <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{a.ip}</span>
              <span style={{ color: '#94a3b8' }}>target: {a.user_id}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Alerts & Logs Table ──────────────────────────────────────
function DataPanel({ 
  alerts, logs, total, limit, offset, onPage, 
  viewMode, setViewMode, search, setSearch,
  sortKey, toggleSort, sortAsc, expanded, setExpanded,
  filteredAlerts, filteredLogs, groupedByIP, groupedByUser
}) {
  let DataToDisplay = [];
  if (viewMode === 'alerts') DataToDisplay = filteredAlerts;
  else if (viewMode === 'logs') DataToDisplay = filteredLogs;
  else if (viewMode === 'ips') DataToDisplay = groupedByIP;
  else if (viewMode === 'users') DataToDisplay = groupedByUser;
  
  const SortIcon = ({ k }) => sortKey === k ? (sortAsc ? ' ↑' : ' ↓') : ' ⇅';

  const formatIST = (ts) => {
    if (!ts) return '—';
    try {
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: 'Asia/Kolkata',
        year: 'numeric', month: 'short', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: true
      }).format(new Date(ts));
    } catch (e) {
      return ts.slice(0, 19).replace('T', ' ');
    }
  };

  return (
    <div className="data-table-container" style={{ gridColumn: '1 / -1' }}>
      <div className="table-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '2rem' }}>
          <h2 
            className={`table-tab ${viewMode === 'alerts' ? 'active' : ''}`}
            onClick={() => setViewMode('alerts')}
            style={{ cursor: 'pointer', margin: 0, paddingBottom: '0.5rem', borderBottom: viewMode === 'alerts' ? '2px solid var(--primary-color)' : '2px solid transparent' }}
          >
            <Shield size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
            Security Threats
          </h2>
          <h2 
            className={`table-tab ${viewMode === 'logs' ? 'active' : ''}`}
            onClick={() => setViewMode('logs')}
            style={{ cursor: 'pointer', margin: 0, paddingBottom: '0.5rem', borderBottom: viewMode === 'logs' ? '2px solid var(--primary-color)' : '2px solid transparent' }}
          >
            <FileText size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
            Raw System Logs
          </h2>
          <h2 
            className={`table-tab ${viewMode === 'ips' ? 'active' : ''}`}
            onClick={() => setViewMode('ips')}
            style={{ cursor: 'pointer', margin: 0, paddingBottom: '0.5rem', borderBottom: viewMode === 'ips' ? '2px solid var(--primary-color)' : '2px solid transparent' }}
          >
            <Network size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
            Unique IPs
          </h2>
          <h2 
            className={`table-tab ${viewMode === 'users' ? 'active' : ''}`}
            onClick={() => setViewMode('users')}
            style={{ cursor: 'pointer', margin: 0, paddingBottom: '0.5rem', borderBottom: viewMode === 'users' ? '2px solid var(--primary-color)' : '2px solid transparent' }}
          >
            <Users size={20} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
            Affected Users
          </h2>
        </div>
        
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className="search-box">
            <Search size={16} style={{ position: 'absolute', marginLeft: '12px', marginTop: '10px', color: 'var(--text-muted)' }} />
            <input
              className="search-input"
              style={{ paddingLeft: '2.5rem' }}
              placeholder={`Search ${viewMode}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button 
            onClick={() => {
              if (DataToDisplay.length === 0) return;
              const keys = Object.keys(DataToDisplay[0]).filter(k => typeof DataToDisplay[0][k] !== 'object');
              const csv = [keys.join(','), ...DataToDisplay.map(row => keys.map(k => `"${row[k] || ''}"`).join(','))].join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `SIEM_${viewMode}_export.csv`;
              a.click();
            }}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', background: '#1e293b', border: '1px solid #334155', color: '#f8fafc', borderRadius: '8px', cursor: 'pointer' }}
          >
            <Download size={16} /> Export CSV
          </button>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="styled-table">
          <thead>
            {viewMode === 'alerts' && (
              <tr>
                {[['timestamp', 'Time'], ['user_id', 'User'], ['ip', 'IP'], ['country', 'Country'], ['risk_level', 'Risk'], ['alert_type', 'Attack Type']].map(([k, label]) => (
                  <th key={k} onClick={() => toggleSort(k)} style={{ cursor: 'pointer' }}>{label}<SortIcon k={k} /></th>
                ))}
                <th>Reasons</th>
              </tr>
            )}
            {viewMode === 'logs' && (
              <tr>
                {[['timestamp', 'Timestamp'], ['user_id', 'User'], ['ip', 'IP Address'], ['log_source', 'Source'], ['login_status', 'Status']].map(([k, label]) => (
                  <th key={k} onClick={() => toggleSort(k)} style={{ cursor: 'pointer' }}>{label}<SortIcon k={k} /></th>
                ))}
              </tr>
            )}
            {viewMode === 'ips' && (
              <tr>
                <th>IP Address</th><th>Country</th><th>Total Attacks</th><th>Threat Types</th><th>Last Seen</th>
              </tr>
            )}
            {viewMode === 'users' && (
              <tr>
                <th>User ID</th><th>Total Attacks</th><th>Associated IPs</th><th>Threat Types</th><th>Last Seen</th>
              </tr>
            )}
          </thead>
          <tbody>
            {DataToDisplay.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>No {viewMode} records found</td></tr>
            )}
            
            {viewMode === 'alerts' && filteredAlerts.map((a, idx) => (
                <React.Fragment key={a.id || idx}>
                  <tr style={{ cursor: 'pointer' }} onClick={() => setExpanded(expanded === idx ? null : idx)}>
                    <td className="text-muted">{formatIST(a.timestamp)}</td>
                    <td>
                      <div className="user-cell">
                        <div className="user-avatar">{(a.user_id || 'U')[0].toUpperCase()}</div>
                        {a.user_id}
                      </div>
                    </td>
                    <td className="font-mono">{a.ip}</td>
                    <td>{a.country || '—'}</td>
                    <td><span className={`badge badge-${a.risk_level}`}>{a.risk_level}</span></td>
                    <td className="text-muted">{a.alert_type}</td>
                    <td>
                      {(a.reasons || []).slice(0, 2).map((r) => <span key={r} className="reason-tag">{r}</span>)}
                    </td>
                  </tr>
                  {expanded === idx && (
                    <tr className="expanded-row-tr">
                      <td colSpan={7} className="expanded-row">
                        <div className="expanded-content">
                          <strong>Full Reasons:</strong> {(a.reasons || []).map(r => <span key={r} className="reason-tag">{r}</span>)}
                          <div style={{ marginTop: '0.5rem' }}>
                            <strong>Risk Score:</strong> <span style={{ color: 'var(--accent-orange)' }}>{a.risk_score}</span> | 
                            <strong> Alert ID:</strong> <code>{a.id}</code>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
            ))}

            {viewMode === 'logs' && filteredLogs.map((l, idx) => (
                <tr key={l.log_id || idx}>
                  <td className="text-muted">{formatIST(l.timestamp)}</td>
                  <td className="font-mono">{l.user_id}</td>
                  <td className="font-mono">{l.ip}</td>
                  <td><span className="badge-outline">{l.log_source}</span></td>
                  <td><span className={`badge ${l.login_status === 'success' ? 'badge-LOW' : 'badge-CRITICAL'}`}>{l.login_status}</span></td>
                </tr>
            ))}

            {viewMode === 'ips' && groupedByIP.map((g, idx) => (
                <tr key={idx}>
                  <td className="font-mono">{g.ip}</td>
                  <td>{g.country || '—'}</td>
                  <td><span className="badge badge-CRITICAL">{g.count}</span></td>
                  <td>{g.types.map(t => <span key={t} className="reason-tag">{t}</span>)}</td>
                  <td className="text-muted">{formatIST(g.last_seen)}</td>
                </tr>
            ))}

            {viewMode === 'users' && groupedByUser.map((g, idx) => (
                <tr key={idx}>
                  <td>
                    <div className="user-cell">
                      <div className="user-avatar">{(g.user_id || 'U')[0].toUpperCase()}</div>
                      {g.user_id}
                    </div>
                  </td>
                  <td><span className="badge badge-CRITICAL">{g.count}</span></td>
                  <td className="font-mono text-muted">{g.ips.join(', ')}</td>
                  <td>{g.types.map(t => <span key={t} className="reason-tag">{t}</span>)}</td>
                  <td className="text-muted">{formatIST(g.last_seen)}</td>
                </tr>
            ))}
          </tbody>
        </table>
      </div>

      {viewMode === 'alerts' && (
        <div className="pagination-bar">
          <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}</span>
          <div className="pagination-btns">
            <button className="page-btn" disabled={offset === 0} onClick={() => onPage(offset - limit)}>← Prev</button>
            <button className="page-btn" disabled={offset + limit >= total} onClick={() => onPage(offset + limit)}>Next →</button>
          </div>
        </div>
      )}
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
  const [activeFilter, setActiveFilter] = useState(null); // 'CRITICAL', 'HIGH', 'IP', 'USER'
  const LIMIT = 50;

  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [secAgo, setSecAgo] = useState(0);
  const [showNormal, setShowNormal] = useState(false);

  // Data Panel State
  const [viewMode, setViewMode] = useState('alerts'); // 'alerts' or 'logs'
  const [rawLogs, setRawLogs] = useState([]);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('timestamp');
  const [sortAsc, setSortAsc] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const filteredAlerts = (alertsData.alerts || [])
    .filter((a) => {
      const matchSearch = [a.user_id, a.ip, a.country, a.risk_level, a.alert_type].join(' ').toLowerCase().includes(search.toLowerCase());
      if (!matchSearch) return false;
      
      if (activeFilter === 'CRITICAL' && a.risk_level !== 'CRITICAL') return false;
      if (activeFilter === 'HIGH' && a.risk_level !== 'HIGH') return false;
      return true;
    })
    .sort((a, b) => {
      const av = a[sortKey] || ''; const bv = b[sortKey] || '';
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });

  const filteredLogs = rawLogs
    .filter((l) => {
      const matchSearch = [l.user_id, l.ip, l.log_source, l.login_status].join(' ').toLowerCase().includes(search.toLowerCase());
      if (!matchSearch) return false;

      if (activeFilter === 'CRITICAL' || activeFilter === 'HIGH') return false;
      return true;
    })
    .sort((a, b) => {
      const av = a[sortKey] || ''; const bv = b[sortKey] || '';
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });

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

      // Fetch Raw Logs
      const logsRes = await fetch(`${window.location.origin.replace(':5173', ':5000')}/api/logs?tenant=${companyId}&limit=50`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('siem_token')}` }
      });
      if (logsRes.ok) {
        const data = await logsRes.json();
        setRawLogs(data);
      }

      setLastUpdated(Date.now());
      setSecAgo(0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [companyId, offset]);

  // Compute grouped views based on current alerts
  const groupedByIP = Object.values(
    (alertsData.alerts || []).reduce((acc, a) => {
      if (!acc[a.ip]) {
        acc[a.ip] = { ip: a.ip, country: a.country, count: 0, types: new Set(), last_seen: a.timestamp };
      }
      acc[a.ip].count += 1;
      acc[a.ip].types.add(a.alert_type);
      if (a.timestamp > acc[a.ip].last_seen) acc[a.ip].last_seen = a.timestamp;
      return acc;
    }, {})
  ).map(g => ({ ...g, types: Array.from(g.types) })).sort((a, b) => b.count - a.count);

  const groupedByUser = Object.values(
    (alertsData.alerts || []).reduce((acc, a) => {
      if (!acc[a.user_id]) {
        acc[a.user_id] = { user_id: a.user_id, count: 0, ips: new Set(), types: new Set(), last_seen: a.timestamp };
      }
      acc[a.user_id].count += 1;
      acc[a.user_id].ips.add(a.ip);
      acc[a.user_id].types.add(a.alert_type);
      if (a.timestamp > acc[a.user_id].last_seen) acc[a.user_id].last_seen = a.timestamp;
      return acc;
    }, {})
  ).map(g => ({ ...g, ips: Array.from(g.ips), types: Array.from(g.types) })).sort((a, b) => b.count - a.count);

  // Initial load + 1s auto-refresh
  useEffect(() => {
    if (!localStorage.getItem('siem_token')) { navigate('/login'); return; }
    load();
    const interval = setInterval(load, 1000);
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
        <div className="topbar-left">
          <Shield size={36} color="var(--primary-color)" />
          <div>
            <h1 className="topbar-title">{companyName}</h1>
            <p className="topbar-sub">SIEM Dashboard · {companyId}</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className="live-badge">🔴 LIVE</span>
          <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
            Updated {secAgo}s ago
          </span>
          <button className="btn-secondary" onClick={() => downloadReport(companyId)}>
            <FileText size={16} /> Report
          </button>
          <button className="btn-danger" onClick={handleLogout}><LogOut size={16} /> Logout</button>
        </div>
      </div>

      {/* ── Metric Cards ── */}
      <div className="metrics-row">
        <MetricCard 
          label="Critical Attacks" 
          value={stats?.critical_alerts} 
          icon={<AlertTriangle />} 
          accent="var(--accent-red)" 
          onClick={() => { setActiveFilter(activeFilter === 'CRITICAL' ? null : 'CRITICAL'); setViewMode('alerts'); }}
          isActive={activeFilter === 'CRITICAL'}
        />
        <MetricCard 
          label="High Risk Attacks" 
          value={stats?.high_alerts} 
          icon={<AlertCircle />} 
          accent="var(--accent-orange)" 
          onClick={() => { setActiveFilter(activeFilter === 'HIGH' ? null : 'HIGH'); setViewMode('alerts'); }}
          isActive={activeFilter === 'HIGH'}
        />
        <MetricCard 
          label="Unique IPs" 
          value={stats?.unique_ips} 
          icon={<Network />} 
          accent="var(--accent-blue)" 
          onClick={() => { setActiveFilter(activeFilter === 'IP' ? null : 'IP'); setViewMode('alerts'); setSortKey('ip'); }}
          isActive={activeFilter === 'IP'}
        />
        <MetricCard 
          label="Affected Users" 
          value={stats?.unique_users_affected} 
          icon={<Users />} 
          accent="var(--accent-purple)" 
          onClick={() => { setActiveFilter(activeFilter === 'USER' ? null : 'USER'); setViewMode('users'); }}
          isActive={activeFilter === 'USER'}
        />
      </div>

      <ThreatIntelFeed alerts={alertsData.alerts || []} />

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

      {/* ── Section 4: Alerts & Logs ── */}
      <DataPanel
        viewMode={viewMode} setViewMode={setViewMode}
        search={search} setSearch={setSearch}
        sortKey={sortKey} toggleSort={toggleSort} sortAsc={sortAsc}
        expanded={expanded} setExpanded={setExpanded}
        alerts={alertsData.alerts} logs={rawLogs}
        filteredAlerts={filteredAlerts} filteredLogs={filteredLogs}
        groupedByIP={groupedByIP} groupedByUser={groupedByUser}
        total={alertsData.total || 0}
        limit={LIMIT}
        offset={offset}
        onPage={(newOffset) => setOffset(Math.max(0, newOffset))}
      />
    </div>
  );
}

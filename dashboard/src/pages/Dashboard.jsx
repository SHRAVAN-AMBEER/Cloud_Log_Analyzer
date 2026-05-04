import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement 
} from 'chart.js';
import { Globe, Building, Activity, FileText, ArrowLeft, LogOut } from 'lucide-react';

import { DashboardHeader } from '../components/DashboardHeader';
import { MetricsRow } from '../components/MetricsRow';
import { RiskDistributionChart } from '../components/RiskDistributionChart';
import { TopUsersChart } from '../components/TopUsersChart';
import { AlertsTable } from '../components/AlertsTable';
import { ThreatMap } from '../components/ThreatMap';
import { fetchAlerts, downloadReport } from '../services/api';

import '../styles/main.css';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

export default function Dashboard() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const role = localStorage.getItem('siem_role');
  const [selectedTenant, setSelectedTenant] = useState(role === 'super_admin' ? null : 'ALL');

  useEffect(() => {
    const token = localStorage.getItem('siem_token');
    if (!token) {
      navigate('/login');
      return;
    }

    if (selectedTenant) {
      setLoading(true);
      const getAlerts = async () => {
        const data = await fetchAlerts(role === 'super_admin' ? selectedTenant : null);
        setAlerts(data);
        setLoading(false);
      };
      getAlerts();
    }
  }, [navigate, selectedTenant, role]);

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  if (!selectedTenant && role === 'super_admin') {
    return (
      <div className="dashboard-container" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <DashboardHeader />
        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <h2 style={{ fontSize: '2rem', marginBottom: '1rem', color: 'var(--text-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Globe size={32} style={{marginRight: '1rem', color: 'var(--primary-color)'}}/> Super Admin: Select Tenant Instance</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '3rem' }}>Select a subscriber to view their isolated intelligence dashboard.</p>
          
          <div style={{ display: 'flex', gap: '2rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            {['HOSPITAL', 'RETAIL'].map(tenant => (
              <div 
                key={tenant}
                onClick={() => setSelectedTenant(tenant)}
                style={{
                  background: 'var(--bg-card)', padding: '3rem 4rem', borderRadius: '1rem', border: '1px solid var(--border-color)',
                  cursor: 'pointer', transition: 'all 0.3s ease', minWidth: '250px'
                }}
                onMouseOver={e => e.currentTarget.style.borderColor = 'var(--primary-color)'}
                onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-color)'}
              >
                <div style={{ fontSize: '3rem', marginBottom: '1rem', color: 'var(--accent-blue)' }}>{tenant === 'HOSPITAL' ? <Activity size={48} /> : <Building size={48} />}</div>
                <h3 style={{ fontSize: '1.5rem', margin: 0, color: 'var(--text-light)' }}>{tenant} Network</h3>
                <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontSize: '0.9rem' }}>View isolated SIEM data</p>
              </div>
            ))}
          </div>
          <button 
            onClick={handleLogout}
            style={{ marginTop: '4rem', padding: '0.75rem 2rem', background: 'transparent', border: '1px solid var(--danger-color)', color: 'var(--danger-color)', borderRadius: '0.5rem', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <LogOut size={18} /> Sign Out
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p style={{ color: 'var(--text-muted)' }}>Initializing Intelligence Layer for {selectedTenant}...</p>
      </div>
    );
  }

  const totalAlerts = alerts.length;
  const highRiskAlerts = alerts.filter(a => ['HIGH', 'CRITICAL'].includes(a.risk_level)).length;
  const uniqueUsers = new Set(alerts.map(a => a.user_id)).size;

  return (
    <div className="dashboard-container">
      <DashboardHeader />
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 style={{ margin: 0 }}>
          {role === 'super_admin' ? (
            <span style={{ color: 'var(--warning-color)' }}>[GOD MODE: {selectedTenant}]</span>
          ) : (
            <span style={{ color: 'var(--success-color)' }}>[TENANT MODE: {localStorage.getItem('siem_company')}]</span>
          )}
        </h2>
        <div>
          {role === 'super_admin' && (
            <button onClick={() => setSelectedTenant(null)} className="btn-primary" style={{ marginRight: '1rem', background: 'var(--bg-card)', color: 'var(--text-main)', border: '1px solid var(--border-color)' }}>
              <ArrowLeft size={16} /> Back to Tenants
            </button>
          )}
          <button onClick={() => downloadReport(selectedTenant)} className="btn-primary" style={{ marginRight: '1rem' }}>
            <FileText size={18} /> Download Threat Report
          </button>
          <button onClick={handleLogout} className="btn-danger">
            <LogOut size={18} /> Logout
          </button>
        </div>
      </div>

      <MetricsRow totalAlerts={totalAlerts} highRiskAlerts={highRiskAlerts} uniqueUsers={uniqueUsers} />

      <div className="charts-grid">
        <RiskDistributionChart alerts={alerts} />
        <TopUsersChart alerts={alerts} />
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <ThreatMap alerts={alerts} />
      </div>

      <AlertsTable alerts={alerts} />
    </div>
  );
}

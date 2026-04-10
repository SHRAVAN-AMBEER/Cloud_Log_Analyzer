import React from 'react';
import { ShieldAlert, Activity, Users } from 'lucide-react';

export const MetricsRow = ({ totalAlerts, highRiskAlerts, uniqueUsers }) => (
  <div className="metrics-row">
    <div className="metric-card">
      <div className="metric-icon" style={{ background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-blue)' }}>
        <Activity size={24} />
      </div>
      <h3>Total Alerts</h3>
      <p className="metric-value">{totalAlerts}</p>
    </div>
    
    <div className="metric-card high-risk">
      <div className="metric-icon" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-red)' }}>
        <ShieldAlert size={24} />
      </div>
      <h3>High Risk Alerts</h3>
      <p className="metric-value">{highRiskAlerts}</p>
    </div>

    <div className="metric-card">
      <div className="metric-icon" style={{ background: 'rgba(167, 139, 250, 0.1)', color: '#a78bfa' }}>
        <Users size={24} />
      </div>
      <h3>Affected Users</h3>
      <p className="metric-value">{uniqueUsers}</p>
    </div>
  </div>
);

import React, { useState, useEffect } from 'react';
import { 
  Chart as ChartJS, 
  ArcElement, 
  Tooltip, 
  Legend, 
  CategoryScale, 
  LinearScale, 
  BarElement 
} from 'chart.js';

import { DashboardHeader } from './components/DashboardHeader';
import { MetricsRow } from './components/MetricsRow';
import { RiskDistributionChart } from './components/RiskDistributionChart';
import { TopUsersChart } from './components/TopUsersChart';
import { AlertsTable } from './components/AlertsTable';
import { fetchAlerts } from './services/api';

import './styles/main.css';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

function App() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getAlerts = async () => {
      const data = await fetchAlerts();
      setAlerts(data);
      setLoading(false);
    };
    getAlerts();
  }, []);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p style={{ color: 'var(--text-muted)' }}>Initializing Intelligence Layer...</p>
      </div>
    );
  }

  // Statistics
  const totalAlerts = alerts.length;
  const highRiskAlerts = alerts.filter(a => ['HIGH', 'CRITICAL'].includes(a.risk_level)).length;
  const uniqueUsers = new Set(alerts.map(a => a.user_id)).size;

  return (
    <div className="dashboard-container">
      <DashboardHeader />

      <MetricsRow 
        totalAlerts={totalAlerts} 
        highRiskAlerts={highRiskAlerts} 
        uniqueUsers={uniqueUsers} 
      />

      <div className="charts-grid">
        <RiskDistributionChart alerts={alerts} />
        <TopUsersChart alerts={alerts} />
      </div>

      <AlertsTable alerts={alerts} />
    </div>
  );
}

export default App;

import React from 'react';
import { Pie } from 'react-chartjs-2';

export const RiskDistributionChart = ({ alerts }) => {
  const riskCounts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  alerts.forEach(a => { if (riskCounts[a.risk_level] !== undefined) riskCounts[a.risk_level]++; });
  
  const data = {
    labels: ['Low', 'Medium', 'High', 'Critical'],
    datasets: [{
      data: [riskCounts.LOW, riskCounts.MEDIUM, riskCounts.HIGH, riskCounts.CRITICAL],
      backgroundColor: [
        'rgba(34, 197, 94, 0.7)',
        'rgba(234, 179, 8, 0.7)',
        'rgba(239, 68, 68, 0.7)',
        'rgba(153, 27, 27, 0.7)'
      ],
      borderColor: ['#22c55e', '#eab308', '#ef4444', '#991b1b'],
      borderWidth: 1,
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'right', labels: { color: '#f8fafc' } } }
  };

  return (
    <div className="chart-panel">
      <h2>Risk Level Distribution</h2>
      <div className="chart-wrapper">
        <Pie data={data} options={options} />
      </div>
    </div>
  );
};

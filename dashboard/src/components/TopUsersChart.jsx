import React from 'react';
import { Bar } from 'react-chartjs-2';

export const TopUsersChart = ({ alerts }) => {
  const userScores = {};
  alerts.forEach(a => {
    if (!userScores[a.user_id] || a.risk_score > userScores[a.user_id]) {
      userScores[a.user_id] = a.risk_score;
    }
  });
  
  const topUsers = Object.keys(userScores)
    .sort((a, b) => userScores[b] - userScores[a])
    .slice(0, 10);

  const data = {
    labels: topUsers,
    datasets: [{
      label: 'Max Risk Score',
      data: topUsers.map(u => userScores[u]),
      backgroundColor: topUsers.map(u => 
        userScores[u] >= 85 ? 'rgba(239, 68, 68, 0.7)' : 
        userScores[u] >= 60 ? 'rgba(234, 179, 8, 0.7)' : 'rgba(34, 197, 94, 0.7)'
      ),
      borderRadius: 6,
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' }, max: 100 },
      x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
    },
    plugins: { legend: { display: false } }
  };

  return (
    <div className="chart-panel">
      <h2>Top Users by Risk Score</h2>
      <div className="chart-wrapper">
        <Bar data={data} options={options} />
      </div>
    </div>
  );
};

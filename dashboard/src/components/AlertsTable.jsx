import React from 'react';

export const AlertsTable = ({ alerts }) => (
  <div className="data-table-container">
    <div className="table-header">
      <h2>Recent Alerts Log</h2>
    </div>
    <div style={{ overflowX: 'auto' }}>
      <table className="styled-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Timestamp</th>
            <th>Log Source</th>
            <th>Risk Score</th>
            <th>Risk Level</th>
            <th>Trigger Reasons</th>
          </tr>
        </thead>
        <tbody>
          {alerts.slice().reverse().map((alert, idx) => (
            <tr key={alert.id || idx}>
              <td>
                <div className="user-cell">
                  <div className="user-avatar">
                    {alert.user_id.charAt(0).toUpperCase()}
                  </div>
                  <span>{alert.user_id}</span>
                </div>
              </td>
              <td style={{ color: 'var(--text-muted)' }}>
                {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'N/A'}
              </td>
              <td>
                {alert.log_sources && alert.log_sources.length > 0 ? (
                  alert.log_sources.map((s, i) => <span key={i} className="reason-tag" style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.3)' }}>{s.replace(/_/g, ' ')}</span>)
                ) : (
                  <span className="reason-tag" style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.3)' }}>Custom API</span>
                )}
              </td>
              <td>
                <span style={{ fontWeight: 600 }}>{alert.risk_score}</span>
              </td>
              <td>
                <span className={`badge badge-${alert.risk_level}`}>
                  {alert.risk_level}
                </span>
              </td>
              <td>
                {alert.reasons && alert.reasons.length > 0 ? (
                  alert.reasons.map((r, i) => <span key={i} className="reason-tag">{r.replace(/_/g, ' ')}</span>)
                ) : (
                  <span className="reason-tag">rule_based</span>
                )}
              </td>
            </tr>
          ))}
          {alerts.length === 0 && (
            <tr>
              <td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                No alerts detected. The system is secure.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);

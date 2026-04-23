import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * CompanySelector — dropdown for super admin to switch tenant context.
 * Props:
 *   companies  — array of { company_id, company_name, industry }
 *   selected   — currently selected company_id (or 'ALL')
 *   onChange   — (company_id) => void
 */

const INDUSTRY_ICONS = {
  Healthcare: '🏥', Retail: '🛒', Finance: '💰', Education: '🎓',
  Logistics: '🚚', Insurance: '🛡️', Technology: '💻', Other: '🏢',
};

export default function CompanySelector({ companies = [], selected, onChange }) {
  return (
    <div className="company-selector">
      <label style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '0.25rem', display: 'block' }}>
        Switch Company
      </label>
      <select
        value={selected || 'ALL'}
        onChange={(e) => onChange(e.target.value)}
        className="login-input login-select"
        style={{ minWidth: 200 }}
      >
        <option value="ALL">🌍 All Companies</option>
        {companies.map((c) => (
          <option key={c.company_id} value={c.company_id}>
            {INDUSTRY_ICONS[c.industry] || '🏢'} {c.company_name}
          </option>
        ))}
      </select>
    </div>
  );
}

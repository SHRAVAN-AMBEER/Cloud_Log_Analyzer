import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { registerCompany } from '../services/api';
import '../styles/main.css';

const INDUSTRIES = [
  'Healthcare', 'Retail', 'Finance', 'Education',
  'Logistics', 'Insurance', 'Technology', 'Other',
];

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    company_name: '', industry: 'Healthcare',
    email: '', password: '', confirm: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [apiKeyModal, setApiKeyModal] = useState(null); // { api_key, company_id }
  const [copied, setCopied] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const validate = () => {
    const errs = {};
    if (!form.company_name.trim()) errs.company_name = 'Company name is required';
    if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      errs.email = 'Valid email is required';
    if (!form.password) errs.password = 'Password is required';
    if (form.password !== form.confirm) errs.confirm = 'Passwords do not match';
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      const data = await registerCompany({
        company_name: form.company_name,
        industry: form.industry,
        email: form.email,
        password: form.password,
      });
      setApiKeyModal({ api_key: data.api_key, company_id: data.company_id });
    } catch (err) {
      setErrors({ global: err.message || 'Registration failed' });
    } finally {
      setLoading(false);
    }
  };

  const copyKey = () => {
    navigator.clipboard.writeText(apiKeyModal.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="login-bg">
      <div className="login-orb orb-1" />
      <div className="login-orb orb-2" />

      {/* Success modal */}
      {apiKeyModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div style={{ fontSize: '3rem', textAlign: 'center' }}>🎉</div>
            <h2 style={{ textAlign: 'center', color: '#f8fafc', margin: '0.5rem 0' }}>
              Welcome to the platform!
            </h2>
            <p style={{ textAlign: 'center', color: '#94a3b8', marginBottom: '1.5rem' }}>
              Company ID: <strong style={{ color: '#60a5fa' }}>{apiKeyModal.company_id}</strong>
            </p>

            <div className="apikey-warning">
              ⚠️ <strong>Save this API key now — it will never be shown again!</strong>
            </div>

            <div className="apikey-box">
              <code style={{ wordBreak: 'break-all', color: '#fbbf24', fontSize: '0.85rem' }}>
                {apiKeyModal.api_key}
              </code>
            </div>

            <button className="modal-btn-copy" onClick={copyKey}>
              {copied ? '✅ Copied!' : '📋 Copy API Key'}
            </button>
            <button className="modal-btn-go" onClick={() => navigate('/login')}>
              Go to Login →
            </button>
          </div>
        </div>
      )}

      <div className="login-card" style={{ maxWidth: '520px' }}>
        <div className="login-logo">
          <span className="login-shield">🛡️</span>
          <h1 className="login-title">Create an Account</h1>
          <p className="login-subtitle">Join the Cloud Log Analyzer platform</p>
        </div>

        {errors.global && <div className="login-error">{errors.global}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="register-row">
            <div className="login-field">
              <label>Company Name</label>
              <input
                className={`login-input ${errors.company_name ? 'input-error' : ''}`}
                value={form.company_name}
                onChange={set('company_name')}
                placeholder="Acme Healthcare Ltd."
              />
              {errors.company_name && <span className="field-error">{errors.company_name}</span>}
            </div>

            <div className="login-field">
              <label>Industry</label>
              <select
                className="login-input login-select"
                value={form.industry}
                onChange={set('industry')}
              >
                {INDUSTRIES.map((i) => (
                  <option key={i} value={i}>{i}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="login-field">
            <label>Email</label>
            <input
              className={`login-input ${errors.email ? 'input-error' : ''}`}
              type="email"
              value={form.email}
              onChange={set('email')}
              placeholder="security@company.com"
            />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </div>

          <div className="register-row">
            <div className="login-field">
              <label>Password</label>
              <input
                className={`login-input ${errors.password ? 'input-error' : ''}`}
                type="password"
                value={form.password}
                onChange={set('password')}
                placeholder="••••••••"
              />
              {errors.password && <span className="field-error">{errors.password}</span>}
            </div>
            <div className="login-field">
              <label>Confirm Password</label>
              <input
                className={`login-input ${errors.confirm ? 'input-error' : ''}`}
                type="password"
                value={form.confirm}
                onChange={set('confirm')}
                placeholder="••••••••"
              />
              {errors.confirm && <span className="field-error">{errors.confirm}</span>}
            </div>
          </div>

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? <span className="login-spinner" /> : 'Register Company →'}
          </button>
        </form>

        <div className="login-footer">
          Already have an account?{' '}
          <Link to="/login" className="login-link">Sign in →</Link>
        </div>
      </div>
    </div>
  );
}

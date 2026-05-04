import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { loginUser, loginWithApiKey } from '../services/api';
import { Shield, Key, Zap, ArrowRight, AlertCircle } from 'lucide-react';
import '../styles/main.css';

export default function Login() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('credentials'); // 'credentials' | 'apikey'
  const [companyId, setCompanyId] = useState('');
  const [password, setPassword] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (localStorage.getItem('siem_token')) {
      const role = localStorage.getItem('siem_role');
      navigate(role === 'super_admin' ? '/admin' : '/dashboard');
    }
  }, [navigate]);

  const storeAndRedirect = (data) => {
    localStorage.setItem('siem_token', data.token);
    localStorage.setItem('siem_role', data.role);
    localStorage.setItem('siem_company', data.company_id);
    localStorage.setItem('siem_company_name', data.company_name || '');
    navigate(data.role === 'super_admin' ? '/admin' : '/dashboard');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      let data;
      if (tab === 'apikey') {
        data = await loginWithApiKey(apiKey);
      } else {
        // support superadmin username too
        if (companyId === 'superadmin') {
          const res = await fetch(
            (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000') + '/api/login',
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ username: 'superadmin', password }),
            }
          );
          data = await res.json();
          if (!res.ok) throw new Error(data.error || 'Login failed');
        } else {
          data = await loginUser(companyId, password);
        }
      }
      storeAndRedirect(data);
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const canSubmit =
    !loading &&
    (tab === 'credentials' ? companyId && password : apiKey);

  return (
    <div className="login-bg">
      {/* Animated gradient orbs */}
      <div className="login-orb orb-1" />
      <div className="login-orb orb-2" />

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <Shield size={48} />
          <h1 className="login-title">Cloud Log Analyzer</h1>
          <p className="login-subtitle">Enterprise Multi-Tenant SIEM Platform</p>
        </div>

        {/* Tabs */}
        <div className="login-tabs">
          <button
            className={`login-tab ${tab === 'credentials' ? 'active' : ''}`}
            onClick={() => { setTab('credentials'); setError(''); }}
            type="button"
          >
            <Key size={16} /> Credentials
          </button>
          <button
            className={`login-tab ${tab === 'apikey' ? 'active' : ''}`}
            onClick={() => { setTab('apikey'); setError(''); }}
            type="button"
          >
            <Zap size={16} /> API Key
          </button>
        </div>

        {/* Error banner */}
        {error && <div className="login-error"><AlertCircle /> {error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          {tab === 'credentials' ? (
            <>
              <div className="login-field">
                <label>Company ID</label>
                <input
                  type="text"
                  value={companyId}
                  onChange={(e) => setCompanyId(e.target.value)}
                  placeholder="e.g. HEALTHCARE_001 or superadmin"
                  autoComplete="off"
                  className="login-input"
                />
              </div>
              <div className="login-field">
                <label>Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="login-input"
                />
              </div>
            </>
          ) : (
            <div className="login-field">
              <label>API Key</label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-live-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                autoComplete="off"
                className="login-input"
              />
            </div>
          )}

          <button type="submit" className="login-btn" disabled={!canSubmit}>
            {loading ? (
              <span className="login-spinner" />
            ) : (
              <>Authenticate <ArrowRight size={18} /></>
            )}
          </button>
        </form>

        <div className="login-footer">
          New to the platform?{' '}
          <Link to="/register" className="login-link">
            Register your company →
          </Link>
        </div>
      </div>
    </div>
  );
}

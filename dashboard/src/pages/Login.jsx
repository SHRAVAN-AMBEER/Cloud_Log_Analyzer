import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser } from '../services/api';
import '../styles/main.css';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Check if already logged in
  React.useEffect(() => {
    if (localStorage.getItem('siem_token')) {
      navigate('/dashboard');
    }
  }, [navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const data = await loginUser(username, password);
      // Store SaaS token and user details natively!
      localStorage.setItem('siem_token', data.token);
      localStorage.setItem('siem_role', data.role);
      localStorage.setItem('siem_company', data.company_id);
      
      // Route securely to dashboard
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Authentication Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at center, #111827 0%, #000000 100%)',
      fontFamily: 'Inter, sans-serif'
    }}>
      <div style={{
        background: 'rgba(31, 41, 55, 0.4)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        padding: '3rem',
        borderRadius: '1rem',
        width: '100%',
        maxWidth: '450px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
      }}>
        
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛡️</div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#f3f4f6', fontWeight: 600 }}>Enterprise SIEM</h1>
          <p style={{ color: '#9ca3af', marginTop: '0.5rem', fontSize: '0.9rem' }}>Authenticate to access threat intelligence</p>
        </div>

        {error && (
          <div style={{ 
            background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5', padding: '0.75rem', borderRadius: '0.5rem', marginBottom: '1.5rem',
            textAlign: 'center', fontSize: '0.9rem'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', color: '#d1d5db', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Tenant ID (Username)</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. hospital, retail, admin"
              autoComplete="off"
              style={{
                width: '100%', padding: '0.75rem 1rem', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '0.5rem', color: 'white', outline: 'none', transition: 'border-color 0.2s', boxSizing: 'border-box'
              }}
              onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
            />
          </div>

          <div>
            <label style={{ display: 'block', color: '#d1d5db', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Secure Phrase</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width: '100%', padding: '0.75rem 1rem', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '0.5rem', color: 'white', outline: 'none', transition: 'border-color 0.2s', boxSizing: 'border-box'
              }}
              onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
            />
          </div>

          <button 
            type="submit" 
            disabled={loading || !username || !password}
            style={{
              marginTop: '1rem', width: '100%', padding: '0.875rem', background: '#2563eb', color: 'white',
              border: 'none', borderRadius: '0.5rem', fontSize: '1rem', fontWeight: 600, cursor: (loading || !username || !password) ? 'not-allowed' : 'pointer',
              opacity: (loading || !username || !password) ? 0.7 : 1, transition: 'background 0.2s'
            }}
            onMouseOver={(e) => !loading && username && password && (e.target.style.background = '#1d4ed8')}
            onMouseOut={(e) => (e.target.style.background = '#2563eb')}
          >
            {loading ? 'Authenticating...' : 'Secure Login →'}
          </button>
        </form>
        
        <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.8rem', color: 'rgba(156, 163, 175, 0.5)' }}>
          Enterprise Network Node Auth 
          <br />Use "hospital", "retail", or "admin" with "password123"
        </div>
      </div>
    </div>
  );
}

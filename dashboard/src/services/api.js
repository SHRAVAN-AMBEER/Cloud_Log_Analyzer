export const loginUser = async (username, password) => {
  try {
    const res = await fetch('http://localhost:5000/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Login failed');
    return data;
  } catch (error) {
    throw error;
  }
};

export const fetchAlerts = async (tenant = null) => {
  try {
    const token = localStorage.getItem('siem_token');
    let url = 'http://localhost:5000/alerts';
    if (tenant) {
      url += `?tenant=${tenant}`;
    }
    
    const res = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!res.ok) throw new Error('Failed to fetch alerts');
    return await res.json();
  } catch (error) {
    console.error(error);
    return [];
  }
};

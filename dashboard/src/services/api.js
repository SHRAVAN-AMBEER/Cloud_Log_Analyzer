export const fetchAlerts = async () => {
  try {
    const res = await fetch('http://localhost:5000/alerts');
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return await res.json();
  } catch (error) {
    console.error(error);
    return [];
  }
};

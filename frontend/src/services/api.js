import axios from 'axios';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: `${apiBaseUrl.replace(/\/$/, '')}/api/v1`,
  headers: { 'X-API-Key': import.meta.env.VITE_API_KEY || 'dev-key' },
});

export const fetchStats = () => api.get('/stats').then(r => r.data);
export const fetchIncidents = (params) => api.get('/incidents', { params }).then(r => r.data);
export const fetchTrends = (hours = 24) => api.get('/trends', { params: { hours } }).then(r => r.data);
export const analyzeContent = (body) => api.post('/analyze', body).then(r => r.data);
export const submitReport = (body) => api.post('/report', body).then(r => r.data);
export const submitFeedback = (body) => api.post('/feedback', body).then(r => r.data);

export default api;

import axios, { type AxiosInstance } from 'axios';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
});

export const getHello = async () => {
  const response = await api.get('/');
  return response.data;
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('aha_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
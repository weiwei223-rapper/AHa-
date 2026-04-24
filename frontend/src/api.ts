import axios, { type AxiosInstance } from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
});

// Auth APIs
export const authAPI = {
  register: (data: { name: string; email: string; password: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
};

// User APIs
export const userAPI = {
  getUser: (userId: number) =>
    api.get(`/users/${userId}`),
  updateUser: (userId: number, data: { name: string; email: string; password?: string }) =>
    api.put(`/users/${userId}`, data),
  getRechargeRecords: (userId: number) =>
    api.get(`/users/${userId}/recharge-records`),
  recharge: (userId: number, data: { points: number; price: number }) =>
    api.post(`/users/${userId}/recharge`, data),
};

export const chatAPI = {
  sendMessage: (data: {
    message: string;
    history: Array<{ role: string; content: string }>;
  }) => api.post('/api/chat', data),
};

export default api;

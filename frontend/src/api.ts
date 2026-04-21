import axios, { type AxiosInstance } from 'axios';

const api: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000',
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

export default api;
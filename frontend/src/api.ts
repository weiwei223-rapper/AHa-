import axios, { type AxiosInstance } from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function parseResponseBody<T>(response: Response): Promise<T | null> {
  const raw = await response.text();
  if (!raw.trim()) {
    return null;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    return "後端服務目前無法連線，請確認 API 伺服器已啟動（http://127.0.0.1:8000）。";
  }
  const body = await parseResponseBody<{ detail?: string; message?: string }>(response);
  return body?.detail || body?.message || fallback;
}

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout
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
  recharge: (userId: number, data: { points: number; price: number; plan_content?: string; payment_method?: string; plan_id?: string }) =>
    api.post(`/users/${userId}/recharge`, data),
  getStats: (userId: number) =>
    api.get(`/users/${userId}/stats`),
  createCheckout: (data: {
    MerchantTradeNo: string;
    MerchantTradeDate: string;
    PaymentType: string;
    TotalAmount: number;
    TradeDesc: string;
    ItemName: string;
    ReturnURL: string;
    ClientBackURL: string;
    ChoosePayment: string;
    EncryptType: number;
  }) => api.post('/ecpay/create-checkmac', data),
};

export const videoAPI = {
  getVideos: (userId: number) => api.get('/api/videos', { params: { user_id: userId } }),
  getVideo: (videoId: number) => api.get(`/api/videos/${videoId}`),
  createVideo: (data: { video_link: string; title?: string | null; outline?: string | null; user_id?: number; cost_points?: number; error_report?: string | null }) =>
    api.post('/api/videos', data),
  deleteVideo: (videoId: number) => api.delete(`/api/videos/${videoId}`),
  analyzeVideo: (videoId: number) => api.get(`/api/videos/${videoId}/analysis`),
  generateQuiz: (videoId: number, userId: number, outline?: string | null) =>
    api.get(`/api/videos/${videoId}/quiz`, { params: { user_id: userId, outline: outline || undefined } }),
};

export const feedbackAPI = {
  createFeedback: (data: { user_id: number; video_id?: number | null; ai_message: string; user_message: string; error_report?: string | null }) =>
    api.post('/api/feedbacks', data),
  getFeedbacks: () => api.get('/api/feedbacks'),
  deleteConversation: (conversationId: string, userId: number) =>
    api.delete(`/api/feedbacks/conversations/${conversationId}`, { params: { user_id: userId } }),
};

export const quizAPI = {
  createQuestion: (data: { user_id: number; video_id: number; question_content: string; reference_answer: string; options: string[]; answer_record?: string | null; accuracy?: number }) =>
    api.post('/api/quiz-questions', data),
  getQuestions: () => api.get('/api/quiz-questions'),
  createResult: (data: { user_id: number; video_id: number; score: number; total_questions: number }) =>
    api.post('/api/quiz-results', data),
  gradeQuiz: (videoId: number, data: { user_id: number; answers: string[] }) =>
    api.post(`/api/quizzes/${videoId}/grade`, data),
};

export const uploadAPI = {
  createUpload: (data: { user_id: number; video_id: number; consumed_points: number }) =>
    api.post('/api/uploads', data),
};

export const generationAPI = {
  createGeneration: (data: { user_id: number; quiz_question_id: number; consumed_points: number }) =>
    api.post('/api/generations', data),
};

export const codeAPI = {
  executeCode: (data: { code: string }) =>
    api.post('/api/execute-code', data),
};

export const chatAPI = {
  sendMessage: (data: { message: string; history: { role: string; content: string }[]; user_id?: number; video_id?: number | null }) =>
    api.post('/api/chat', data),
};

export default api;

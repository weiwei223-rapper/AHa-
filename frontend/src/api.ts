import axios, { type AxiosInstance } from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '';

export async function parseResponseBody<T>(response: Response): Promise<T | null> {
  const raw = await response.text();
  if (!raw.trim()) return null;
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
  timeout: 300000, 
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
  updateUser: (userId: number, data: { name: string; email: string; password?: string; current_quiz_draft?: string | null }) =>
    api.put(`/users/${userId}`, data),
  getRechargeRecords: (userId: number) =>
    api.get(`/users/${userId}/recharge-records`),
  recharge: (userId: number, data: { points: number; price: number; plan_content?: string; payment_method?: string; plan_id?: string }) =>
    api.post(`/users/${userId}/recharge`, data),
  getStats: (userId: number) =>
    api.get(`/users/${userId}/stats`),
  claimAchievementPoints: (userId: number) =>
    api.post(`/users/${userId}/claim-achievement-points`),
};

export const videoAPI = {
  getVideos: (userId: number) => api.get('/api/videos', { params: { user_id: userId } }),
  getVideo: (videoId: number) => api.get(`/api/videos/${videoId}`),
  createVideo: (data: { video_link: string; title?: string | null; outline?: string | null; user_id?: number; cost_points?: number; error_report?: string | null }) =>
    api.post('/api/videos', data),
  deleteVideo: (videoId: number) => api.delete(`/api/videos/${videoId}`),
  analyzeVideo: (videoId: number, userId: number) => api.get(`/api/videos/${videoId}/analysis`, { params: { user_id: userId } }),
  generateQuiz: (videoId: number, userId: number, count?: number) =>
    api.get(`/api/videos/${videoId}/quiz`, { params: { user_id: userId, count: count || 5 } }),
  reportError: (videoId: number, errorReport: string) =>
    api.post(`/api/videos/${videoId}/report-error`, { error_report: errorReport }),
};

export const documentAPI = {
  getDocuments: (userId: number) => api.get('/api/documents', { params: { user_id: userId } }),
  uploadDocument: (userId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId.toString());
    return api.post('/api/documents', formData);
  },
  analyzeDocument: (docId: number, userId: number) =>
    api.get(`/api/documents/${docId}/analysis`, { params: { user_id: userId } }),
  generateQuiz: (docId: number, userId: number, count?: number) =>
    api.get(`/api/documents/${docId}/quiz`, { params: { user_id: userId, count: count || 5 } }),
  reportError: (docId: number, errorReport: string) =>
    api.post(`/api/documents/${docId}/report-error`, { error_report: errorReport }),
};

export const feedbackAPI = {
  createFeedback: (data: { user_id: number; ai_message: string; user_message: string; error_report?: string | null }) =>
    api.post('/api/feedbacks', data),
  getFeedbacks: () => api.get('/api/feedbacks'),
  deleteConversation: (conversationId: string, userId: number) =>
    api.delete(`/api/feedbacks/conversations/${conversationId}`, { params: { user_id: userId } }),
};

export const quizAPI = {
  getResults: (userId: number) => api.get('/api/quiz-results', { params: { user_id: userId } }),
  deleteResult: (resultId: number) => api.delete(`/api/quiz-results/${resultId}`),
  updateResult: (resultId: number, data: { title?: string; score?: number; details_json?: string; error_report?: string }) =>
    api.put(`/api/quiz-results/${resultId}`, data),
  createResult: (data: { user_id: number; video_id?: number; document_id?: number; score: number; total_questions: number; title?: string; details_json?: string }) =>
    api.post('/api/quiz-results', data),
  gradeQuiz: (videoId: number, data: { user_id: number; answers: string[]; document_id?: number | null }) =>
    api.post(`/api/quizzes/${videoId}/grade`, data),
  getDrafts: (userId: number) => api.get('/api/quiz-drafts', { params: { user_id: userId } }),
  upsertDraft: (data: { user_id: number; video_id?: number; document_id?: number; draft_json: string }) =>
    api.post('/api/quiz-drafts', data),
  deleteDraft: (videoId: number, userId: number) =>
    api.delete(`/api/quiz-drafts/${videoId}`, { params: { user_id: userId } }),
  reportQuizError: (resultId: number, errorReport: string) =>
    api.post(`/api/quiz-results/${resultId}/report-error`, { error_report: errorReport }),
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

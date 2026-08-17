import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000/api/';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach Auth Token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authAPI = {
  register: (data) => api.post('auth/register/', data),
  login: (data) => api.post('auth/login/', data),
  logout: () => api.post('auth/logout/'),
};

export const chatAPI = {
  getConversations: () => api.get('chats/'),
  createConversation: (title) => api.post('chats/', { title }),
  getConversationDetail: (id) => api.get(`chats/${id}/`),
  deleteConversation: (id) => api.delete(`chats/${id}/`),
  sendMessage: (conversationId, content, documentId = null) =>
    api.post(`chats/${conversationId}/messages/`, {
      content,
      document_id: documentId,
    }),
};

export const documentAPI = {
  getDocuments: () => api.get('documents/'),
  uploadDocument: (formData) =>
    api.post('documents/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteDocument: (id) => api.delete(`documents/${id}/`),
};

export default api;

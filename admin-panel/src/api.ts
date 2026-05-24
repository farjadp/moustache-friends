import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export interface Document {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: "processing" | "ready" | "error";
  chunk_count: number;
  error_message?: string;
  uploaded_by?: string;
  created_at: string;
}

export interface ChatLog {
  id: number;
  user_id: string;
  username?: string;
  chat_id: string;
  question: string;
  answer: string;
  sources?: string;
  created_at: string;
}

export interface Stats {
  total_questions: number;
  unique_users: number;
}

export const fetchDocuments = () => api.get<Document[]>("/documents/").then((r) => r.data);
export const deleteDocument = (id: number) => api.delete(`/documents/${id}`);
export const uploadDocument = (file: File, onProgress?: (p: number) => void) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<{ id: number; filename: string; status: string }>("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
};
export const fetchDocumentStatus = (id: number) =>
  api.get<{ id: number; status: string; chunk_count: number; error_message?: string }>(`/documents/${id}/status`).then((r) => r.data);

export const fetchLogs = (limit = 50, offset = 0) =>
  api.get<ChatLog[]>(`/logs/?limit=${limit}&offset=${offset}`).then((r) => r.data);
export const fetchStats = () => api.get<Stats>("/logs/stats").then((r) => r.data);

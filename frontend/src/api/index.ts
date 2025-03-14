import axios, { AxiosResponse } from 'axios';
import { Conversation, Message, Document, UploadResponse, DocumentStatus, Workgroup, Workspace } from '../types';
import { 
  WorkgroupCreate, 
  WorkspaceCreate 
} from '../types/workspace';

// 确保 baseURL 不包含重复的 /api
const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 工作组相关 API
export const workgroupApi = {
  list: () => api.get<Workgroup[]>('/api/workgroups').then(res => {
    return res.data.map(workgroup => ({
      id: workgroup.id,
      name: workgroup.name || '',
      description: workgroup.description || null,
      created_at: workgroup.created_at || null
    }));
  }),
  create: (data: { name: string; description?: string }) => 
    api.post<Workgroup>('/api/workgroups', data).then(res => res.data),
  update: (id: number, data: { name: string; description?: string }) => 
    api.put<Workgroup>(`/api/workgroups/${id}`, data).then(res => res.data),
  delete: (id: number) => api.delete(`/api/workgroups/${id}`).then(res => res.data),
};

// 工作空间相关 API
export const workspaceApi = {
  listWorkgroups: () => 
    axios.get<Workgroup[]>(`${baseURL}/api/workgroups`).then(res => res.data),
  
  createWorkgroup: (data: WorkgroupCreate) => 
    axios.post<Workgroup>(`${baseURL}/api/workgroups`, data).then(res => res.data),
  
  updateWorkgroup: (id: number, data: WorkgroupCreate) => 
    axios.put<Workgroup>(`${baseURL}/api/workgroups/${id}`, data).then(res => res.data),
  
  deleteWorkgroup: (id: number) => 
    axios.delete(`${baseURL}/api/workgroups/${id}`).then(res => res.data),

  listWorkspaces: (groupId?: number) => 
    axios.get<Workspace[]>(`${baseURL}/api/workspaces`, { 
      params: { group_id: groupId } 
    }).then(res => res.data),
  
  createWorkspace: (data: WorkspaceCreate) => 
    axios.post<Workspace>(`${baseURL}/api/workspaces`, data).then(res => res.data),
  
  updateWorkspace: (id: number, data: WorkspaceCreate) => 
    axios.put<Workspace>(`${baseURL}/api/workspaces/${id}`, data).then(res => res.data),
  
  deleteWorkspace: (id: number) => 
    axios.delete(`${baseURL}/api/workspaces/${id}`).then(res => res.data),

  linkDocumentToWorkspaces: (documentId: number, workspaceIds: number[]) => 
    axios.post(`${baseURL}/api/documents/${documentId}/workspaces`, {
      workspace_ids: workspaceIds
    }).then(res => res.data)
};

// 文档相关 API
export const documentApi = {
  list: () => api.get<Document[]>('/api/documents').then(res => res.data),
  
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<UploadResponse>(
      '/api/documents',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
  
  delete: (documentId: number) => 
    api.delete(`/api/documents/${documentId}`).then(res => res.data),
  
  getStatus: (documentId: number) => 
    api.get<DocumentStatus>(`/api/documents/${documentId}/status`).then(res => res.data),
  
  linkWorkspace: async (documentId: number, workspaceIds: number[]) => {
    const response = await api.post(`/api/documents/${documentId}/workspaces`, {
      workspace_ids: workspaceIds
    });
    return response.data;
  },
  
  unlinkWorkspace: async (documentId: number, workspaceId: number) => {
    const response = await api.delete(`/api/documents/${documentId}/workspaces/${workspaceId}`);
    return response.data;
  },
  
  download: async (documentId: number) => {
    const response = await api.get(`/api/chat/documents/${documentId}/download`, {
      responseType: 'blob'
    });
    return response.data;
  },
};

// 对话相关 API
export const conversationApi = {
  list: () => api.get<Conversation[]>('/chat/conversations').then(res => res.data),
  create: (name: string) => 
    api.post<Conversation>('/chat/conversations', { name }).then(res => res.data),
  getMessages: (conversationId: number) => 
    api.get<Message[]>(`/chat/conversations/${conversationId}/messages`).then(res => res.data),
  sendMessage: async (conversationId: number | null, message: string, useRag: boolean = true) => {
    if (conversationId === null) {
      const newConversation = await conversationApi.create('新对话');
      conversationId = newConversation.id;
    }
    
    return api.post<Message>(`/chat/conversations/${conversationId}/messages`, { 
      message, 
      use_rag: useRag 
    }).then(res => res.data);
  },
};

export default api; 
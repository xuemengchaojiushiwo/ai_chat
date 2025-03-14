export interface Citation {
  text: string;
  document_id: number;
  segment_id: number;
  index: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface Conversation {
  id: number;
  name: string;
  created_at: string;
  messages: Message[];
}

export interface Document {
  id: number;
  name: string;
  content?: string;
  mime_type: string;
  status: string;
  error?: string;
  created_at: string;
}

export interface UploadResponse {
  id: number;
  name: string;
  status: string;
  mime_type: string;
  created_at: string;
}

export interface DocumentStatus {
  status: string;
  segments?: number;
  segments_with_embeddings?: number;
  error?: string;
}

export interface Workgroup {
  id: number;
  name: string;
  description: string | null;
  created_at: string | null;
}

export interface Workspace {
  id: number;
  name: string;
  description: string | null;
  group_id: number;
  created_at: string | null;
  updated_at: string | null;
  document_count: number;
} 
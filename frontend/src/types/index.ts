export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  tokens?: number;
  citations?: string[];
  created_at?: string;
}

export interface Citation {
  title?: string;
  text: string;
  document_id?: number;
  segment_id?: number;
}

export interface Conversation {
  id: number;
  name: string;
  created_at: string;
  messages: Message[];
}

export interface Document {
  id: number;
  dataset_id: number;
  name: string;
  content: string;
  mime_type: string;
  status: 'pending' | 'completed' | 'error';
  error?: string;
  created_at: string;
} 
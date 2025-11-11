export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: 'user' | 'admin' | 'viewer';
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface Document {
  id: string;
  user_id: string;
  filename: string;
  original_filename: string;
  file_type: 'pdf' | 'docx' | 'html' | 'txt';
  file_size: number;
  title: string;
  description: string | null;
  ingestion_status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  processing_error: string | null;
  access_level: 'public' | 'private' | 'restricted';
  tags: string[];
  created_at: string;
  updated_at: string;
  indexed_at: string | null;
  is_indexed: boolean;
}

export interface IngestionJob {
  id: string;
  document_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  total_steps: number;
  error_message: string | null;
  started_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface SourceCitation {
  document_id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number;
  chunk_text: string;
  relevance_score: number;
  url: string | null;
  snippet: string;
}

export interface RetrievalConfig {
  k: number;
  rerank: boolean;
  filters?: Record<string, any>;
  threshold?: number;
  hybrid_search?: boolean;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: SourceCitation[];
  confidence_score?: 'high' | 'medium' | 'low';
  model_used?: string;
  token_count?: number;
  cost_estimate?: string;
  feedback?: 'helpful' | 'not_helpful' | 'inappropriate';
  feedback_comment?: string | null;
  status: 'pending' | 'completed' | 'failed';
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string | null;
  description: string | null;
  is_active: boolean;
  total_messages: number;
  total_tokens_used: number;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

export interface ChatQuery {
  query: string;
  session_id?: string;
  retrieval_config?: RetrievalConfig;
}

export interface ChatResponse {
  answer: string;
  sources: SourceCitation[];
  session_id: string;
  message_id: string;
  confidence_score?: 'high' | 'medium' | 'low';
  retrieval_config: RetrievalConfig;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model_used: string;
}

export interface DocumentUploadResponse {
  message: string;
  document_id: string;
  ingestion_job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface ApiResponse<T> {
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface WebSocketMessage {
  type: 'query' | 'status' | 'sources' | 'message_chunk' | 'complete' | 'error' | 'pong';
  data: Record<string, any>;
  timestamp?: string;
}

export interface UsageStats {
  total_sessions: number;
  total_messages: number;
  total_tokens_used: number;
  average_messages_per_session: number;
}

export interface DocumentStats {
  total_documents: number;
  pending_documents: number;
  processing_documents: number;
  completed_documents: number;
  failed_documents: number;
  total_chunks: number;
  total_size_mb: number;
}

export interface AppSettings {
  theme: 'light' | 'dark';
  language: string;
  notifications_enabled: boolean;
  auto_save_sessions: boolean;
  default_retrieval_k: number;
  rerank_enabled: boolean;
  max_file_upload_size: number;
}
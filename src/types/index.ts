// src/types/index.ts (Enhanced)

export interface Document {
  id: string;
  filename: string;
  uploadTime: string;
  chunks: number;
  size: string | number;
  language: 'ko' | 'en';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processedAt?: string;
  errorMessage?: string;
  url?: string;
  created_at?: string;
  processed_at?: string;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  references?: ChatReference[];
  sources?: ChatSource[];
  processing_time?: number;
}

export interface ChatReference {
  documentId: string;
  filename: string;
  pageNumber: number;
  relevantText: string;
}

export interface ChatSource {
  document_id: string;
  filename: string;
  chunk_index: number;
  page_number: number;
  bbox?: BoundingBox;
  content_preview: string;
  full_content: string;
  relevance_score: number;
}

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface PDFLocation {
  page_number: number;
  bbox: BoundingBox;
  context: string;
  matched_text: string;
}

export interface PDFDocument {
  id: string;
  filename: string;
  url: string;
  pageNumber?: number;
  highlightText?: string;
  searchLocations?: PDFLocation[];
  totalPages?: number;
}

export interface UploadProgress {
  stage: 'uploading' | 'processing' | 'completed' | 'failed';
  message: string;
  progress: number;
}

export interface ProcessResponse {
  status: string;
  message: string;
  document_id: string;
  filename: string;
  file_size: number;
  processing: boolean;
}

export interface DocumentResponse {
  status: string;
  data: Document;
}

export interface DocumentListResponse {
  status: string;
  data: Document[];
  count: number;
  total: number;
  page: number;
  limit: number;
}

export interface ChatRequest {
  message: string;
  document_ids?: string[];
  max_results?: number;
}

export interface ChatResponse {
  status: string;
  answer: string;
  sources: ChatSource[];
  document_ids: string[];
  processing_time: number;
}

export interface SearchResult {
  document_id: string;
  filename: string;
  chunk_index: number;
  content: string;
  relevance_score: number;
  distance: number;
  page_number: number;
  navigation_info: {
    can_highlight: boolean;
    can_navigate: boolean;
  };
}

export interface HighlightRequest {
  document_id: string;
  page_number: number;
  search_text: string;
}

export interface HighlightResponse {
  status: string;
  highlighted_pdf_url?: string;
  page_number?: number;
  bbox?: BoundingBox;
  total_highlights?: number;
  message?: string;
}

export interface PageNavigationInfo {
  status: string;
  document_id: string;
  search_text: string;
  total_matches: number;
  locations: PDFLocation[];
  primary_page: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

export interface LanguageContextType {
  language: 'ko' | 'en';
  setLanguage: (lang: 'ko' | 'en') => void;
  t: (key: string) => string;
}

// API Response Types
export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  error?: string;
}

export interface DocumentStats {
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface ChunkLocation {
  chunk_index: number;
  text: string;
  start_page: number;
  end_page: number;
  chunk_hash: string;
  char_count: number;
}

export interface ProcessingResult {
  status: 'success' | 'failed';
  message: string;
  document_id: string;
  chunk_count?: number;
  location_info?: {
    total_pages: number;
    chunks_with_pages: ChunkLocation[];
  };
}

// Event Types
export interface ChatEventHandlers {
  onSourceClick?: (documentId: string, pageNumber: number, highlightText: string) => void;
  onMessageSent?: () => void;
  onPageChange?: (pageNumber: number) => void;
  onHighlightRequest?: (text: string) => void;
}

// Component Props Types
export interface EnhancedChatInterfaceProps extends ChatEventHandlers {
  initialMessage?: string;
  availableDocuments?: Document[];
}

export interface EnhancedPDFViewerProps extends ChatEventHandlers {
  document: PDFDocument | null;
  className?: string;
}

export interface DocumentUploadProps {
  onUploadComplete?: (document: Document) => void;
  onUploadError?: (error: string) => void;
  autoProcess?: boolean;
}

// Constants
export const DOCUMENT_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing', 
  COMPLETED: 'completed',
  FAILED: 'failed'
} as const;

export const MESSAGE_TYPES = {
  USER: 'user',
  ASSISTANT: 'assistant'
} as const;

export const SUPPORTED_LANGUAGES = {
  KOREAN: 'ko',
  ENGLISH: 'en'
} as const;

export type DocumentStatus = typeof DOCUMENT_STATUS[keyof typeof DOCUMENT_STATUS];
export type MessageType = typeof MESSAGE_TYPES[keyof typeof MESSAGE_TYPES];
export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[keyof typeof SUPPORTED_LANGUAGES];
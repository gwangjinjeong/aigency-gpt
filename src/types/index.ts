
export interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
  name: string;
}

export interface Document {
  id: string;
  filename: string;
  uploadTime: string;
  chunks: number;
  size: string;
  language: 'ko' | 'en';
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  references?: DocumentReference[];
}

export interface DocumentReference {
  documentId: string;
  filename: string;
  pageNumber: number;
  relevantText: string;
}

export type Language = 'ko' | 'en';

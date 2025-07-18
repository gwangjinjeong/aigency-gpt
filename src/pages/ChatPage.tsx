import React, { useState, useEffect } from 'react';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import EnhancedChatInterface from '@/components/Chat/EnhancedChatInterface';
import EnhancedPDFViewer from '@/components/Chat/EnhancedPDFViewer';
import Header from '@/components/Layout/Header';

// Vite 환경변수 사용
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

// 타입 정의
interface BoundingBox {
  x0: number; y0: number; x1: number; y1: number;
}

interface ChatSource {
  document_id: string;
  filename: string;
  page_number: number;
  bbox?: BoundingBox;
  content_preview: string;
  relevance_score: number;
  full_content?: string;
  chunk_index?: number;
  end_page?: number;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: ChatSource[];
  processing_time?: number;
}

interface CurrentDocument {
  id: string;
  filename: string;
  url: string;
  pageNumber?: number;
  highlightText?: string;
}

const ChatPage: React.FC = () => {
  const [currentDocument, setCurrentDocument] = useState<CurrentDocument | null>(null);
  const [showPDFViewer, setShowPDFViewer] = useState(false);
  const [documentCache, setDocumentCache] = useState<Map<string, any>>(new Map());

  // 상태를 ChatPage로 이동
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: '안녕하세요! 업로드된 PDF 문서에 대해 질문해보세요. 답변과 함께 해당 페이지로 자동 이동하고 관련 부분을 하이라이트해드립니다.',
      timestamp: new Date().toISOString(),
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchDocumentInfo = async (documentId: string) => {
    if (documentCache.has(documentId)) {
      return documentCache.get(documentId);
    }
    try {
      // API 경로 수정
      const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setDocumentCache(prev => new Map(prev).set(documentId, data.data));
          return data.data;
        }
      }
    } catch (error) {
      console.error('문서 정보 조회 실패:', error);
    }
    return null;
  };

  // 메시지 전송 로직을 ChatPage로 이동
  const handleSendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setShowPDFViewer(true); // 메시지 보내면 바로 PDF 뷰어 표시

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, max_results: 5 }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.status === 'success') {
        const assistantMessage: ChatMessage = {
          id: Math.random().toString(36).substr(2, 9),
          type: 'assistant',
          content: data.answer,
          timestamp: new Date().toISOString(),
          sources: data.sources || [],
          processing_time: data.processing_time
        };
        setMessages(prev => [...prev, assistantMessage]);

        if (data.sources && data.sources.length > 0) {
          const firstSource = data.sources[0];
          handleSourceClick(firstSource.document_id, firstSource.page_number);
        }
      } else {
        throw new Error(data.message || '답변 생성에 실패했습니다.');
      }
    } catch (error) {
      console.error('메시지 전송 실패:', error);
      const errorMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        type: 'assistant',
        content: '죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSourceClick = async (documentId: string, pageNumber: number, highlightText?: string) => {
    const docInfo = await fetchDocumentInfo(documentId);
    if (docInfo) {
      setCurrentDocument({
        id: documentId,
        filename: docInfo.filename,
        url: docInfo.url,
        pageNumber,
        highlightText
      });
      setShowPDFViewer(true);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="h-[calc(100vh-4rem)]">
        <ResizablePanelGroup direction="horizontal" className="h-full">
          <ResizablePanel defaultSize={45} minSize={30}>
            <EnhancedChatInterface
              messages={messages} // 상태 전달
              isLoading={isLoading} // 상태 전달
              onSendMessage={handleSendMessage} // 함수 전달
              onSourceClick={handleSourceClick}
            />
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={55} minSize={30}>
            <EnhancedPDFViewer document={currentDocument} />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
};

export default ChatPage;
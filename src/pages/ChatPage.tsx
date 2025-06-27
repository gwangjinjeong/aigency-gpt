import React, { useState } from 'react';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import EnhancedChatInterface from '@/components/Chat/EnhancedChatInterface';
import EnhancedPDFViewer from '@/components/Chat/EnhancedPDFViewer';
import Header from '@/components/Layout/Header';

interface CurrentDocument {
  id: string;
  filename: string;
  url: string;
  pageNumber?: number;
  highlightText?: string;
  searchLocations?: any[];
}

const ChatPage: React.FC = () => {
  const [currentDocument, setCurrentDocument] = useState<CurrentDocument | null>(null);
  const [showPDFViewer, setShowPDFViewer] = useState(false);

  const handleSourceClick = (documentId: string, pageNumber: number, highlightText: string) => {
    // 문서 정보를 설정하고 PDF 뷰어 표시
    setCurrentDocument({
      id: documentId,
      filename: `Document ${documentId}`, // 실제로는 API에서 파일명을 가져와야 함
      url: '', // 실제 PDF URL (API에서 가져와야 함)
      pageNumber,
      highlightText
    });
    setShowPDFViewer(true);
  };

  const handleMessageSent = () => {
    // 메시지 전송 시 PDF 뷰어 표시 (답변을 기다리기 위해)
    setShowPDFViewer(true);
  };

  const handlePageChange = (pageNumber: number) => {
    if (currentDocument) {
      setCurrentDocument({
        ...currentDocument,
        pageNumber
      });
    }
  };

  const handleHighlightRequest = (text: string) => {
    if (currentDocument) {
      setCurrentDocument({
        ...currentDocument,
        highlightText: text
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="h-[calc(100vh-4rem)]">
        {showPDFViewer ? (
          // 분할된 화면: 채팅 + PDF 뷰어
          <ResizablePanelGroup direction="horizontal" className="h-full">
            <ResizablePanel defaultSize={45} minSize={30}>
              <EnhancedChatInterface
                onSourceClick={handleSourceClick}
                onMessageSent={handleMessageSent}
              />
            </ResizablePanel>
            
            <ResizableHandle withHandle />
            
            <ResizablePanel defaultSize={55} minSize={30}>
              <EnhancedPDFViewer
                document={currentDocument}
                onPageChange={handlePageChange}
                onHighlightRequest={handleHighlightRequest}
              />
            </ResizablePanel>
          </ResizablePanelGroup>
        ) : (
          // 전체 화면: 채팅만
          <div className="h-full">
            <EnhancedChatInterface
              onSourceClick={handleSourceClick}
              onMessageSent={handleMessageSent}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
//src/Chat/EnhancedChatInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { ChatMessage } from '@/pages/ChatPage'; // ChatPage에서 타입 임포트
import {
  Send,
  Bot,
  User,
  FileText,
  MapPin,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Highlighter,
  Loader2
} from 'lucide-react';

// Vite 환경변수 사용
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

interface ChatSource {
  document_id: string;
  filename: string;
  page_number: number;
  content_preview: string;
  relevance_score: number;
  full_content?: string;
}

interface Document {
  id: string;
  filename: string;
}

interface EnhancedChatInterfaceProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  onSourceClick: (documentId: string, pageNumber: number, highlightText?: string) => void;
}

const EnhancedChatInterface: React.FC<EnhancedChatInterfaceProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onSourceClick,
}) => {
  const { t } = useLanguage();
  const [message, setMessage] = useState('');
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const fetchAvailableDocuments = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/chat/documents`);
        const data = await response.json();
        if (data.status === 'success') {
          setAvailableDocuments(data.documents);
        }
      } catch (error) {
        console.error('문서 목록 조회 실패:', error);
      }
    };
    fetchAvailableDocuments();
  }, []);

  const handleSendMessage = () => {
    onSendMessage(message);
    setMessage('');
  };

  const handleHighlightClick = (source: ChatSource, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSourceClick && source.full_content) {
      onSourceClick(
        source.document_id,
        source.page_number,
        source.full_content
      );
    }
  };

  const handleCopyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      alert('메시지가 복사되었습니다.');
    } catch (error) {
      console.error('복사 실패:', error);
    }
  };

  const formatProcessingTime = (time?: number): string => {
    if (!time) return '';
    return `${time.toFixed(2)}초`;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="border-b p-4 bg-gray-50">
        <h2 className="font-semibold text-gray-900">AI 문서 질의응답</h2>
        <p className="text-sm text-gray-600 mt-1">
          질문하시면 관련 문서 페이지로 자동 이동하고 하이라이트해드립니다
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-4 ${msg.type === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
              <div className="flex items-start space-x-2">
                {msg.type === 'assistant' && <Bot className="w-5 h-5 mt-0.5 text-blue-600 flex-shrink-0" />}
                <div className="flex-1 min-w-0">
                  <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                  {msg.processing_time && <p className="text-xs text-gray-500 mt-1">처리 시간: {formatProcessingTime(msg.processing_time)}</p>}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-600 mb-2 flex items-center"><FileText className="w-3 h-3 mr-1" />참조된 문서 ({msg.sources.length}개):</p>
                      <div className="space-y-2">
                        {msg.sources.map((source, index) => (
                          <Card key={index} className="cursor-pointer hover:bg-blue-50 transition-colors border border-gray-200" onClick={() => onSourceClick(source.document_id, source.page_number)}>
                            <CardContent className="p-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-medium text-sm text-blue-600 truncate">{source.filename}</span>
                                <div className="flex items-center space-x-2">
                                  <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-800"><MapPin className="w-3 h-3 mr-1" />페이지 {source.page_number}</Badge>
                                  <Badge variant="outline" className="text-xs">{Math.round(source.relevance_score * 100)}% 일치</Badge>
                                </div>
                              </div>
                              <p className="text-xs text-gray-600 line-clamp-2">{source.content_preview}</p>
                              <div className="flex items-center justify-between mt-2">
                                <div className="flex items-center space-x-2 text-xs text-gray-500"><ExternalLink className="w-3 h-3" /><span>클릭하여 해당 페이지로 이동</span></div>
                                <Button size="sm" variant="ghost" className="h-6 px-2 text-xs text-yellow-600 hover:bg-yellow-50" onClick={(e) => handleHighlightClick(source, e)}><Highlighter className="w-3 h-3 mr-1" />하이라이트</Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                  {msg.type === 'assistant' && (
                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-200">
                      <div className="flex items-center space-x-2">
                        <Button size="sm" variant="ghost" onClick={() => handleCopyMessage(msg.content)} className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700"><Copy className="w-3 h-3 mr-1" />복사</Button>
                      </div>
                    </div>
                  )}
                </div>
                {msg.type === 'user' && <User className="w-5 h-5 mt-0.5 flex-shrink-0" />}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-4 max-w-[80%]">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-blue-600" />
                <div className="flex items-center space-x-2"><Loader2 className="w-4 h-4 animate-spin text-blue-600" /><span className="text-sm text-gray-600">문서를 검색하고 답변을 생성하는 중...</span></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t p-4 bg-gray-50">
        <div className="flex space-x-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="PDF 문서에 대해 질문해보세요..."
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }}}
            disabled={isLoading}
            className="flex-1"
          />
          <Button onClick={handleSendMessage} disabled={!message.trim() || isLoading} className="px-4">
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>{availableDocuments.length > 0 ? `${availableDocuments.length}개 문서에서 검색합니다` : '사용 가능한 문서가 없습니다'}</span>
          <span className="flex items-center space-x-1"><span>💡</span><span>답변과 함께 관련 페이지로 자동 이동됩니다</span></span>
        </div>
      </div>
    </div>
  );
};

export default EnhancedChatInterface;
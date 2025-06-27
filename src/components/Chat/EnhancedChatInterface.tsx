import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
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

interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

interface ChatSource {
  document_id: string;
  filename: string;
  page_number: number;
  bbox?: BoundingBox;
  content_preview: string;
  relevance_score: number;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: ChatSource[];
  processing_time?: number;
}

interface EnhancedChatInterfaceProps {
  onSourceClick?: (documentId: string, pageNumber: number, highlightText?: string) => void;
  onMessageSent?: () => void;
}

// Vite 환경변수 사용
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const EnhancedChatInterface: React.FC<EnhancedChatInterfaceProps> = ({
  onSourceClick,
  onMessageSent
}) => {
  const { t } = useLanguage();
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: '안녕하세요! 업로드된 PDF 문서에 대해 질문해보세요. 답변과 함께 해당 페이지로 자동 이동하고 관련 부분을 하이라이트해드립니다.',
      timestamp: new Date().toISOString(),
    }
  ]);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    fetchAvailableDocuments();
  }, []);

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

  const handleSendMessage = async () => {
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setMessage('');
    setIsLoading(true);

    // 메시지 전송 콜백 호출
    if (onMessageSent) {
      onMessageSent();
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          max_results: 5
        }),
      });

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

        // 🔥 첫 번째 소스가 있으면 자동으로 해당 페이지로 이동 (highlightText 없이)
        if (data.sources && data.sources.length > 0 && onSourceClick) {
          const firstSource = data.sources[0];
          onSourceClick(
            firstSource.document_id,
            firstSource.page_number
            // 🔥 highlightText 제거 - 자동 하이라이트하지 않음
          );
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

  const handleSourceClick = (source: ChatSource) => {
    if (onSourceClick) {
      // 🔥 페이지 이동만 (하이라이트 없이)
      onSourceClick(
        source.document_id,
        source.page_number
      );
    }
  };

  const handleHighlightClick = (source: ChatSource, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSourceClick) {
      // 🔥 하이라이트 기능: 키워드만 추출하여 전달
      const keywords = extractKeywords(source.content_preview);
      onSourceClick(
        source.document_id,
        source.page_number,
        keywords
      );
    }
  };

  // 🔥 content_preview에서 의미있는 키워드만 추출하는 함수
  const extractKeywords = (content: string): string => {
    // 간단한 키워드 추출 로직 (실제로는 더 정교하게 구현 가능)
    const words = content.split(/\s+/);

    // 의미있는 단어들 필터링 (숫자, 한글, 영문 포함)
    const meaningfulWords = words.filter(word =>
      word.length >= 2 &&
      /[가-힣a-zA-Z0-9]/.test(word) &&
      !['은', '는', '이', '가', '을', '를', '의', '에', '와', '과', '로', '으로'].includes(word)
    );

    // 처음 2-3개 단어만 선택
    return meaningfulWords.slice(0, 3).join(' ').slice(0, 50);
  };

  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    // 간단한 피드백 (실제로는 toast 등 사용)
    alert('메시지가 복사되었습니다.');
  };

  const handleFeedback = async (messageId: string, rating: 'up' | 'down') => {
    try {
      const message = messages.find(m => m.id === messageId);
      if (!message) return;

      await fetch(`${API_BASE_URL}/api/chat/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message.content,
          answer: message.content,
          rating: rating === 'up' ? 5 : 1,
          page_navigation_used: message.sources && message.sources.length > 0,
          highlight_used: false
        }),
      });

      // 피드백 성공 표시
      alert(rating === 'up' ? '좋은 평가 감사합니다!' : '피드백 감사합니다. 개선하겠습니다.');
    } catch (error) {
      console.error('피드백 전송 실패:', error);
    }
  };

  const formatProcessingTime = (time?: number) => {
    if (!time) return '';
    return `${time.toFixed(2)}초`;
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 헤더 */}
      <div className="border-b p-4 bg-gray-50">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">AI 문서 질의응답</h2>
          <Badge variant="outline" className="text-xs">
            {availableDocuments.length}개 문서 사용 가능
          </Badge>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          질문하시면 관련 문서 페이지로 자동 이동하고 하이라이트해드립니다
        </p>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                msg.type === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-start space-x-2">
                {msg.type === 'assistant' && (
                  <Bot className="w-5 h-5 mt-0.5 text-blue-600 flex-shrink-0" />
                )}

                <div className="flex-1 min-w-0">
                  <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>

                  {/* 처리 시간 표시 */}
                  {msg.processing_time && (
                    <p className="text-xs text-gray-500 mt-1">
                      처리 시간: {formatProcessingTime(msg.processing_time)}
                    </p>
                  )}

                  {/* 소스 정보 */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-600 mb-2 flex items-center">
                        <FileText className="w-3 h-3 mr-1" />
                        참조된 문서 ({msg.sources.length}개):
                      </p>
                      <div className="space-y-2">
                        {msg.sources.map((source, index) => (
                          <Card
                            key={index}
                            className="cursor-pointer hover:bg-blue-50 transition-colors border border-gray-200"
                            onClick={() => handleSourceClick(source)}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-medium text-sm text-blue-600 truncate">
                                  {source.filename}
                                </span>
                                <div className="flex items-center space-x-2">
                                  <Badge
                                    variant="secondary"
                                    className="text-xs bg-blue-100 text-blue-800"
                                  >
                                    <MapPin className="w-3 h-3 mr-1" />
                                    페이지 {source.page_number}
                                  </Badge>
                                  <Badge
                                    variant="outline"
                                    className="text-xs"
                                  >
                                    {Math.round(source.relevance_score * 100)}% 일치
                                  </Badge>
                                </div>
                              </div>
                              <p className="text-xs text-gray-600 line-clamp-2">
                                {source.content_preview}
                              </p>
                              <div className="flex items-center justify-between mt-2">
                                <div className="flex items-center space-x-2 text-xs text-gray-500">
                                  <ExternalLink className="w-3 h-3" />
                                  <span>클릭하여 해당 페이지로 이동</span>
                                </div>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 px-2 text-xs text-yellow-600 hover:bg-yellow-50"
                                  onClick={(e) => handleHighlightClick(source, e)}
                                >
                                  <Highlighter className="w-3 h-3 mr-1" />
                                  하이라이트
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 메시지 액션 */}
                  {msg.type === 'assistant' && (
                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-200">
                      <div className="flex items-center space-x-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleCopyMessage(msg.content)}
                          className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700"
                        >
                          <Copy className="w-3 h-3 mr-1" />
                          복사
                        </Button>
                      </div>

                      <div className="flex items-center space-x-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleFeedback(msg.id, 'up')}
                          className="h-6 w-6 p-0 text-gray-400 hover:text-green-600"
                        >
                          <ThumbsUp className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleFeedback(msg.id, 'down')}
                          className="h-6 w-6 p-0 text-gray-400 hover:text-red-600"
                        >
                          <ThumbsDown className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                {msg.type === 'user' && (
                  <User className="w-5 h-5 mt-0.5 flex-shrink-0" />
                )}
              </div>
            </div>
          </div>
        ))}

        {/* 로딩 상태 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-4 max-w-[80%]">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-blue-600" />
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span className="text-sm text-gray-600">
                    문서를 검색하고 답변을 생성하는 중...
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <div className="border-t p-4 bg-gray-50">
        <div className="flex space-x-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="PDF 문서에 대해 질문해보세요... (예: 대출 조건이 무엇인가요?)"
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!message.trim() || isLoading}
            className="px-4"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* 사용 가능한 문서 수 표시 */}
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>
            {availableDocuments.length > 0
              ? `${availableDocuments.length}개 문서에서 검색합니다`
              : '사용 가능한 문서가 없습니다'
            }
          </span>
          <span className="flex items-center space-x-1">
            <span>💡</span>
            <span>답변과 함께 관련 페이지로 자동 이동됩니다</span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default EnhancedChatInterface;
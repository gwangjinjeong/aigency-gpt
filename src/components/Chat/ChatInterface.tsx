
import React, { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Bot, User } from 'lucide-react';
import { ChatMessage } from '@/types';

interface ChatInterfaceProps {
  onMessageSent?: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onMessageSent }) => {
  const { t } = useLanguage();
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: t('chat.welcome'),
      timestamp: new Date().toISOString(),
    }
  ]);

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

    // Call the callback to show PDF viewer
    if (onMessageSent) {
      onMessageSent();
    }

    // Mock AI response - replace with actual OpenAI API call
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        type: 'assistant',
        content: "네, 새로 임용된 공무원도 공적 대출을 신청할 수 있습니다. 재직증명서 등의 서류가 필요합니다. 대출 정책 가이드의 구체적인 요건을 참조해 주세요.",
        timestamp: new Date().toISOString(),
        references: [
          {
            documentId: '1',
            filename: 'loan_products_guide_ko.pdf',
            pageNumber: 7,
            relevantText: '재직 3개월 이상인 공무원은 재직증명서와 함께...'
          }
        ]
      };
      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 2000);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[70%] rounded-lg p-4 ${
                msg.type === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-start space-x-2">
                {msg.type === 'assistant' && (
                  <Bot className="w-5 h-5 mt-0.5 text-blue-600" />
                )}
                <div className="flex-1">
                  <p className="text-sm">{msg.content}</p>
                  {msg.references && msg.references.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-600 mb-2">
                        {t('chat.references')}:
                      </p>
                      {msg.references.map((ref, index) => (
                        <div
                          key={index}
                          className="text-xs bg-white p-2 rounded border cursor-pointer hover:bg-gray-50"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{ref.filename}</span>
                            <span className="text-blue-600">
                              {t('chat.page')} {ref.pageNumber}
                            </span>
                          </div>
                          <p className="text-gray-600 mt-1 truncate">
                            {ref.relevantText}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {msg.type === 'user' && (
                  <User className="w-5 h-5 mt-0.5" />
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-4 max-w-[70%]">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-blue-600" />
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="border-t p-4">
        <div className="flex space-x-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t('chat.placeholder')}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!message.trim() || isLoading}
            className="px-4"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;

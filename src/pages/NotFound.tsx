import React from 'react';
import { useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { Button } from '@/components/ui/button';
import { FileText, Home, MessageCircle } from 'lucide-react';

const NotFound: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname
    );
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md mx-auto p-8">
        {/* 아이콘 */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
            <FileText className="w-8 h-8 text-white" />
          </div>
        </div>

        {/* 제목 */}
        <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">
          페이지를 찾을 수 없습니다
        </h2>
        <p className="text-gray-600 mb-8">
          요청하신 페이지가 존재하지 않거나 이동되었을 수 있습니다.
        </p>

        {/* 액션 버튼들 */}
        <div className="space-y-4">
          <Button
            onClick={() => navigate('/')}
            className="bg-blue-600 hover:bg-blue-700 w-full"
          >
            <Home className="w-4 h-4 mr-2" />
            홈으로 돌아가기
          </Button>

          <Button
            onClick={() => navigate('/chat')}
            variant="outline"
            className="w-full"
          >
            <MessageCircle className="w-4 h-4 mr-2" />
            채팅하기
          </Button>
        </div>

        {/* 디버그 정보 (개발 환경에서만) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-8 p-4 bg-gray-100 rounded-lg text-left">
            <p className="text-sm text-gray-600">
              <strong>경로:</strong> {location.pathname}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default NotFound;
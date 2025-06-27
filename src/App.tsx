import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
// 상대 경로로 변경
import { LanguageProvider } from './contexts/LanguageContext';
import { Toaster } from './components/ui/toaster';
import LandingPage from './pages/LandingPage';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';
import LoginPage from './pages/LoginPage';

// 메인 앱 컴포넌트
const AppContent: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          {/* 메인 랜딩 페이지 */}
          <Route path="/" element={<LandingPage />} />

          {/* 로그인 페이지 (껍데기) */}
          <Route path="/login" element={<LoginPage />} />

          {/* 채팅 페이지 */}
          <Route path="/chat" element={<ChatPage />} />

          {/* 관리자 페이지 (자체 인증 포함) */}
          <Route path="/admin" element={<AdminPage />} />

          {/* 데모 페이지 */}
          <Route path="/demo" element={<ChatPage />} />

          {/* 404 페이지 */}
          <Route
            path="*"
            element={
              <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
                  <p className="text-xl text-gray-600 mb-8">페이지를 찾을 수 없습니다</p>
                  <div className="space-x-4">
                    <a
                      href="/"
                      className="bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 inline-block"
                    >
                      홈으로 돌아가기
                    </a>
                    <a
                      href="/chat"
                      className="bg-gray-200 text-gray-700 px-6 py-3 rounded-md hover:bg-gray-300 inline-block"
                    >
                      채팅하기
                    </a>
                  </div>
                </div>
              </div>
            }
          />
        </Routes>

        {/* 전역 토스트 알림 */}
        <Toaster />
      </div>
    </Router>
  );
};

// 최상위 App 컴포넌트 - Auth 제거
const App: React.FC = () => {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
};

export default App;
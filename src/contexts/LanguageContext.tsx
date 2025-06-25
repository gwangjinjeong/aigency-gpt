
import React, { createContext, useContext, useState, ReactNode } from 'react';

type Language = 'ko' | 'en';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const translations = {
  ko: {
    // Navigation
    'nav.admin': '관리자',
    'nav.chat': '대화',
    'nav.login': '로그인',
    'nav.logout': '로그아웃',
    
    // Admin Page
    'admin.title': '문서 관리',
    'admin.upload': '파일 업로드',
    'admin.uploadDesc': 'PDF 파일을 업로드하여 대출 상품 및 정책 가이드를 관리하세요',
    'admin.selectFile': '파일 선택',
    'admin.uploadButton': '업로드',
    'admin.documents': '업로드된 문서',
    'admin.filename': '파일명',
    'admin.uploadTime': '업로드 시간',
    'admin.chunks': '청크 수',
    'admin.size': '크기',
    'admin.noDocuments': '업로드된 문서가 없습니다',
    
    // Chat Page
    'chat.title': '대출 상담 채팅',
    'chat.placeholder': '대출에 관해 궁금한 점을 물어보세요...',
    'chat.send': '전송',
    'chat.references': '참조 문서',
    'chat.page': '페이지',
    'chat.welcome': '안녕하세요! 대출 관련 질문을 도와드리겠습니다.',
    
    // Auth
    'auth.title': '로그인',
    'auth.email': '이메일',
    'auth.password': '비밀번호',
    'auth.login': '로그인',
    'auth.adminOnly': '관리자만 접근 가능합니다',
    
    // Common
    'common.loading': '로딩 중...',
    'common.error': '오류가 발생했습니다',
    'common.success': '성공적으로 완료되었습니다',
  },
  en: {
    // Navigation
    'nav.admin': 'Admin',
    'nav.chat': 'Chat',
    'nav.login': 'Login',
    'nav.logout': 'Logout',
    
    // Admin Page
    'admin.title': 'Document Management',
    'admin.upload': 'File Upload',
    'admin.uploadDesc': 'Upload PDF files to manage loan products and policy guides',
    'admin.selectFile': 'Select File',
    'admin.uploadButton': 'Upload',
    'admin.documents': 'Uploaded Documents',
    'admin.filename': 'Filename',
    'admin.uploadTime': 'Upload Time',
    'admin.chunks': 'Chunks',
    'admin.size': 'Size',
    'admin.noDocuments': 'No documents uploaded',
    
    // Chat Page
    'chat.title': 'Loan Consultation Chat',
    'chat.placeholder': 'Ask me anything about loans...',
    'chat.send': 'Send',
    'chat.references': 'Reference Documents',
    'chat.page': 'Page',
    'chat.welcome': 'Hello! I\'m here to help with your loan-related questions.',
    
    // Auth
    'auth.title': 'Login',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.login': 'Login',
    'auth.adminOnly': 'Admin access only',
    
    // Common
    'common.loading': 'Loading...',
    'common.error': 'An error occurred',
    'common.success': 'Successfully completed',
  }
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>('ko');

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

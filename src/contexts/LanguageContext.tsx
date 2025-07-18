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

    // Common
    'common.loading': '로딩 중...',
    'common.error': '오류가 발생했습니다',
    'common.success': '성공적으로 완료되었습니다',

    // Landing
    'landing.startChat': '시작하기',

    // Chat
    'chat.title': 'AI 문서 대화',
    'chat.welcome': '안녕하세요! PDF 문서에 대해 질문해보세요.',
    'chat.placeholder': '질문을 입력하세요...',
    'chat.references': '참조 문서',
    'chat.page': '페이지',
    'chat.noDocument': '문서가 선택되지 않았습니다',
  },
  en: {
    // Navigation
    'nav.admin': 'Admin',
    'nav.chat': 'Chat',
    'nav.login': 'Login',
    'nav.logout': 'Logout',

    // Common
    'common.loading': 'Loading...',
    'common.error': 'An error occurred',
    'common.success': 'Successfully completed',

    // Landing
    'landing.startChat': 'Get Started',

    // Chat
    'chat.title': 'AI Document Chat',
    'chat.welcome': 'Hello! Feel free to ask questions about your PDF documents.',
    'chat.placeholder': 'Enter your question...',
    'chat.references': 'References',
    'chat.page': 'Page',
    'chat.noDocument': 'No document selected',
  }
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>('ko');

  const t = (key: string): string => {
    const translation = translations[language][key as keyof typeof translations[typeof language]];
    return translation || key;
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
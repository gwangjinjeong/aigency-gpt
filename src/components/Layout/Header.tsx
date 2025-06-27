import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { FileText, MessageCircle } from 'lucide-react';

const Header = () => {
  const { t } = useLanguage();

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">DocuChat AI</span>
            </div>
            
            <nav className="flex space-x-4 ml-8">
              <a
                href="/chat"
                className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 transition-colors"
              >
                <MessageCircle className="w-4 h-4" />
                <span>{t('nav.chat')}</span>
              </a>
              <a
                href="/admin"
                className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 transition-colors"
              >
                <span>{t('nav.admin')}</span>
              </a>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.href = '/login'}
            >
              {t('nav.login')}
            </Button>
            <Button
              size="sm"
              onClick={() => window.location.href = '/chat'}
            >
              {t('nav.chat')}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
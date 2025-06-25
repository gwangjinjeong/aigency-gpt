
import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Languages, LogOut, FileText, MessageCircle, Shield } from 'lucide-react';

const Header = () => {
  const { language, setLanguage, t } = useLanguage();
  const { user, logout } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">BankBot</span>
            </div>
            
            {user && (
              <nav className="flex space-x-4 ml-8">
                <a
                  href="/chat"
                  className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>{t('nav.chat')}</span>
                </a>
                {user.role === 'admin' && (
                  <a
                    href="/admin"
                    className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                  >
                    <Shield className="w-4 h-4" />
                    <span>{t('nav.admin')}</span>
                  </a>
                )}
              </nav>
            )}
          </div>

          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setLanguage(language === 'ko' ? 'en' : 'ko')}
              className="flex items-center space-x-2"
            >
              <Languages className="w-4 h-4" />
              <span>{language === 'ko' ? '한국어' : 'English'}</span>
            </Button>

            {user ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-700">{user.name}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={logout}
                  className="flex items-center space-x-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span>{t('nav.logout')}</span>
                </Button>
              </div>
            ) : (
              <Button
                variant="default"
                size="sm"
                onClick={() => window.location.href = '/login'}
              >
                {t('nav.login')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;

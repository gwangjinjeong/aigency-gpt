
import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import Header from '@/components/Layout/Header';
import DocumentUpload from '@/components/Admin/DocumentUpload';
import { Shield } from 'lucide-react';

const AdminPage = () => {
  const { user } = useAuth();
  const { t } = useLanguage();

  if (!user) {
    return <div>Please log in</div>;
  }

  if (user.role !== 'admin') {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            <Shield className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {t('auth.adminOnly')}
            </h1>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">{t('admin.title')}</h1>
        </div>
        <DocumentUpload />
      </div>
    </div>
  );
};

export default AdminPage;


import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import Header from '@/components/Layout/Header';
import ChatInterface from '@/components/Chat/ChatInterface';
import PDFViewer from '@/components/Chat/PDFViewer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, MessageCircle } from 'lucide-react';

const Index = () => {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [showPDFViewer, setShowPDFViewer] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<{
    filename: string;
    pageNumber?: number;
  } | null>(null);

  const handleChatMessage = () => {
    setShowPDFViewer(true);
    // Mock selecting a document when user sends a message
    setSelectedDocument({
      filename: 'loan_products_guide_ko.pdf',
      pageNumber: 7
    });
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-8">
              {t('chat.title')}
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              {t('auth.adminOnly')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className={`grid gap-6 h-[calc(100vh-200px)] transition-all duration-300 ${
          showPDFViewer ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1 max-w-4xl mx-auto'
        }`}>
          {/* Chat Interface */}
          <div className="w-full">
            <Card className="h-full">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center space-x-2">
                  <MessageCircle className="w-5 h-5 text-blue-600" />
                  <span>{t('chat.title')}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 h-[calc(100%-80px)]">
                <ChatInterface onMessageSent={handleChatMessage} />
              </CardContent>
            </Card>
          </div>

          {/* PDF Viewer - Only shown after first chat message */}
          {showPDFViewer && (
            <div className="w-full">
              <Card className="h-full">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-blue-600" />
                    <span>{t('chat.references')}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0 h-[calc(100%-80px)]">
                  <PDFViewer document={selectedDocument} />
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Index;

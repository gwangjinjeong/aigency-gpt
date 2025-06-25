
import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { FileText, ExternalLink } from 'lucide-react';

interface PDFViewerProps {
  document: {
    filename: string;
    pageNumber?: number;
  } | null;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ document }) => {
  const { t } = useLanguage();

  if (!document) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p>{t('chat.noDocument')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Document Header */}
      <div className="border-b p-4 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <span className="font-medium text-gray-900">{document.filename}</span>
          </div>
          {document.pageNumber && (
            <span className="text-sm text-blue-600 bg-blue-50 px-2 py-1 rounded">
              {t('chat.page')} {document.pageNumber}
            </span>
          )}
        </div>
      </div>

      {/* PDF Content Area */}
      <div className="flex-1 bg-white border-2 border-dashed border-gray-200 flex items-center justify-center">
        <div className="text-center p-8">
          <div className="w-full h-96 bg-gray-100 rounded-lg flex items-center justify-center mb-4">
            <div className="text-center">
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 text-lg font-medium mb-2">PDF 뷰어</p>
              <p className="text-gray-500 text-sm mb-4">
                실제 PDF 내용이 여기에 표시됩니다
              </p>
              {document.pageNumber && (
                <div className="bg-yellow-100 border border-yellow-300 rounded p-3 text-sm">
                  <p className="text-yellow-800 font-medium">
                    📍 참조된 페이지: {document.pageNumber}
                  </p>
                  <p className="text-yellow-700 mt-1">
                    "정부 공무원은 재직증명서와 함께 대출을 신청할 수 있습니다..."
                  </p>
                </div>
              )}
            </div>
          </div>
          
          <button className="flex items-center space-x-2 text-blue-600 hover:text-blue-800 mx-auto">
            <ExternalLink className="w-4 h-4" />
            <span className="text-sm">새 창에서 열기</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default PDFViewer;


import React, { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Upload, FileText, Clock, Hash, HardDrive } from 'lucide-react';
import { Document } from '@/types';

const DocumentUpload = () => {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([
    {
      id: '1',
      filename: 'loan_products_guide_ko.pdf',
      uploadTime: '2024-06-25 14:30',
      chunks: 45,
      size: '2.3 MB',
      language: 'ko'
    },
    {
      id: '2',
      filename: 'public_loan_policy_en.pdf',
      uploadTime: '2024-06-25 13:15',
      chunks: 32,
      size: '1.8 MB',
      language: 'en'
    }
  ]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setUploading(true);
    // Mock upload process - replace with actual Supabase upload
    setTimeout(() => {
      const newDoc: Document = {
        id: Math.random().toString(36).substr(2, 9),
        filename: selectedFile.name,
        uploadTime: new Date().toLocaleString('ko-KR'),
        chunks: Math.floor(Math.random() * 50) + 10,
        size: `${(selectedFile.size / 1024 / 1024).toFixed(1)} MB`,
        language: 'ko'
      };
      setDocuments([newDoc, ...documents]);
      setSelectedFile(null);
      setUploading(false);
    }, 2000);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Upload className="w-5 h-5 text-blue-600" />
            <span>{t('admin.upload')}</span>
          </CardTitle>
          <CardDescription>{t('admin.uploadDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <Input
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              className="mb-4"
            />
            {selectedFile && (
              <div className="text-sm text-gray-600 mb-4">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
              </div>
            )}
            <Button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="w-full"
            >
              {uploading ? t('common.loading') : t('admin.uploadButton')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('admin.documents')}</CardTitle>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              {t('admin.noDocuments')}
            </div>
          ) : (
            <div className="space-y-4">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-blue-600" />
                    <div>
                      <div className="font-medium text-gray-900">{doc.filename}</div>
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{doc.uploadTime}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Hash className="w-3 h-3" />
                          <span>{doc.chunks} chunks</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <HardDrive className="w-3 h-3" />
                          <span>{doc.size}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      doc.language === 'ko' 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {doc.language === 'ko' ? '한국어' : 'English'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DocumentUpload;

import React, { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Upload, 
  FileText, 
  Clock, 
  Hash, 
  HardDrive, 
  CheckCircle, 
  XCircle, 
  Loader2,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';

// API 설정
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// 정확한 타입 정의
interface ApiDocument {
  id: string;
  filename: string;
  created_at: string;
  chunk_count?: number;
  file_size?: number;
  language?: 'ko' | 'en';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processed_at?: string;
  error_message?: string;
}

interface Document {
  id: string;
  filename: string;
  uploadTime: string;
  chunks: number;
  size: string | number;
  language: 'ko' | 'en';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processedAt?: string;
  errorMessage?: string;
}

interface ApiResponse<T> {
  status: 'success' | 'error';
  data: T;
  message?: string;
}

interface UploadResponse {
  status: string;
  document_id: string;
  filename: string;
  file_size: number;
  processing: boolean;
  message: string;
}

interface StatusResponse {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  document_id: string;
  filename: string;
  error_message?: string;
}

interface UploadProgress {
  stage: 'uploading' | 'processing' | 'completed' | 'failed';
  message: string;
  progress: number;
}

const DocumentUpload = () => {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 문서 목록 조회
  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/documents?limit=50`);
      const data: ApiResponse<ApiDocument[]> = await response.json();

      if (data.status === 'success') {
        const formattedDocs: Document[] = data.data.map((doc: ApiDocument) => ({
          id: doc.id,
          filename: doc.filename,
          uploadTime: new Date(doc.created_at).toLocaleString('ko-KR'),
          chunks: doc.chunk_count || 0,
          size: doc.file_size || 'Unknown',
          language: doc.language || 'ko',
          status: doc.status,
          processedAt: doc.processed_at,
          errorMessage: doc.error_message
        }));
        setDocuments(formattedDocs);
      }
    } catch (err) {
      console.error('문서 목록 조회 실패:', err);
      setError('문서 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트 마운트 시 문서 목록 조회
  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        setError('PDF 파일만 업로드 가능합니다.');
        return;
      }

      if (file.size > 50 * 1024 * 1024) { // 50MB 제한
        setError('파일 크기는 50MB 이하여야 합니다.');
        return;
      }

      setSelectedFile(file);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setError(null);
    setUploadProgress({
      stage: 'uploading',
      message: '파일을 업로드하는 중...',
      progress: 0
    });

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      // 파일 업로드
      const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error('파일 업로드에 실패했습니다.');
      }

      const uploadResult: UploadResponse = await uploadResponse.json();
      const documentId = uploadResult.document_id;

      // 업로드 완료, 처리 시작
      setUploadProgress({
        stage: 'processing',
        message: 'PDF를 분석하고 벡터화하는 중...',
        progress: 30
      });

      // 처리 상태 폴링
      const pollProcessingStatus = async () => {
        let attempts = 0;
        const maxAttempts = 60; // 최대 5분 (5초 간격)

        const poll = async () => {
          try {
            const statusResponse = await fetch(`${API_BASE_URL}/upload/status/${documentId}`);
            const statusData: StatusResponse = await statusResponse.json();

            if (statusData.status === 'completed') {
              setUploadProgress({
                stage: 'completed',
                message: '처리가 완료되었습니다!',
                progress: 100
              });

              // 문서 목록 새로고침
              await fetchDocuments();

              // 3초 후 상태 초기화
              setTimeout(() => {
                setUploadProgress(null);
                setSelectedFile(null);
              }, 3000);

            } else if (statusData.status === 'failed') {
              throw new Error(statusData.error_message || '처리 중 오류가 발생했습니다.');
            } else if (statusData.status === 'processing') {
              const progress = Math.min(30 + (attempts * 2), 90);
              setUploadProgress({
                stage: 'processing',
                message: '텍스트 추출 및 임베딩 생성 중...',
                progress
              });

              attempts++;
              if (attempts < maxAttempts) {
                setTimeout(poll, 5000); // 5초마다 상태 확인
              } else {
                throw new Error('처리 시간이 초과되었습니다.');
              }
            } else {
              // pending 상태
              setTimeout(poll, 5000);
            }
          } catch (error) {
            console.error('상태 확인 중 오류:', error);
            setUploadProgress({
              stage: 'failed',
              message: error instanceof Error ? error.message : '처리 중 오류가 발생했습니다.',
              progress: 0
            });
          }
        };

        poll();
      };

      pollProcessingStatus();

    } catch (err) {
      console.error('업로드 실패:', err);
      setUploadProgress({
        stage: 'failed',
        message: err instanceof Error ? err.message : '업로드에 실패했습니다.',
        progress: 0
      });
    }
  };

  const handleRetry = () => {
    setUploadProgress(null);
    setError(null);
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-600" />;
    }
  };

  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'processing':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
  };

  const getStatusText = (status: Document['status']) => {
    switch (status) {
      case 'completed': return '완료';
      case 'failed': return '실패';
      case 'processing': return '처리중';
      default: return '대기중';
    }
  };

  return (
    <div className="space-y-6">
      {/* 시스템 상태 표시 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center space-x-2">
              <Upload className="w-5 h-5 text-blue-600" />
              <span>PDF 업로드</span>
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchDocuments}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </CardTitle>
          <CardDescription>PDF 파일을 업로드하여 AI 벡터화 처리를 시작하세요</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 에러 메시지 */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* 업로드 영역 */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />

            {!uploadProgress ? (
              <>
                <Input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="mb-4"
                  disabled={loading}
                />
                {selectedFile && (
                  <div className="text-sm text-gray-600 mb-4 p-3 bg-gray-50 rounded">
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-xs text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                    </p>
                  </div>
                )}
                <Button
                  onClick={handleUpload}
                  disabled={!selectedFile || loading}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      업로드 중...
                    </>
                  ) : (
                    'PDF 업로드'
                  )}
                </Button>
              </>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-center space-x-2">
                  {uploadProgress.stage === 'uploading' && <Upload className="w-5 h-5 text-blue-600" />}
                  {uploadProgress.stage === 'processing' && <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />}
                  {uploadProgress.stage === 'completed' && <CheckCircle className="w-5 h-5 text-green-600" />}
                  {uploadProgress.stage === 'failed' && <XCircle className="w-5 h-5 text-red-600" />}
                  <span className="text-sm font-medium">{uploadProgress.message}</span>
                </div>

                <Progress value={uploadProgress.progress} className="w-full" />

                {uploadProgress.stage === 'failed' && (
                  <Button
                    onClick={handleRetry}
                    variant="outline"
                    size="sm"
                    className="mt-2"
                  >
                    다시 시도
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 문서 목록 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>업로드된 문서</span>
            <span className="text-sm text-gray-500">
              총 {documents.length}개 문서
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span className="ml-2 text-gray-600">문서 목록을 불러오는 중...</span>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p>업로드된 문서가 없습니다</p>
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
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{doc.filename}</div>
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{doc.uploadTime}</span>
                        </span>
                        {doc.chunks > 0 && (
                          <span className="flex items-center space-x-1">
                            <Hash className="w-3 h-3" />
                            <span>{doc.chunks} chunks</span>
                          </span>
                        )}
                        <span className="flex items-center space-x-1">
                          <HardDrive className="w-3 h-3" />
                          <span>{doc.size}</span>
                        </span>
                      </div>
                      {doc.errorMessage && (
                        <div className="text-xs text-red-600 mt-1 truncate max-w-md">
                          오류: {doc.errorMessage}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(doc.status)}`}>
                      <span className="flex items-center space-x-1">
                        {getStatusIcon(doc.status)}
                        <span>{getStatusText(doc.status)}</span>
                      </span>
                    </span>
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
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
  RefreshCw,
  Wifi,
  WifiOff
} from 'lucide-react';

// API 설정 - 연결 상태 확인 포함
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return 'http://127.0.0.1:8000';
};

const API_BASE_URL = getApiBaseUrl();

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
  status: string; // API call status
  document_id: string;
  filename: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'; // Actual document status
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
  const [serverStatus, setServerStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  // 서버 연결 확인
  const checkServerConnection = async () => {
    try {
      setServerStatus('checking');
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        // timeout: 5000
      });

      if (response.ok) {
        setServerStatus('connected');
        console.log(`✅ API server connected at: ${API_BASE_URL}`);
        return true;
      }
    } catch (error) {
      console.log(`❌ No server at: ${API_BASE_URL}`);
      setServerStatus('disconnected');
      return false;
    }
    return false;
  };

  // 문서 목록 조회
  const fetchDocuments = async () => {
    if (serverStatus !== 'connected') {
      setError('API 서버에 연결되지 않았습니다. 백엔드 서버를 실행해주세요.');
      return;
    }

    try {
      setLoading(true);
      console.log('API 호출:', `${API_BASE_URL}/documents?limit=50`);

      const response = await fetch(`${API_BASE_URL}/documents?limit=50`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: ApiResponse<ApiDocument[]> = await response.json();

      if (data.status === 'success') {
        const formattedDocs: Document[] = data.data.map((doc: ApiDocument) => ({
          id: doc.id,
          filename: doc.filename,
          uploadTime: new Date(doc.created_at).toLocaleString('ko-KR'),
          chunks: doc.chunk_count || 0,
          size: typeof doc.file_size === 'number' ? `${(doc.file_size / 1024 / 1024).toFixed(1)} MB` : 'Unknown',
          language: doc.language || 'ko',
          status: doc.status,
          processedAt: doc.processed_at,
          errorMessage: doc.error_message
        }));
        setDocuments(formattedDocs);
        setError(null);
      }
    } catch (err) {
      console.error('문서 목록 조회 실패:', err);
      setError(`서버 연결 실패: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트 마운트 시 서버 연결 확인 및 문서 목록 조회
  useEffect(() => {
    handleRefresh(); // 컴포넌트 마운트 시 바로 새로고침 로직 실행
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
    if (!selectedFile || serverStatus !== 'connected') return;

    setError(null);
    setUploadProgress({
      stage: 'uploading',
      message: '파일을 업로드하는 중...',
      progress: 0
    });

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('auto_process', 'true'); // 자동 처리 활성화

      // 파일 업로드
      const uploadResponse = await fetch(`${API_BASE_URL}/api/upload`, {
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
            const statusResponse = await fetch(`${API_BASE_URL}/api/upload/status/${documentId}`);
            const statusData: StatusResponse = await statusResponse.json();

            if (statusData.processing_status === 'completed') {
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

            } else if (statusData.processing_status === 'failed') {
              throw new Error(statusData.error_message || '처리 중 오류가 발생했습니다.');
            } else if (statusData.processing_status === 'processing') {
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

  const handleRefresh = async () => {
    const isConnected = await checkServerConnection();
    if (isConnected) {
      await fetchDocuments();
    }
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

  // 서버 상태 표시 컴포넌트
  const ServerStatusIndicator = () => (
    <div className="flex items-center space-x-2 text-sm">
      {serverStatus === 'checking' && (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          <span className="text-gray-600">서버 연결 확인 중...</span>
        </>
      )}
      {serverStatus === 'connected' && (
        <>
          <Wifi className="w-4 h-4 text-green-600" />
          <span className="text-green-600">서버 연결됨</span>
        </>
      )}
      {serverStatus === 'disconnected' && (
        <>
          <WifiOff className="w-4 h-4 text-red-600" />
          <span className="text-red-600">서버 연결 실패</span>
          <Button
            onClick={handleRefresh}
            size="sm"
            variant="outline"
            className="ml-2"
          >
            다시 시도
          </Button>
        </>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* 서버 상태 표시 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center space-x-2">
              <Upload className="w-5 h-5 text-blue-600" />
              <span>PDF 업로드</span>
            </span>
            <div className="flex items-center space-x-2">
              <ServerStatusIndicator />
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={loading || serverStatus === 'checking'}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </CardTitle>
          <CardDescription>PDF 파일을 업로드하여 AI 벡터화 처리를 시작하세요</CardDescription>
        </CardHeader>

        {/* 서버 연결 실패 시 경고 메시지 */}
        {serverStatus === 'disconnected' && (
          <CardContent>
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <p>백엔드 서버에 연결할 수 없습니다. ({API_BASE_URL})</p>
                  <div className="text-sm">
                    <p className="font-medium">해결 방법:</p>
                    <ol className="list-decimal list-inside space-y-1 mt-1">
                      <li>터미널에서 <code className="bg-gray-100 px-1 rounded">cd backend</code></li>
                      <li><code className="bg-gray-100 px-1 rounded">python main.py</code> 실행</li>
                      <li>서버가 http://localhost:8000 에서 실행되는지 확인</li>
                    </ol>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          </CardContent>
        )}

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
                  disabled={loading || serverStatus !== 'connected'}
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
                  disabled={!selectedFile || loading || serverStatus !== 'connected'}
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
              {serverStatus === 'disconnected' && (
                <p className="text-sm mt-2">서버 연결 후 새로고침해주세요</p>
              )}
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

      {/* 관리자 도구 */}
      <Card>
        <CardHeader>
          <CardTitle>관리자 도구</CardTitle>
        </CardHeader>
        <CardContent>
          <Button 
            variant="destructive"
            onClick={async () => {
              if (window.confirm('정말로 모든 벡터 데이터를 삭제하고 데이터베이스를 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
                try {
                  const response = await fetch(`${API_BASE_URL}/admin/reset-vector-db`, { method: 'POST' });
                  const data = await response.json();
                  if (response.ok) {
                    alert('벡터 데이터베이스가 성공적으로 초기화되었습니다.');
                    handleRefresh();
                  } else {
                    throw new Error(data.message || '초기화 실패');
                  }
                } catch (err) {
                  alert(`초기화 중 오류 발생: ${err instanceof Error ? err.message : err}`);
                }
              }
            }}
          >
            벡터 DB 초기화
          </Button>
          <p className="text-sm text-gray-500 mt-2">데이터 불일치 문제가 발생할 경우, 벡터 데이터베이스를 초기화하세요. 모든 문서의 벡터가 삭제되며, 재처리가 필요할 수 있습니다.</p>
        </CardContent>
      </Card>
    </div>
  );
};

export default DocumentUpload;
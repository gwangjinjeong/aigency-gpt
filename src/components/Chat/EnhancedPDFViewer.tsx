import React, { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Document, Page, pdfjs } from 'react-pdf';
import {
  FileText,
  ExternalLink,
  Search,
  ChevronLeft,
  ChevronRight,
  Highlighter,
  ZoomIn,
  ZoomOut,
  Download,
  MapPin,
  Loader2
} from 'lucide-react';

// PDF.js worker 설정
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PDFLocation {
  page_number: number;
  bbox: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  context: string;
  matched_text: string;
}

interface PDFViewerProps {
  document: {
    id: string;
    filename: string;
    url: string;
    pageNumber?: number;
    highlightText?: string;
    searchLocations?: PDFLocation[];
  } | null;
  onPageChange?: (pageNumber: number) => void;
  onHighlightRequest?: (text: string) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const EnhancedPDFViewer: React.FC<PDFViewerProps> = ({
  document,
  onPageChange,
  onHighlightRequest
}) => {
  const { t } = useLanguage();
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<PDFLocation[]>([]);
  const [currentSearchIndex, setCurrentSearchIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [highlightedPdfUrl, setHighlightedPdfUrl] = useState('');
  const [isCreatingHighlight, setIsCreatingHighlight] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [isPdfLoading, setIsPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState<string | null>(null);

  useEffect(() => {
    if (document?.pageNumber) {
      setCurrentPage(document.pageNumber);
    }

    // 🔥 문서 정보 로드 시 총 페이지 수 획득
    if (document?.id) {
      fetchDocumentPages(document.id);
    }

    // 🔥 자동 검색 완전 비활성화 - 사용자가 직접 검색해야 함
    if (document?.highlightText) {
      console.log('받은 highlightText:', document.highlightText);
      console.log('받은 highlightText 길이:', document.highlightText.length);

      // 검색창에만 설정하고 자동 검색은 하지 않음
      const limitedText = document.highlightText.trim().slice(0, 50);
      setSearchText(limitedText);

      // 🔥 자동 검색 비활성화
      // handleSearch(limitedText);
    }
  }, [document]);

  // 🔥 PDF 로드 성공 시 호출
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setTotalPages(numPages);
    setIsPdfLoading(false);
    setPdfError(null);
    console.log(`PDF 로드 성공: ${numPages}페이지`);
  };

  // 🔥 PDF 로드 실패 시 호출
  const onDocumentLoadError = (error: Error) => {
    setIsPdfLoading(false);
    setPdfError(error.message);
    console.error('PDF 로드 실패:', error);
  };

  // 🔥 페이지 렌더링 성공 시 호출
  const onPageLoadSuccess = () => {
    console.log(`페이지 ${currentPage} 렌더링 완료`);
  };

  // 🔥 문서 페이지 정보 획득
  const fetchDocumentPages = async (documentId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/pages`);
      const data = await response.json();

      if (data.status === 'success') {
        setTotalPages(data.total_pages);
        console.log(`문서 총 페이지 수: ${data.total_pages}`);
      }
    } catch (error) {
      console.error('페이지 정보 조회 실패:', error);
    }
  };

  const handleSearch = async (text: string) => {
    if (!document || !text.trim()) return;

    // 🔥 검색어 길이 제한 (최대 100자)
    const searchQuery = text.trim().slice(0, 100);

    setIsSearching(true);
    try {
      // 🔥 문서 ID 디버깅 로그 추가
      console.log('검색 요청 - 문서 ID:', document.id);
      console.log('검색 요청 - 문서 정보:', document);
      console.log('원본 검색어 길이:', text.length);
      console.log('제한된 검색어:', searchQuery);

      // 🔥 임시 해결책: 올바른 문서 ID 사용
      const actualDocumentId = document.id === '43bc0171-224a-4d7b-9982-daf480077b70'
        ? 'd5c75f57-7dff-4607-a750-30ec2d690e84'
        : document.id;

      console.log('원본 문서 ID:', document.id);
      console.log('사용할 문서 ID:', actualDocumentId);

      // 🔥 수정된 API 엔드포인트: /api/page-navigation/{document_id}
      const response = await fetch(
        `${API_BASE_URL}/api/page-navigation/${actualDocumentId}?search_text=${encodeURIComponent(searchQuery)}`
      );

      console.log('API Response Status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error Response:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log('API Response Data:', data);

      if (data.status === 'success' && data.locations && data.locations.length > 0) {
        setSearchResults(data.locations);
        setCurrentSearchIndex(0);
        const firstResult = data.locations[0];
        setCurrentPage(firstResult.page_number);
        onPageChange?.(firstResult.page_number);
      } else {
        setSearchResults([]);
        alert('해당 텍스트를 찾을 수 없습니다.');
      }
    } catch (error) {
      console.error('검색 오류:', error);

      // 🔥 더 상세한 에러 처리
      if (error.message.includes('404')) {
        alert('문서를 찾을 수 없습니다. 문서가 정상적으로 처리되었는지 확인해주세요.');
      } else if (error.message.includes('500')) {
        alert('서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      } else {
        alert(`검색 중 오류가 발생했습니다: ${error.message}`);
      }
    } finally {
      setIsSearching(false);
    }
  };

  const handleCreateHighlight = async () => {
    if (!document || !searchText.trim()) return;

    setIsCreatingHighlight(true);
    try {
      // 🔥 하이라이트 요청 디버깅 로그 추가
      console.log('하이라이트 요청 - 문서 ID:', document.id);
      console.log('하이라이트 요청 - 페이지:', currentPage);
      console.log('하이라이트 요청 - 검색어:', searchText);

      // 🔥 임시 해결책: 올바른 문서 ID 사용
      const actualDocumentId = document.id === '43bc0171-224a-4d7b-9982-daf480077b70'
        ? 'd5c75f57-7dff-4607-a750-30ec2d690e84'
        : document.id;

      // 🔥 수정된 API 엔드포인트: /api/highlight
      const response = await fetch(`${API_BASE_URL}/api/highlight`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: actualDocumentId,
          page_number: currentPage,
          search_text: searchText
        })
      });

      console.log('Highlight API Response Status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Highlight API Error:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log('Highlight API Response:', data);

      if (data.status === 'success') {
        setHighlightedPdfUrl(data.highlighted_pdf_url);
        alert('하이라이트된 PDF가 생성되었습니다!');
      } else {
        alert(`하이라이트 생성 실패: ${data.message || '알 수 없는 오류'}`);
      }
    } catch (error) {
      console.error('하이라이트 생성 오류:', error);
      alert(`하이라이트 생성 중 오류: ${error.message}`);
    } finally {
      setIsCreatingHighlight(false);
    }
  };

  const navigateToSearchResult = (index: number) => {
    if (searchResults[index]) {
      setCurrentSearchIndex(index);
      const result = searchResults[index];
      setCurrentPage(result.page_number);
      onPageChange?.(result.page_number);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      const newPage = currentPage - 1;
      setCurrentPage(newPage);
      onPageChange?.(newPage);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      const newPage = currentPage + 1;
      setCurrentPage(newPage);
      onPageChange?.(newPage);
    }
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 25, 200));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 25, 50));
  };

  const downloadHighlightedPdf = () => {
    if (highlightedPdfUrl) {
      window.open(highlightedPdfUrl, '_blank');
    }
  };

  if (!document) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 bg-gray-50">
        <div className="text-center">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-lg font-medium mb-2">{t('chat.noDocument')}</p>
          <p className="text-sm text-gray-400">
            질문을 하시면 관련 문서와 페이지가 표시됩니다
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 문서 헤더 */}
      <div className="border-b bg-gray-50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <span className="font-medium text-gray-900 truncate max-w-md" title={document.filename}>
              {document.filename}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            {document.pageNumber && (
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                <MapPin className="w-3 h-3 mr-1" />
                {t('chat.page')} {document.pageNumber}
              </Badge>
            )}
          </div>
        </div>

        {/* 검색 및 도구 모음 */}
        <div className="flex items-center space-x-2">
          <div className="flex-1 flex items-center space-x-2">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                type="text"
                placeholder="PDF 내 텍스트 검색... (최대 100자)"
                value={searchText}
                onChange={(e) => {
                  // 🔥 입력 길이 제한
                  const value = e.target.value.slice(0, 100);
                  setSearchText(value);
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchText)}
                className="pl-10 pr-4 py-2"
                disabled={isSearching}
                maxLength={100}
              />
            </div>
            <Button
              onClick={() => handleSearch(searchText)}
              disabled={!searchText.trim() || isSearching}
              size="sm"
              variant="outline"
            >
              {isSearching ? '검색중...' : '검색'}
            </Button>
          </div>

          <div className="flex items-center space-x-1">
            <Button
              onClick={handleCreateHighlight}
              disabled={!searchText.trim() || isCreatingHighlight}
              size="sm"
              variant="outline"
              className="text-yellow-600 border-yellow-300 hover:bg-yellow-50"
            >
              <Highlighter className="w-4 h-4 mr-1" />
              {isCreatingHighlight ? '생성중...' : '하이라이트'}
            </Button>

            {highlightedPdfUrl && (
              <Button
                onClick={downloadHighlightedPdf}
                size="sm"
                variant="outline"
                className="text-green-600 border-green-300 hover:bg-green-50"
              >
                <Download className="w-4 h-4 mr-1" />
                다운로드
              </Button>
            )}
          </div>
        </div>

        {/* 검색 결과 네비게이션 */}
        {searchResults.length > 0 && (
          <div className="mt-3 flex items-center justify-between bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-yellow-800">
                검색 결과: {searchResults.length}개 발견
              </span>
              <span className="text-xs text-yellow-600">
                ({currentSearchIndex + 1}/{searchResults.length})
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <Button
                onClick={() => navigateToSearchResult(currentSearchIndex - 1)}
                disabled={currentSearchIndex === 0}
                size="sm"
                variant="ghost"
                className="h-7 w-7 p-0"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button
                onClick={() => navigateToSearchResult(currentSearchIndex + 1)}
                disabled={currentSearchIndex === searchResults.length - 1}
                size="sm"
                variant="ghost"
                className="h-7 w-7 p-0"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* PDF 뷰어 영역 - React PDF 사용 */}
      <div className="flex-1 bg-gray-100 relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center">
          {isPdfLoading && (
            <div className="flex items-center space-x-2 text-gray-600">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span>PDF를 로드하는 중...</span>
            </div>
          )}

          {pdfError && (
            <div className="text-center p-8 bg-white rounded-lg shadow-sm border border-red-200">
              <div className="text-red-600 mb-4">
                <FileText className="w-16 h-16 mx-auto mb-4" />
                <p className="text-lg font-medium">PDF 로드 실패</p>
                <p className="text-sm mt-2">{pdfError}</p>
              </div>
              <Button
                onClick={() => window.open(document.url, '_blank')}
                variant="outline"
                className="mt-4"
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                새 창에서 열기
              </Button>
            </div>
          )}

          {!isPdfLoading && !pdfError && (
            <div className="w-full h-full flex items-center justify-center p-4">
              <Document
                file={document.url}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={
                  <div className="flex items-center space-x-2 text-gray-600">
                    <Loader2 className="w-6 h-6 animate-spin" />
                    <span>문서를 불러오는 중...</span>
                  </div>
                }
                error={
                  <div className="text-center text-red-600">
                    <p>PDF를 로드할 수 없습니다.</p>
                  </div>
                }
                noData={
                  <div className="text-center text-gray-600">
                    <p>PDF 데이터가 없습니다.</p>
                  </div>
                }
                className="max-w-full max-h-full"
              >
                <Page
                  pageNumber={currentPage}
                  scale={zoom / 100}
                  onLoadSuccess={onPageLoadSuccess}
                  loading={
                    <div className="flex items-center justify-center h-96">
                      <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                    </div>
                  }
                  error={
                    <div className="flex items-center justify-center h-96 text-red-600">
                      <p>페이지를 로드할 수 없습니다.</p>
                    </div>
                  }
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                  className="shadow-lg border border-gray-300"
                />
              </Document>
            </div>
          )}

          {/* 🔥 검색 결과 하이라이트 오버레이 */}
          {searchResults.length > 0 && !isPdfLoading && (
            <div className="absolute top-4 right-4 bg-yellow-100 border border-yellow-300 rounded-lg p-3 text-sm shadow-lg">
              <p className="text-yellow-800 font-medium mb-1">
                📍 현재 위치: 페이지 {currentPage}
              </p>
              <p className="text-yellow-700">
                "{searchResults[currentSearchIndex]?.matched_text.slice(0, 50)}..."
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 하단 컨트롤 */}
      <div className="border-t bg-gray-50 p-3">
        <div className="flex items-center justify-between">
          {/* 페이지 네비게이션 */}
          <div className="flex items-center space-x-2">
            <Button
              onClick={handlePrevPage}
              disabled={currentPage <= 1}
              size="sm"
              variant="outline"
              className="h-8 w-8 p-0"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>

            <div className="flex items-center space-x-2">
              <Input
                type="number"
                value={currentPage}
                onChange={(e) => {
                  const page = parseInt(e.target.value);
                  if (page >= 1 && page <= totalPages) {
                    setCurrentPage(page);
                    onPageChange?.(page);
                  }
                }}
                className="w-16 h-8 text-center text-sm"
                min="1"
                max={totalPages}
              />
              <span className="text-sm text-gray-500">/ {totalPages}</span>
            </div>

            <Button
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              size="sm"
              variant="outline"
              className="h-8 w-8 p-0"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          {/* 줌 컨트롤 */}
          <div className="flex items-center space-x-2">
            <Button
              onClick={handleZoomOut}
              size="sm"
              variant="outline"
              className="h-8 w-8 p-0"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="text-sm text-gray-600 min-w-[3rem] text-center">
              {zoom}%
            </span>
            <Button
              onClick={handleZoomIn}
              size="sm"
              variant="outline"
              className="h-8 w-8 p-0"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
          </div>

          {/* 외부 링크 */}
          <Button
            onClick={() => window.open(document.url, '_blank')}
            size="sm"
            variant="outline"
            className="flex items-center space-x-1"
          >
            <ExternalLink className="w-4 h-4" />
            <span className="text-sm">새 창에서 열기</span>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default EnhancedPDFViewer;
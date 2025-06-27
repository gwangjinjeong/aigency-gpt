import React, { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
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
  MapPin
} from 'lucide-react';

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

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

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

  useEffect(() => {
    if (document?.pageNumber) {
      setCurrentPage(document.pageNumber);
    }
    if (document?.highlightText) {
      setSearchText(document.highlightText);
      handleSearch(document.highlightText);
    }
  }, [document]);

  const handleSearch = async (text: string) => {
    if (!document || !text.trim()) return;

    setIsSearching(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/chat/page-navigation/${document.id}?search_text=${encodeURIComponent(text)}`
      );
      const data = await response.json();

      if (data.status === 'success' && data.locations.length > 0) {
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
      alert('검색 중 오류가 발생했습니다.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleCreateHighlight = async () => {
    if (!document || !searchText.trim()) return;

    setIsCreatingHighlight(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/highlight`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: document.id,
          page_number: currentPage,
          search_text: searchText
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        setHighlightedPdfUrl(data.highlighted_pdf_url);
        alert('하이라이트된 PDF가 생성되었습니다!');
      } else {
        alert('하이라이트 생성에 실패했습니다.');
      }
    } catch (error) {
      console.error('하이라이트 생성 오류:', error);
      alert('하이라이트 생성 중 오류가 발생했습니다.');
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
                placeholder="PDF 내 텍스트 검색..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchText)}
                className="pl-10 pr-4 py-2"
                disabled={isSearching}
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

      {/* PDF 뷰어 영역 */}
      <div className="flex-1 bg-gray-100 relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center p-8 bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300">
            <div className="w-full h-96 bg-gradient-to-br from-blue-50 to-gray-50 rounded-lg flex items-center justify-center mb-4 relative overflow-hidden">
              {/* PDF 미리보기 시뮬레이션 */}
              <div className="absolute inset-4 bg-white border border-gray-200 rounded shadow-sm">
                <div className="p-4 h-full">
                  <div className="space-y-2">
                    <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-full"></div>
                    <div className="h-3 bg-gray-200 rounded w-5/6"></div>

                    {/* 하이라이트 시뮬레이션 */}
                    {searchText && (
                      <div className="h-3 bg-yellow-200 rounded w-2/3 animate-pulse"></div>
                    )}

                    <div className="h-3 bg-gray-200 rounded w-4/5"></div>
                    <div className="h-3 bg-gray-200 rounded w-full"></div>
                  </div>
                </div>
              </div>

              {/* 페이지 표시 */}
              <div className="absolute bottom-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                {currentPage} / {totalPages || '?'}
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-gray-600 text-lg font-medium">PDF 뷰어</p>
              <p className="text-gray-500 text-sm">
                실제 PDF 내용이 여기에 표시됩니다
              </p>

              {searchResults.length > 0 && (
                <div className="bg-yellow-100 border border-yellow-300 rounded p-3 text-sm">
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
              <span className="text-sm text-gray-500">/ {totalPages || '?'}</span>
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
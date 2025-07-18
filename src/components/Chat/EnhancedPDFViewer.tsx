// src/components/Chat/EnhancedPDFViewer.tsx
import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  FileText,
  Search,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Loader2
} from 'lucide-react';

// PDF.js worker 설정
pdfjs.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.mjs`;

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

interface PDFLocation {
  page_number: number;
  bbox: { x0: number; y0: number; x1: number; y1: number; };
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
  } | null;
}

const EnhancedPDFViewer: React.FC<PDFViewerProps> = ({ document }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<PDFLocation[]>([]);
  const [currentSearchIndex, setCurrentSearchIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const pageContainerRef = useRef<HTMLDivElement>(null);

  const getSearchableSnippet = (text: string): string => {
    const trimmedText = text.trim();
    const sentenceEnd = trimmedText.indexOf('.');
    if (sentenceEnd > 10 && sentenceEnd < 100) {
      return trimmedText.substring(0, sentenceEnd + 1);
    }
    return trimmedText.split(/\s+/).slice(0, 10).join(' ');
  };

  useEffect(() => {
    if (document) {
      // 문서가 변경되면 관련 상태 초기화
      setSearchResults([]);
      setSearchText('');
      setTotalPages(1);
      setCurrentPage(document.pageNumber || 1);
      setPdfError(null);

      // 하이라이트 텍스트가 있으면 자동 검색 실행
      if (document.highlightText) {
        const snippet = getSearchableSnippet(document.highlightText);
        setSearchText(snippet);
        handleSearch(snippet, document.id);
      }
    }
  }, [document]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setTotalPages(numPages);
    setPdfError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    setPdfError(error.message);
    console.error('PDF 로드 실패:', error);
  };

  const handleSearch = async (text: string, docId: string) => {
    if (!docId || !text.trim()) return;
    const searchQuery = text.trim().slice(0, 100);
    setIsSearching(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/page-navigation/${docId}?search_text=${encodeURIComponent(searchQuery)}`
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.status === 'success' && data.locations?.length > 0) {
        setSearchResults(data.locations);
        setCurrentSearchIndex(0);
        setCurrentPage(data.locations[0].page_number);
      } else {
        setSearchResults([]);
        alert('해당 텍스트를 찾을 수 없습니다.');
      }
    } catch (error) {
      console.error('검색 오류:', error);
      alert(`검색 중 오류가 발생했습니다.`);
    } finally {
      setIsSearching(false);
    }
  };

  const navigateToSearchResult = (index: number) => {
    if (searchResults[index]) {
      setCurrentSearchIndex(index);
      setCurrentPage(searchResults[index].page_number);
    }
  };

  if (!document) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 bg-gray-50">
        <div className="text-center">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-lg font-medium mb-2">문서가 선택되지 않았습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="border-b bg-gray-50 p-4">
        <h3 className="font-semibold text-lg mb-3 truncate">{document.filename}</h3>
        <div className="flex items-center space-x-2">
          <Input
            type="text"
            placeholder="PDF 내 텍스트 검색..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchText, document.id)}
            disabled={isSearching}
          />
          <Button onClick={() => handleSearch(searchText, document.id)} disabled={!searchText.trim() || isSearching}>
            {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </Button>
        </div>
        {searchResults.length > 0 && (
          <div className="mt-3 flex items-center justify-between bg-yellow-50 p-3 rounded-md">
            <span className="text-sm font-medium text-yellow-800">결과: {currentSearchIndex + 1} / {searchResults.length}</span>
            <div className="flex items-center">
              <Button onClick={() => navigateToSearchResult(currentSearchIndex - 1)} disabled={currentSearchIndex === 0} size="sm" variant="ghost">
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button onClick={() => navigateToSearchResult(currentSearchIndex + 1)} disabled={currentSearchIndex >= searchResults.length - 1} size="sm" variant="ghost">
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 bg-gray-100 overflow-auto p-4">
        <div ref={pageContainerRef} style={{ position: 'relative', width: 'fit-content', margin: 'auto' }}>
          <Document
            key={document.url} // URL이 바뀔 때마다 컴포넌트를 새로 마운트
            file={document.url}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center justify-center p-10">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-600">PDF를 불러오는 중...</span>
              </div>
            }
            error={
              <div className="text-center text-red-500 p-10">
                <p>PDF 로드 실패</p>
                <p className="text-sm">{pdfError}</p>
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              scale={zoom / 100}
              renderAnnotationLayer={false} // 하이라이트와 충돌 방지
              renderTextLayer={true}
            />
          </Document>
          {searchResults
            .filter(result => result.page_number === currentPage)
            .map((result, index) => {
              const scale = zoom / 100;
              const viewport = pageContainerRef.current?.querySelector('.react-pdf__Page__canvas')?.getBoundingClientRect();
              const page_width = viewport?.width || 0;
              const page_height = viewport?.height || 0;

              const highlightStyle: React.CSSProperties = {
                position: 'absolute',
                left: `${result.bbox.x0 * scale}px`,
                top: `${result.bbox.y0 * scale}px`,
                width: `${(result.bbox.x1 - result.bbox.x0) * scale}px`,
                height: `${(result.bbox.y1 - result.bbox.y0) * scale}px`,
                backgroundColor: 'rgba(255, 255, 0, 0.4)',
                pointerEvents: 'none',
              };
              return <div key={index} style={highlightStyle} />;
            })}
        </div>
      </div>

      <div className="border-t bg-gray-50 p-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage <= 1}><ChevronLeft /></Button>
          <span className="text-sm">{currentPage} / {totalPages}</span>
          <Button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage >= totalPages}><ChevronRight /></Button>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={() => setZoom(z => Math.max(50, z - 25))}><ZoomOut /></Button>
          <span className="text-sm">{zoom}%</span>
          <Button onClick={() => setZoom(z => Math.min(200, z + 25))}><ZoomIn /></Button>
        </div>
      </div>
    </div>
  );
};

export default EnhancedPDFViewer;
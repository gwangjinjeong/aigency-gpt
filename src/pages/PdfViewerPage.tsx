import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Use a more stable CDN for the worker and explicitly set the version
pdfjs.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.mjs`;

const PDFViewerPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [highlightText, setHighlightText] = useState<string>('');
  const [textToHighlight, setTextToHighlight] = useState<string>('');

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { files } = event.target;
    if (files && files[0]) {
      console.log('File selected:', files[0]); // For debugging
      setFile(files[0]);
      setPageNumber(1);
    }
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('PDF loaded successfully');
    setNumPages(numPages);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('Failed to load PDF file:', error.message);
    // Also log the worker source to ensure it's set correctly
    console.error('PDF.js worker source:', pdfjs.GlobalWorkerOptions.workerSrc);
  };

  const goToPreviousPage = () => {
    setPageNumber((prevPageNumber) => Math.max(prevPageNumber - 1, 1));
  };

  const goToNextPage = () => {
    setPageNumber((prevPageNumber) => Math.min(prevPageNumber + 1, numPages || 1));
  };

  const handleHighlight = () => {
    setHighlightText(textToHighlight);
  };

  const customTextRenderer = (textItem: any) => {
    if (!highlightText || !textItem.str) {
      return textItem.str;
    }
    const regex = new RegExp(`(${highlightText})`, 'gi');
    const parts = textItem.str.split(regex);
    return parts.map((part:any, index:any) =>
      regex.test(part) ? <mark key={index}>{part}</mark> : part
    );
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">PDF Viewer</h1>
      <div className="mb-4">
        <input type="file" onChange={onFileChange} accept="application/pdf" />
      </div>
      <div className="mb-4 flex items-center">
        <input
          type="text"
          value={textToHighlight}
          onChange={(e) => setTextToHighlight(e.target.value)}
          placeholder="Enter text to highlight"
          className="border p-2 mr-2"
        />
        <button onClick={handleHighlight} className="bg-blue-500 text-white p-2 rounded">
          Highlight
        </button>
      </div>
      {file && (
        <div>
          <div className="flex justify-center items-center mb-4">
            <button onClick={goToPreviousPage} disabled={pageNumber <= 1} className="bg-gray-300 p-2 rounded mr-2">
              Previous
            </button>
            <span>
              Page {pageNumber} of {numPages}
            </span>
            <button onClick={goToNextPage} disabled={pageNumber >= (numPages || 0)} className="bg-gray-300 p-2 rounded ml-2">
              Next
            </button>
          </div>
          <div className="flex justify-center border">
            <Document
              file={file}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              onSourceError={onDocumentLoadError} // Also handle source errors
            >
              <Page
                pageNumber={pageNumber}
                customTextRenderer={customTextRenderer}
              />
            </Document>
          </div>
        </div>
      )}
    </div>
  );
};

export default PDFViewerPage;
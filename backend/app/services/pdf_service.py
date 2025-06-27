# backend/app/services/pdf_service.py
import fitz  # PyMuPDF
import os
import tempfile
import requests
import re
import json
from typing import List, Dict, Optional, Tuple, NamedTuple
from datetime import datetime
import logging
from pathlib import Path
import hashlib

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextLocation(NamedTuple):
    """텍스트 위치 정보"""
    page_number: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str
    context: str  # 앞뒤 문맥


class ChunkLocation(NamedTuple):
    """청크 위치 정보"""
    chunk_text: str
    page_locations: List[TextLocation]
    start_page: int
    end_page: int
    chunk_hash: str


class PDFProcessor:
    """PDF 파일 처리를 위한 클래스 (RAG/RAGAS 대응)"""

    def __init__(self):
        self.supported_formats = ['.pdf']
        self.location_cache = {}  # 텍스트 위치 캐시

    def validate_pdf(self, file_path: str) -> bool:
        """PDF 파일의 유효성을 검증"""
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()

            if page_count == 0:
                logger.error(f"PDF 파일이 비어있습니다: {file_path}")
                return False

            logger.info(f"PDF 검증 성공: {page_count}페이지")
            return True

        except Exception as e:
            logger.error(f"PDF 검증 실패: {e}")
            return False

    def extract_text_with_locations(self, file_path: str) -> Dict:
        """PDF에서 텍스트를 위치 정보와 함께 추출"""
        try:
            doc = fitz.open(file_path)
            text_content = []
            page_locations = {}  # page_num -> [TextLocation]

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # 텍스트 블록별로 추출 (위치 정보 포함)
                blocks = page.get_text("dict")["blocks"]
                page_text_locations = []
                page_full_text = ""

                for block in blocks:
                    if "lines" in block:  # 텍스트 블록인 경우
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                if text:
                                    bbox = span["bbox"]  # (x0, y0, x1, y1)

                                    # 텍스트 위치 정보 저장
                                    text_location = TextLocation(
                                        page_number=page_num + 1,
                                        bbox=bbox,
                                        text=text,
                                        context=""  # 나중에 설정
                                    )
                                    page_text_locations.append(text_location)
                                    page_full_text += text + " "

                # 페이지별 위치 정보 저장
                page_locations[page_num + 1] = page_text_locations

                if page_full_text.strip():
                    text_content.append({
                        "page_number": page_num + 1,
                        "text": page_full_text.strip(),
                        "char_count": len(page_full_text),
                        "text_locations": page_text_locations
                    })

            doc.close()

            total_text = " ".join([page["text"] for page in text_content])

            return {
                "status": "success",
                "total_pages": len(doc),
                "text_pages": len(text_content),
                "total_characters": len(total_text),
                "full_text": total_text,
                "page_contents": text_content,
                "page_locations": page_locations,
                "extracted_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"위치 정보 텍스트 추출 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "extracted_at": datetime.now().isoformat()
            }

    def find_text_in_pdf(self, file_path: str, search_text: str, context_chars: int = 100) -> List[TextLocation]:
        """PDF에서 특정 텍스트의 위치를 찾기"""
        try:
            doc = fitz.open(file_path)
            locations = []

            search_text_clean = re.sub(r'\s+', ' ', search_text.strip().lower())

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                page_text_clean = re.sub(r'\s+', ' ', page_text.lower())

                # 텍스트 검색
                if search_text_clean in page_text_clean:
                    # 정확한 위치 찾기
                    text_instances = page.search_for(search_text)

                    for rect in text_instances:
                        # 앞뒤 문맥 추출
                        start_idx = max(0, page_text_clean.find(search_text_clean) - context_chars)
                        end_idx = min(len(page_text),
                                      page_text_clean.find(search_text_clean) + len(search_text_clean) + context_chars)
                        context = page_text[start_idx:end_idx]

                        location = TextLocation(
                            page_number=page_num + 1,
                            bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                            text=search_text,
                            context=context
                        )
                        locations.append(location)

            doc.close()
            return locations

        except Exception as e:
            logger.error(f"텍스트 위치 검색 실패: {e}")
            return []

    def split_text_with_locations(
            self,
            extraction_result: Dict,
            chunk_size: int = 1000,
            chunk_overlap: int = 200
    ) -> List[ChunkLocation]:
        """텍스트를 청크로 분할하면서 위치 정보 유지"""
        if extraction_result["status"] != "success":
            return []

        full_text = extraction_result["full_text"]
        page_contents = extraction_result["page_contents"]

        chunks_with_locations = []
        start = 0

        while start < len(full_text):
            # 청크 끝 위치 계산
            end = start + chunk_size

            # 마지막 청크가 아닌 경우, 단어 경계에서 자르기
            if end < len(full_text):
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if full_text[i] in ' \n\t.!?;':
                        end = i + 1
                        break

            chunk_text = full_text[start:end].strip()
            if not chunk_text:
                break

            # 청크가 어느 페이지들에 걸쳐 있는지 찾기
            chunk_pages = self._find_chunk_pages(chunk_text, page_contents)

            # 청크 해시 생성 (추후 검색용)
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()

            chunk_location = ChunkLocation(
                chunk_text=chunk_text,
                page_locations=[],  # 필요시 세부 위치 추가
                start_page=min(chunk_pages) if chunk_pages else 1,
                end_page=max(chunk_pages) if chunk_pages else 1,
                chunk_hash=chunk_hash
            )

            chunks_with_locations.append(chunk_location)

            # 다음 청크 시작 위치
            start = max(start + chunk_size - chunk_overlap, end)

            if start >= len(full_text):
                break

        return chunks_with_locations

    def _find_chunk_pages(self, chunk_text: str, page_contents: List[Dict]) -> List[int]:
        """청크 텍스트가 어느 페이지들에 포함되어 있는지 찾기"""
        chunk_words = set(chunk_text.lower().split())
        chunk_pages = []

        for page in page_contents:
            page_words = set(page["text"].lower().split())

            # 청크 단어의 상당 부분이 페이지에 있는지 확인
            overlap = len(chunk_words & page_words)
            if overlap > len(chunk_words) * 0.3:  # 30% 이상 겹치면 해당 페이지로 간주
                chunk_pages.append(page["page_number"])

        return chunk_pages

    def create_highlight_annotations(
            self,
            file_path: str,
            text_locations: List[TextLocation],
            output_path: str = None
    ) -> str:
        """PDF에 하이라이트 주석 추가"""
        try:
            doc = fitz.open(file_path)

            for location in text_locations:
                page = doc.load_page(location.page_number - 1)

                # 하이라이트 주석 추가
                rect = fitz.Rect(location.bbox)
                highlight = page.add_highlight_annot(rect)
                highlight.set_colors(stroke=[1, 1, 0])  # 노란색
                highlight.update()

            # 파일 저장
            if not output_path:
                base, ext = os.path.splitext(file_path)
                output_path = f"{base}_highlighted{ext}"

            doc.save(output_path)
            doc.close()

            logger.info(f"하이라이트된 PDF 저장: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"하이라이트 추가 실패: {e}")
            return file_path

    def extract_and_chunk_with_locations(
            self,
            file_path: str,
            chunk_size: int = 1000,
            chunk_overlap: int = 200
    ) -> Dict:
        """PDF에서 텍스트를 추출하고 위치 정보와 함께 청크로 분할"""
        try:
            # 1. 위치 정보와 함께 텍스트 추출
            extract_result = self.extract_text_with_locations(file_path)

            if extract_result["status"] != "success":
                return extract_result

            # 2. 위치 정보를 유지하면서 청크 분할
            chunks_with_locations = self.split_text_with_locations(
                extract_result, chunk_size, chunk_overlap
            )

            # 3. 메타데이터 추출
            metadata_result = self.extract_metadata(file_path)

            # 4. 청크 정보를 딕셔너리 형태로 변환
            chunks_data = []
            for i, chunk_loc in enumerate(chunks_with_locations):
                chunks_data.append({
                    "chunk_index": i,
                    "text": chunk_loc.chunk_text,
                    "start_page": chunk_loc.start_page,
                    "end_page": chunk_loc.end_page,
                    "chunk_hash": chunk_loc.chunk_hash,
                    "char_count": len(chunk_loc.chunk_text)
                })

            return {
                "status": "success",
                "text_extraction": extract_result,
                "chunks": [chunk.chunk_text for chunk in chunks_with_locations],
                "chunks_with_locations": chunks_data,
                "chunk_count": len(chunks_with_locations),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "metadata": metadata_result.get("pdf_metadata", {}),
                "processed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"위치 정보 PDF 처리 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }

    def extract_metadata(self, file_path: str) -> Dict:
        """PDF 메타데이터 추출"""
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata

            file_stats = os.stat(file_path)

            result = {
                "status": "success",
                "file_info": {
                    "filename": os.path.basename(file_path),
                    "file_size": file_stats.st_size,
                    "created_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                },
                "pdf_metadata": {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "subject": metadata.get("subject", ""),
                    "creator": metadata.get("creator", ""),
                    "producer": metadata.get("producer", ""),
                    "creation_date": metadata.get("creationDate", ""),
                    "modification_date": metadata.get("modDate", "")
                },
                "document_info": {
                    "page_count": len(doc),
                    "is_encrypted": doc.needs_pass,
                    "is_pdf": doc.is_pdf,
                    "version": getattr(doc, 'pdf_version', 'Unknown')
                },
                "extracted_at": datetime.now().isoformat()
            }

            doc.close()
            return result

        except Exception as e:
            logger.error(f"메타데이터 추출 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "extracted_at": datetime.now().isoformat()
            }

    def download_and_process_pdf(
            self,
            url: str,
            chunk_size: int = 1000,
            chunk_overlap: int = 200
    ) -> Dict:
        """URL에서 PDF를 다운로드하고 위치 정보와 함께 처리"""
        temp_file = None
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tf:
                temp_file = tf.name

            # PDF 다운로드
            logger.info(f"PDF 다운로드 시작: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(temp_file, 'wb') as f:
                f.write(response.content)

            logger.info(f"PDF 다운로드 완료: {len(response.content)} bytes")

            # PDF 처리 (위치 정보 포함)
            result = self.extract_and_chunk_with_locations(temp_file, chunk_size, chunk_overlap)
            result["download_info"] = {
                "url": url,
                "file_size": len(response.content),
                "downloaded_at": datetime.now().isoformat(),
                "temp_file": temp_file  # 하이라이트 기능을 위해 임시 파일 경로 유지
            }

            return result

        except requests.RequestException as e:
            logger.error(f"PDF 다운로드 실패: {e}")
            return {
                "status": "failed",
                "error": f"다운로드 실패: {str(e)}",
                "url": url
            }
        except Exception as e:
            logger.error(f"PDF 처리 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "url": url
            }
        # 임시 파일은 하이라이트 기능을 위해 유지 (별도 정리 필요)

    def create_rag_response_with_locations(
            self,
            file_path: str,
            matched_chunks: List[Dict],
            user_question: str
    ) -> Dict:
        """RAG 응답에 페이지 위치 정보 추가"""
        try:
            response_data = {
                "answer": "",
                "sources": [],
                "page_references": [],
                "highlight_info": []
            }

            for chunk_data in matched_chunks:
                chunk_text = chunk_data.get("text", "")
                chunk_metadata = chunk_data.get("metadata", {})

                # 청크가 위치한 페이지 찾기
                text_locations = self.find_text_in_pdf(file_path, chunk_text[:200])  # 첫 200자로 검색

                if text_locations:
                    primary_location = text_locations[0]

                    source_info = {
                        "chunk_text": chunk_text[:300] + "...",
                        "page_number": primary_location.page_number,
                        "bbox": primary_location.bbox,
                        "context": primary_location.context,
                        "relevance_score": chunk_data.get("score", 0.0)
                    }

                    response_data["sources"].append(source_info)
                    response_data["page_references"].append(primary_location.page_number)
                    response_data["highlight_info"].append({
                        "page": primary_location.page_number,
                        "bbox": primary_location.bbox,
                        "text": chunk_text[:100]
                    })

            # 중복 페이지 제거
            response_data["page_references"] = list(set(response_data["page_references"]))

            return {
                "status": "success",
                "rag_response": response_data,
                "processed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"RAG 응답 위치 정보 생성 실패: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }


# 전역 인스턴스
pdf_processor = PDFProcessor()


# 편의 함수들 (RAG/RAGAS 대응)
def process_pdf_file_with_locations(file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict:
    """PDF 파일 처리 (위치 정보 포함)"""
    return pdf_processor.extract_and_chunk_with_locations(file_path, chunk_size, chunk_overlap)


def process_pdf_url_with_locations(url: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict:
    """PDF 파일 처리 (URL, 위치 정보 포함)"""
    return pdf_processor.download_and_process_pdf(url, chunk_size, chunk_overlap)


def find_text_locations(file_path: str, search_text: str) -> List[TextLocation]:
    """PDF에서 텍스트 위치 찾기"""
    return pdf_processor.find_text_in_pdf(file_path, search_text)


def create_highlighted_pdf(file_path: str, text_locations: List[TextLocation], output_path: str = None) -> str:
    """하이라이트된 PDF 생성"""
    return pdf_processor.create_highlight_annotations(file_path, text_locations, output_path)


def create_rag_response_with_pages(file_path: str, matched_chunks: List[Dict], question: str) -> Dict:
    """RAG 응답에 페이지 정보 추가"""
    return pdf_processor.create_rag_response_with_locations(file_path, matched_chunks, question)


# 기존 함수들도 유지 (하위 호환성)
def process_pdf_file(file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict:
    """PDF 파일 처리 (기존 버전)"""
    result = pdf_processor.extract_and_chunk_with_locations(file_path, chunk_size, chunk_overlap)
    # 기존 형식으로 변환
    if result["status"] == "success":
        return {
            "status": "success",
            "chunks": result["chunks"],
            "chunk_count": result["chunk_count"],
            "processed_at": result["processed_at"]
        }
    return result


def validate_pdf_file(file_path: str) -> bool:
    """PDF 파일 유효성 검증"""
    return pdf_processor.validate_pdf(file_path)


def extract_pdf_metadata(file_path: str) -> Dict:
    """PDF 메타데이터 추출"""
    return pdf_processor.extract_metadata(file_path)


# 테스트 함수
if __name__ == "__main__":
    # 테스트용 PDF 파일 생성 및 처리
    test_pdf_path = "test_document.pdf"

    # 간단한 PDF 생성 (테스트용)
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    text = "이것은 테스트 PDF 문서입니다. PDF 처리 기능을 테스트하기 위한 샘플 텍스트입니다. RAG와 RAGAS를 위한 위치 정보도 포함됩니다."
    page.insert_text((100, 100), text)
    doc.save(test_pdf_path)
    doc.close()

    try:
        # 위치 정보 포함 PDF 처리 테스트
        result = process_pdf_file_with_locations(test_pdf_path, chunk_size=100, chunk_overlap=20)
        print("위치 정보 포함 PDF 처리 결과:")
        print(f"상태: {result['status']}")
        if result['status'] == 'success':
            print(f"청크 수: {result['chunk_count']}")
            print(f"첫 번째 청크 위치: 페이지 {result['chunks_with_locations'][0]['start_page']}")

            # 텍스트 위치 찾기 테스트
            locations = find_text_locations(test_pdf_path, "테스트")
            print(f"'테스트' 텍스트 위치: {len(locations)}개 발견")

            if locations:
                # 하이라이트 PDF 생성 테스트
                highlighted_path = create_highlighted_pdf(test_pdf_path, locations)
                print(f"하이라이트된 PDF: {highlighted_path}")
        else:
            print(f"오류: {result['error']}")

    except Exception as e:
        print(f"테스트 중 오류: {e}")
    finally:
        # 테스트 파일 정리
        for test_file in [test_pdf_path, "test_document_highlighted.pdf"]:
            if os.path.exists(test_file):
                os.remove(test_file)
                print(f"테스트 파일 삭제: {test_file}")
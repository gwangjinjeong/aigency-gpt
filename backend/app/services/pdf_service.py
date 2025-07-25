# backend/app/services/pdf_service.py
import fitz  # PyMuPDF
import os
import tempfile
import requests
import re
import json
import time
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

    def normalize_text(self, text: str) -> str:
        """텍스트 정규화 (한글 검색 개선)"""
        if not text:
            return ""

        # 연속된 공백을 하나로 합치기
        text = re.sub(r'\s+', ' ', text)

        # 앞뒤 공백 제거
        text = text.strip()

        return text

    def validate_pdf(self, file_path: str) -> bool:
        """PDF 파일의 유효성을 검증"""
        doc = None
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)

            if page_count == 0:
                logger.error(f"PDF 파일이 비어있습니다: {file_path}")
                return False

            logger.info(f"PDF 검증 성공: {page_count}페이지")
            return True

        except Exception as e:
            logger.error(f"PDF 검증 실패: {e}")
            return False
        finally:
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

    def extract_text_with_locations(self, file_path: str) -> Dict:
        """PDF에서 텍스트를 위치 정보와 함께 추출"""
        doc = None
        try:
            doc = fitz.open(file_path)
            text_content = []
            page_locations = {}  # page_num -> [TextLocation]
            total_pages = len(doc)  # 문서가 열린 상태에서 페이지 수 저장

            for page_num in range(total_pages):
                page = doc.load_page(page_num)

                # 텍스트 블록별로 추출 (위치 정보 포함)
                blocks = page.get_text("dict")["blocks"]
                page_text_locations = []
                page_full_text = ""

                for block in blocks:
                    if "lines" in block:  # 텍스트 블록인 경우
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = self.normalize_text(span["text"])  # 🔥 정규화 추가
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
                    page_full_text_normalized = self.normalize_text(page_full_text)  # 🔥 정규화 추가
                    text_content.append({
                        "page_number": page_num + 1,
                        "text": page_full_text_normalized,  # 🔥 정규화된 텍스트 사용
                        "char_count": len(page_full_text_normalized),
                        "text_locations": page_text_locations
                    })

            # 전체 텍스트 결합
            total_text = " ".join([page["text"] for page in text_content])

            # 결과 준비 (문서가 열린 상태에서)
            result = {
                "status": "success",
                "total_pages": total_pages,
                "text_pages": len(text_content),
                "total_characters": len(total_text),
                "full_text": total_text,
                "page_contents": text_content,
                "page_locations": page_locations,
                "extracted_at": datetime.now().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"위치 정보 텍스트 추출 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "extracted_at": datetime.now().isoformat()
            }
        finally:
            # 문서가 열린 상태라면 반드시 닫기
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

    def find_text_in_pdf(self, file_path: str, search_text: str, context_chars: int = 100) -> List[TextLocation]:
        """PDF에서 특정 텍스트의 위치를 찾기 (개선된 한글 검색 및 부분 일치)"""
        doc = None
        try:
            doc = fitz.open(file_path)
            locations = []

            # 검색어의 앞 30자만 사용 (안정성 확보)
            search_snippet = search_text[:30]
            search_snippet_normalized = self.normalize_text(search_snippet)
            
            logger.info(f"검색 시작: 파일 '{file_path}', 원본 검색어 '{search_text}', 검색 스니펫 '{search_snippet_normalized}'")

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # PyMuPDF의 search_for로 위치 찾기
                text_instances = page.search_for(search_snippet_normalized)

                if text_instances:
                    logger.info(f"페이지 {page_num + 1}에서 '{search_snippet_normalized}' 검색 결과: {len(text_instances)}개 발견")
                    page_full_text = page.get_text("text")
                    page_text_normalized = self.normalize_text(page_full_text)

                    for rect in text_instances:
                        # 문맥 추출
                        # find_text_in_pdf 함수 내에서 context를 추출하는 부분 수정
                        try:
                            # PyMuPDF Rect 객체에서 직접 텍스트를 추출하여 정확도 향상
                            matched_text = page.get_text("text", clip=rect)
                            match_start_idx = page_text_normalized.lower().find(matched_text.lower())
                            
                            context = ""
                            if match_start_idx != -1:
                                start_idx = max(0, match_start_idx - context_chars)
                                end_idx = min(len(page_full_text), match_start_idx + len(matched_text) + context_chars)
                                context = page_full_text[start_idx:end_idx]
                            else:
                                # 백업: Rect 주변 텍스트 추출
                                context = page.get_text("text", clip=rect.irect.expand(10))

                        except Exception:
                            context = "(문맥 추출 오류)"

                        location = TextLocation(
                            page_number=page_num + 1,
                            bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                            text=search_text, # 원본 검색어를 반환
                            context=context
                        )
                        locations.append(location)

            return locations

        except Exception as e:
            logger.error(f"텍스트 위치 검색 실패: {e}")
            return []
        finally:
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

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
                # 🔥 한글 문장 부호 포함
                sentence_endings = ['.', '!', '?', '。', '！', '？', '\n']
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if full_text[i] in sentence_endings or full_text[i].isspace():
                        end = i + 1
                        break

            chunk_text = full_text[start:end].strip()
            if not chunk_text:
                break

            # 청크가 어느 페이지들에 걸쳐 있는지 찾기
            chunk_pages = self._find_chunk_pages(chunk_text, page_contents)

            # 청크 해시 생성 (추후 검색용)
            chunk_hash = hashlib.md5(chunk_text.encode('utf-8')).hexdigest()  # 🔥 utf-8 인코딩 명시

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
        """청크 텍스트가 어느 페이지들에 포함되어 있는지 찾기 (한글 개선)"""
        chunk_text_normalized = self.normalize_text(chunk_text.lower())
        chunk_words = set(chunk_text_normalized.split())
        chunk_pages = []

        for page in page_contents:
            page_text_normalized = self.normalize_text(page["text"].lower())
            page_words = set(page_text_normalized.split())

            # 청크 단어의 상당 부분이 페이지에 있는지 확인
            if chunk_words and page_words:
                overlap = len(chunk_words & page_words)
                overlap_ratio = overlap / len(chunk_words)

                if overlap_ratio > 0.3:  # 30% 이상 겹치면 해당 페이지로 간주
                    chunk_pages.append(page["page_number"])

        return chunk_pages

    def create_highlight_annotations(
            self,
            file_path: str,
            text_locations: List[TextLocation],
            output_path: str = None
    ) -> str:
        """PDF에 하이라이트 주석 추가"""
        doc = None
        try:
            doc = fitz.open(file_path)

            for location in text_locations:
                if location.page_number <= len(doc):  # 🔥 페이지 범위 체크 추가
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
            logger.info(f"하이라이트된 PDF 저장: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"하이라이트 추가 실패: {e}")
            return file_path
        finally:
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

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
        doc = None
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata

            file_stats = os.stat(file_path)

            # 문서가 열린 상태에서 정보 수집
            page_count = len(doc)
            is_encrypted = doc.needs_pass
            is_pdf = doc.is_pdf
            version = getattr(doc, 'pdf_version', 'Unknown')

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
                    "page_count": page_count,
                    "is_encrypted": is_encrypted,
                    "is_pdf": is_pdf,
                    "version": version
                },
                "extracted_at": datetime.now().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"메타데이터 추출 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "extracted_at": datetime.now().isoformat()
            }
        finally:
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

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

            # 파일 시스템이 완전히 반영될 시간을 주기 위해 지연 추가
            time.sleep(0.1)

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
        """RAG 응답에 페이지 위치 정보 추가 (개선된 버전)"""
        try:
            # 🔥 파일 존재 여부 확인
            if not os.path.exists(file_path):
                logger.error(f"PDF 파일을 찾을 수 없습니다: {file_path}")
                return {
                    "status": "failed",
                    "error": f"PDF 파일을 찾을 수 없습니다: {file_path}"
                }

            response_data = {
                "answer": "",
                "sources": [],
                "page_references": [],
                "highlight_info": []
            }

            for chunk_data in matched_chunks:
                chunk_text = chunk_data.get("text", "")
                chunk_metadata = chunk_data.get("metadata", {})

                # 🔥 개선된 검색 로직 - 단계별 검색
                text_locations = []

                # 1차: 청크의 첫 문장으로 검색 (더 정확함)
                sentences = chunk_text.split('.')
                if sentences:
                    first_sentence = sentences[0].strip()
                    if len(first_sentence) > 10:  # 너무 짧은 문장 제외
                        text_locations = self.find_text_in_pdf(file_path, first_sentence)
                        logger.debug(f"1차 검색 (첫 문장): '{first_sentence}' -> {len(text_locations)}개 발견")

                # 2차: 첫 문장으로 안 되면 키워드 추출해서 검색
                if not text_locations:
                    words = chunk_text.split()
                    if len(words) >= 3:
                        keyword_phrase = ' '.join(words[:3])  # 첫 3단어
                        text_locations = self.find_text_in_pdf(file_path, keyword_phrase)
                        logger.debug(f"2차 검색 (키워드): '{keyword_phrase}' -> {len(text_locations)}개 발견")

                # 3차: 그래도 안 되면 청크의 앞부분으로 검색
                if not text_locations:
                    search_snippet = chunk_text[:50].strip()  # 🔥 50자로 축소
                    if search_snippet:
                        text_locations = self.find_text_in_pdf(file_path, search_snippet)
                        logger.debug(f"3차 검색 (앞부분): '{search_snippet}' -> {len(text_locations)}개 발견")

                if text_locations:
                    primary_location = text_locations[0]

                    source_info = {
                        "chunk_text": chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text,
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
                        "text": text_locations[0].text[:100] if text_locations else chunk_text[:50]
                    })
                else:
                    # 🔥 위치를 찾지 못한 경우에도 정보 추가 (페이지 없이)
                    logger.warning(f"청크 위치를 찾지 못했습니다: {chunk_text[:50]}...")
                    source_info = {
                        "chunk_text": chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text,
                        "page_number": chunk_metadata.get("page", 1),  # 메타데이터에서 페이지 정보 사용
                        "bbox": None,
                        "context": "",
                        "relevance_score": chunk_data.get("score", 0.0)
                    }
                    response_data["sources"].append(source_info)

            # 🔥 중복 페이지 제거 (None 제외)
            page_refs = [ref for ref in response_data["page_references"] if ref is not None]
            response_data["page_references"] = list(set(page_refs))

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
    """PDF에서 텍스트 위치 찾기 (개선된 한글 검색)"""
    return pdf_processor.find_text_in_pdf(file_path, search_text)


def create_highlighted_pdf(file_path: str, text_locations: List[TextLocation], output_path: str = None) -> str:
    """하이라이트된 PDF 생성 (전체 문서 유지)"""
    doc = None
    try:
        # 원본 문서를 열고, 수정본을 위한 새 문서를 만들지 않습니다.
        doc = fitz.open(file_path)

        for location in text_locations:
            if location.page_number <= len(doc):
                page = doc.load_page(location.page_number - 1)
                
                # PyMuPDF의 search_for를 사용해 텍스트의 정확한 위치를 다시 한번 찾습니다.
                # 이는 find_text_locations에서 반환된 bbox가 때때로 부정확할 수 있기 때문입니다.
                rects = page.search_for(location.text, quads=False)
                
                for rect in rects:
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=[1, 1, 0]) # Yellow
                    highlight.update()

        # 변경사항을 포함하여 전체 문서를 새 파일에 저장합니다.
        if not output_path:
            # 임시 파일로 저장하여 반환
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                output_path = temp_file.name
        
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        logger.info(f"하이라이트된 PDF 저장 완료: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"하이라이트 추가 실패: {e}")
        # 오류 발생 시 원본 파일 경로 반환
        return file_path
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception as e:
                logger.error(f"PDF 문서 닫기 실패: {e}")


def create_rag_response_with_pages(file_path: str, matched_chunks: List[Dict], question: str) -> Dict:
    """RAG 응답에 페이지 정보 추가 (개선된 버전)"""
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

if __name__ == "__main__":
    # 테스트용 PDF 파일 생성 및 처리
    test_pdf_path = "test_document.pdf"

    try:
        # PDF 생성 - 수정된 방식
        doc = fitz.open()  # with 문 사용하지 않음
        page = doc.new_page()
        text = "이것은 테스트 PDF 문서입니다. PDF 처리 기능을 테스트하기 위한 샘플 텍스트입니다. RAG와 RAGAS를 위한 위치 정보도 포함됩니다."
        page.insert_text((100, 100), text)
        doc.save(test_pdf_path)
        doc.close()  # 명시적으로 닫기

        # 파일 시스템이 완전히 반영될 시간을 주기 위해 지연 추가
        time.sleep(0.2)  # 지연 시간 증가

        # 파일 존재 확인
        if not os.path.exists(test_pdf_path):
            print(f"오류: 테스트 PDF 파일이 생성되지 않았습니다: {test_pdf_path}")
            exit(1)

        # 위치 정보 포함 PDF 처리 테스트
        result = process_pdf_file_with_locations(test_pdf_path, chunk_size=100, chunk_overlap=20)
        print("--- 위치 정보 포함 PDF 처리 결과 ---")
        print(f"상태: {result['status']}")
        if result['status'] == 'success':
            print(f"총 페이지 수: {result['text_extraction']['total_pages']}")
            print(f"총 문자 수: {result['text_extraction']['total_characters']}")
            print(f"청크 수: {result['chunk_count']}")
            if result['chunks_with_locations']:
                print(f"첫 번째 청크 텍스트: {result['chunks_with_locations'][0]['text'][:50]}...")
                print(
                    f"첫 번째 청크 위치: 페이지 {result['chunks_with_locations'][0]['start_page']} - {result['chunks_with_locations'][0]['end_page']}")

            # 텍스트 위치 찾기 테스트
            search_term = "테스트"
            locations = find_text_locations(test_pdf_path, search_term)
            print(f"\n--- '{search_term}' 텍스트 위치 찾기 결과 ---")
            print(f"'{search_term}' 텍스트 {len(locations)}개 발견")

            if locations:
                for i, loc in enumerate(locations):
                    print(
                        f"  위치 {i + 1}: 페이지 {loc.page_number}, BBox: {loc.bbox}, 텍스트: '{loc.text}', 문맥: '{loc.context[:50]}...'")

                # 하이라이트 PDF 생성 테스트
                highlighted_path = create_highlighted_pdf(test_pdf_path, locations)
                print(f"\n--- 하이라이트된 PDF 생성 결과 ---")
                print(f"하이라이트된 PDF: {highlighted_path}")
                print(f"이 파일을 다운로드하여 하이라이트를 확인할 수 있습니다.")
            else:
                print(f"'{search_term}' 텍스트를 찾지 못했습니다.")

            # 메타데이터 추출 테스트
            metadata_result = extract_pdf_metadata(test_pdf_path)
            print(f"\n--- PDF 메타데이터 추출 결과 ---")
            if metadata_result['status'] == 'success':
                print(json.dumps(metadata_result['pdf_metadata'], indent=2, ensure_ascii=False))
            else:
                print(f"메타데이터 추출 오류: {metadata_result['error']}")

        else:
            print(f"PDF 처리 오류: {result['error']}")

    except Exception as e:
        print(f"테스트 중 예상치 못한 오류 발생: {e}")
        import traceback

        print(f"상세 오류 정보: {traceback.format_exc()}")
    finally:
        # 테스트 파일 정리
        for test_file in [test_pdf_path, "test_document_highlighted.pdf", "downloaded_highlighted.pdf"]:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                    print(f"테스트 파일 삭제: {test_file}")
                except:
                    print(f"테스트 파일 삭제 실패: {test_file}")
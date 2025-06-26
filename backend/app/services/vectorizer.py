#llm_doc_poc/vectorizer.py
import os
import fitz  # PyMuPDF
import openai
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv() # .env 파일 로드

# OpenAI API 키 설정
openai.api_key = os.environ.get("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

def get_text_chunks(filepath: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    PDF 파일에서 텍스트를 추출하고, 지정된 크기로 청크를 분할합니다.
    """
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()

    # 간단한 청크 분할 (더 정교한 방법론이 필요할 수 있습니다)
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunk = text[i:i + chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    텍스트 청크 리스트에 대한 임베딩을 생성합니다.
    """
    if not texts:
        return []
    response = openai.embeddings.create(
        model="text-embedding-ada-002", # OpenAI 임베딩 모델
        input=texts
    )
    return [data.embedding for data in response.data]

def process_pdf_for_vectorization(filepath: str) -> Dict:
    """
    PDF 파일을 받아 텍스트 청크를 생성하고 임베딩합니다.
    """
    print(f"PDF 파일 텍스트 추출 및 청크 분할 중: {filepath}")
    chunks = get_text_chunks(filepath)
    print(f"생성된 청크 수: {len(chunks)}")

    if not chunks:
        return {"status": "failed", "message": "텍스트 청크를 생성할 수 없습니다."}

    print("임베딩 생성 중...")
    embeddings = get_embeddings(chunks)
    print(f"생성된 임베딩 수: {len(embeddings)}")

    if len(chunks) != len(embeddings):
        raise ValueError("청크 수와 임베딩 수가 일치하지 않습니다.")

    # 각 청크와 해당 임베딩을 함께 반환
    return {
        "status": "success",
        "chunks": chunks,
        "embeddings": embeddings,
        "chunk_count": len(chunks)
    }

# 테스트용 코드
if __name__ == "__main__":
    # 테스트용 PDF 파일 생성 (실제 PDF 파일로 대체해야 합니다)
    test_pdf_path = "test_document.pdf"
    with open(test_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj\n4 0 obj<</Length 16>>stream\nBT /F1 24 Tf 100 700 Td (Hello World!) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000057 00000 n\n0000000107 00000 n\n0000000180 00000 n\ntrailer<</Size 5/Root 1 0 R>>startxref\n200\n%%EOF")
    print(f"테스트용 PDF 파일 '{test_pdf_path}' 생성됨.")

    try:
        result = process_pdf_for_vectorization(test_pdf_path)
        print("\nPDF 벡터화 처리 결과:")
        print(f"상태: {result['status']}")
        if result['status'] == 'success':
            print(f"처리된 청크 수: {result['chunk_count']}")
            print(f"첫 번째 청크: {result['chunks'][0][:100]}...")
            print(f"첫 번째 임베딩 차원: {len(result['embeddings'][0])}")
    except Exception as e:
        print(f"PDF 벡터화 처리 중 오류 발생: {e}")
    finally:
        os.remove(test_pdf_path)
        print(f"테스트용 PDF 파일 '{test_pdf_path}' 삭제됨.")
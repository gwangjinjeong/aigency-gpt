# chromadb_debug.py - ChromaDB 상태 확인 및 정리
import chromadb
from collections import Counter


def check_chromadb_status():
    """ChromaDB의 현재 상태를 확인합니다"""
    try:
        # ChromaDB 클라이언트 초기화
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_collection(name="pdf_document_embeddings")

        print("📊 ChromaDB 상태 분석")
        print("=" * 50)

        # 전체 벡터 수
        total_vectors = collection.count()
        print(f"총 벡터 수: {total_vectors}")

        if total_vectors > 0:
            # 모든 메타데이터 가져오기
            results = collection.get(include=['metadatas'])

            if results['metadatas']:
                # 문서 ID별 통계
                document_ids = [meta.get('document_id', 'Unknown') for meta in results['metadatas']]
                doc_counts = Counter(document_ids)

                print(f"\n📄 문서별 청크 수:")
                for doc_id, count in doc_counts.items():
                    filename = next((meta.get('filename', 'Unknown')
                                     for meta in results['metadatas']
                                     if meta.get('document_id') == doc_id), 'Unknown')
                    print(f"  - {doc_id[:8]}...{doc_id[-8:]} ({filename}): {count}개 청크")

                # 생성 날짜별 통계
                created_dates = [meta.get('created_at', 'Unknown')[:10] for meta in results['metadatas']]
                date_counts = Counter(created_dates)

                print(f"\n📅 생성 날짜별 통계:")
                for date, count in sorted(date_counts.items()):
                    print(f"  - {date}: {count}개 청크")

                # 파일명별 통계
                filenames = [meta.get('filename', 'Unknown') for meta in results['metadatas']]
                filename_counts = Counter(filenames)

                print(f"\n📁 파일명별 통계:")
                for filename, count in filename_counts.items():
                    print(f"  - {filename}: {count}개 청크")

        return doc_counts if total_vectors > 0 else {}

    except Exception as e:
        print(f"❌ ChromaDB 상태 확인 실패: {e}")
        return {}


def cleanup_orphaned_documents():
    """고아 문서 데이터 정리"""
    from app.services.supabase_client import supabase

    try:
        # 실제 존재하는 문서 목록 가져오기
        response = supabase.from_('documents').select('id').eq('status', 'completed').execute()
        valid_doc_ids = {doc['id'] for doc in response.data} if response.data else set()

        print(f"\n🗃️ Supabase에 실제 존재하는 문서: {len(valid_doc_ids)}개")
        for doc_id in valid_doc_ids:
            print(f"  - {doc_id}")

        # ChromaDB에서 고아 문서 찾기
        doc_counts = check_chromadb_status()
        chromadb_doc_ids = set(doc_counts.keys())

        orphaned_ids = chromadb_doc_ids - valid_doc_ids

        if orphaned_ids:
            print(f"\n🗑️ 정리 대상 고아 문서: {len(orphaned_ids)}개")
            for orphan_id in orphaned_ids:
                print(f"  - {orphan_id} ({doc_counts[orphan_id]}개 청크)")

            # 정리 여부 확인
            confirm = input("\n이 고아 문서들을 삭제하시겠습니까? (y/N): ").strip().lower()

            if confirm == 'y':
                chroma_client = chromadb.PersistentClient(path="./chroma_db")
                collection = chroma_client.get_collection(name="pdf_document_embeddings")

                deleted_count = 0
                for orphan_id in orphaned_ids:
                    try:
                        # 해당 문서의 모든 벡터 삭제
                        results = collection.get(where={"document_id": orphan_id})
                        if results["ids"]:
                            collection.delete(ids=results["ids"])
                            deleted_count += len(results["ids"])
                            print(f"  ✅ 삭제됨: {orphan_id} ({len(results['ids'])}개 청크)")
                    except Exception as e:
                        print(f"  ❌ 삭제 실패: {orphan_id} - {e}")

                print(f"\n✅ 총 {deleted_count}개 청크 삭제 완료")
            else:
                print("삭제 취소됨")
        else:
            print("\n✅ 고아 문서 없음 - ChromaDB가 정상 상태입니다")

    except Exception as e:
        print(f"❌ 고아 문서 정리 실패: {e}")


def main():
    print("🔍 ChromaDB 디버깅 도구")
    print("=" * 50)

    # 1. 상태 확인
    doc_counts = check_chromadb_status()

    # 2. 고아 문서 정리
    if doc_counts:
        cleanup_orphaned_documents()

    # 3. 정리 후 상태 재확인
    print(f"\n🔄 정리 후 상태:")
    check_chromadb_status()


if __name__ == "__main__":
    main()
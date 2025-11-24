"""
ChromaDB 클라이언트
"""
import chromadb
from chromadb.config import Settings
from django.conf import settings as django_settings
import os


class ChromaDBClient:
    """ChromaDB 싱글톤 클라이언트"""
    _instance = None
    _client = None
    _collection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaDBClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """ChromaDB 초기화"""
        db_path = django_settings.CHROMA_DB_PATH
        os.makedirs(db_path, exist_ok=True)

        self._client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=db_path
        ))

        # 컬렉션 생성 또는 가져오기
        collection_name = django_settings.CHROMA_COLLECTION_NAME
        try:
            self._collection = self._client.get_collection(collection_name)
        except:
            self._collection = self._client.create_collection(
                name=collection_name,
                metadata={"description": "Python documentation embeddings"}
            )

    @property
    def collection(self):
        """컬렉션 반환"""
        return self._collection

    def add_documents(self, documents, metadatas=None, ids=None):
        """문서 추가"""
        self._collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_texts, n_results=5):
        """쿼리 실행"""
        results = self._collection.query(
            query_texts=query_texts,
            n_results=n_results
        )
        return results

    def delete_collection(self):
        """컬렉션 삭제"""
        self._client.delete_collection(django_settings.CHROMA_COLLECTION_NAME)

    def persist(self):
        """데이터 영구 저장"""
        self._client.persist()


# 싱글톤 인스턴스 사용
def get_chroma_client():
    """ChromaDB 클라이언트 인스턴스 반환"""
    return ChromaDBClient()

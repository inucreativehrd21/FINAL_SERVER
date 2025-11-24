"""
임베딩 생성 유틸리티
"""
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """임베딩 생성기"""
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingGenerator, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """모델 초기화"""
        # 한국어 지원 임베딩 모델
        self._model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

    def encode(self, texts):
        """텍스트를 임베딩 벡터로 변환"""
        if isinstance(texts, str):
            texts = [texts]
        return self._model.encode(texts)


def get_embedding_generator():
    """임베딩 생성기 인스턴스 반환"""
    return EmbeddingGenerator()

"""
RAG (Retrieval-Augmented Generation) 시스템

Qdrant 벡터 DB와 multilingual-e5-large 임베딩 모델을 사용하여
챕터 내용을 벡터화하고 의미적으로 유사한 구절을 검색합니다.

주요 기능:
- 챕터 내용을 단락 단위로 분할하여 임베딩
- Qdrant 벡터 DB에 저장 (프로젝트별 네임스페이스 분리)
- 쿼리와 의미적으로 유사한 상위 5개 구절 검색
- Redis 임베딩 캐싱 (24시간 TTL)
- 챕터 수정 시 임베딩 업데이트
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis

from backend.app.config import settings

logger = logging.getLogger(__name__)

# ─── 상수 ─────────────────────────────────────────────────────────────────────

COLLECTION_NAME = "novel_passages"
EMBEDDING_DIM = 768
MIN_PARAGRAPH_CHARS = 50          # 단락 최소 길이
EMBEDDING_CACHE_TTL = 86400       # 24시간 (초)
EMBEDDING_CACHE_PREFIX = "rag:embedding"

# E5 모델 prefix 규칙
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "


# ─── 데이터 클래스 ─────────────────────────────────────────────────────────────

@dataclass
class RelevantPassage:
    """검색된 유사 구절"""
    chapter_id: str
    chapter_number: int
    paragraph_index: int
    text: str
    similarity_score: float
    character_mentions: List[str] = field(default_factory=list)


# ─── 임베딩 서비스 ─────────────────────────────────────────────────────────────

class EmbeddingService:
    """
    multilingual-e5-large 모델을 사용한 한국어 임베딩 서비스.

    지연 초기화(lazy initialization)를 사용하여 첫 호출 시 모델을 로드합니다.
    CPU 바운드 작업은 asyncio.to_thread를 통해 비동기로 실행합니다.
    """

    def __init__(self) -> None:
        self._model = None
        self._model_name = "intfloat/multilingual-e5-large"
        self._lock = asyncio.Lock()

    async def _get_model(self):
        """모델 싱글턴을 반환합니다 (지연 초기화)."""
        if self._model is not None:
            return self._model

        async with self._lock:
            # double-checked locking
            if self._model is not None:
                return self._model

            logger.info("임베딩 모델 로딩 중: %s", self._model_name)
            try:
                from sentence_transformers import SentenceTransformer
                model = await asyncio.to_thread(
                    SentenceTransformer, self._model_name
                )
                self._model = model
                logger.info("임베딩 모델 로딩 완료: %s", self._model_name)
            except ImportError:
                logger.error(
                    "sentence-transformers 패키지가 설치되지 않았습니다. "
                    "pip install sentence-transformers 를 실행하세요."
                )
                raise
            except Exception as exc:
                logger.error("임베딩 모델 로딩 실패: %s", exc)
                raise

        return self._model

    def _encode_sync(self, texts: List[str]) -> List[List[float]]:
        """동기 방식으로 텍스트를 임베딩합니다 (to_thread에서 호출)."""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 목록을 배치로 임베딩합니다.

        Args:
            texts: 임베딩할 텍스트 목록 (E5 prefix 포함)

        Returns:
            768차원 임베딩 벡터 목록
        """
        model = await self._get_model()
        return await asyncio.to_thread(self._encode_sync, texts)


# ─── RAG 시스템 ────────────────────────────────────────────────────────────────

class RAGSystem:
    """
    RAG (Retrieval-Augmented Generation) 시스템.

    Qdrant 벡터 DB와 multilingual-e5-large 임베딩 모델을 사용하여
    챕터 내용을 벡터화하고 의미적으로 유사한 구절을 검색합니다.

    사용 예시:
        rag = RAGSystem()
        await rag.embed_chapter("chapter-1", content, "project-1", 1)
        passages = await rag.retrieve_relevant_passages("주인공의 여정", "project-1")
        context = rag.build_rag_context(passages)
    """

    def __init__(self) -> None:
        self._qdrant_client = None
        self._embedding_service = EmbeddingService()
        self._redis: Optional[aioredis.Redis] = None
        self._collection_initialized = False
        self._qdrant_lock = asyncio.Lock()

    # ─── Qdrant 클라이언트 ────────────────────────────────────────────────────

    def _get_redis(self) -> aioredis.Redis:
        """Redis 클라이언트 싱글턴을 반환합니다."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def _get_qdrant_client(self):
        """Qdrant 클라이언트 싱글턴을 반환합니다 (지연 초기화)."""
        if self._qdrant_client is not None:
            return self._qdrant_client

        async with self._qdrant_lock:
            if self._qdrant_client is not None:
                return self._qdrant_client

            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http.exceptions import UnexpectedResponse

                client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY or None,
                    timeout=30,
                )
                self._qdrant_client = client
                logger.info("Qdrant 클라이언트 초기화 완료: %s", settings.QDRANT_URL)
            except ImportError:
                logger.error(
                    "qdrant-client 패키지가 설치되지 않았습니다. "
                    "pip install qdrant-client 를 실행하세요."
                )
                raise
            except Exception as exc:
                logger.warning("Qdrant 클라이언트 초기화 실패: %s", exc)
                raise

        return self._qdrant_client

    async def _ensure_collection(self) -> None:
        """
        Qdrant 컬렉션이 존재하지 않으면 생성합니다.

        컬렉션 설정:
        - 768차원 벡터
        - Cosine 거리 (한국어 의미 유사도에 적합)
        """
        if self._collection_initialized:
            return

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as qdrant_models

            client = await self._get_qdrant_client()

            # 컬렉션 존재 여부 확인
            collections = await asyncio.to_thread(client.get_collections)
            existing_names = [c.name for c in collections.collections]

            if COLLECTION_NAME not in existing_names:
                logger.info("Qdrant 컬렉션 생성 중: %s", COLLECTION_NAME)
                await asyncio.to_thread(
                    client.create_collection,
                    collection_name=COLLECTION_NAME,
                    vectors_config=qdrant_models.VectorParams(
                        size=EMBEDDING_DIM,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info("Qdrant 컬렉션 생성 완료: %s", COLLECTION_NAME)
            else:
                logger.debug("Qdrant 컬렉션 이미 존재: %s", COLLECTION_NAME)

            self._collection_initialized = True

        except Exception as exc:
            logger.warning("Qdrant 컬렉션 초기화 실패: %s", exc)
            raise

    # ─── 임베딩 캐싱 ──────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(text: str) -> str:
        """텍스트의 SHA-256 해시 앞 16자를 사용한 캐시 키를 반환합니다."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return f"{EMBEDDING_CACHE_PREFIX}:{text_hash}"

    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Redis에서 캐시된 임베딩을 조회합니다."""
        try:
            redis = self._get_redis()
            cached = await redis.get(self._cache_key(text))
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning("임베딩 캐시 조회 실패: %s", exc)
        return None

    async def _set_cached_embedding(self, text: str, embedding: List[float]) -> None:
        """Redis에 임베딩을 캐시합니다 (TTL: 24시간)."""
        try:
            redis = self._get_redis()
            await redis.setex(
                self._cache_key(text),
                EMBEDDING_CACHE_TTL,
                json.dumps(embedding),
            )
        except Exception as exc:
            logger.warning("임베딩 캐시 저장 실패: %s", exc)

    # ─── 배치 임베딩 ──────────────────────────────────────────────────────────

    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 목록을 배치로 임베딩합니다.
        Redis 캐시를 우선 조회하고, 캐시 미스 시 모델로 임베딩합니다.

        Args:
            texts: 임베딩할 텍스트 목록 (E5 prefix 없이 전달)

        Returns:
            768차원 임베딩 벡터 목록
        """
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        # 캐시 조회
        for i, text in enumerate(texts):
            cached = await self._get_cached_embedding(text)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # 캐시 미스 텍스트 임베딩
        if uncached_texts:
            # E5 모델 passage prefix 추가
            prefixed_texts = [f"{E5_PASSAGE_PREFIX}{t}" for t in uncached_texts]
            embeddings = await self._embedding_service.embed_texts(prefixed_texts)

            for idx, (orig_text, embedding) in zip(uncached_indices, zip(uncached_texts, embeddings)):
                results[idx] = embedding
                await self._set_cached_embedding(orig_text, embedding)

        return [r for r in results if r is not None]

    # ─── 단락 분할 ────────────────────────────────────────────────────────────

    @staticmethod
    def _split_into_paragraphs(content: str) -> List[str]:
        """
        챕터 내용을 단락 단위로 분할합니다.

        분할 기준: 이중 개행(\\n\\n)
        최소 길이: MIN_PARAGRAPH_CHARS (50자) 미만 단락은 제외

        Args:
            content: 챕터 전체 내용

        Returns:
            단락 목록
        """
        raw_paragraphs = content.split("\n\n")
        paragraphs = [
            p.strip()
            for p in raw_paragraphs
            if len(p.strip()) >= MIN_PARAGRAPH_CHARS
        ]
        return paragraphs

    @staticmethod
    def _extract_character_mentions(text: str) -> List[str]:
        """
        텍스트에서 캐릭터 이름으로 추정되는 단어를 추출합니다.

        한국어 고유명사 패턴 (2~4자 한글 단어)을 기반으로 추출합니다.
        실제 캐릭터 목록이 없으므로 간단한 휴리스틱을 사용합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            추출된 이름 목록 (중복 제거)
        """
        # 2~4자 한글 단어 추출 (간단한 휴리스틱)
        pattern = re.compile(r"[가-힣]{2,4}")
        candidates = pattern.findall(text)
        # 중복 제거 및 빈도 기반 필터링 (2회 이상 등장)
        from collections import Counter
        counts = Counter(candidates)
        return [name for name, count in counts.items() if count >= 2]

    # ─── 핵심 RAG 메서드 ──────────────────────────────────────────────────────

    async def embed_chapter(
        self,
        chapter_id: str,
        content: str,
        project_id: str,
        chapter_number: int,
    ) -> None:
        """
        챕터 내용을 단락 단위로 분할하여 임베딩하고 Qdrant에 저장합니다.

        Req 3.1: RAG_System SHALL embed all generated Chapter content into the Vector_Store

        Args:
            chapter_id: 챕터 ID
            content: 챕터 전체 내용
            project_id: 프로젝트 ID (네임스페이스 분리용)
            chapter_number: 챕터 번호
        """
        try:
            await self._ensure_collection()
        except Exception as exc:
            logger.warning(
                "Qdrant 사용 불가, 임베딩 건너뜀: chapter_id=%s, error=%s",
                chapter_id, exc
            )
            return

        paragraphs = self._split_into_paragraphs(content)
        if not paragraphs:
            logger.warning("임베딩할 단락이 없습니다: chapter_id=%s", chapter_id)
            return

        logger.info(
            "챕터 임베딩 시작: chapter_id=%s, paragraphs=%d",
            chapter_id, len(paragraphs)
        )

        try:
            # 배치 임베딩
            embeddings = await self.embed_text(paragraphs)

            # Qdrant 포인트 구성
            from qdrant_client.http import models as qdrant_models

            points = []
            now_ts = datetime.now(timezone.utc).timestamp()

            for para_idx, (paragraph, embedding) in enumerate(zip(paragraphs, embeddings)):
                point_id = self._make_point_id(chapter_id, para_idx)
                character_mentions = self._extract_character_mentions(paragraph)

                point = qdrant_models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "project_id": project_id,
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "paragraph_index": para_idx,
                        "text": paragraph,
                        "character_mentions": character_mentions,
                        "created_at": now_ts,
                    },
                )
                points.append(point)

            # Qdrant upsert
            client = await self._get_qdrant_client()
            await asyncio.to_thread(
                client.upsert,
                collection_name=COLLECTION_NAME,
                points=points,
            )

            logger.info(
                "챕터 임베딩 완료: chapter_id=%s, points=%d",
                chapter_id, len(points)
            )

        except Exception as exc:
            logger.error(
                "챕터 임베딩 실패: chapter_id=%s, error=%s",
                chapter_id, exc, exc_info=True
            )
            raise

    async def retrieve_relevant_passages(
        self,
        query: str,
        project_id: str,
        top_k: int = 5,
    ) -> List[RelevantPassage]:
        """
        쿼리와 의미적으로 유사한 구절을 검색합니다.

        Req 3.2: WHEN generating a new Chapter, RAG_System SHALL retrieve the top 5
                 most relevant previous passages based on semantic similarity

        Args:
            query: 검색 쿼리 텍스트
            project_id: 프로젝트 ID (네임스페이스 필터)
            top_k: 반환할 최대 구절 수 (기본값: 5)

        Returns:
            유사도 순으로 정렬된 RelevantPassage 목록
        """
        try:
            await self._ensure_collection()
        except Exception as exc:
            logger.warning(
                "Qdrant 사용 불가, 빈 결과 반환: project_id=%s, error=%s",
                project_id, exc
            )
            return []

        try:
            # E5 모델 query prefix 추가
            prefixed_query = f"{E5_QUERY_PREFIX}{query}"
            query_embeddings = await self._embedding_service.embed_texts([prefixed_query])
            query_vector = query_embeddings[0]

            # 프로젝트별 필터링
            from qdrant_client.http import models as qdrant_models

            project_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="project_id",
                        match=qdrant_models.MatchValue(value=project_id),
                    )
                ]
            )

            client = await self._get_qdrant_client()
            search_results = await asyncio.to_thread(
                client.search,
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=project_filter,
                limit=top_k,
                with_payload=True,
            )

            passages: List[RelevantPassage] = []
            for result in search_results:
                payload = result.payload or {}
                passage = RelevantPassage(
                    chapter_id=payload.get("chapter_id", ""),
                    chapter_number=payload.get("chapter_number", 0),
                    paragraph_index=payload.get("paragraph_index", 0),
                    text=payload.get("text", ""),
                    similarity_score=result.score,
                    character_mentions=payload.get("character_mentions", []),
                )
                passages.append(passage)

            logger.info(
                "유사 구절 검색 완료: project_id=%s, query_len=%d, results=%d",
                project_id, len(query), len(passages)
            )
            return passages

        except Exception as exc:
            logger.warning(
                "유사 구절 검색 실패, 빈 결과 반환: project_id=%s, error=%s",
                project_id, exc
            )
            return []

    async def update_embeddings(
        self,
        chapter_id: str,
        updated_content: str,
        project_id: str,
        chapter_number: int,
    ) -> None:
        """
        챕터 수정 시 기존 임베딩을 삭제하고 새로 임베딩합니다.

        Req 3.5: WHEN a Chapter is modified, RAG_System SHALL update the
                 corresponding embeddings in the Vector_Store

        Args:
            chapter_id: 챕터 ID
            updated_content: 수정된 챕터 내용
            project_id: 프로젝트 ID
            chapter_number: 챕터 번호
        """
        logger.info("챕터 임베딩 업데이트 시작: chapter_id=%s", chapter_id)

        # 기존 임베딩 삭제
        await self.delete_chapter_embeddings(chapter_id)

        # 새 임베딩 생성
        await self.embed_chapter(chapter_id, updated_content, project_id, chapter_number)

        logger.info("챕터 임베딩 업데이트 완료: chapter_id=%s", chapter_id)

    async def delete_chapter_embeddings(self, chapter_id: str) -> None:
        """
        챕터의 모든 임베딩을 Qdrant에서 삭제합니다.

        Args:
            chapter_id: 삭제할 챕터 ID
        """
        try:
            await self._ensure_collection()
        except Exception as exc:
            logger.warning(
                "Qdrant 사용 불가, 삭제 건너뜀: chapter_id=%s, error=%s",
                chapter_id, exc
            )
            return

        try:
            from qdrant_client.http import models as qdrant_models

            client = await self._get_qdrant_client()

            # chapter_id 기반 필터로 삭제
            await asyncio.to_thread(
                client.delete,
                collection_name=COLLECTION_NAME,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="chapter_id",
                                match=qdrant_models.MatchValue(value=chapter_id),
                            )
                        ]
                    )
                ),
            )

            logger.info("챕터 임베딩 삭제 완료: chapter_id=%s", chapter_id)

        except Exception as exc:
            logger.warning(
                "챕터 임베딩 삭제 실패: chapter_id=%s, error=%s",
                chapter_id, exc
            )

    # ─── RAG 컨텍스트 구성 ────────────────────────────────────────────────────

    def build_rag_context(self, passages: List[RelevantPassage]) -> str:
        """
        검색된 구절을 Qwen 프롬프트에 포함할 형식으로 구성합니다.

        Req 3.3: RAG_System SHALL provide retrieved context to the Qwen_Model
                 as additional input

        Args:
            passages: 검색된 유사 구절 목록

        Returns:
            프롬프트에 포함할 RAG 컨텍스트 문자열
        """
        if not passages:
            return ""

        parts = ["[관련 이전 내용]"]
        for passage in passages:
            part = (
                f"챕터 {passage.chapter_number}, 단락 {passage.paragraph_index}:\n"
                f"{passage.text}\n"
                f"(유사도: {passage.similarity_score:.2f})"
            )
            parts.append(part)
            parts.append("---")

        # 마지막 구분선 제거
        if parts and parts[-1] == "---":
            parts.pop()

        return "\n".join(parts)

    # ─── 내부 유틸리티 ────────────────────────────────────────────────────────

    @staticmethod
    def _make_point_id(chapter_id: str, paragraph_index: int) -> str:
        """
        Qdrant 포인트 ID를 생성합니다.

        Qdrant는 UUID 또는 unsigned int를 ID로 사용합니다.
        chapter_id:paragraph_index 형식의 문자열을 UUID로 변환합니다.

        Args:
            chapter_id: 챕터 ID
            paragraph_index: 단락 인덱스

        Returns:
            UUID 형식의 포인트 ID 문자열
        """
        import uuid
        # chapter_id + paragraph_index 조합으로 결정론적 UUID 생성
        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        name = f"{chapter_id}:{paragraph_index}"
        return str(uuid.uuid5(namespace, name))


# ─── 싱글턴 인스턴스 (의존성 주입용) ─────────────────────────────────────────

rag_system = RAGSystem()

# Implementation Tasks: AI 장편소설 생성 플랫폼

## Task Overview

이 작업 목록은 AI 장편소설 생성 플랫폼의 전체 구현을 단계별로 분해한 것입니다. 각 작업은 요구사항 문서와 설계 문서를 기반으로 하며, 순차적으로 실행되어야 합니다.

---

## Phase 1: 프로젝트 초기 설정

- [x] 1. 프로젝트 구조 및 개발 환경 설정
  - [x] 1.1 백엔드 Python 프로젝트 초기화 (FastAPI, Poetry/pip)
    - `backend/` 디렉토리 생성
    - `pyproject.toml` 또는 `requirements.txt` 작성 (fastapi, uvicorn, sqlalchemy, alembic, celery, redis, pydantic, httpx, python-jose, passlib, hypothesis, pytest 등)
    - `backend/app/` 패키지 구조 생성 (`main.py`, `config.py`, `database.py`)
  - [x] 1.2 프론트엔드 React 프로젝트 초기화 (Vite + TypeScript)
    - `frontend/` 디렉토리 생성
    - Vite + React + TypeScript 설정
    - TailwindCSS, React Query, React Router, Axios 설치
    - `src/` 디렉토리 구조 생성 (`components/`, `pages/`, `hooks/`, `api/`, `store/`, `types/`)
  - [x] 1.3 Docker Compose 개발 환경 구성
    - `docker-compose.yml` 작성 (PostgreSQL, Redis, Qdrant, backend, frontend)
    - 각 서비스 환경변수 설정 (`.env.example`)
    - 개발용 볼륨 마운트 설정
  - [x] 1.4 환경변수 및 설정 관리
    - `backend/app/config.py`에 Pydantic Settings 기반 설정 클래스 구현
    - Qwen API 키, DB URL, Redis URL, JWT Secret 등 환경변수 정의
    - `.env.example` 파일 작성

---

## Phase 2: 데이터베이스 설계 및 구축

- [-] 2. PostgreSQL 데이터베이스 스키마 구현
  - [ ] 2.1 SQLAlchemy ORM 모델 정의
    - `backend/app/models/` 디렉토리 생성
    - `User`, `Project`, `Chapter`, `ChapterVersion`, `Character`, `PlotPoint`, `WorldBuilding`, `ConsistencyIssue`, `GenerationLog` 모델 구현
    - 모든 관계(relationship) 및 외래키 설정
  - [ ] 2.2 Alembic 마이그레이션 설정
    - Alembic 초기화 및 `alembic.ini` 설정
    - 초기 마이그레이션 스크립트 생성 (설계 문서의 SQL 스키마 기반)
    - 인덱스 생성 마이그레이션 포함
  - [ ] 2.3 데이터베이스 연결 및 세션 관리
    - `backend/app/database.py`에 비동기 SQLAlchemy 엔진 설정
    - 커넥션 풀 설정 (최소 10개)
    - 의존성 주입용 `get_db()` 함수 구현
  - [ ] 2.4 Pydantic 스키마(DTO) 정의
    - `backend/app/schemas/` 디렉토리 생성
    - 각 모델별 Create/Update/Response 스키마 정의
    - `GenerationParameters`, `StoryContext`, `ConsistencyReport` 등 핵심 스키마 구현

---

## Phase 3: 인증 및 사용자 관리

- [ ] 3. 사용자 인증 시스템 구현
  - [ ] 3.1 비밀번호 해싱 및 JWT 토큰 유틸리티
    - `backend/app/core/security.py` 구현
    - bcrypt 기반 비밀번호 해싱/검증 함수
    - JWT 액세스/리프레시 토큰 생성 및 검증 함수
    - 토큰 만료 시간 설정 (액세스: 30분, 리프레시: 7일)
  - [ ] 3.2 인증 API 엔드포인트 구현
    - `POST /api/auth/register` - 회원가입
    - `POST /api/auth/login` - 로그인 (JWT 반환)
    - `POST /api/auth/refresh` - 토큰 갱신
    - `POST /api/auth/logout` - 로그아웃
  - [ ] 3.3 인증 미들웨어 및 의존성
    - JWT 검증 미들웨어 구현
    - `get_current_user()` 의존성 함수 구현
    - 속도 제한 미들웨어 (100 req/min/user, Redis 기반)

---

## Phase 4: 핵심 백엔드 서비스 구현

- [ ] 4. 프로젝트 관리 서비스
  - [ ] 4.1 프로젝트 CRUD API
    - `POST /api/projects` - 프로젝트 생성
    - `GET /api/projects` - 목록 조회 (페이지네이션)
    - `GET /api/projects/{id}` - 상세 조회
    - `PUT /api/projects/{id}` - 수정
    - `DELETE /api/projects/{id}` - 삭제 (cascade)
  - [ ] 4.2 프로젝트 권한 검증
    - 모든 프로젝트 엔드포인트에 소유자 검증 로직 추가
    - HTTP 403 응답 처리

- [ ] 5. 챕터 관리 서비스 (ChapterManagerService)
  - [ ] 5.1 챕터 CRUD 구현
    - `backend/app/services/chapter_manager.py` 생성
    - `create_chapter()`, `update_chapter()`, `delete_chapter()`, `get_chapter()` 구현
    - 챕터 번호 순서 관리 로직
  - [ ] 5.2 챕터 버전 관리
    - 챕터 수정 시 자동 버전 저장 (최대 5개 유지)
    - `get_chapter_versions()` 구현
    - 버전 롤백 기능
  - [ ] 5.3 챕터 순서 변경
    - `reorder_chapters()` 구현
    - 챕터 번호 연속성 보장 로직
  - [ ] 5.4 챕터 API 엔드포인트
    - `POST /api/projects/{id}/chapters/generate`
    - `GET /api/projects/{id}/chapters`
    - `GET /api/chapters/{id}`
    - `PUT /api/chapters/{id}`
    - `DELETE /api/chapters/{id}`
    - `POST /api/chapters/{id}/regenerate`
    - `GET /api/chapters/{id}/versions`
    - `POST /api/projects/{id}/chapters/reorder`

- [ ] 6. 컨텍스트 관리 서비스 (ContextManagerService)
  - [ ] 6.1 StoryContext 저장 및 조회
    - `backend/app/services/context_manager.py` 생성
    - `get_story_context()` - Redis 캐시 우선, DB 폴백
    - `update_context()` - 챕터 수정 시 컨텍스트 업데이트
    - 캐시 히트율 80% 이상 목표 설정
  - [ ] 6.2 컨텍스트 윈도우 관리
    - 토큰 카운팅 유틸리티 구현 (tiktoken 또는 유사 라이브러리)
    - `summarize_old_chapters()` - 100,000 토큰 초과 시 자동 요약
    - 요약 시 캐릭터명, 핵심 플롯, 세계관 규칙 보존 로직
  - [ ] 6.3 캐릭터 추적
    - `track_character_development()` 구현
    - 챕터별 캐릭터 등장 및 변화 추적

- [ ] 7. 캐릭터 관리 API
  - [ ] 7.1 캐릭터 CRUD
    - `POST /api/projects/{id}/characters`
    - `GET /api/projects/{id}/characters`
    - `PUT /api/characters/{id}`
    - `DELETE /api/characters/{id}`
  - [ ] 7.2 캐릭터 프로필 StoryContext 연동
    - 캐릭터 생성/수정 시 StoryContext 자동 업데이트

- [ ] 8. 플롯 구조 관리 API
  - [ ] 8.1 플롯 포인트 CRUD
    - `GET /api/projects/{id}/plot`
    - `PUT /api/projects/{id}/plot`
    - 플롯 단계 관리 (exposition, rising_action, climax, falling_action, resolution)
  - [ ] 8.2 플롯 완료 상태 관리
    - 플롯 포인트 완료 표시 기능
    - 현재 플롯 위치 추적

- [ ] 9. 세계관 설정 관리 API
  - [ ] 9.1 세계관 요소 CRUD
    - `GET /api/projects/{id}/worldbuilding`
    - `PUT /api/projects/{id}/worldbuilding`
    - 카테고리별 관리 (location, magic_system, technology, culture)

---

## Phase 5: AI 통합

- [ ] 10. Qwen API 클라이언트 구현
  - [ ] 10.1 QwenAPIClient 기본 구현
    - `backend/app/services/qwen_client.py` 생성
    - Qwen API 인증 및 HTTP 클라이언트 설정 (httpx 비동기)
    - `generate_text()` 메서드 구현
    - 요청/응답 로깅
  - [ ] 10.2 재시도 및 에러 처리
    - 지수 백오프 재시도 로직 (3회, 1s/2s/4s)
    - `QwenAPIError`, `QwenRateLimitError`, `QwenTimeoutError` 예외 클래스 정의
    - 실패한 요청 DB 저장 (나중에 재시도 가능)
  - [ ] 10.3 스트리밍 응답 지원
    - Server-Sent Events(SSE)를 통한 생성 진행 상황 전송
    - 5초 이상 소요 시 진행률 업데이트

- [ ] 11. RAG 시스템 구현
  - [ ] 11.1 Qdrant 벡터 DB 연결
    - `backend/app/services/rag_system.py` 생성
    - Qdrant 클라이언트 설정
    - 컬렉션 생성 (768차원, 한국어 최적화)
    - 프로젝트별 네임스페이스 분리
  - [ ] 11.2 한국어 임베딩 서비스
    - multilingual-e5-large 또는 KoSimCSE 모델 통합
    - `embed_text()` 배치 처리 구현
    - 임베딩 캐싱 (Redis)
  - [ ] 11.3 챕터 임베딩 및 검색
    - `embed_chapter()` - 챕터를 단락 단위로 분할 후 임베딩
    - `retrieve_relevant_passages()` - 상위 5개 유사 구절 반환
    - `update_embeddings()` - 챕터 수정 시 임베딩 업데이트
  - [ ] 11.4 RAG 컨텍스트 구성
    - 검색된 구절을 Qwen 프롬프트에 포함하는 로직

- [ ] 12. Novel Generator Service 구현
  - [ ] 12.1 프롬프트 엔지니어링
    - `backend/app/services/novel_generator.py` 생성
    - `_build_prompt()` - StoryContext + RAG 결과 + 파라미터 기반 프롬프트 구성
    - 한국어 장편소설 특화 시스템 프롬프트 작성
    - 캐릭터 프로필, 플롯 위치, 세계관 규칙 포함 로직
  - [ ] 12.2 챕터 생성 파이프라인
    - `generate_chapter()` 전체 파이프라인 구현
    - ContextManager → RAG → Qwen → ChapterManager 순서
    - 최소 2,000자 한국어 생성 보장
    - Celery 비동기 작업으로 처리
  - [ ] 12.3 챕터 재생성
    - `regenerate_chapter()` - 사용자 피드백 반영
    - 기존 StoryContext 보존하면서 재생성
    - 피드백 파라미터 (톤 조정, 플롯 방향) 프롬프트 반영

- [ ] 13. 일관성 검증 서비스 (ConsistencyCheckerService)
  - [ ] 13.1 캐릭터 일관성 검증
    - `backend/app/services/consistency_checker.py` 생성
    - `_check_character_consistency()` - 이름, 속성, 관계 검증
    - 한국어 텍스트에서 캐릭터명 추출 (정규식 + NLP)
  - [ ] 13.2 플롯 일관성 검증
    - `_check_plot_consistency()` - 논리적 모순 검증
    - 시간순 이벤트 검증
  - [ ] 13.3 세계관 일관성 검증
    - `_check_worldbuilding_consistency()` - 규칙, 위치, 타임라인 검증
  - [ ] 13.4 일관성 점수 계산
    - `_calculate_consistency_score()` - 0~100 점수 반환
    - 이슈 심각도별 가중치 적용
  - [ ] 13.5 일관성 API 엔드포인트
    - `GET /api/chapters/{id}/consistency`
    - `GET /api/projects/{id}/consistency`

---

## Phase 6: 내보내기 기능

- [ ] 14. 소설 내보내기 서비스
  - [ ] 14.1 PDF 내보내기
    - ReportLab 또는 WeasyPrint 기반 PDF 생성
    - 한국어 폰트 설정 (Noto Sans KR 등)
    - 목차, 챕터 제목, 페이지 번호 포함
    - 폰트/여백/줄간격 커스터마이징
  - [ ] 14.2 EPUB 내보내기
    - ebooklib 기반 EPUB 생성
    - Kindle, Kobo, Apple Books 호환
    - 목차 포함
  - [ ] 14.3 텍스트 내보내기
    - UTF-8 인코딩 plain text 생성
  - [ ] 14.4 내보내기 API
    - `POST /api/projects/{id}/export` (format: pdf/epub/txt)
    - Celery 비동기 처리 (60초 내 완료)
    - 완료 후 다운로드 링크 반환

---

## Phase 7: 프론트엔드 구현

- [-] 15. 프론트엔드 기반 구조
  - [ ] 15.1 라우팅 및 레이아웃 설정
    - React Router 설정 (로그인, 대시보드, 프로젝트, 에디터 페이지)
    - 공통 레이아웃 컴포넌트 (Header, Sidebar, Footer)
    - 인증 보호 라우트 구현
  - [ ] 15.2 API 클라이언트 설정
    - Axios 인스턴스 설정 (baseURL, 인터셉터)
    - JWT 토큰 자동 첨부 및 갱신 로직
    - 에러 인터셉터 (401 → 자동 로그아웃)
  - [ ] 15.3 전역 상태 관리
    - React Query 설정 (캐싱, 재시도, 무효화)
    - 인증 상태 관리 (Zustand 또는 Context API)
  - [ ] 15.4 디자인 시스템 구축
    - TailwindCSS 커스텀 테마 설정 (색상, 폰트, 간격)
    - 한국어 폰트 적용 (Noto Sans KR, Nanum Myeongjo)
    - 공통 UI 컴포넌트 (Button, Input, Modal, Toast, Spinner, Card)
    - 다크/라이트 모드 지원

- [ ] 16. 인증 페이지
  - [ ] 16.1 로그인 페이지
    - 이메일/비밀번호 폼
    - 유효성 검사 (react-hook-form + zod)
    - 에러 메시지 표시
  - [ ] 16.2 회원가입 페이지
    - 이름, 이메일, 비밀번호 폼
    - 비밀번호 강도 표시

- [ ] 17. 프로젝트 대시보드
  - [ ] 17.1 프로젝트 목록 페이지
    - 프로젝트 카드 그리드 (제목, 장르, 챕터 수, 총 글자 수, 최종 수정일)
    - 새 프로젝트 생성 모달
    - 프로젝트 삭제 확인 다이얼로그
    - 검색 및 정렬 기능
  - [ ] 17.2 프로젝트 생성 모달
    - 제목, 장르, 설명 입력
    - 장르 선택 (판타지, 로맨스, 미스터리, SF, 스릴러)

- [ ] 18. 소설 에디터 (핵심 페이지)
  - [ ] 18.1 에디터 레이아웃
    - 3단 레이아웃: 좌측 챕터 목록 / 중앙 에디터 / 우측 컨텍스트 패널
    - 반응형 디자인 (768px 이상)
    - 키보드 단축키 (Ctrl+S 저장, Ctrl+G 생성, Ctrl+N 새 챕터)
  - [ ] 18.2 챕터 목록 패널
    - 챕터 카드 (번호, 제목, 글자 수, 생성일, 일관성 점수)
    - 드래그 앤 드롭 순서 변경 (react-beautiful-dnd)
    - 챕터 추가/삭제 버튼
  - [ ] 18.3 리치 텍스트 에디터
    - TipTap 또는 Quill 기반 에디터
    - 한국어 입력 최적화
    - 자동 저장 (30초마다)
    - 저장 상태 표시 (저장됨/저장 중/저장 실패)
    - 글자 수 카운터
  - [ ] 18.4 챕터 생성 패널
    - 생성 파라미터 설정 (장르, 톤, 창의성 슬라이더)
    - 사용자 지정 프롬프트 입력
    - 생성 버튼 및 진행 상태 표시 (SSE 기반)
    - 재생성 버튼 (피드백 입력 포함)
  - [ ] 18.5 컨텍스트 사이드바
    - 캐릭터 목록 및 빠른 참조
    - 플롯 타임라인 시각화
    - 세계관 참조 패널
    - 일관성 점수 및 이슈 표시

- [ ] 19. 캐릭터 관리 UI
  - [ ] 19.1 캐릭터 목록 및 카드
    - 캐릭터 카드 (이름, 나이, 주요 특성, 외모 요약)
    - 캐릭터 추가/수정/삭제
  - [ ] 19.2 캐릭터 상세 폼
    - 이름, 나이, 성격 특성, 외모, 배경 입력
    - 관계 설정 (다른 캐릭터와의 관계)

- [ ] 20. 플롯 관리 UI
  - [ ] 20.1 플롯 타임라인 뷰
    - 5단계 플롯 구조 시각화 (발단-전개-절정-하강-결말)
    - 플롯 포인트 카드 (완료/미완료 상태)
  - [ ] 20.2 플롯 포인트 편집
    - 플롯 포인트 추가/수정/삭제
    - 완료 표시 기능

- [ ] 21. 세계관 관리 UI
  - [ ] 21.1 세계관 요소 목록
    - 카테고리별 탭 (장소, 마법 체계, 기술, 문화)
    - 세계관 요소 카드
  - [ ] 21.2 세계관 요소 편집
    - 이름, 설명, 규칙 입력 폼

- [ ] 22. 내보내기 UI
  - [ ] 22.1 내보내기 모달
    - 형식 선택 (PDF, EPUB, TXT)
    - PDF 옵션 (폰트, 여백, 줄간격)
    - 내보내기 진행 상태 표시
    - 완료 후 다운로드 버튼

---

## Phase 8: 실시간 통신

- [ ] 23. Server-Sent Events (SSE) 구현
  - [ ] 23.1 백엔드 SSE 엔드포인트
    - `GET /api/chapters/generate/stream/{task_id}` SSE 엔드포인트
    - Celery 작업 진행 상황 실시간 전송
    - 완료/에러 이벤트 전송
  - [ ] 23.2 프론트엔드 SSE 클라이언트
    - EventSource API 기반 SSE 수신
    - 진행 상태 UI 업데이트 (프로그레스 바)
    - 연결 끊김 시 재연결 로직

---

## Phase 9: 테스팅

- [ ] 24. Property-Based 테스트 구현
  - [ ] 24.1 테스트 환경 설정
    - `tests/` 디렉토리 구조 생성
    - pytest, hypothesis, pytest-asyncio 설정
    - 테스트용 DB/Redis 픽스처 설정
  - [ ] 24.2 핵심 속성 테스트 구현
    - Property 1: 파라미터 유효성 검증 완전성
    - Property 3: StoryContext 라운드트립 보존
    - Property 6: RAG 임베딩 라운드트립
    - Property 7: RAG 검색 결과 수 및 정렬
    - Property 10: 챕터 메타데이터 완전성
    - Property 12: 챕터 순서 무결성
    - Property 13: 버전 히스토리 최대 5개 유지
    - Property 16: 일관성 점수 범위 (0-100)
    - Property 24: 프로젝트 삭제 시 cascade 완전성
    - Property 25: 민감 데이터 암호화
    - Property 27: 권한 검증 (타 사용자 접근 차단)
    - Property 29: 속도 제한 적용
    - Property 31: 한국어 텍스트 인코딩 라운드트립
  - [ ] 24.3 커스텀 Hypothesis 전략
    - `tests/strategies.py` - 한국어 텍스트 생성기
    - `generation_parameters()` 전략
    - `story_context()` 전략

- [ ] 25. 단위 테스트 구현
  - [ ] 25.1 서비스 단위 테스트
    - NovelGeneratorService 테스트 (Qwen API 모킹)
    - ContextManagerService 테스트
    - ConsistencyCheckerService 테스트
    - RAGSystem 테스트 (벡터 DB 모킹)
  - [ ] 25.2 API 엔드포인트 단위 테스트
    - 인증 엔드포인트 테스트
    - 프로젝트/챕터 CRUD 테스트
    - 에러 응답 형식 테스트

- [ ] 26. 통합 테스트 구현
  - [ ] 26.1 챕터 생성 전체 플로우 테스트
    - testcontainers 기반 PostgreSQL/Redis 사용
    - 프로젝트 생성 → 캐릭터 추가 → 챕터 생성 → 저장 검증
  - [ ] 26.2 RAG 시스템 통합 테스트
    - 임베딩 저장 → 검색 → 프롬프트 포함 검증

---

## Phase 10: 모니터링 및 관리자 기능

- [ ] 27. 생성 품질 모니터링
  - [ ] 27.1 생성 메트릭 로깅
    - 응답 시간, 토큰 수, 일관성 점수 자동 기록
    - `GenerationLog` 테이블 활용
  - [ ] 27.2 관리자 대시보드 API
    - `GET /api/admin/stats` - 생성 통계
    - 평균 일관성 점수 70 미만 시 알림 트리거
  - [ ] 27.3 에러 로깅 시스템
    - 구조화된 로깅 설정 (structlog 또는 loguru)
    - 타임스탬프, 사용자 컨텍스트, 스택 트레이스 포함

---

## Phase 11: 배포 준비

- [ ] 28. 프로덕션 설정
  - [ ] 28.1 백엔드 프로덕션 설정
    - Gunicorn + Uvicorn 워커 설정
    - CORS 설정 (프론트엔드 도메인 허용)
    - 보안 헤더 설정 (HTTPS, HSTS)
  - [ ] 28.2 프론트엔드 빌드 최적화
    - Vite 프로덕션 빌드 설정
    - 코드 스플리팅 및 레이지 로딩
    - 환경변수 기반 API URL 설정
  - [ ] 28.3 Docker 프로덕션 이미지
    - 백엔드 멀티스테이지 Dockerfile
    - 프론트엔드 Nginx 기반 Dockerfile
    - docker-compose.prod.yml 작성
  - [ ] 28.4 데이터베이스 백업 설정
    - 24시간 주기 자동 백업 스크립트
    - 백업 파일 보관 정책 설정

---

## Phase 12: AI 모델 추상화 레이어

- [ ] 29. AI Model Adapter 구현
  - [ ] 29.1 추상 인터페이스 정의
    - `backend/app/services/ai_adapter/base.py` 생성
    - `AIModelAdapter` 추상 클래스 구현 (Strategy 패턴)
    - `generate_text()`, `generate_stream()` 추상 메서드 정의
    - `AIModelResponse` 공통 응답 모델 정의
  - [ ] 29.2 Qwen 어댑터 구현
    - `backend/app/services/ai_adapter/qwen_adapter.py` 생성
    - 기존 QwenAPIClient를 `AIModelAdapter` 인터페이스로 래핑
    - `model_name = "qwen-max"`, `max_context_tokens = 128000` 설정
  - [ ] 29.3 Claude 어댑터 구현 (선택적)
    - `backend/app/services/ai_adapter/claude_adapter.py` 생성
    - Anthropic SDK 기반 구현
    - `model_name = "claude-3-5-sonnet"`, `max_context_tokens = 200000` 설정
  - [ ] 29.4 GPT 어댑터 구현 (선택적)
    - `backend/app/services/ai_adapter/gpt_adapter.py` 생성
    - OpenAI SDK 기반 구현
    - `model_name = "gpt-4o"`, `max_context_tokens = 128000` 설정
  - [ ] 29.5 AIModelFactory 구현
    - `backend/app/services/ai_adapter/factory.py` 생성
    - 환경변수 또는 프로젝트 설정에 따라 어댑터 선택
    - `create(model_type, api_key)` 팩토리 메서드 구현
  - [ ] 29.6 NovelGeneratorService 어댑터 연동
    - 기존 `QwenAPIClient` 직접 호출을 `AIModelAdapter` 인터페이스로 교체
    - 프로젝트별 모델 설정 지원 (`projects.ai_model` 컬럼 활용)
  - [ ] 29.7 모델 선택 API 및 DB 마이그레이션
    - `projects` 테이블에 `ai_model`, `ai_model_config` 컬럼 추가 마이그레이션
    - `PUT /api/projects/{id}/ai-model` 엔드포인트 구현
    - 프론트엔드 모델 선택 UI (프로젝트 설정 페이지)

---

## Phase 13: 내러티브 아크 엔진

- [ ] 30. NarrativeArcEngine 백엔드 구현
  - [ ] 30.1 DB 스키마 및 ORM 모델
    - `foreshadowing_elements`, `chapter_emotional_arcs` 테이블 마이그레이션
    - `ForeshadowingElement`, `ChapterEmotionalArc` SQLAlchemy 모델 구현
    - 관련 인덱스 생성
  - [ ] 30.2 복선/떡밥 추출 서비스
    - `backend/app/services/narrative_arc_engine.py` 생성
    - `extract_foreshadowing()` - Qwen 모델로 챕터에서 복선 요소 추출
    - 복선 추출용 전용 프롬프트 작성 (한국어 문학적 표현 특화)
    - 챕터 생성/저장 시 자동으로 복선 추출 트리거
  - [ ] 30.3 복선 회수 감지 서비스
    - `detect_payoff()` - RAG로 이전 복선 검색 후 현재 챕터와 매칭
    - 회수된 복선 자동 `is_resolved = True` 업데이트
    - 회수 감지 정확도 향상을 위한 유사도 임계값 설정 (0.75 이상)
  - [ ] 30.4 감정 곡선 분석 서비스
    - `calculate_emotional_arc()` - 단락별 감정 강도 분석
    - 감정 분류: 긴장, 슬픔, 기쁨, 분노, 공포, 설렘 등
    - 챕터 전체 감정 강도 (0-100) 및 주요 감정 반환
  - [ ] 30.5 챕터 간 연결성 점수 계산
    - `calculate_narrative_cohesion()` - 현재 챕터와 이전 챕터들의 서사적 연결성
    - RAG 유사도 + 캐릭터 연속성 + 플롯 연결성 종합 점수
    - 0.0~1.0 범위 반환
  - [ ] 30.6 내러티브 아크 API 엔드포인트
    - `GET /api/projects/{id}/narrative/arc` - 전체 아크 요약
    - `GET /api/projects/{id}/narrative/foreshadowing` - 복선 목록
    - `PUT /api/foreshadowing/{id}/resolve` - 수동 회수 처리
    - `GET /api/chapters/{id}/narrative/emotional-arc` - 챕터 감정 곡선
    - `GET /api/projects/{id}/narrative/cohesion` - 연결성 히트맵

- [ ] 31. 내러티브 아크 프론트엔드 UI
  - [ ] 31.1 복선/떡밥 트래커 패널
    - 에디터 우측 사이드바에 복선 목록 표시
    - 미회수 복선 강조 표시 (빨간색 배지)
    - 회수된 복선 체크 표시 및 회수 챕터 링크
    - 수동 복선 추가/회수 처리 버튼
  - [ ] 31.2 감정 곡선 시각화
    - Recharts 기반 라인 차트로 챕터별 감정 강도 표시
    - 챕터 클릭 시 해당 챕터로 이동
    - 감정 유형별 색상 구분
  - [ ] 31.3 챕터 연결성 히트맵
    - 챕터 간 연결성 강도를 색상 히트맵으로 시각화
    - 연결성 낮은 챕터 쌍 경고 표시

---

## Phase 14: 소설 전체 요약 대시보드

- [ ] 32. StoryDashboardService 백엔드 구현
  - [ ] 32.1 소설 전체 요약 생성
    - `backend/app/services/story_dashboard.py` 생성
    - `get_full_story_summary()` - 전체/파트별/챕터별 계층적 요약
    - Qwen 모델로 챕터 그룹 요약 생성 (Celery 비동기)
    - 요약 결과 Redis 캐싱 (TTL: 1시간)
    - 새 챕터 추가 시 캐시 무효화
  - [ ] 32.2 캐릭터 타임라인 생성
    - `get_character_timeline()` - 캐릭터별 챕터 등장 이력
    - 각 챕터에서의 주요 행동, 감정 상태, 관계 변화 추출
    - 전체 캐릭터 또는 특정 캐릭터 필터링 지원
  - [ ] 32.3 사건 지도 생성
    - `get_event_map()` - 챕터별 주요 사건 매핑
    - 사건 카테고리 분류 (전투, 만남, 이별, 발견, 반전 등)
    - 사건 간 인과관계 연결
  - [ ] 32.4 서사 건강도 리포트
    - `get_narrative_health_report()` - 종합 서사 분석
    - 일관성 점수 + 미회수 복선 수 + 감정 균형 + 캐릭터 균형 종합
    - Qwen 기반 AI 개선 제안 생성 (최대 5개)
    - 전체 건강도 점수 (0-100) 계산
  - [ ] 32.5 대시보드 API 엔드포인트
    - `GET /api/projects/{id}/dashboard` - 전체 대시보드 데이터
    - `GET /api/projects/{id}/dashboard/summary` - 소설 요약
    - `GET /api/projects/{id}/dashboard/character-timeline` - 캐릭터 타임라인
    - `GET /api/projects/{id}/dashboard/event-map` - 사건 지도
    - `GET /api/projects/{id}/dashboard/health-report` - 건강도 리포트

- [ ] 33. 소설 대시보드 프론트엔드 페이지
  - [ ] 33.1 대시보드 페이지 레이아웃
    - 프로젝트 에디터에서 접근 가능한 "대시보드" 탭 추가
    - 4개 섹션: 전체 요약 / 캐릭터 타임라인 / 사건 지도 / 건강도 리포트
  - [ ] 33.2 소설 전체 요약 섹션
    - 전체 요약 텍스트 카드
    - 파트별 요약 아코디언
    - 챕터별 한 줄 요약 목록 (챕터 클릭 시 에디터로 이동)
  - [ ] 33.3 캐릭터 타임라인 시각화
    - 가로 타임라인: X축 챕터, Y축 캐릭터
    - 각 교차점에 등장 강도 표시 (주요/조연/언급)
    - 캐릭터 카드 호버 시 해당 챕터 주요 행동 툴팁
  - [ ] 33.4 사건 지도 시각화
    - 챕터별 주요 사건 카드 타임라인
    - 사건 카테고리별 색상 구분
    - 사건 간 인과관계 화살표 연결
  - [ ] 33.5 서사 건강도 리포트 섹션
    - 종합 건강도 점수 게이지 차트
    - 세부 항목별 점수 바 차트 (일관성, 복선, 감정, 캐릭터 균형)
    - AI 개선 제안 목록 (각 제안에 관련 챕터 링크)
    - "리포트 새로고침" 버튼 (Celery 비동기 재생성)

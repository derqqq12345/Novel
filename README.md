# ✍️ AI 장편소설 생성 플랫폼

> Ollama + Qwen 모델을 활용한 한국어 장편소설 창작 도구

<br>
<img width="1549" height="834" alt="image" src="https://github.com/user-attachments/assets/e529dcad-b5c4-4d3c-84c3-041dc69af6ab" />

## 📌 개요

기존 AI 도구들이 단편소설에만 특화되어 장편소설 생성 시 일관성이 떨어지는 문제를 해결하기 위해 만든 플랫폼입니다.  
로컬 LLM(Ollama)을 사용하여 **인터넷 연결 없이** 한국어 장편소설을 생성할 수 있습니다.

<br>

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📖 챕터 생성 | Ollama Qwen 모델로 2,000자 이상 한국어 소설 자동 생성 |
| ⚡ 실시간 스트리밍 | 생성되는 텍스트를 타이핑되듯 실시간으로 표시 |
| 🎭 캐릭터 관리 | 등장인물 프로필 및 성격 특성 관리 |
| 📊 플롯 구조 | 발단-전개-절정-하강-결말 5단계 플롯 관리 |
| 🌍 세계관 설정 | 장소, 마법 체계, 기술, 문화 등 세계관 요소 관리 |
| 🎨 톤 & 장르 설정 | 판타지/로맨스/미스터리/SF/스릴러 × 진지함/유머/어두움/가벼움 |

<br>

## 🛠️ 기술 스택

**Frontend**
- React 18 + TypeScript
- Vite, TailwindCSS
- React Router, React Query, Zustand

**Backend**
- Python 3.13 + FastAPI
- Uvicorn (ASGI 서버)
- httpx (비동기 HTTP)

**AI**
- [Ollama](https://ollama.com) — 로컬 LLM 런타임
- Qwen 2.5 — 한국어 소설 생성 모델

<br>

## 🚀 빠른 시작

### 사전 요구사항

- [Node.js 18+](https://nodejs.org)
- [Python 3.11+](https://python.org)
- [Ollama](https://ollama.com/download)

<br>

### 1. Ollama 모델 설치

```bash
# Qwen 모델 다운로드 (최초 1회)
ollama pull qwen2.5:14b

# 설치 확인
ollama list
```

<br>

### 2. 백엔드 설정

```bash
# 의존성 설치
pip install fastapi uvicorn httpx pydantic pydantic-settings python-dotenv

# 환경변수 설정
cp .env.example .env
# .env 파일에서 OLLAMA_MODEL 값을 설치한 모델명으로 수정
```

`.env` 주요 설정:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b   # ollama list 에서 확인한 모델명
```

<br>

### 3. 실행

터미널 3개를 열어서 각각 실행하세요.

```bash
# 터미널 1 — Ollama (이미 실행 중이면 생략)
ollama serve

# 터미널 2 — 백엔드 (프로젝트 루트에서)
uvicorn backend.app.main:app --reload --port 8000

# 터미널 3 — 프론트엔드
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

<br>

## 📁 프로젝트 구조

```
AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── generate.py     # 소설 생성 API (Ollama 연동)
│   │   ├── config.py           # 환경변수 설정
│   │   └── main.py             # FastAPI 앱 진입점
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.tsx       # 로그인
│       │   ├── RegisterPage.tsx    # 회원가입
│       │   ├── DashboardPage.tsx   # 프로젝트 목록
│       │   └── EditorPage.tsx      # 소설 에디터 (핵심)
│       └── App.tsx
│
├── .env                        # 환경변수 (Git 제외)
├── .env.example                # 환경변수 예시
└── docker-compose.yml
```

<br>

## 🖥️ 화면 구성

```
에디터 페이지 레이아웃

┌─────────────┬──────────────────────────┬──────────────┐
│  챕터 목록   │       텍스트 에디터        │  생성 패널   │
│             │                          │              │
│ • 챕터 1    │  소설 본문이 실시간으로    │  톤 설정     │
│ • 챕터 2    │  스트리밍되어 표시됩니다.  │  창의성 슬라이더│
│ • 챕터 3    │                          │  추가 지시사항│
│             │  글자 수: 3,200자         │              │
│  [+ 추가]   │                          │ [✨ 챕터 생성]│
└─────────────┴──────────────────────────┴──────────────┘
```

<br>

## ⚙️ API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/generate` | 소설 챕터 스트리밍 생성 |
| `GET` | `/api/generate/health` | Ollama 연결 상태 확인 |
| `GET` | `/api/generate/models` | 사용 가능한 모델 목록 |
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/docs` | Swagger UI (DEBUG=true 시) |

<br>

### 생성 요청 예시

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "genre": "fantasy",
    "tone": "serious",
    "temperature": 0.7,
    "chapter_number": 1,
    "user_prompt": "주인공이 마법사를 처음 만나는 장면"
  }'
```

<br>

## 🔧 트러블슈팅

**모델을 찾을 수 없음 (`model not found`)**
```bash
# 설치된 모델 확인
ollama list

# .env 의 OLLAMA_MODEL 값을 목록에 있는 정확한 이름으로 수정
OLLAMA_MODEL=qwen2.5:14b
```

**Ollama 포트 충돌 (`bind: Only one usage...`)**
```
이미 Ollama가 실행 중입니다. ollama serve 를 다시 실행할 필요 없습니다.
```

**백엔드 모듈 에러 (`No module named 'backend'`)**
```bash
# 반드시 프로젝트 루트(AI/)에서 실행
cd C:\Users\pc\Desktop\AI
uvicorn backend.app.main:app --reload --port 8000
```

<br>

## 📝 라이선스

MIT

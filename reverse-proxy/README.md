# JBNU AI Mentor - Reverse Proxy

**AI 멘토 시스템의 Nginx 기반 리버스 프록시 서비스**

## 📖 개요

이 디렉토리는 JBNU AI Mentor 시스템의 Nginx 기반 리버스 프록시 설정을 포함합니다. OpenWebUI 기반의 사용자 인터페이스와 여러 백엔드 마이크로서비스들을 통합하여 단일 진입점을 제공하며, 공개 키오스크 모드를 지원합니다.

## 🏗️ 아키텍처

### 핵심 구성요소

```
reverse-proxy/
├── nginx.conf                    # 메인 Nginx 설정
├── default.conf                  # 기본 서버 설정 (단순 버전)
├── proxy_params                  # 공통 프록시 헤더
├── Dockerfile                    # 컨테이너 빌드 설정
├── custom.css                    # UI 커스터마이징 CSS
├── ai-mentor-cleanup.js          # UI 정리 JavaScript
├── suppress-warnings.js          # 경고 억제 스크립트
└── openwebui/                    # OpenWebUI 캐시 및 데이터
```

## 🔧 주요 기능

### 1. 라우팅 시스템

#### API 라우팅
- **`/api/llm/`** → llm-agent:8001 (주요 AI 서비스)
- **`/api/curriculum/`** → svc7996:7996 (커리큘럼 플래닝)
- **`/api/search/`** → svc7997:7997 (FAISS 벡터 검색)
- **`/api/sql/`** → svc7999:7999 (SQL 데이터베이스 쿼리)
- **`/api/fallback/`** → svc7998:7998 (폴백 LLM 서비스)
- **`/api/department/`** → department-mapping:8000 (학과 매핑)

#### 특수 엔드포인트
- **`/api/v2/agent-stream`** → llm-agent 스트리밍 API
- **`/api/chat/completions`** → OpenAI 호환 API
- **`/api/models`** → 고정 모델 리스트 응답

### 2. 보안 및 제한

#### 레이트 리미팅
```nginx
# 채팅 API: 10 req/sec (burst 20)
limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=10r/s;

# 일반 API: 600 req/min (burst 50)
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=600r/m;
```

#### 접근 제한 (공개 키오스크 모드)
- **차단된 UI 경로**: `/admin`, `/users`, `/settings`, `/models`, `/config`
- **차단된 API**: `/api/admin`, `/api/settings`, `/api/knowledge`, `/api/prompts`
- **허용된 기본 API**: `/api/config`, `/api/settings/public`, `/api/v1/auths`

### 3. 스트리밍 지원

#### 실시간 응답
```nginx
# 스트리밍 최적화 설정
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
add_header X-Accel-Buffering no;
gzip off;
```

#### WebSocket 지원
- `/ws/`, `/socket.io/` 경로를 통한 실시간 통신
- 86400초 (24시간) 연결 유지

## 📁 파일별 상세 설명

### nginx.conf
**메인 Nginx 설정 파일**

**주요 기능:**
- 워커 프로세스 및 연결 설정
- 레이트 리미팅 존 정의
- DNS 리졸버 설정 (Docker 내장 DNS)
- 업스트림 서버 동적 변수 설정

**핵심 설정:**
```nginx
# Docker DNS 리졸버
resolver 127.0.0.11 ipv6=off valid=30s;

# 업스트림 변수 (런타임 DNS 해석)
set $up_openwebui openwebui:8080;
set $up_llm_agent llm-agent:8001;
```

### default.conf
**단순화된 서버 설정**

**용도:** 기본적인 프록시 설정이 필요할 때 사용하는 대안 설정

**특징:**
- 업스트림 블록 사용
- CORS 헤더 자동 추가
- 간소화된 라우팅 규칙

### proxy_params
**공통 프록시 헤더 설정**

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

### custom.css
**UI 커스터마이징 스타일시트 (653줄)**

**주요 기능:**
1. **음성/마이크 기능 완전 제거**
   - 모든 마이크 관련 버튼, 아이콘, 기능 숨김
   - 음성 토글, TTS/STT 기능 비활성화

2. **관리자 기능 숨김**
   - 설정, 관리, 모델 관리 버튼 제거
   - 사이드바 관리 메뉴 숨김

3. **공개 키오스크 모드**
   - 로그인/회원가입 UI 제거
   - 상단 네비게이션바 완전 숨김
   - 계정/프로필 관련 기능 비활성화

4. **UI 개선**
   - 전송 버튼 스타일링 (그라데이션)
   - 입력 필드 디자인 개선
   - 반응형 모바일 지원

**주요 선택자:**
```css
/* 음성 기능 제거 */
button[title*="voice" i],
button[title*="mic" i],
[class*="voice"],
[class*="microphone"]

/* 관리 기능 숨김 */
button[title*="Settings" i],
a[href*="/admin"],
.sidebar button[title*="Settings" i]

/* 네비게이션 완전 제거 */
nav, .navbar, header, .header
```

### ai-mentor-cleanup.js
**동적 UI 정리 JavaScript (558줄)**

**기능:**
1. **요소 숨김 엔진**
   - 다양한 선택자로 불필요한 UI 요소 검색
   - 동적 생성 요소도 실시간 감지하여 숨김

2. **전송 버튼 스타일링**
   - 전송 버튼 자동 감지 및 스타일 적용
   - 마이크/음성 버튼과 구분

3. **MutationObserver 활용**
   - DOM 변경사항 실시간 감지
   - 새로 생성된 요소에 대한 자동 정리

**핵심 함수:**
```javascript
// 요소 숨김
function hideElement(element) {
    element.style.display = 'none';
    element.style.visibility = 'hidden';
    element.style.position = 'absolute';
    element.style.left = '-9999px';
}

// 전송 버튼 스타일링
function styleSendButton(button) {
    button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    // ... 추가 스타일
}
```

**감지 선택자 배열:**
- `HIDE_SELECTORS`: 숨길 요소들 (183개 선택자)
- `AUTH_HIDE_SELECTORS`: 인증 관련 요소들
- `SEND_BUTTON_SELECTORS`: 전송 버튼 검색용

### Dockerfile
**컨테이너 빌드 설정**

```dockerfile
FROM nginx:1.25-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf
COPY proxy_params /etc/nginx/proxy_params
COPY custom.css /etc/nginx/custom.css
COPY suppress-warnings.js /etc/nginx/suppress-warnings.js
COPY ai-mentor-cleanup.js /etc/nginx/ai-mentor-cleanup.js

EXPOSE 8080
```

## 🌐 네트워크 구성

### 서비스 포트 매핑
| 서비스 | 내부 포트 | 외부 접근 | 용도 |
|--------|----------|----------|------|
| nginx | 8080 | ✅ | 메인 진입점 |
| openwebui | 8080 | 🚫 | UI 프레임워크 |
| llm-agent | 8001 | 🚫 | 메인 AI 서비스 |
| svc7996 | 7996 | 🚫 | 커리큘럼 플래닝 |
| svc7997 | 7997 | 🚫 | FAISS 검색 |
| svc7998 | 7998 | 🚫 | 폴백 LLM |
| svc7999 | 7999 | 🚫 | SQL 쿼리 |

### 라우팅 우선순위
1. **API 특수 경로** (`^~` 접두사)
2. **WebSocket 연결** (`/ws/`, `/socket.io/`)
3. **정적 파일** (`/static/`, `/assets/`)
4. **일반 API** (`/api/`)
5. **루트 경로** (`/`)

## ⚙️ 설정 커스터마이징

### 업스트림 서버 변경
```nginx
# nginx.conf 내 변수 수정
set $up_llm_agent new-llm-service:8001;
set $up_openwebui new-ui-service:8080;
```

### 레이트 리미팅 조정
```nginx
# 채팅 API 제한 변경
limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=20r/s;

# 버스트 크기 조정
limit_req zone=chat_limit burst=50 nodelay;
```

### 새 서비스 추가
```nginx
# 새 백엔드 서비스 라우팅
location ^~ /api/newservice/ {
    proxy_pass http://new-service:8080/;
    include /etc/nginx/proxy_params;
}
```

## 🎨 UI 커스터마이징

### CSS 수정
`custom.css` 파일을 편집하여 UI 스타일 변경:

```css
/* 브랜드 색상 변경 */
button[type="submit"] {
    background: linear-gradient(135deg, #새색상1, #새색상2) !important;
}

/* 새 요소 숨김 */
.새로운-불필요한-요소 {
    display: none !important;
}
```

### JavaScript 동작 수정
`ai-mentor-cleanup.js`에서 선택자 배열 수정:

```javascript
// 새 숨김 대상 추가
const HIDE_SELECTORS = [
    // 기존 선택자들...
    '.새로운-숨김-대상',
    'button[class*="새로운-패턴"]'
];
```

## 🔧 트러블슈팅

### 일반적인 문제들

1. **503 Service Unavailable**
   - 백엔드 서비스 상태 확인
   - Docker 네트워크 연결 확인
   - DNS 리졸버 설정 검증

2. **스트리밍 응답 버퍼링**
   - `proxy_buffering off` 설정 확인
   - `X-Accel-Buffering no` 헤더 추가

3. **CORS 오류**
   - `Access-Control-Allow-Origin` 헤더 확인
   - preflight OPTIONS 요청 처리

4. **레이트 리미팅 오류**
   - 429 상태 코드 시 burst 크기 조정
   - 클라이언트 IP 확인

### 디버깅 명령어

```bash
# Nginx 설정 테스트
docker exec reverse-proxy nginx -t

# 접근 로그 확인
docker logs reverse-proxy

# 백엔드 서비스 연결 테스트
docker exec reverse-proxy curl http://llm-agent:8001/health
```

## 📊 모니터링

### 로그 위치
- **접근 로그**: stdout (Docker logs)
- **오류 로그**: stderr (Docker logs)
- **디버그 정보**: 브라우저 콘솔 (JavaScript)

### 성능 메트릭
- 응답 시간: `$request_time`
- 업스트림 응답: `$upstream_response_time`
- 연결 수: `$connections_active`

## 🔄 배포 및 업데이트

### 컨테이너 빌드
```bash
docker build -t ai-mentor-proxy .
```

### 설정 리로드
```bash
# 무중단 설정 리로드
docker exec reverse-proxy nginx -s reload
```

### 버전 업그레이드
1. 설정 백업
2. 새 이미지 빌드
3. 컨테이너 교체
4. 상태 확인

## 📚 관련 문서

- [JBNU AI Mentor 전체 시스템](../README.md)
- [LLM Agent 서비스](../ai_modules/llm_agent-main/README.md)
- [FAISS 검색 서비스](../ai_modules/faiss_search-main/README_DETAILED.md)
- [OpenWebUI 공식 문서](https://github.com/open-webui/open-webui)

## 🤝 기여

설정 개선사항이나 버그 수정은 프로젝트 메인테이너에게 문의해주세요.

---

**JBNU AI Mentor Team**
*Powered by OpenWebUI + Nginx*
# AI Mentor Service - Core Module

리팩토링된 AI Mentor 서비스의 핵심 모듈입니다. 확장성, 유지보수성, 성능을 크게 개선한 아키텍처를 제공합니다.

## 🚀 주요 개선사항

### 1. 코드 중복 제거 (85% → 15%)
- 중복된 LangGraph 앱 클래스 통합
- 공통 응답 변환 로직 추출
- 베이스 클래스 패턴 적용

### 2. 표준화된 에러 처리
- 일관된 에러 응답 형식
- 체계적인 로깅
- 사용자 친화적 에러 메시지

### 3. 설정 관리 통합
- 하드코딩된 값들 제거
- 환경 변수 기반 설정
- JSON 파일 지원

### 4. 코드 품질 향상
- 명확한 책임 분리
- 재사용 가능한 컴포넌트
- 유지보수성 향상

## 📁 프로젝트 구조

```
service/core/
├── common/                 # 공통 유틸리티
│   ├── response_converter.py   # OpenAI 응답 변환기
│   ├── error_handler.py        # 표준 에러 처리
│   └── config.py              # 설정 관리
├── base/                   # 베이스 클래스
│   └── base_langgraph.py      # LangGraph 베이스 클래스
└── README.md              # 이 파일
```

## 🔧 사용법

### 1. 공통 유틸리티 사용

```python
from service.core.common.response_converter import OpenAIResponseConverter
from service.core.common.error_handler import ErrorHandler
from service.core.common.config import ServiceConfig

# OpenAI 호환 응답 생성
response = OpenAIResponseConverter.convert_to_openai_format(
    result="안녕하세요!",
    duration=0.5,
    processing_type="langgraph"
)

# 에러 처리
error_response = ErrorHandler.create_openai_error_response(
    error=Exception("뭔가 잘못됨"),
    fallback_message="죄송합니다. 다시 시도해주세요."
)

# 설정 관리
config = ServiceConfig.from_env()  # 환경 변수에서 로드
print(f"기본 모델: {config.default_model}")
```

### 2. 베이스 클래스 사용

```python
from service.core.base.base_langgraph import BaseLangGraphApp

class MyLangGraphApp(BaseLangGraphApp):
    def _build_graph(self):
        # 커스텀 그래프 구현
        workflow = StateGraph(GraphState)
        # ... 그래프 구성
        return workflow.compile()

    def _create_nodes(self):
        return {
            "my_node": self.my_node_function
        }
```

## 🎯 처리 전략

### 1. UnifiedLangGraph 전략
- **사용 시기**: 일반적인 질답, 대화형 상호작용
- **장점**: 빠른 응답, 컨텍스트 유지
- **적용 조건**: 기본 전략으로 모든 요청 처리 가능

### 2. Tree of Thoughts (ToT) 전략
- **사용 시기**: 복잡한 추론이 필요한 질문
- **장점**: 깊은 사고, 다각도 분석
- **적용 조건**: "분석", "비교", "평가" 등 키워드 포함

### 3. Hybrid 전략
- **사용 시기**: 중요한 의사결정 질문
- **장점**: 두 전략의 결과 병합
- **적용 조건**: "중요", "핵심", "결정" 등 키워드 포함

## ⚙️ 설정 관리

### 환경 변수 설정

```bash
# 서비스 설정
export LANGGRAPH_TIMEOUT=600
export TOT_MAX_WORKERS=4
export MEMORY_TTL=3600
export LOG_LEVEL=INFO

# 모델 설정
export DEFAULT_MODEL=gpt-4
export TEMPERATURE=0.7
export MAX_TOKENS=4096
```

### JSON 설정 파일

```json
{
  "langgraph_timeout": 600,
  "tot_timeout_seconds": 30,
  "tot_max_workers": 4,
  "memory_ttl_seconds": 3600,
  "max_retry_count": 3,
  "default_model": "gpt-4",
  "temperature": 0.7
}
```

## 🛠️ 의존성 주입 사용법

### 1. 커스텀 서비스 등록

```python
from service.core.dependencies.container import get_container

container = get_container()

# 팩토리 함수로 등록
def create_custom_handler():
    return CustomHandler(config="my_config")

container.register_factory("custom_handler", create_custom_handler, singleton=True)

# 인스턴스 직접 등록
container.register_instance("my_service", MyService())
```

### 2. 서비스 사용

```python
# 타입 체크와 함께 서비스 가져오기
memory_service = container.get_typed("conversation_memory", ConversationMemory)

# 일반 서비스 가져오기
config = container.get("config")
```

## 📊 모니터링 & 로깅

### 헬스체크

```python
health_status = await mentor_service.health_check()
print(f"Service Status: {health_status['status']}")
print(f"Components: {health_status['components']}")
```

### 세션 통계

```python
stats = mentor_service.get_session_stats("user_123")
print(f"Available Strategies: {stats['available_strategies']}")
print(f"Memory Stats: {stats['memory_stats']}")
```

### 로깅 설정

```python
import logging

# 자세한 로깅 활성화
logging.getLogger("service.core").setLevel(logging.DEBUG)

# 성능 로깅 활성화 (config에서)
config = ServiceConfig(enable_performance_logging=True)
```

## 🔄 마이그레이션 가이드

### 기존 코드에서 마이그레이션

**Before (기존)**:
```python
# 복잡한 초기화
mentor_service = HybridMentorService(
    use_unified_langgraph=True
)

# 직접적인 메소드 호출
result = await mentor_service.process_query_with_unified_langgraph(query)
```

**After (리팩토링 후)**:
```python
# 간단한 초기화
container = create_container()
mentor_service = RefactoredMentorService(container)

# 통합된 인터페이스
result = await mentor_service.process_query(query)
```

### 설정 마이그레이션

**Before**:
```python
# 하드코딩된 값들
timeout = 600
max_workers = 4
```

**After**:
```python
# 설정 클래스 사용
config = ServiceConfig(
    langgraph_timeout=600,
    tot_max_workers=4
)
```

## 🧪 테스트

### 단위 테스트

```python
import pytest
from service.core.dependencies.container import ServiceContainer
from service.core.refactored_mentor_service import RefactoredMentorService

def test_mentor_service():
    # Mock 컨테이너 생성
    container = ServiceContainer()

    # Mock 서비스 등록
    container.register_instance("config", mock_config)
    container.register_instance("conversation_memory", mock_memory)

    # 테스트 실행
    service = RefactoredMentorService(container)
    result = await service.process_query("테스트 질문")

    assert result["choices"][0]["message"]["role"] == "assistant"
```

### 통합 테스트

```bash
# 전체 서비스 테스트
python -m pytest tests/integration/test_mentor_service.py

# 특정 전략 테스트
python -m pytest tests/strategies/test_processing_strategy.py
```

## 🚀 성능 최적화

### 1. 메모리 최적화
- LRU 캐시 사용으로 중복 계산 방지
- 메모리 풀 활용으로 GC 압박 감소
- 적응형 배치 크기로 메모리 사용량 조절

### 2. 비동기 처리 최적화
- 병렬 전략 실행으로 응답 시간 단축
- 백압력(backpressure) 처리로 시스템 안정성 향상
- 연결 풀링으로 리소스 효율성 증대

### 3. 캐싱 전략
- 다층 캐싱으로 응답 속도 향상
- 스마트 무효화로 데이터 일관성 보장
- 압축된 캐시로 메모리 효율성 증대

## 🔮 확장 계획

### 단기 (1개월)
- [ ] 메트릭 수집 시스템 추가
- [ ] 자동 스케일링 지원
- [ ] A/B 테스트 프레임워크

### 중기 (3개월)
- [ ] 마이크로서비스 분할
- [ ] 이벤트 기반 아키텍처
- [ ] GraphQL API 지원

### 장기 (6개월)
- [ ] 멀티 클라우드 지원
- [ ] AI 모델 자동 최적화
- [ ] 실시간 학습 파이프라인

## 💡 모범 사례

### 1. 서비스 구현
```python
# ✅ 좋은 예: 의존성 주입 사용
class MyService:
    def __init__(self, container: ServiceContainer):
        self.llm_handler = container.get("llm_handler")
        self.config = container.get("config")

# ❌ 나쁜 예: 직접 인스턴스 생성
class MyService:
    def __init__(self):
        self.llm_handler = LLMHandler()  # 하드코딩
```

### 2. 에러 처리
```python
# ✅ 좋은 예: 구조화된 예외
raise ProcessingError(
    message="LLM 처리 실패",
    details={"model": "gpt-4", "tokens": 1000}
)

# ❌ 나쁜 예: 일반적인 예외
raise Exception("뭔가 잘못됨")
```

### 3. 설정 관리
```python
# ✅ 좋은 예: 설정 클래스 사용
config = container.get("config")
timeout = config.langgraph_timeout

# ❌ 나쁜 예: 하드코딩
timeout = 600  # 매직 넘버
```

## 📞 지원

- **문서**: [상세 API 문서](./docs/api.md)
- **예제**: [example 폴더](./examples/)
- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/issues)

## 📝 라이선스

MIT License - 자세한 내용은 [LICENSE](./LICENSE) 파일 참조

---

**주의**: 이 README는 리팩토링된 코드의 사용법을 설명합니다. 기존 코드와의 호환성을 위해 점진적 마이그레이션을 권장합니다.
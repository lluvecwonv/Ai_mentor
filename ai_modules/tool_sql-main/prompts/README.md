# 📝 프롬프트 관리

이 폴더는 SQL 에이전트에서 사용하는 프롬프트들을 txt 파일로 관리합니다.

## 📁 파일 구조

```
prompts/
├── sql_system_prompt.txt      # SQL 에이전트 시스템 프롬프트
├── sanitize_prompt.txt        # 질문 세니타이징 프롬프트
└── README.md                  # 이 파일
```

## 🔧 사용 방법

### 1. 프롬프트 로드
```python
from util.prompt_loader import PromptLoader

loader = PromptLoader()

# SQL 시스템 프롬프트 로드
sql_prompt = loader.load_sql_system_prompt()

# 세니타이징 프롬프트 로드
sanitize_prompt = loader.load_sanitize_prompt()
```

### 2. 프롬프트 수정
- 각 txt 파일을 직접 편집하여 프롬프트 수정
- 서버 재시작 없이 실시간 반영 가능
- 버전 관리 시스템으로 프롬프트 변경 이력 추적 가능

### 3. 새 프롬프트 추가
1. `prompts/` 폴더에 새 txt 파일 생성
2. `util/prompt_loader.py`에 로드 메서드 추가
3. 필요한 곳에서 프롬프트 사용

## 📋 프롬프트 목록

- **sql_system_prompt.txt**: LangChain SQL 에이전트용 시스템 프롬프트
- **sanitize_prompt.txt**: 사용자 질문 정제용 프롬프트

## ⚠️ 주의사항

- 파일 인코딩은 UTF-8로 저장
- 프롬프트 수정 시 문법 오류 주의
- 테스트 후 배포 권장

# Antigravity Development Rules & Skills
## Lesson Plan Automation App

---

## 1. 코딩 및 구조 룰 (Coding Standards)
- **모듈화 원칙**: 단일 책임 원칙(SRP)에 따라 기능을 파일별/클래스별로 엄격히 분리합니다.
  - `auth.py`: Google API 인증 관리 (OAuth / Service Account)
  - `drive_scanner.py`: 폴더 및 파일 탐색
  - `docs_parser.py`: Google Docs 표 데이터 추출 및 주차 판별
  - `notifier.py`: 미제출자 대상 Gmail 발송
  - `main.py`: 전체 흐름 제어 및 CLI/오케스트레이션
- **타입힌팅 및 문서화**: 모든 함수와 클래스에 Python Type Hints 및 Docstring을 작성합니다.
- **예외 처리**: 외부 API 호출 시 발생할 수 있는 `HttpError`, `RateLimitExceeded`, `Timeout` 등을 반드시 캐치하고 로깅(`logging` 모듈)합니다.

---

## 2. 필수 기술 스택 및 라이브러리 (Required Skills & Dependencies)
- `google-api-python-client`: 구글 드라이브 및 문서 API 조작
- `google-auth-oauthlib`, `google-auth-httplib2`: 인증 처리
- `python-dotenv`: 환경 변수 관리 (`.env`)
- `jinja2` (선택): 이메일 템플릿 렌더링용

---

## 3. API 사용 및 보안 룰 (Security & API Guidelines)
- **자격 증명 관리**: `credentials.json` 및 `token.json` 파일은 절대 Git에 커밋하지 않으며 `.gitignore`에 등록합니다.
- **API Quota 관리**: 100개 이상의 문서를 순회할 때 API Quota Limit에 걸리지 않도록 적절한 지연(`time.sleep`) 또는 배치 요청을 고려합니다.
- **읽기 전용 우선 원칙**: 교사들의 문서는 원칙적으로 **읽기(Read-only)** 권한으로만 접근하여 실수로 원본이 손상되는 것을 방지합니다.
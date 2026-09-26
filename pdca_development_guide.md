# PDCA Execution Plan
## Lesson Plan Automation App Development Framework

---

## 1. Plan (계획 단계)
- [x] 사용자 요구사항 정의 (100개 Google Docs 자동 점검 및 미제출자 메일 발송)
- [x] PRD 작성 및 시스템 아키텍처 설계 (`prd.md`)
- [ ] Google Cloud Console 프로젝트 생성 및 API 활성화 (Google Drive API, Google Docs API, Gmail API)
- [ ] OAuth 2.0 클라이언트 ID 및 자격 증명 파일(`credentials.json`) 발급 계획 수립

---

## 2. Do (실행 및 구현 단계)
- **Step 1: 인증 및 연결 모듈 구현**
  - 구글 API 인증 토큰 발급 및 세션 유지 로직 작성 (`auth.py`)
- **Step 2: 구글 드라이브 폴더 스캐너 구현**
  - 루트 폴더 ID를 입력받아 하위 교사 폴더 및 Lesson Plan 문서 ID 매핑 기능 구현 (`drive_scanner.py`)
- **Step 3: Google Docs 파서 및 검증 엔진 구현**
  - 문서 내 테이블 파싱, 첫 번째 행의 날짜/주차 추출, 이번 주 업데이트 여부 판별 로직 구현 (`docs_parser.py`)
- **Step 4: 메일 알림 모듈 구현**
  - 미제출 교사 이메일 주소 추출 및 Gmail API를 통한 독촉 메일 자동 발송 구현 (`notifier.py`)
- **Step 5: 통합 실행 스크립트 구현**
  - `main.py`를 통해 전체 파이프라인 연결 및 실행 로그 출력

---

## 3. Check (검증 및 테스트 단계)
- **단위 테스트 (Unit Testing)**:
  - 가상의 Google Docs 템플릿 구조를 Mocking하여 파서가 주차를 정확히 인식하는지 테스트.
- **통합 테스트 (Integration Testing)**:
  - 테스트용 구글 폴더 및 문서를 생성하여 실제 Drive API 및 Docs API 연동 테스트 수행.
- **예외 상황 테스트**:
  - 권한이 없는 문서, 비어 있는 문서, 템플릿 형식이 어긋난 문서가 존재할 때 프로그램이 중단되지 않고 예외 처리를 수행하는지 검증.

---

## 4. Act (조치 및 운영 개선 단계)
- **피드백 반영 및 리팩토링**:
  - 테스트 과정에서 발견된 API Quota 이슈나 날짜 포맷 파싱 오류 수정.
- **운영 자동화 (Cron / Task Scheduler)**:
  - 매주 월요일 오전 등 정해진 시간에 자동으로 스크립트가 실행되도록 OS 스케줄러(Cron 또는 Task Scheduler) 연동 가이드 작성.
- **고도화**:
  - 추후 웹 UI(Streamlit 등)를 얹어 교감 선생님이 버튼 클릭 한 번으로 현황을 시각적으로 확인할 수 있도록 확장.
```

I have successfully generated the PRD, development rules and skills, and the PDCA execution guide in Markdown file blocks. You can now use these files directly in Antigravity to build your Lesson Plan automation app step-by-step. Let me know if you need help with any specific module code!
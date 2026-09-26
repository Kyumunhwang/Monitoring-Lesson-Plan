# 📋 Monitoring Lesson Plan

**Google Docs & Sheets Lesson Plan Auto-Monitor & Rollover Detection System**

교감 선생님과 학교 관리자를 위한 **수업계획서 자동 모니터링, 다중 주차 제출 현황 매트릭스 추적, 공휴일 이월 수업(복사본) 감지 및 Gmail 독촉 알림 자동화 시스템**입니다.

---

## 🌟 핵심 기능 (Key Features)

1. **Google Docs & Sheets 전 과목 통합 스캔**:
   - 국어, 수학, 영어, 과학, 사회/역사, 컴퓨터, 중국어, 선택과목 등 전 과목 커리큘럼 계획서(51개 $\rightarrow$ 정규 48개) 자동 탐색.
   - Google Docs(문서 내 다중 차시 테이블) 및 Google Sheets(스프레드시트) 동시 지원.
2. **공휴일 이월(Rollover) 및 복사본 정밀 감지**:
   - 최신 차시와 직전 차시 간 **교육 활동 본문 텍스트 유사도(SequenceMatcher)** 산출.
   - 날짜는 이번 주로 변경되었으나 본문이 80% 이상 일치하는 경우 `ROLLOVER (공휴일 이월 / 복사본)`으로 자동 분류하여 관리자 확인 지원.
3. **주차별 달성률 매트릭스 & 문서 바로가기 링크**:
   - 최근 4개 주차별 제출 추이(✅ Submitted, ⚠️ Rollover, ❌ Missing)를 한눈에 파악.
   - 각 교사의 계획서를 새 탭에서 즉시 열어볼 수 있는 **`Open Plan ↗`** 하이퍼링크 제공.
4. **Google Sheets 양방향 자동 동기화**:
   - 스캔 결과를 지정된 구글 스프레드시트에 `=HYPERLINK(...)` 수식과 함께 실시간 자동 기록.
5. **독촉 이메일 실시간 편집기 (Custom Notice Composer)**:
   - 교감 선생님이 원하는 맞춤 공지 문구를 대시보드에서 직접 수정하여 미제출 교사에게 Gmail API로 일괄 발송.
   - 사전 서식 확인을 위한 **`Send Test Email to Me`** 즉시 테스트 기능 및 안전 발송 모드(`Dry Run` vs `Live Send`) 탑재.
6. **모바일 웹 앱(PWA) 지원**:
   - 스마트폰(iOS 사파리 / Android 크롬)에서 홈 화면에 추가 시 **`Monitoring Lesson Plan`** 앱 이름으로 설치되어 모바일 네이티브 앱처럼 사용 가능.

---

## 🚀 빠른 시작 (Getting Started)

### 1. 필수 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 설정 (.env)
`.env.example`을 복사하여 `.env` 파일을 생성하고 드라이브 및 시트 ID를 입력합니다:
```env
GOOGLE_OAUTH_CREDENTIALS=credentials.json
GOOGLE_TOKEN_PATH=token.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_drive_root_folder_id
GOOGLE_TARGET_SPREADSHEET_ID=your_google_sheet_id
SENDER_EMAIL=me
```

### 3. 웹 대시보드 실행
```bash
python -m streamlit run app.py --server.port 3085
```
브라우저에서 `http://localhost:3085`로 접속하여 **`🚀 Run Verification Scan`** 버튼을 클릭합니다.

---

## 📱 모바일 홈 화면 추가 (Mobile Web App)

* **아이폰 (iOS Safari)**:
  1. 배포된 대시보드 URL 접속
  2. 하단 중앙 **[공유 버튼]** $\rightarrow$ **[홈 화면에 추가 (Add to Home Screen)]**
  3. 자동으로 **`Monitoring Lesson Plan`** 이름으로 홈 화면에 아이콘 생성.
* **안드로이드 (Android Chrome)**:
  1. 배포된 대시보드 URL 접속
  2. 우측 상단 **[더보기(점 3개)]** $\rightarrow$ **[홈 화면에 추가 / 앱 설치]**

---

## ☁️ Streamlit Community Cloud 배포 방법

1. GitHub 리포지토리(`Kyumunhwang/Monitoring-Lesson-Plan`) 생성 후 코드 푸시.
2. [share.streamlit.io](https://share.streamlit.io/) 접속 후 본 리포지토리 선택.
3. **App settings** $\rightarrow$ **Secrets** 메뉴에 `credentials.json` 내용과 환경변수 설정 추가.

---

## 🔒 보안 (Security & Quota)
* `credentials.json`, `token.json`, `.env` 등 민감한 개인정보 및 토큰 파일은 `.gitignore`에 등록되어 GitHub에 절대 업로드되지 않습니다.
* 모든 Google Docs 및 Drive 접근은 원본 훼손 방지를 위해 **읽기 전용(Read-only)** 권한으로 동작합니다.

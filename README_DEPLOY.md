# 🚀 Streamlit Community Cloud 배포 가이드 (Windows 10/11)

이 가이드는 **파이썬 설치, streamlit 설치, ngrok 설치가 전혀 필요 없습니다.**
PC는 코드를 GitHub에 올리는 용도로만 쓰고, 실제 앱은 Streamlit 서버가 돌립니다.
결과: `https://내앱이름.streamlit.app` 영구 URL이 생기고 어디서나 접속 가능.

---

## STEP 1. GitHub 계정 만들기 (3분)

1. 브라우저에서 https://github.com/signup 열기
2. 이메일 → 비밀번호 → 사용자명 입력 (사용자명은 영문 소문자 추천, 예: `hong-site-safety`)
3. 이메일 인증 코드 입력 → 완료
4. **중요**: 왼쪽 상단 `+` → `New repository` 클릭
   - Repository name: `dashboard-v6`
   - Public 선택 (무료 Streamlit Cloud는 Public 저장소만 지원 — 민감정보는 들어있지 않으므로 OK)
   - "Add a README file" 체크 안 함
   - `Create repository` 클릭

지금 뜬 화면의 URL (예: `https://github.com/hong-site-safety/dashboard-v6`) 을 메모해두세요.

---

## STEP 2. GitHub Desktop으로 코드 업로드 (5분)

### 2-1. 설치
1. https://desktop.github.com 접속 → **"Download for Windows"** 클릭
2. 다운받은 `GitHubDesktopSetup.exe` 더블클릭 → 설치 (관리자 권한 필요 없음)
3. 설치 후 자동 실행 → `Sign in to GitHub.com` 클릭 → STEP 1에서 만든 계정으로 로그인

### 2-2. 저장소 복제
1. GitHub Desktop 상단: `File` → `Clone repository`
2. `URL` 탭에서 STEP 1의 URL 붙여넣기 (예: `https://github.com/hong-site-safety/dashboard-v6`)
3. `Local path`: 그대로 두거나 바탕화면 등 원하는 위치 지정
4. `Clone` 클릭 → 빈 폴더가 PC에 생성됨 (예: `C:\Users\내이름\Documents\GitHub\dashboard-v6`)

### 2-3. 파일 복사
1. 압축 푼 `dashboard_v6` 폴더를 엽니다
2. 폴더 **내용물 전체** (app.py, worker_app.py, worker_data.py, worker_styles.py, requirements.txt, README.md, data 폴더, .streamlit 폴더 등) 를 복사
3. 2-2에서 만들어진 `dashboard-v6` 폴더 안에 그대로 붙여넣기
   - ⚠️ `dashboard_v6` 폴더 자체를 통째로 넣지 말고 **내용물만** 넣기 (app.py가 최상단에 있어야 함)

### 2-4. 업로드 (커밋 + 푸시)
1. GitHub Desktop 화면 왼쪽 아래에서:
   - `Summary` 칸에 아무거나 입력 (예: `초기 커밋`)
   - `Commit to main` 버튼 클릭
2. 상단의 `Push origin` 버튼 클릭 → 몇 초 기다리기
3. 브라우저에서 STEP 1 저장소 URL 새로고침 → 파일들이 올라와 있으면 성공 ✅

---

## STEP 3. Streamlit Community Cloud 배포 (3분)

1. https://share.streamlit.io 접속
2. `Continue with GitHub` 클릭 → STEP 1 계정으로 로그인 → 권한 승인(Authorize)
3. 오른쪽 상단 `Create app` → **"Deploy a public app from GitHub"** 선택
4. 입력:
   - **Repository**: `본인계정명/dashboard-v6` 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL** (하단): 원하는 이름 입력 (예: `site-safety-dashboard`) → URL 미리보기 확인
5. 오른쪽 아래 `Deploy` 클릭
6. 1~3분 대기 — 로그에 `You can now view your Streamlit app in your browser` 가 뜨면 완료
7. 상단 주소창에 뜬 URL (예: `https://site-safety-dashboard.streamlit.app`) 이 **영구 URL**

---

## STEP 4. 폰에서 접속

1. 폰 브라우저에 위 URL 입력 (Wi-Fi든 LTE든 상관없음)
2. 근로자 계정 로그인: `sokcho01` / `1234`
3. 자동으로 모바일 레이아웃(하단 탭 4개) 노출 ✅

### 홈 화면에 아이콘으로 저장 (앱처럼 쓰기)
- **iPhone (Safari)**: 하단 공유 버튼 → `홈 화면에 추가`
- **Android (Chrome)**: 우상단 ⋮ → `홈 화면에 추가`

---

## ⚠️ 배포 실패 시 체크리스트

Streamlit Cloud 로그 화면 하단에 에러가 뜹니다. 가장 흔한 것:

| 에러 | 원인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: xlrd` | requirements.txt 안 올라감 | GitHub 저장소에 requirements.txt 있는지 확인 |
| `FileNotFoundError: data/2018.xls` | data 폴더 안 올라감 | GitHub Desktop에서 data 폴더 보이는지 확인, 안 보이면 다시 복사 후 커밋+푸시 |
| `app.py not found` | Main file path 오타 | 설정에서 `app.py` 로 수정 |
| 앱은 뜨는데 메일 발송 실패 | `gsk gmail send_email` 은 로컬 전용 | 메일 발송만 실패, 문의는 JSON에 저장됨 (정상 동작) |

---

## 수정 후 재배포 하는 법

코드를 수정하면 그냥:
1. GitHub Desktop 켜기 → 변경된 파일이 자동으로 보임
2. Summary 입력 → `Commit to main` → `Push origin`
3. Streamlit Cloud가 1~2분 안에 자동으로 재배포

**끝.** 매번 배포 설정을 다시 할 필요 없습니다.

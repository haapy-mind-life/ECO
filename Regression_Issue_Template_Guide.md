
# 🧩 Regression Issue Summary Template — LLM 활용용 상세 가이드

## 🧾 1. 표 구조 정의 (최종 버전)

| DATE | MODEL | TEST TYPE | TEST LOCATION | COUNTRY | ISSUE SUMMARY | CATEGORY | PATCH STATUS | STATUS | NOTE |
|------|--------|------------|----------------|----------|----------------|-----------|---------------|---------|-------|

## 🧠 2. 필드별 상세 정의 및 입력 규칙

| 필드명 | 데이터 타입 | 입력 예시 | 정의 및 규칙 |
|---------|--------------|------------|----------------|
| **DATE** | `YYYY-MM-DD` | 2025-11-10 | 테스트 수행일. 날짜 포맷 통일 필수 |
| **MODEL** | `문자열` | FMW_1.3 / APP_v2.0 | 테스트 대상 모델명 또는 빌드 버전 |
| **TEST TYPE** | `문자열` | Regression / Field / Performance / Smoke / Integration | 테스트 유형을 지정 |
| **TEST LOCATION** | `문자열` | Internal / Vendor / Field / Lab / Customer Site | 테스트 수행 장소 또는 형태 (내부/외부/현장 등) |
| **COUNTRY** | `문자열` | Korea / Poland / India / Vietnam | 테스트가 수행된 국가 |
| **ISSUE SUMMARY** | `문자열` | “Dashboard KPI Delay” / “Login Timeout” | 이슈 핵심 요약 (한 줄) |
| **CATEGORY** | `문자열` | Functional / Performance / Infra / UI / Config | 이슈 유형 구분 |
| **PATCH STATUS** | `문자열` | Not Ready / Ready / Applied / Verified | 패치 진행 단계 |
| **STATUS** | `문자열` | PASS / FAIL / RETEST / BLOCK | 테스트 결과 상태 |
| **NOTE** | `문자열` | “Recheck after patch”, “3s delay remains” | 보충 설명 또는 후속 메모 |

## ⚙️ 3. LLM용 프롬프트 세트

### 🧩 [프롬프트 ①] 신규 이슈 등록 자동 생성

```
너는 Regression Issue Sheet 관리 전문가야.  
아래 자연어 설명을 표 구조에 맞춰 자동 변환해줘.  
모든 필드는 반드시 채우되, 모르는 값은 “-” 로 남겨.

출력은 Markdown 표 형식으로, 컬럼 순서는 다음과 같아:
DATE | MODEL | TEST TYPE | TEST LOCATION | COUNTRY | ISSUE SUMMARY | CATEGORY | PATCH STATUS | STATUS | NOTE

예시 입력:
"11월 10일 FMW_1.3 버전에서 벤더 테스트 중 폴란드 현장에서 KPI 로딩 지연 발생. 아직 패치 준비 안됨."

예시 출력:
| DATE | MODEL | TEST TYPE | TEST LOCATION | COUNTRY | ISSUE SUMMARY | CATEGORY | PATCH STATUS | STATUS | NOTE |
|------|--------|------------|----------------|----------|----------------|-----------|---------------|---------|-------|
| 2025-11-10 | FMW_1.3 | Regression | Vendor | Poland | KPI loading delay | Performance | Not Ready | FAIL | Awaiting patch |
```

### 🧩 [프롬프트 ②] 일일 리포트 요약 자동 생성

```
아래 Regression Issue Summary 표를 분석하여  
1) FAIL / RETEST 항목 요약  
2) CATEGORY별 주요 원인 3가지  
3) 패치 진행 현황(PATCH STATUS) 분포  
4) 개선 우선순위 제안  
을 구조적으로 요약하라.
```

### 🧩 [프롬프트 ③] 상태 기반 자동 분류

```
아래 Regression Issue Summary 표를 읽고  
- STATUS가 FAIL 또는 RETEST인 행만 필터링  
- CATEGORY별로 그룹화  
- PATCH STATUS가 Not Ready인 항목은 "Pending Fix"로 라벨링하여 표로 재정렬하라.
```

## 📊 4. LLM 통합 자동화 예시

1️⃣ QA Engineer가 자연어로 입력  
→ “벤더 테스트 중 폴란드에서 알람 전송 지연, 패치 아직 미적용”  
2️⃣ LLM이 표 생성  
→ 위 구조의 Markdown Row 자동 추가  
3️⃣ PLM-BOT이 Fail 항목만 요약  
→ 슬랙/메일로 일일 리포트 발송  
4️⃣ Dashboard 연동  
→ Patch Status 분포 자동 그래프화

## 📘 5. 샘플 데이터 (20건)

| DATE | MODEL | TEST TYPE | TEST LOCATION | COUNTRY | ISSUE SUMMARY | CATEGORY | PATCH STATUS | STATUS | NOTE |
|------|--------|------------|----------------|----------|----------------|-----------|---------------|---------|-------|
| 2025-11-10 | FMW_1.3 | Regression | Internal | Korea | OTP Verification fails randomly | Functional | Verified | PASS | Stable after patch |
| 2025-11-10 | FMW_1.3 | Regression | Vendor | Poland | Dashboard KPI load delay | Performance | Not Ready | FAIL | 3s latency observed |
| 2025-11-10 | FMW_1.3 | Smoke | Internal | Korea | Config sync not applied | Configuration | Verified | PASS | OK |
| 2025-11-10 | FMW_1.3 | Integration | Field | India | CSV export timeout over 100MB | Functional | Ready | FAIL | Needs optimization |
| 2025-11-10 | FMW_1.3 | Regression | Vendor | Poland | Push alert delayed >10s | Infra | Applied | RETEST | Monitor again after patch |
| 2025-11-09 | FMW_1.3 | Regression | Internal | Korea | Password reset mail not sent | Functional | Verified | PASS | Stable |
| 2025-11-09 | FMW_1.3 | Performance | Vendor | Korea | ETL batch delay >5min | Performance | Not Ready | FAIL | Re-run planned |
| 2025-11-09 | FMW_1.3 | Regression | Internal | Poland | Role permission not updating | Functional | Verified | PASS | OK |
| 2025-11-09 | FMW_1.3 | Integration | Field | India | System restore memory leak | Functional | Applied | FAIL | Patch in QA |
| 2025-11-09 | FMW_1.3 | Regression | Internal | Korea | Real-time graph freeze | Functional | Verified | PASS | - |
| 2025-11-08 | FMW_1.3 | Performance | Vendor | Poland | Network RTT high (>200ms) | Infra | Not Ready | FAIL | Under ISP review |
| 2025-11-08 | FMW_1.3 | Regression | Internal | India | SMS 2FA verification fine | Functional | Verified | PASS | OK |
| 2025-11-08 | FMW_1.3 | Regression | Vendor | Korea | PDF export font missing | Functional | Ready | FAIL | Font patch pending |
| 2025-11-08 | FMW_1.3 | Performance | Vendor | Poland | Dashboard memory spike | Performance | Applied | FAIL | Retest after patch |
| 2025-11-07 | FMW_1.3 | Regression | Internal | India | System audit log incomplete | Functional | Verified | PASS | OK |
| 2025-11-07 | FMW_1.3 | Integration | Vendor | Korea | Email alert timeout (SMTP) | Functional | Ready | FAIL | Increase retry interval |
| 2025-11-07 | FMW_1.3 | UI | Internal | Poland | Login screen misaligned | UI/UX | Verified | PASS | Fixed |
| 2025-11-07 | FMW_1.3 | Regression | Vendor | Korea | Dark mode not applied | UI/UX | Verified | PASS | OK |
| 2025-11-07 | FMW_1.3 | Performance | Field | India | Trend chart inaccurate | Performance | Applied | FAIL | Formula fix needed |
| 2025-11-07 | FMW_1.3 | Regression | Internal | Korea | Auto backup schedule passed | Functional | Verified | PASS | - |

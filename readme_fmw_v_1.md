# 🌐 Feature Monitoring Web (FMW)
### — Unified Project Overview · v1.0 (2025-11-05)

> **Feature Monitoring Web (FMW)** 은  
> 사내 단말 Feature 정책 데이터를 **자동 수집·통합·시각화**하는 내부 플랫폼입니다.  
> 단순한 데이터베이스가 아닌, “정책 변화의 흐름을 관찰하는 창(Window)”이 되는 것을 목표로 합니다.

---

## 1️⃣ 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | Feature Monitoring Web (FMW) |
| **핵심 목적** | Feature 정책 자동 수집, 통합 관리, 시각화 |
| **운영 환경** | Windows Server (내부망) |
| **구성요소** | **NGINX (보안 게이트웨이)** · Django (Backend) · Streamlit (Dashboard) · Static Portal (사내 소개 페이지) |
| **팀 구성** | 3명 (리더 · Backend · Frontend / 유동적 역할) |
| **보안정책** | 외부 API, GPT 코드, 클라우드 연동 금지 · 내부망 전용 운영 |

---

## 2️⃣ 시스템 구조

```
project-root/
├─ django/         → Backend (DB, API, 동기화)
├─ streamlit/      → Dashboard (시각화)
├─ static_portal/  → 사내 소개용 정적 페이지
├─ config/         → 환경 및 로깅 설정 / NGINX 템플릿 포함
├─ utils/          → 공용 스크립트 / 파서
├─ docs/           → 문서 / 협업 자료
├─ logs/           → 실행 로그 (Git 제외)
└─ *.bat, manage.py, requirements.txt, README.md
```

### 🔐 NGINX 역할
- **1차 보안 게이트웨이** : 모든 API / Dashboard 요청은 NGINX 통과 후 허용  
- **IP Allow List** : 팀별 / 운영자 / 벤더 IP를 그룹별 관리  
- **Phase 2 예정 : SSO (사내 인증 연동)** — SSO 토큰을 기반으로 API Key 인증 대체 예정  

---

## 3️⃣ 주요 동작 흐름

1. 각 **브랜치 코드**가 사내 API를 통해 Feature 데이터 자동 수집  
2. 파싱된 데이터를 `features` 테이블(v1)에 저장  
3. `mcc`, `mnc`, `region`, `country`, `operator`, `sp_fci` 등 메타 정보를 upsert  
4. `sync.bat` 또는 Windows Task Scheduler (매일 06:00 KST)로 자동 동기화  
5. Streamlit 대시보드에서 Feature 현황 및 정책 변동을 시각화  

> 모든 데이터는 **내부망 내부 순환**이며 외부 연동 없음.  

---

## 4️⃣ 실행 요약 (Windows 전용)

### ⚙️ 환경 준비
```bash
python -m venv .venv
.\.venv\\Scripts\\activate
pip install -r requirements.txt
```

### ▶️ 운영 스크립트
| 스크립트 | 설명 |
|-----------|------|
| `start.bat` | Django + Streamlit + NGINX 시작 |
| `stop.bat` | 모든 서비스 종료 |
| `reset.bat` | DB 및 캐시 초기화 |
| `setup.bat` | 초기 환경 세팅 (venv, 설치, migrate) |
| `sync.bat` | 수동 동기화 실행 (자동 스케줄러 대체 가능) |

> Windows 환경 기준. Linux 배포 시 PowerShell → Bash 변환 필요.  

---

## 5️⃣ 데이터 모델 구조 (개선 중)

> **v1** 단일 기준으로 정리 중이며, 기타 모델은 `dev` 그룹으로 통합 중입니다.  

| 그룹 | 테이블 | 설명 |
|------|---------|------|
| **v1** | `features`, `rel_features`, `as_rel`, `ue_capa` | Feature 정책 및 관계 핵심 모델 |
| **dev** | `allowlist`, `blocklist`, `name_map`, `mcc_mnc_map`, `req_log`, `sync_history`, `change_history`, `err_log` | 운영/감사 및 보조 데이터 |

---

## 6️⃣ API 개요

| 구분 | 설명 | 접근 정책 |
|------|------|------------|
| `/api/v1/*` | 일반 조회용 API (Streamlit 및 내부 조회) | Allowlist IP |
| `/api/dev/*` | 운영자/벤더 API | 운영자 Allowlist + Key 인증 |

> 모든 API 요청은 NGINX 를 통해 Allowlist 검증 후 처리됩니다.  
> Phase 2에서 SSO 연동 도입 예정 (사내 SSO → JWT 토큰 전달 → DRF Auth 적용).  

---

## 7️⃣ 보안 정책 요약

- 외부 API, GPT 코드, 클라우드 연동 **금지**  
- NGINX IP Allowlist 기반 보안 게이트 운용  
- 운영자 API는 **Key + IP** 이중 인증  
- SSO Phase 2 준비 (사내 토큰 인증 체계 적용 예정)  
- 로그에는 개인/민감 데이터 저장 금지  
- `.gitignore` 필수 항목:  
  ```
  logs/
  static_portal/dist/
  .streamlit/
  .venv/
  *.log
  ```

---

## 8️⃣ static_portal (사내 소개 페이지)

> FMW의 철학과 가치를 담은 정적 포털 페이지입니다.  
> 기술보다 “왜 이 시스템이 필요한가”에 집중합니다.  

### 💡 주요 메시지
- **Why FMW?** “복잡한 Feature 관리, 이제 한 곳에서.”  
- **How It Helps** : 브랜치별 정책 비교, 자동 동기화, 직관적 대시보드.  
- **What’s Next** : Phase 2 → SSO + 운영자동화 + Policy Audit 대시보드.  

---

## ✅ 핵심 요약

| 항목 | 내용 |
|------|------|
| **시스템명** | Feature Monitoring Web (FMW) |
| **핵심 목적** | Feature 정책 자동 수집 · 통합 · 시각화 |
| **구성요소** | NGINX · Django · Streamlit · Static Portal |
| **데이터 모델** | v1 (핵심) / dev (보조) |
| **운영 방식** | `.bat` 기반 실행 및 스케줄링 |
| **보안 원칙** | Allowlist 기반 내부망 전용 · SSO Phase 2 예정 |
| **문서 정책** | 단일 README 중심 관리 · `docs/` 보조 |

---

📅 **최종 업데이트:** 2025-11-05  
✍️ **작성자:** FMW Documentation Team  
© 2025 Feature Monitoring Web — Internal Use Only


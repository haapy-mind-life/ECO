# 📘 FMW README 개선 프로젝트 (최신 버전 2025‑11‑05)

---

## 🧭 프로젝트 배경 요약
| 항목 | 내용 |
|------|------|
| **서버 OS** | Windows 기반 서버 PC |
| **팀 구성** | 개발자 3명 (Project 리더, Backend, Frontend — 역할은 유동적) |
| **보안 제한** | 외부 API / GPT 코드 직접 사용 불가 |
| **활용 방식** | GPT는 문서 초안·설계·가이드용으로만 사용 |
| **문제점** | 실행 환경 불일치, 정보 공유 단절, 버전 관리 혼선 |
| **목표** | 환경 불일치 최소화 + 문서 기반 협업 체계 구축 |

---

## 📂 제안 폴더 구조 (README 관리 중심)
```
project-root/
├─ django/                # 백엔드 코드
│   └─ README.md          # Django 전용 문서
├─ streamlit/             # Streamlit UI
│   └─ README.md          # 프론트엔드 문서
├─ docs/                  # 문서 중심 협업 허브
│   ├─ README.md          # 문서 인덱스
│   ├─ 00_PROJECT_OVERVIEW.md
│   ├─ 01_TEAM_GUIDE.md
│   ├─ 02_SETUP_GUIDE.md
│   ├─ 03_SECURITY_NOTES.md
│   ├─ 04_CHANGELOG.md
│   └─ team/
│        ├─ project_lead.md
│        ├─ backend_dev.md
│        └─ frontend_dev.md
├─ requirements.txt
├─ manage.py
├─ LICENSE
└─ README.md              # 최상위 개요 (간략 버전)
```

---

## 🧱 각 문서 역할
| 문서 | 목적 | 작성자 | 유지 주기 |
|------|------|--------|------------|
| **README.md** | 전체 개요, 실행 요약 | 전체 | 상시 |
| **docs/README.md** | 문서 허브 | 리더 | 상시 |
| **django/README.md** | 백엔드 설정 | Backend | 코드 변경 시 |
| **streamlit/README.md** | 프론트 가이드 | Frontend | 코드 변경 시 |
| **team/*.md** | 개인 환경 기록 | 개인별 | 필요 시 |
| **03_SECURITY_NOTES.md** | 보안 정책 | 리더 | 분기별 |
| **04_CHANGELOG.md** | 변경 이력 | 전원 | 배포 시 |

---

## 🧩 공통 README 템플릿
```markdown
# 🧠 FMW Internal AI Tool

> 📌 본 문서는 사내 AI 도구 프로젝트(FMW) 관련 자료입니다. 
> 외부 API 및 GPT 코드는 포함되지 않으며, 문서 초안 및 협업용으로만 활용됩니다.

---

**문서 버전:** {{version}}  
**작성일:** {{date}}  
**작성자:** {{author}}  
**소속:** FMW Dev Team
```

---

### 🧩 공통 Footer
```markdown
---

📚 **참고 문서**
- [프로젝트 개요](../00_PROJECT_OVERVIEW.md)
- [팀 협업 가이드](../01_TEAM_GUIDE.md)
- [보안 지침](../03_SECURITY_NOTES.md)
- [변경 이력](../04_CHANGELOG.md)

🧭 **문서 규칙 요약**
1. Markdown 기반 작성
2. 코드 블록 언어 명시 (`bash`, `python` 등)
3. 보안 정보는 docs/team 내부에만 기록
4. 변경 시 CHANGELOG에 반영

---
© FMW Dev Team — Internal Use Only
```

---

## 📘 문서 작성 규칙 요약
| 항목 | 규칙 | 예시 |
|------|------|------|
| **파일명 규칙** | 대문자 + 언더스코어 | `00_PROJECT_OVERVIEW.md` |
| **날짜 포맷** | ISO 8601 | `2025-11-05` |
| **버전 태그** | SemVer | `v1.0.0`, `v1.1.2` |
| **코드 블록** | 언어 명시 필수 | ```python``` |
| **링크 경로** | 상대 경로 유지 | `../docs/README.md` |
| **보안 제한** | API Key, 내부 IP 등은 비공개 | ✅ |

---

## 🧭 개선 요약
| 문제 | 개선안 | 효과 |
|------|---------|------|
| 루트 README 과다 | `docs/` 폴더 집중 관리 | 루트 깔끔 유지 |
| 개인 README 혼재 | `docs/team/`에 정리 | 코드와 분리, 깔끔함 |
| 협업 문서 분산 | `docs/README.md` 인덱스 통합 | 탐색성 향상 |

---

## 🗓 향후 계획
- 🧱 **README 자동 생성 스크립트** (Python)
- 🔍 **README Lint** 검증 도구
- 🌐 **MkDocs 기반 문서 사이트화** (내부 배포)

---

📅 **최종 업데이트:** 2025‑11‑05  
📘 **작성자:** FMW Documentation Team


# ECO

## 📁 레포지토리 구조 (제안)

```

feature-monitoring-web/
├── developer_A/
│   └── to_merge/         # 공유 대상 파일
├── developer_B/
├── developer_C/
├── common/               # 공통 참고자료
└── sync_log.md           # 이관 내역 간단 메모

````

### 📑 sync_log.md (기록 예시)

```markdown
# 2025-07-25
- [B] streamlit_chart_v2.py → 회사 dev 브랜치 반영
- [A] arch_driver_overview.md → 내부 참고용으로만 유지 (미반영)
````

> ✅ 간단한 메모 수준이면 충분하며, 필요 시만 작성해도 무방합니다.

---

## 🧪 Streamlit Cloud 테스트 브랜치

- 이 브랜치는 **Streamlit Cloud 배포 실험**을 위해 최소 구성으로 유지합니다.
- `main.py`는 `app/core/navigation.py`에 정의된 페이지 레지스트리를 사용하므로 필요한 화면을 간단히 추가할 수 있습니다.
- 공용 의존성은 `requirements.txt`에 정리되어 있어 Cloud 환경에서도 바로 설치됩니다.

> 구조를 간결하게 유지하면서도 페이지 확장에 대비한 형태입니다.

---

## 🚀 배포 가이드

### 1. Git 원격 저장소로 올리기

1. 새 브랜치에서 작업 중이라면 커밋을 완료합니다.
   ```bash
   git status
   git add <파일>
   git commit -m "feat: streamlit v4 layout"
   ```
2. 회사 GitHub 저장소를 원격으로 등록합니다. (이미 등록돼 있다면 생략)
   ```bash
   git remote add origin git@github.com:<org>/<repo>.git
   ```
3. 원하는 브랜치로 push 합니다.
   ```bash
   git push -u origin <branch-name>
   ```

> ℹ️ GPT 환경에서는 외부 네트워크 접속이 제한되어 **실제 push 명령은 실행할 수 없습니다.** 위 명령을 로컬 개발 환경이나 회사 CI에서 실행해주세요.

### 2. Streamlit Cloud 배포하기

1. [streamlit.io/cloud](https://streamlit.io/cloud)에 접속해 GitHub 계정으로 로그인합니다.
2. “New app” 버튼을 눌러 위에서 push 한 저장소와 브랜치, `main.py` 진입 파일을 선택합니다.
3. 필요 시 `requirements.txt`에 `streamlit`, `pandas` 등의 의존성을 명시합니다. (현재 레포지토리는 Streamlit 1.x, pandas를 사용합니다.)
4. “Deploy”를 누르면 몇 분 내에 앱이 생성되며, 배포 URL이 발급됩니다.
5. 추후 코드를 업데이트하면 `git push`만으로 Streamlit Cloud가 자동으로 재배포합니다.

> 💡 사내망 정책으로 Streamlit Cloud 사용이 제한될 경우, 사내 Kubernetes/VM에 `streamlit run main.py --server.port <포트>` 형태로 배포하고 리버스 프록시를 연결하는 대안도 고려할 수 있습니다.

---

## 🔐 보안 정책

| 구분                    | 정책                   |
| --------------------- | -------------------- |
| 정책 명세, MCC/MNC, DB 구조 | ❌ 절대 포함 금지           |
| GPT 입력 내용             | ✅ 구조 설계, 흐름 설명만 허용   |
| 회사 레포지토리 작업           | ✅ 실제 로직, 민감 정보 작성 허용 |

---

## 🤝 협업 규칙

* 문서화보다 **주석 포함된 실 파일 중심 공유**
* Slack에 `.md` 또는 `.py` 링크만 전달해도 충분
* 공통 자료는 `common/` 폴더에 정리

---

📌 FMW는 메인 과제가 아니므로
**가볍고 효율적인 협업**,
**문서보다 실험 중심**,
**회의보다 공유 중심**의
**비동기 흐름**을 지향합니다.

```

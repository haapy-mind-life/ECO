#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="${BASE_BRANCH:-main}"
FEATURE_BRANCH="${FEATURE_BRANCH:-fix/streamlit-cloud-health-$(date +%Y%m%d-%H%M)}"

echo "==> 최신 동기화 & 작업 브랜치 생성"
git fetch origin --prune
git checkout -B "${FEATURE_BRANCH}" "origin/${BASE_BRANCH}"

echo "==> Cloud/On-prem 분리 설정 생성"
# Cloud 기본값: baseUrlPath 제거(헬스체크 404 방지)
cat > .streamlit/config.toml <<'TOML'
[server]
port = 8501
enableXsrfProtection = true
enableCORS = false
# NOTE: Cloud는 baseUrlPath를 설정하지 않습니다 (health 404 방지)
TOML

# On-prem 예시(참고용): 필요 시 이 파일을 config.toml로 교체하거나
# 배포 환경변수 STREAMLIT_SERVER_BASE_URL_PATH=/fmw 로 대체 운영 권장
cat > .streamlit/config.onprem.toml <<'TOML'
[server]
port = 8501
baseUrlPath = "/fmw"
enableXsrfProtection = true
enableCORS = false
TOML

echo "==> requirements 최소 조정(Cloud 호환 범위 유지)"
cat > requirements.txt <<'REQ'
streamlit>=1.33,<2.0
pandas>=2.0,<3.0
requests>=2.31
pyarrow>=14.0
REQ

echo "==> 사용 안하는 import 정리(런타임 순환/불필요 의존 제거)"
python - <<'PY'
from pathlib import Path

def clean_file(path: str):
    p = Path(path)
    if not p.exists(): return
    s = p.read_text(encoding="utf-8")
    # navigation.py: pandas 런타임 임포트 제거 -> 타입힌트 전용
    if path == "app/core/navigation.py":
        if "import pandas as pd" in s:
            s = s.replace("import pandas as pd\n", "")
        if "from typing import Callable, Iterable, Sequence" in s and "TYPE_CHECKING" not in s:
            s = s.replace("from typing import Callable, Iterable, Sequence",
                          "from typing import Callable, Iterable, Sequence, TYPE_CHECKING")
            s = s.replace("RenderFn = Callable[[FilterState, pd.DataFrame], FilterState]",
                          "if TYPE_CHECKING:\n    import pandas as pd\nRenderFn = Callable[[FilterState, \"pd.DataFrame\"], FilterState]")
    # home.py / visualization.py: pandas가 타입힌트에만 필요하면 TYPE_CHECKING으로 교체
    if path in ("app/views/home.py","app/views/visualization.py"):
        if "import pandas as pd" in s and "TYPE_CHECKING" not in s:
            s = s.replace("from __future__ import annotations\n",
                          "from __future__ import annotations\nfrom typing import TYPE_CHECKING\n")
            s = s.replace("import pandas as pd\n","")
            s = s.replace("pd.DataFrame","\"pd.DataFrame\"")
            s = s.replace("from typing import TYPE_CHECKING\n",
                          "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pandas as pd  # type: ignore\n")
    p.write_text(s, encoding="utf-8")

for f in ["app/core/navigation.py","app/views/home.py","app/views/visualization.py"]:
    clean_file(f)
print("imports cleaned")
PY

echo "==> 간단 스모크(임포트만 확인)"
python - <<'PY'
import importlib
for m in [
  "app.core.navigation","app.views.state","app.views.home",
  "app.views.visualization","app.data.sample_features","app.data.data_manager"
]:
    importlib.import_module(m)
print("SMOKE_OK")
PY

echo "==> CI 보조(옵션): 임포트 스모크"
mkdir -p .github/workflows
cat > .github/workflows/ci.yml <<'YML'
name: CI
on:
  pull_request:
    branches: [ main, develop ]
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Import smoke
        run: |
          python - << 'PY'
          import importlib
          for m in [
            "app.core.navigation","app.views.state","app.views.home",
            "app.views.visualization","app.data.sample_features","app.data.data_manager"
          ]:
              importlib.import_module(m)
          print("OK")
          PY
YML

echo "==> 커밋/푸시/PR 생성"
git add -A
git commit -m "fix(streamlit-cloud): remove baseUrlPath on Cloud; cleanup unused imports; add smoke CI"
git push -u origin "${FEATURE_BRANCH}"

if command -v gh >/dev/null 2>&1; then
  gh pr create --base "${BASE_BRANCH}" --head "${FEATURE_BRANCH}" \
    --title "fix: Streamlit Cloud health 404 & cleanup imports" \
    --body "Cloud에서는 baseUrlPath 미설정으로 헬스체크 404를 해소했고, 불필요 import를 제거했습니다. On-prem은 config.onprem.toml 또는 ENV(STREAMLIT_SERVER_BASE_URL_PATH=/fmw)로 운영하세요."
  gh pr view --web || true
else
  echo "⚠️ GitHub CLI(gh) 미설치: 웹에서 PR 생성하세요."
fi

echo "==> 완료"

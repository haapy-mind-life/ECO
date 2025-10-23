from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Sequence

from app.views.home import render_home
from app.views.visualization import render_visualization
from app.views.history import render_history

@dataclass(frozen=True)
class Page:
    label: str
    renderer: callable
    description: str | None = None

_DEFAULT_PAGES: tuple[Page, ...] = (
    Page("🏠 오버뷰", render_home, "동기화 요약·탐색·다운로드"),
    Page("📈 시각화", render_visualization, "그룹/피처별 차트 가이드"),
    Page("🕒 변경 이력", render_history, "동기화 후 변경 로그/런 상세"),
)

def get_pages(extra_pages: Iterable[Page] | None = None) -> Sequence[Page]:
    if not extra_pages:
        return _DEFAULT_PAGES
    return _DEFAULT_PAGES + tuple(extra_pages)

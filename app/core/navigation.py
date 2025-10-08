from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
import pandas as pd

from app.views.home import render_home
from app.views.state import FilterState
from app.views.visualization import render_visualization

RenderFn = Callable[[FilterState, pd.DataFrame], FilterState]

@dataclass(frozen=True)
class Page:
    label: str
    renderer: RenderFn
    description: str | None = None

_DEFAULT_PAGES: tuple[Page, ...] = (
    Page("🏠 홈", render_home, "필터 기반 홈 대시보드"),
    Page("📈 시각화", render_visualization, "선택된 FEATURE GROUP 기준 가이드"),
)

def get_pages(extra_pages: Iterable[Page] | None = None) -> Sequence[Page]:
    if not extra_pages:
        return _DEFAULT_PAGES
    return _DEFAULT_PAGES + tuple(extra_pages)

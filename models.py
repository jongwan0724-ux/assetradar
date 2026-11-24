"""AssetRadar 공통 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

CATEGORIES = ("tool", "3d", "2d", "vfx", "audio", "tmpl", "pixel")
STORES = ("Unity", "Fab", "itch.io")


@dataclass
class Offer:
    """한 번의 수집에서 본 세일 상품 하나."""

    id: str                      # 스토어 접두어 + 스토어 고유 ID (예: u14290, f-<uid>, i-<game_id>)
    store: str                   # Unity | Fab | itch.io
    name: str
    url: str
    price: Optional[float]       # 현재가(USD). 모르면 None
    regular: Optional[float]     # 정가(USD). 모르면 None
    publisher: str = ""
    category: str = "tool"
    ends: Optional[str] = None   # 세일 종료 ISO8601(UTC). 모르면 None
    free: bool = False           # 기간 한정 무료(정가>0, 현재가 0)

    def __post_init__(self) -> None:
        if self.store not in STORES:
            raise ValueError(f"unknown store: {self.store}")
        if self.category not in CATEGORIES:
            self.category = "tool"
        self.name = " ".join(self.name.split())[:200]
        self.publisher = " ".join(self.publisher.split())[:120]
        if self.price is not None and self.price < 0:
            raise ValueError("negative price")
        if self.price == 0 and self.regular and self.regular > 0:
            self.free = True

    @property
    def discount(self) -> Optional[int]:
        if self.price is None or not self.regular:
            return None
        return round((1 - self.price / self.regular) * 100)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SourceResult:
    store: str
    offers: list[Offer] = field(default_factory=list)
    ok: bool = True
    error: str = ""

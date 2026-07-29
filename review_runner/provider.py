from __future__ import annotations

from typing import Protocol

from .models import ProviderResult, ReviewChunk


class ReviewProvider(Protocol):
    async def review(self, chunk: ReviewChunk) -> ProviderResult: ...

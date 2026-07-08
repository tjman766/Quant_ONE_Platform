"""
Kiwoom REST API Header Builder

Sprint : 001-14B
Purpose : Build common HTTP headers for all REST APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


JSON_CONTENT_TYPE = "application/json;charset=UTF-8"


@dataclass(slots=True)
class HeaderContext:
    api_id: str
    authorization: Optional[str] = None
    cont_yn: str = "N"
    next_key: Optional[str] = None
    content_type: str = JSON_CONTENT_TYPE


class HeaderBuilder:
    """Build Kiwoom REST API headers."""

    def build(self, ctx: HeaderContext) -> dict[str, str]:
        headers = {
            "Content-Type": ctx.content_type,
            "api-id": ctx.api_id,
            "cont-yn": ctx.cont_yn,
        }

        if ctx.authorization:
            headers["authorization"] = ctx.authorization

        if ctx.next_key:
            headers["next-key"] = ctx.next_key

        return headers
from __future__ import annotations

from typing import Any

from .kiwoom_client import KiwoomRestClient
from ..core.risk_engine import risk_engine
from .settings import settings
from ..core.realtime_state import add_event, ingest_realtime_packet


def _trade_type(order_type: str, price: int | None) -> str:
    text = (order_type or "LIMIT").upper()
    if text in {"MARKET", "MKT"}:
        return "3"
    return "0" if price else "3"


class OrderExecutor:
    """주문 실행 어댑터.

    모의/실전 여부는 상단 모의/실전 전환값(KIWOOM_ACTIVE_PROFILE)만 따른다.
    MOCK이면 키움 모의투자 계좌에 실제 주문 API를 전송하고, LIVE이면 실전 계좌 주문 API를 전송한다.
    """

    def __init__(self, client: KiwoomRestClient | None = None) -> None:
        self.client = client or KiwoomRestClient()

    async def place_order(
        self,
        *,
        side: str,
        code: str,
        qty: int,
        price: int | None = None,
        name: str | None = None,
        order_type: str = "LIMIT",
        snapshot: dict[str, Any] | None = None,
        stop_price: int | None = None,
        exchange: str = "KRX",
    ) -> dict[str, Any]:
        decision = risk_engine.validate_order(
            side=side,
            code=code,
            qty=qty,
            price=price,
            snapshot=snapshot,
            stop_price=stop_price,
        )
        if not decision.allowed:
            add_event("리스크", f"주문 차단: {code} {side} {qty}주 · {decision.reason}")
            return {"ok": False, "blocked": True, "risk": decision.to_dict()}

        intent = {
            "type": "manual_order_intent",
            "code": code,
            "name": name or code,
            "side": side,
            "qty": qty,
            "price": price or 0,
            "order_type": order_type,
        }
        ingest_realtime_packet(intent)

        api_id = "kt10000" if side.upper() == "BUY" else "kt10001"
        body = {
            "dmst_stex_tp": exchange,
            "stk_cd": code,
            "ord_qty": str(int(qty)),
            "trde_tp": _trade_type(order_type, price),
        }
        if price:
            body["ord_uv"] = str(int(price))
        result = await self.client.call(api_id, body)
        add_event("주문", f"{settings.profile_label} 계좌 주문 전송: {api_id} {code} {side} {qty}주 · HTTP {result.get('status_code')}")
        return {"ok": result.get("status_code", 500) < 400, "dry_run": False, "api_id": api_id, "request": body, "response": result, "risk": decision.to_dict()}


order_executor = OrderExecutor()

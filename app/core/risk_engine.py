from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, time as dtime
from typing import Any

from ..services.settings import settings


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str
    side: str
    qty: int
    price: int
    risk_amount: int = 0
    max_qty_by_risk: int = 0
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["notes"] = list(self.notes)
        return data


class RiskEngine:
    """자동/수동 주문 전 공통 리스크 게이트.

    실제 주문 전 반드시 통과해야 하는 최소 조건만 이 레이어에서 검증한다.
    전략 신호의 품질 판단은 StrategyEngine, 주문 전송은 OrderExecutor가 담당한다.
    """

    def __init__(self, *, max_positions: int = 20, per_trade_risk_rate: float = 0.005) -> None:
        self.max_positions = max_positions
        self.per_trade_risk_rate = per_trade_risk_rate

    def validate_order(
        self,
        *,
        side: str,
        code: str,
        qty: int,
        price: int | None,
        snapshot: dict[str, Any] | None = None,
        stop_price: int | None = None,
        require_market_hours: bool = False,
    ) -> RiskDecision:
        snap = snapshot or {}
        side = (side or "").upper().strip()
        price = int(price or 0)
        qty = int(qty or 0)
        notes: list[str] = []

        if settings.emergency_stop:
            return RiskDecision(False, "긴급중지 상태입니다.", side, qty, price)
        if side not in {"BUY", "SELL"}:
            return RiskDecision(False, "매수/매도 구분이 올바르지 않습니다.", side, qty, price)
        if not code or len(str(code).strip()) < 6:
            return RiskDecision(False, "종목코드가 올바르지 않습니다.", side, qty, price)
        if qty <= 0:
            return RiskDecision(False, "주문수량은 1주 이상이어야 합니다.", side, qty, price)
        if side == "BUY" and price <= 0:
            return RiskDecision(False, "매수 주문은 기준 가격이 필요합니다.", side, qty, price)

        now = datetime.now().time()
        if require_market_hours and not (dtime(9, 0) <= now <= dtime(15, 30)):
            return RiskDecision(False, "정규 자동매매 허용 시간이 아닙니다.", side, qty, price)

        summary = snap.get("summary", {}) if isinstance(snap, dict) else {}
        positions = snap.get("positions", []) if isinstance(snap, dict) else []
        total_assets = int(summary.get("총자산") or 0)
        daily_pnl = int(summary.get("일일손익") or 0)
        orderable = int(summary.get("주문가능금액") or summary.get("예수금") or 0)
        current_positions = [p for p in positions if isinstance(p, dict) and p.get("종목명") and p.get("종목명") != "합계"]

        if total_assets > 0 and daily_pnl <= -abs(total_assets * settings.daily_loss_limit):
            return RiskDecision(False, "일 손실 제한에 도달했습니다.", side, qty, price)

        if side == "BUY":
            max_positions = int(getattr(settings, "max_positions", self.max_positions) or self.max_positions)
            if len(current_positions) >= max_positions:
                return RiskDecision(False, f"최대 보유 종목 수({max_positions})에 도달했습니다.", side, qty, price)
            order_value = qty * price
            if orderable and order_value > orderable:
                return RiskDecision(False, "주문가능금액을 초과합니다.", side, qty, price)
            if stop_price and stop_price > 0 and stop_price < price and total_assets > 0:
                per_share_risk = price - stop_price
                risk_budget = int(total_assets * float(getattr(settings, "per_trade_risk_rate", self.per_trade_risk_rate) or self.per_trade_risk_rate))
                max_qty = max(risk_budget // max(per_share_risk, 1), 0)
                if qty > max_qty:
                    return RiskDecision(False, "종목당 허용 손실 기준 수량을 초과합니다.", side, qty, price, risk_budget, max_qty)
                notes.append(f"종목당 손실한도 {risk_budget:,}원 이내")
            else:
                notes.append("손절가 미지정: 수량·금액 제한만 검증")

        return RiskDecision(True, "리스크 검증 통과", side, qty, price, notes=tuple(notes))


risk_engine = RiskEngine()

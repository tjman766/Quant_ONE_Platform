from __future__ import annotations
from datetime import datetime

REPORT_LABELS = {
    "daily": "금일",
    "weekly": "금주",
    "monthly": "금월",
    "quarterly": "금분기",
    "yearly": "금년",
    "all": "전체",
}


def build_report_message(kind: str, snapshot: dict) -> tuple[str, str]:
    label = REPORT_LABELS.get(kind, kind)
    summary = snapshot.get("summary", {})
    profile = snapshot.get("mode", "-")
    positions = snapshot.get("positions", [])
    strategies = snapshot.get("strategies", [])
    pnl = summary.get("일일손익", 0)
    total = summary.get("총자산", 0)
    eval_amt = summary.get("총평가금액", 0)
    cash = summary.get("예수금", 0)
    trade = summary.get("거래", 0)
    buy = summary.get("매수", 0)
    sell = summary.get("매도", 0)
    top_positions = "\n".join([f"• {p['종목명']} | 수량 {p['보유수량']} | 손익 {p['평가손익']:,}원" for p in positions[:5]]) or "• 보유 종목 없음"
    top_strategies = "\n".join([f"• {s['전략명']} | {s['상태']} | 금일손익 {s['금일손익']:,}원" for s in strategies[:5]]) or "• 전략 없음"
    title = f"Quant {label} 리포트 ({profile})"
    body = (
        f"📊 <b>{label} 성과 요약</b>\n"
        f"• 총 자산: {total:,}원\n"
        f"• 예수금: {cash:,}원\n"
        f"• 총 평가금액: {eval_amt:,}원\n"
        f"• 손익: {pnl:+,}원\n"
        f"• 거래: {trade}건 / 매수 {buy}건 / 매도 {sell}건\n\n"
        f"📦 <b>보유 종목 TOP</b>\n{top_positions}\n\n"
        f"🧠 <b>전략 상태</b>\n{top_strategies}\n\n"
        f"✅ 기준: 수수료/세금 포함·제외 값을 함께 관리, TokenManager 자동 토큰 관리\n"
        f"🗓 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return title, body

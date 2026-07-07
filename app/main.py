from __future__ import annotations
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio, time
from pydantic import BaseModel

from .services.catalog import load_catalog, list_apis, get_api, korean_field_map
from .services.kiwoom_realtime import RealtimeSubscribeRequest, realtime_engine
from .services.settings import settings
from .core.realtime_state import dashboard_snapshot, ingest_realtime_packet, set_ws_state, set_lifecycle, reset_for_profile_switch, mark_backup_now

from .services.telegram import telegram_notifier
from .services.reports import build_report_message
from .services.token_manager import token_manager
from .services.live_bridge import live_supervisor
from .services.order_executor import order_executor

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Quant 시스템 v1 Kiwoom - 실시간 API 우선", version="27.40")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
engine = realtime_engine


@app.on_event("startup")
async def on_startup():
    set_lifecycle("프로그램 시작", f"{settings.profile_label} · 웹창/TokenManager/Telegram 초기화")
    set_ws_state("CONNECTING", "키움 WebSocket 자동 연결 시작", enabled=True)
    # 프로그램 시작 즉시 실시간 WebSocket 상시 자동 연결을 시작한다.
    # 연결 실패/서버 정상 종료는 RealtimeEngine 내부 supervisor가 계속 재연결한다.
    asyncio.create_task(engine.ensure_started())
    live_supervisor.start()
    await telegram_notifier.send("프로그램 시작", f"{settings.profile_label} 모드로 Quant 시스템이 시작되었습니다.\n토큰은 TokenManager가 au10001로 내부 자동 관리합니다.\n실시간 WebSocket은 프로그램 시작과 동시에 자동 연결됩니다.")

class ManualOrder(BaseModel):
    code: str
    name: str = ""
    side: str
    qty: int
    price: int | None = None
    order_type: str = "LIMIT"

class ProfileSwitch(BaseModel):
    profile: str

class ReportRequest(BaseModel):
    kind: str = "daily"
    send_telegram: bool = True

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/catalog")
def catalog():
    c = load_catalog()
    return {**c, "policy": "토큰 발급/폐기 API를 제외하고 화면·시세·잔고·주문/체결 자료는 실시간 API 수신값 우선 사용"}

@app.get("/api/apis")
def apis(kind: str | None = None):
    apis = list_apis(kind)
    return [a for a in apis if a.get("api_id") not in {"au10001", "au10002"}]

@app.get("/api/catalog/{api_id}")
def catalog_detail(api_id: str):
    if api_id in {"au10001", "au10002"}:
        raise HTTPException(400, "토큰 API는 TokenManager가 au10001로 내부 자동 관리합니다.")
    return get_api(api_id)

@app.get("/api/field-map/{api_id}")
def field_map(api_id: str, direction: str = "response"):
    return korean_field_map(api_id, direction)

@app.post("/api/realtime/subscribe")
async def realtime_subscribe(req: RealtimeSubscribeRequest):
    """xlsx 실시간 API 문서의 REG payload 구조로 키움 WebSocket을 등록합니다."""
    return await engine.subscribe(req)

@app.post("/api/realtime/stop")
async def realtime_stop():
    await engine.stop()
    return {"ok": True, "message": "실시간 연결을 중지했습니다. 수동 중지는 자동 재시작하지 않습니다."}

@app.get("/api/dashboard")
def dashboard_api():
    return JSONResponse(dashboard_snapshot(), headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0", "Pragma":"no-cache"})

@app.post("/api/account/sync")
async def account_sync():
    await live_supervisor.sync_account_once("수동 새로고침")
    return {"ok": True, "snapshot": dashboard_snapshot()}

@app.post("/api/manual-order")
async def manual_order(order: ManualOrder):
    # 상단 모의/실전 전환값(KIWOOM_ACTIVE_PROFILE)에 따라 해당 계좌로 kt10000/kt10001 주문 API를 전송합니다.
    result = await order_executor.place_order(
        side=order.side,
        code=order.code,
        name=order.name or order.code,
        qty=order.qty,
        price=order.price,
        order_type=order.order_type,
        snapshot=dashboard_snapshot(),
    )
    return {"ok": bool(result.get("ok")), "message": result.get("message", "주문 처리 완료"), "order": order.model_dump(), "result": result}


@app.get("/api/settings/public")
def public_settings():
    return settings.as_public_dict()

@app.post("/api/profile/switch")
async def switch_profile(req: ProfileSwitch):
    old = settings.profile_label
    settings.set_profile(req.profile)
    token_manager.invalidate()
    new = settings.profile_label
    reset_for_profile_switch()
    set_ws_state("CONNECTING", f"프로필 전환: {old} → {new} · WebSocket 재시작", enabled=True)
    set_lifecycle("모의/실전 전환", f"{old} → {new}")
    await engine.stop(notify=False, silent=True)
    await engine.ensure_started()
    await live_supervisor.sync_account_once("프로필 전환")
    snap = dashboard_snapshot()
    result = await telegram_notifier.send("모의/실전 프로필 전환", f"{old}에서 {new}으로 전환했습니다.\n웹창 버튼, REST 도메인, WebSocket URL, Telegram TOKEN이 현재 프로필 기준으로 함께 변경되었습니다.\nWebSocket은 자동으로 재연결됩니다.\nWebSocket: {snap['full_ws_url']}")
    return {"ok": True, "old": old, "new": new, "telegram": result, "snapshot": snap}

@app.post("/api/realtime/on")
async def realtime_on():
    req = RealtimeSubscribeRequest(api_id="00,04,0B,0A,0C,0D,0J,0U", items=["005930", "000660", "005380", "035420", "035720", "373220"], mock_stream=False)
    result = await engine.subscribe(req)
    await telegram_notifier.send("실시간 WebSocket ON", f"{settings.profile_label} 실시간 WebSocket을 수동으로 켰습니다.\nURL: {settings.ws_url}")
    return result

@app.post("/api/notify/lifecycle/{event}")
async def notify_lifecycle(event: str):
    labels = {
        "program_start": "프로그램 시작",
        "market_start": "운영 시장 시작",
        "trade_start": "매매 시작",
        "buy": "매수",
        "sell": "매도",
        "trade_end": "매매 종료",
        "market_end": "운영 시장 종료",
    }
    title = labels.get(event, event)
    snap = dashboard_snapshot()
    body = f"{settings.profile_label}\n총자산: {snap['summary']['총자산']:,}원\n예수금: {snap['summary']['예수금']:,}원\n금일손익: {snap['summary']['일일손익']:+,}원\n거래: {snap['summary']['거래']}건 / 매수 {snap['summary']['매수']} / 매도 {snap['summary']['매도']}\nWebSocket: {snap['status']['ws']}\nToken: TokenManager 자동 관리"
    result = await telegram_notifier.send(title, body)
    set_lifecycle(title, f"Telegram={result.get('ok', False)}")
    if event in {"market_end", "trade_end"}:
        mark_backup_now(title)
    if event in {"market_start", "trade_start", "buy", "sell"}:
        await engine.ensure_started()
        await live_supervisor.sync_account_once(title)
    return {"ok": True, "event": event, "title": title, "telegram": result}

@app.post("/api/report")
async def make_report(req: ReportRequest):
    snap = dashboard_snapshot()
    title, body = build_report_message(req.kind, snap)
    result = await telegram_notifier.send(title, body) if req.send_telegram else {"ok": True, "skipped": True}
    mark_backup_now(f"{title} 생성")
    return {"ok": True, "title": title, "body": body, "telegram": result, "snapshot": dashboard_snapshot()}

@app.get("/api/token/status")
def token_status():
    # 토큰 원문은 노출하지 않고, 발급 가능 여부/오류만 확인합니다.
    return token_manager.public_status()

@app.post("/api/token/refresh")
async def token_refresh():
    # UI 표시용이 아니라 진단/복구용입니다. 토큰 원문은 마스킹만 반환합니다.
    try:
        status = await token_manager.refresh()
        set_lifecycle("토큰 갱신", f"{settings.profile_label} 접근토큰 정상 갱신")
        return {"ok": True, "status": status}
    except Exception as exc:
        set_lifecycle("토큰 오류", str(exc))
        set_ws_state("ERROR", f"토큰 오류: {exc}", enabled=True)
        raise HTTPException(400, str(exc))

@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(dashboard_snapshot())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return

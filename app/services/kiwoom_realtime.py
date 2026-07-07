from __future__ import annotations
from pydantic import BaseModel, Field
import asyncio, json, inspect
import websockets
from .settings import settings
from .token_manager import token_manager
from .telegram import telegram_notifier
from ..core.realtime_state import ingest_realtime_packet, set_ws_state, add_event

class RealtimeSubscribeRequest(BaseModel):
    api_id: str = Field("00,04,0B,0A,0C,0D,0J,0U", description="xlsx 실시간 API ID 또는 타입. 여러 개는 쉼표로 구분")
    items: list[str] = Field(default_factory=lambda:["005930","000660"])
    group_no: str = "1"
    refresh: str = "1"
    mock_stream: bool = False

class RealtimeEngine:
    """Kiwoom WebSocket manager.

    기본 정책은 상시 자동 연결입니다. 사용자가 OFF를 누르면 stop_event가 세팅되어
    자동 재연결하지 않고, 다시 ON을 누르면 동일 정책으로 재시작합니다.
    .env 앱키/시크릿이 비어 있으면 실제 연결을 시작하지 않고 오류를 웹창에 표시합니다.
    """
    def __init__(self):
        self.task: asyncio.Task | None = None
        self.stop_event = asyncio.Event()
        self.current_req: RealtimeSubscribeRequest | None = None
        self._last_items_key: tuple[str, ...] = tuple()

    def build_payload(self, req: RealtimeSubscribeRequest) -> dict:
        types = [x.strip() for x in str(req.api_id).split(',') if x.strip()]
        account_types = [t for t in types if t in {"00", "04"}]
        stock_types = [t for t in types if t not in {"00", "04", "0J", "0U"}]
        market_types = [t for t in types if t in {"0J", "0U"}]
        data = []
        # 00 주문체결 / 04 잔고는 ACCESS TOKEN 계좌 기준이라 item 등록과 무관합니다.
        if account_types:
            data.append({"item": [""], "type": account_types})
        if stock_types:
            data.append({"item": req.items, "type": stock_types})
        # 업종지수/업종등락은 기본 업종코드를 함께 등록합니다.
        if market_types:
            data.append({"item": ["001", "101", "201", "000"], "type": market_types})
        return {"trnm": "REG", "grp_no": req.group_no, "refresh": req.refresh, "data": data}

    async def subscribe(self, req: RealtimeSubscribeRequest):
        await self.stop(notify=False, silent=True)
        self.stop_event.clear()
        self.current_req = req
        if req.mock_stream:
            return {"ok": False, "mode":"disabled_mock_stream", "payload": self.build_payload(req), "message":"샘플 스트림은 제거되었습니다. 실제 Kiwoom WebSocket 수신값만 반영합니다."}
        if not (settings.app_key and settings.app_secret):
            set_ws_state("ERROR", "앱키/시크릿 미설정 · .env 현재 프로필 값을 입력해야 실제 WebSocket 연결 가능", enabled=True)
            add_event("오류", "현재 프로필 앱키/시크릿이 비어 있어 실제 키움 WebSocket 연결을 시작할 수 없습니다.")
            return {"ok": False, "mode":"missing_credentials", "payload": self.build_payload(req), "message":".env의 현재 프로필 APP_KEY/APP_SECRET을 입력해야 실제 WebSocket 연결이 가능합니다."}
        self.task = asyncio.create_task(self._supervised_ws_loop(req))
        set_ws_state("CONNECTING", "키움 WebSocket 상시 자동 연결 시작", enabled=True)
        return {"ok": True, "mode":"kiwoom_websocket", "payload": self.build_payload(req), "message":"키움 WebSocket 실시간 등록을 시작했습니다."}

    async def ensure_started(self):
        # 상시 자동 연결 정책: 수동 OFF가 아닌 한 시작/재시작한다.
        if not self.task or self.task.done():
            req = self.current_req or RealtimeSubscribeRequest(api_id="00,04,0B,0A,0C,0D,0J,0U", items=["005930", "000660", "005380", "035420", "035720", "373220"], mock_stream=False)
            return await self.subscribe(req)
        return {"ok": True, "message": "이미 실시간 WebSocket이 실행 중입니다."}



    async def update_items_if_changed(self, items: list[str]):
        """보유종목 변동 시 0B 현재가 등록 종목을 실제 보유코드 중심으로 재등록한다."""
        clean = []
        for x in items or []:
            code = str(x or '').strip()[-6:]
            if code and code not in clean:
                clean.append(code)
        key = tuple(sorted(clean))
        if not clean or key == self._last_items_key:
            return {"ok": True, "message": "실시간 등록 종목 변경 없음"}
        self._last_items_key = key
        req = self.current_req or RealtimeSubscribeRequest()
        # 00/04 계좌 이벤트 + 0B/0A/0C/0D 실시간 시세 + 0J/0U 시장/업종은 항상 유지한다.
        req = RealtimeSubscribeRequest(api_id="00,04,0B,0A,0C,0D,0J,0U", items=clean, group_no=req.group_no, refresh="1", mock_stream=False)
        return await self.subscribe(req)

    async def stop(self, notify: bool = True, silent: bool = False):
        self.stop_event.set()
        if self.task and not self.task.done():
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
        self.task = None
        if not silent:
            set_ws_state("OFF", "실시간 WebSocket 사용자가 직접 중지", enabled=False)
            if notify:
                await telegram_notifier.send("실시간 WebSocket OFF", f"{settings.profile_label} 실시간 WebSocket을 수동으로 중지했습니다.")

    async def _supervised_ws_loop(self, req: RealtimeSubscribeRequest):
        retry = 0
        last_telegram_at = 0.0
        while not self.stop_event.is_set():
            try:
                await self._ws_once(req)
                retry = 0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                retry += 1
                # 실시간 매매에서는 긴 백오프가 오히려 장애입니다.
                # 키움 서버/네트워크 보호를 위해 최소한의 짧은 텀만 두고 즉시 재연결 루프를 유지합니다.
                delay = 0.15 if retry <= 5 else 0.5 if retry <= 20 else 1.0
                set_ws_state("RECONNECTING", f"WebSocket 자동 재연결 중 · 즉시 재시도({delay:.2f}s): {e}", enabled=True)
                # 사용자 요청: 자동 재연결 반복 메시지는 웹창/텔레그램 알림에서 제외한다.
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    continue

    async def _ws_once(self, req: RealtimeSubscribeRequest):
        try:
            auth = await token_manager.auth_header()
        except Exception as exc:
            set_ws_state("ERROR", f"토큰 발급 실패 · WebSocket 연결 보류: {exc}", enabled=True)
            add_event("오류", f"토큰 발급 실패로 WebSocket 연결 보류: {exc}")
            # 자격증명/토큰 오류는 초단위 재시도해도 해결되지 않습니다.
            # 사용자가 .env를 수정하거나 프로필을 전환하면 즉시 다시 시작됩니다.
            await asyncio.sleep(5)
            raise
        headers = {"authorization": auth, "api-id": str(req.api_id).split(",")[0].strip()}
        # websockets 버전에 따라 헤더 인자가 extra_headers 또는 additional_headers로 다르다.
        sig = inspect.signature(websockets.connect)
        header_arg = "additional_headers" if "additional_headers" in sig.parameters else "extra_headers"
        connect_kwargs = {header_arg: headers, "ping_interval": None, "ping_timeout": None, "close_timeout": 0.2}
        async with websockets.connect(settings.ws_url, **connect_kwargs) as ws:
            set_ws_state("CONNECTED", "키움 WebSocket TCP 연결 완료 · 실시간 등록 요청", enabled=True)
            await ws.send(json.dumps(self.build_payload(req), ensure_ascii=False))
            set_ws_state("CONNECTED", "키움 WebSocket 등록 완료 · 실시간 수신 대기", enabled=True)
            while not self.stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=70)
                except asyncio.TimeoutError:
                    # 실시간 종목/주문 이벤트가 없으면 recv가 없어도 연결은 살아있을 수 있습니다.
                    # Ping 응답 여부를 기준으로 종료/유지를 판단하고, OFF로는 절대 바꾸지 않습니다.
                    set_ws_state("WAITING", "WebSocket 연결 유지 · 실시간 수신 대기", enabled=True)
                    try:
                        pong = await ws.ping()
                        await asyncio.wait_for(pong, timeout=3)
                        set_ws_state("WAITING", "WebSocket ping 응답 정상 · 실시간 수신 대기", enabled=True)
                        continue
                    except Exception:
                        raise
                try: packet = json.loads(raw)
                except Exception: packet = {"raw": raw}
                ingest_realtime_packet(packet)
                set_ws_state("CONNECTED", "실시간 원문 수신", enabled=True)


# 앱 전체에서 하나의 WebSocket 엔진만 사용한다.
realtime_engine = RealtimeEngine()

from __future__ import annotations
import asyncio
from datetime import datetime, time as dtime

from .kiwoom_client import KiwoomRestClient
from .settings import settings
from ..core.realtime_state import ingest_rest_account, ingest_rest_price, ingest_rest_market, position_codes, add_event, set_lifecycle, mark_backup_now

class LiveDataSupervisor:
    """웹창 실행 → 토큰 → 실시간 접속 → 운영시간 → 전략/매매 → 종료/리포트 흐름 관리자.

    원칙: 웹창 표시는 실제 Kiwoom REST/WebSocket 수신값만 사용한다.
    WebSocket 04는 주문/체결 발생 시에만 오므로, 시작/전환/주기 동기화는 REST 잔고 조회로 보강한다.
    """
    def __init__(self) -> None:
        self.task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._sent_today: set[str] = set()

    def start(self) -> None:
        if not self.task or self.task.done():
            self._stop.clear()
            self.task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self.task and not self.task.done():
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
        self.task = None

    def reset_day_flags(self) -> None:
        self._sent_today.clear()


    async def _refresh_realtime_items_for_positions(self) -> None:
        """보유종목이 확인되면 0B 현재가 실시간 등록 대상에 즉시 포함한다."""
        codes = position_codes()
        if not codes:
            return
        try:
            from .kiwoom_realtime import realtime_engine, RealtimeSubscribeRequest
            base = ["005930", "000660", "005380", "035420", "035720", "373220"]
            items = list(dict.fromkeys(codes + base))[:80]
            await realtime_engine.update_items_if_changed(items)
        except Exception as exc:
            add_event("오류", f"보유종목 실시간 현재가 등록 갱신 실패: {exc}")

    async def sync_prices_once(self, reason: str = "현재가 보강") -> None:
        """실시간 0B 수신 공백을 줄이기 위해 보유종목 현재가 REST를 보조 동기화한다."""
        codes = position_codes()[:20]
        if not codes:
            return
        client = KiwoomRestClient()
        ok = 0
        for code in codes:
            try:
                res = await client.call("ka10001", {"stk_cd": code})
                if res.get('status_code', 0) < 400:
                    ingest_rest_price("ka10001", res, code)
                    ok += 1
            except Exception as exc:
                add_event("오류", f"현재가 REST 보강 실패({code}): {exc}")
            await asyncio.sleep(0.02)
        if ok:
            add_event("시세", f"보유종목 현재가 REST 보강 완료 · {reason} · {ok}종목")


    async def sync_market_once(self, reason: str = "시장/업종 보강") -> None:
        """운영현황의 시장지수/업종등락률을 ka20003 전업종지수로 보강한다."""
        client = KiwoomRestClient()
        ok = 0
        for inds_cd in ("001", "101"):
            try:
                res = await client.call("ka20003", {"inds_cd": inds_cd})
                if res.get('status_code', 0) < 400:
                    ingest_rest_market("ka20003", res, inds_cd)
                    ok += 1
                else:
                    add_event("오류", f"시장/업종 REST 보강 실패({inds_cd}): HTTP {res.get('status_code')}")
            except Exception as exc:
                add_event("오류", f"시장/업종 REST 보강 실패({inds_cd}): {exc}")
            await asyncio.sleep(0.02)
        if ok:
            add_event("시장", f"시장지수/업종등락률 REST 보강 완료 · {reason} · {ok}개 시장")

    async def sync_account_once(self, reason: str = "수동/시작") -> None:
        client = KiwoomRestClient()
        failures = []
        for api_id, body in (
            ("kt00018", {"qry_tp": "1", "dmst_stex_tp": "KRX"}),
            ("kt00005", {"dmst_stex_tp": "KRX"}),
        ):
            try:
                res = await client.call(api_id, body)
                if res.get('status_code', 0) >= 400:
                    failures.append(f"{api_id} HTTP {res.get('status_code')}")
                    continue
                ingest_rest_account(api_id, res)
            except Exception as exc:
                failures.append(f"{api_id}: {exc}")
        if failures:
            add_event("오류", f"계좌/잔고 REST 동기화 실패({reason}): " + " / ".join(failures))
        else:
            add_event("계좌", f"계좌/잔고 REST 동기화 완료 · {reason}")
            await self._refresh_realtime_items_for_positions()
            await self.sync_prices_once(reason)
            await self.sync_market_once(reason)

    async def _run(self) -> None:
        await asyncio.sleep(1.0)
        await self.sync_account_once("웹창 시작")
        last_sync = 0.0
        last_price_sync = 0.0
        last_market_sync = 0.0
        while not self._stop.is_set():
            try:
                now = datetime.now()
                today_key = now.strftime('%Y%m%d')
                if not any(x.startswith(today_key) for x in self._sent_today):
                    self._sent_today = {x for x in self._sent_today if x.startswith(today_key)}
                # 휴일/주말은 자동매매 시작/종료 이벤트를 발생시키지 않고 계좌 동기화만 유지한다.
                is_weekday = now.weekday() < 5
                if is_weekday:
                    for key, t, label in [
                        ('market_start', dtime(9,0,0), '운영 시장 시작'),
                        ('trade_start', dtime(9,1,0), '매매 시작'),
                        ('trade_end', dtime(15,30,0), '매매 종료'),
                        ('market_end', dtime(16,0,0), '운영 시장 종료'),
                    ]:
                        flag = f"{today_key}:{key}"
                        if now.time() >= t and flag not in self._sent_today:
                            self._sent_today.add(flag)
                            set_lifecycle(label, '운영 시간 자동 판단')
                            if key in {'trade_end','market_end'}:
                                mark_backup_now(label)
                # 장중 10초, 장외/휴일 60초 계좌 동기화. 실제 매수/매도 직후 04가 오지 않아도 화면은 REST로 보강된다.
                interval = 3 if is_weekday and dtime(9,0) <= now.time() <= dtime(15,40) else 60
                price_interval = 1.0 if is_weekday and dtime(9,0) <= now.time() <= dtime(15,40) else 30.0
                if now.timestamp() - last_sync >= interval:
                    last_sync = now.timestamp()
                    await self.sync_account_once('주기 동기화')
                elif now.timestamp() - last_price_sync >= price_interval:
                    last_price_sync = now.timestamp()
                    await self.sync_prices_once('주기 현재가')
                if now.timestamp() - last_market_sync >= max(interval, 30):
                    last_market_sync = now.timestamp()
                    await self.sync_market_once('주기 시장/업종')
            except Exception as exc:
                add_event('오류', f'자동 운영 감독 오류: {exc}')
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

live_supervisor = LiveDataSupervisor()

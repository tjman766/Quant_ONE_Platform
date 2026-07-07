from __future__ import annotations
import asyncio, json, websockets
from .catalog import get_api
from .settings import settings

def build_realtime_payload(api_id: str, items: list[str], group_no: str = "0001", refresh: str = "1") -> dict:
    """실시간 API 문서(xlsx)의 Body 구조(REG/REMOVE, grp_no, refresh, data)를 기준으로 등록 payload 생성."""
    api = get_api(api_id)
    return {
        "trnm": "REG",
        "grp_no": group_no,
        "refresh": refresh,
        "data": [{"item": item, "type": api["api_id"]} for item in items],
    }

async def realtime_subscribe(access_token: str, api_id: str, items: list[str]):
    headers = {"authorization": f"Bearer {access_token}", "api-id": api_id}
    async with websockets.connect(settings.ws_url, extra_headers=headers, ping_interval=20) as ws:
        await ws.send(json.dumps(build_realtime_payload(api_id, items), ensure_ascii=False))
        while True:
            raw = await ws.recv()
            yield json.loads(raw)
            await asyncio.sleep(0)

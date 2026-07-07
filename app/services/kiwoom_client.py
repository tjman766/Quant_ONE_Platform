from __future__ import annotations
import httpx
from .catalog import get_api, required_body_fields
from .settings import settings
from .token_manager import token_manager

class KiwoomRestClient:
    """xlsx API 문서의 Method / URL / Header / Body를 1:1로 사용하는 REST 클라이언트."""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    async def _headers(self, api_id: str, cont_yn: str = "N", next_key: str = "") -> dict:
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": api_id,
            "cont-yn": cont_yn,
            "next-key": next_key,
        }
        if api_id not in {"au10001"} and self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        elif api_id not in {"au10001"}:
            headers["authorization"] = await token_manager.auth_header()
        return headers

    def validate_body(self, api_id: str, body: dict) -> None:
        missing = [k for k in required_body_fields(api_id) if k not in body or body[k] in ("", None)]
        if missing:
            raise ValueError(f"{api_id} 필수 입력 누락: {', '.join(missing)}")

    async def call(self, api_id: str, body: dict | None = None, cont_yn: str = "N", next_key: str = "") -> dict:
        api = get_api(api_id)
        body = body or {}
        self.validate_body(api_id, body)

        async def _request(force_token_refresh: bool = False):
            headers = await self._headers(api_id, cont_yn, next_key)
            if force_token_refresh and api_id not in {"au10001"}:
                headers["authorization"] = await token_manager.auth_header(force_refresh=True)
            async with httpx.AsyncClient(base_url=settings.base_url.rstrip("/"), timeout=20.0) as client:
                return await client.request(
                    method=api["method"] or "POST",
                    url=api["url"],
                    headers=headers,
                    json=body,
                )

        res = await _request(False)
        # 만료/잘못된 토큰이면 1회 강제 갱신 후 재시도합니다.
        if api_id not in {"au10001"} and res.status_code in {401, 403}:
            token_manager.invalidate(f"REST {api_id} 인증 실패 HTTP {res.status_code} · 토큰 강제 갱신")
            res = await _request(True)

        try:
            payload = res.json() if res.content else {}
        except Exception:
            payload = {"raw": res.text[:500]}
        return {
            "status_code": res.status_code,
            "headers": dict(res.headers),
            "json": payload,
            "api": {"api_id": api_id, "name": api["name"], "url": api["url"]},
        }

async def issue_token() -> dict:
    # 호환용: 실제 운영에서는 TokenManager가 내부 자동 관리한다.
    token = await token_manager.get_access_token()
    return {"ok": True, "managed_by": "TokenManager", "token_masked": token[:4] + "****" if token else ""}

async def revoke_token(token: str) -> dict:
    client = KiwoomRestClient(access_token=token)
    return await client.call("au10002", {
        "appkey": settings.app_key,
        "secretkey": settings.app_secret,
        "token": token,
    })

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx

from .settings import settings


TOKEN_API_ID = "au10001"
TOKEN_PATH = "/oauth2/token"
TOKEN_REFRESH_MARGIN = timedelta(minutes=10)


def _parse_expires_dt(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    for fmt in ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19] if "T" in value else value, fmt)
        except ValueError:
            continue
    return None


def _mask(value: str | None, head: int = 4, tail: int = 4) -> str:
    if not value:
        return ""
    value = str(value)
    if len(value) <= head + tail:
        return "****"
    return f"{value[:head]}****{value[-tail:]}"


def _normalize_token_type(raw: str | None) -> str:
    token_type = (raw or "Bearer").strip()
    # 키움 응답 예시는 bearer 소문자지만 Header 예시는 Bearer입니다. Header는 항상 Bearer로 정규화합니다.
    return "Bearer" if token_type.lower() == "bearer" else token_type


class TokenManager:
    """Kiwoom au10001 접근토큰 내부 자동 관리자.

    원칙
    - UI/프론트/사용자 입력에서 access_token을 받지 않는다.
    - 현재 프로필(MOCK/LIVE)의 APP_KEY/APP_SECRET만 사용한다.
    - 만료 10분 전 자동 갱신한다.
    - 프로필 전환 시 기존 토큰은 즉시 폐기한다.
    """

    def __init__(self) -> None:
        self._token: str = ""
        self._token_type: str = "Bearer"
        self._expires_at: datetime | None = None
        self._issued_at: datetime | None = None
        self._profile: str = settings.active_profile
        self._base_url: str = settings.base_url
        self._lock = asyncio.Lock()
        self._last_error: str = ""
        self._last_status_code: int | None = None
        self._last_return_code: str = ""
        self._last_return_msg: str = ""

    def invalidate(self, reason: str = "") -> None:
        self._token = ""
        self._expires_at = None
        self._issued_at = None
        self._profile = settings.active_profile
        self._base_url = settings.base_url
        if reason:
            self._last_error = reason

    def _needs_refresh(self) -> bool:
        if not self._token:
            return True
        if self._profile != settings.active_profile or self._base_url != settings.base_url:
            return True
        if self._expires_at is None:
            return True
        return datetime.now() >= self._expires_at - TOKEN_REFRESH_MARGIN

    def _credentials_error(self) -> str | None:
        missing: list[str] = []
        if not settings.app_key:
            missing.append(f"KIWOOM_{settings.active_profile}_APP_KEY")
        if not settings.app_secret:
            missing.append(f"KIWOOM_{settings.active_profile}_APP_SECRET")
        if missing:
            return f"{settings.profile_label} 토큰 발급 불가: .env에 {', '.join(missing)} 값이 없습니다."
        return None

    async def get_access_token(self, force_refresh: bool = False) -> str:
        async with self._lock:
            if not force_refresh and not self._needs_refresh():
                return self._token

            cred_error = self._credentials_error()
            if cred_error:
                self._last_error = cred_error
                raise RuntimeError(cred_error)

            payload = {
                "grant_type": "client_credentials",
                "appkey": settings.app_key.strip(),
                "secretkey": settings.app_secret.strip(),
            }
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json",
                "api-id": TOKEN_API_ID,
            }

            try:
                async with httpx.AsyncClient(base_url=settings.base_url.rstrip("/"), timeout=httpx.Timeout(20.0, connect=10.0)) as client:
                    res = await client.post(TOKEN_PATH, headers=headers, json=payload)
            except Exception as exc:
                self._last_status_code = None
                self._last_return_code = "NETWORK"
                self._last_return_msg = str(exc)
                self._last_error = f"접근토큰 발급 네트워크 오류: {exc}"
                raise RuntimeError(self._last_error) from exc

            self._last_status_code = res.status_code
            data: dict[str, Any]
            try:
                data = res.json() if res.content else {}
            except Exception:
                data = {"return_msg": res.text[:500]}

            return_code = str(data.get("return_code", "0" if res.status_code < 400 else res.status_code)).strip()
            return_msg = str(data.get("return_msg", "")).strip()
            self._last_return_code = return_code
            self._last_return_msg = return_msg

            if res.status_code >= 400 or return_code not in {"0", ""}:
                msg = return_msg or data.get("msg") or data.get("message") or f"HTTP {res.status_code}"
                self._last_error = f"접근토큰 발급 실패({settings.profile_label}, {settings.base_url}, code={return_code}): {msg}"
                self.invalidate(self._last_error)
                raise RuntimeError(self._last_error)

            token = str(data.get("token") or data.get("access_token") or "").strip()
            if not token:
                self._last_error = f"접근토큰 발급 실패: 응답에 token 값이 없습니다. 응답키={list(data.keys())}"
                self.invalidate(self._last_error)
                raise RuntimeError(self._last_error)

            self._token = token
            self._token_type = _normalize_token_type(str(data.get("token_type") or "Bearer"))
            self._expires_at = _parse_expires_dt(data.get("expires_dt")) or (datetime.now() + timedelta(hours=23))
            self._issued_at = datetime.now()
            self._profile = settings.active_profile
            self._base_url = settings.base_url
            self._last_error = ""
            return self._token

    async def auth_header(self, force_refresh: bool = False) -> str:
        token = await self.get_access_token(force_refresh=force_refresh)
        return f"Bearer {token}"

    async def refresh(self) -> dict:
        token = await self.get_access_token(force_refresh=True)
        return {**self.public_status(), "token_masked": _mask(token)}

    def public_status(self) -> dict:
        remaining_seconds = None
        if self._expires_at:
            remaining_seconds = max(0, int((self._expires_at - datetime.now()).total_seconds()))
        return {
            "managed": True,
            "profile": settings.active_profile,
            "profile_label": settings.profile_label,
            "base_url": settings.base_url,
            "token_ready": bool(self._token),
            "token_masked": _mask(self._token),
            "issued_at": self._issued_at.strftime("%Y-%m-%d %H:%M:%S") if self._issued_at else "자동 발급 전",
            "expires_at": self._expires_at.strftime("%Y-%m-%d %H:%M:%S") if self._expires_at else "자동 발급 전",
            "remaining_seconds": remaining_seconds,
            "last_error": self._last_error,
            "last_status_code": self._last_status_code,
            "last_return_code": self._last_return_code,
            "last_return_msg": self._last_return_msg,
        }


# 전역 단일 인스턴스
token_manager = TokenManager()

from __future__ import annotations
import httpx
from datetime import datetime
from .settings import settings


class TelegramNotifier:
    def enabled(self) -> bool:
        return bool(settings.telegram_chat_id and settings.telegram_token)

    async def send(self, title: str, body: str) -> dict:
        message = f"📌 {title}\n\n{body}\n\n⏱ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if not self.enabled():
            return {"ok": False, "skipped": True, "message": "TELEGRAM_CHAT_ID 또는 현재 프로필용 TELEGRAM_TOKEN이 없습니다.", "preview": message}
        url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
        payload = {"chat_id": settings.telegram_chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
            return {"ok": res.status_code < 400, "status_code": res.status_code, "response": res.json() if res.content else {}}
        except Exception as e:
            return {"ok": False, "error": str(e), "preview": message}


telegram_notifier = TelegramNotifier()

from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class ApiResponse:
    success: bool
    return_code: int
    return_msg: str
    data: dict[str, Any]

class ResponseParser:
    def parse(self, payload: dict[str, Any]) -> ApiResponse:
        code=int(payload.get("return_code",-1))
        msg=str(payload.get("return_msg",""))
        data={k:v for k,v in payload.items() if k not in ("return_code","return_msg")}
        return ApiResponse(code==0, code, msg, data)

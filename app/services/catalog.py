from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "kiwoom_api_catalog.json"

@lru_cache
def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

def get_api(api_id: str) -> dict:
    catalog = load_catalog()
    for api in catalog["apis"]:
        if api["api_id"] == api_id:
            return api
    raise KeyError(f"API ID not found: {api_id}")

def list_apis(kind: str | None = None) -> list[dict]:
    apis = load_catalog()["apis"]
    if kind == "rest":
        return [a for a in apis if not a["prod_domain"].startswith("wss")]
    if kind == "realtime":
        return [a for a in apis if a["prod_domain"].startswith("wss")]
    return apis

def required_body_fields(api_id: str) -> list[str]:
    api = get_api(api_id)
    return [f["element"] for f in api["request"]["body"] if f.get("required") == "Y"]

def korean_field_map(api_id: str, direction: str = "response") -> dict[str, str]:
    api = get_api(api_id)
    fields = api.get(direction, {}).get("body", []) + api.get(direction, {}).get("headers", [])
    return {f["element"]: f["korean"] for f in fields if f.get("element")}

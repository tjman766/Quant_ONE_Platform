from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH, override=True)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _set_env_value(key: str, value: str) -> None:
    """Preserve comments/order as much as possible while updating .env."""
    lines: list[str] = []
    found = False
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    os.environ[key] = value


@dataclass
class QuantSettings:
    active_profile: str = os.getenv("KIWOOM_ACTIVE_PROFILE", "MOCK").upper()
    mock_base_url: str = os.getenv("KIWOOM_MOCK_BASE_URL", "https://mockapi.kiwoom.com")
    live_base_url: str = os.getenv("KIWOOM_LIVE_BASE_URL", "https://api.kiwoom.com")
    mock_ws_url: str = os.getenv("KIWOOM_MOCK_WS_URL", "wss://mockapi.kiwoom.com:10000/api/dostk/websocket")
    live_ws_url: str = os.getenv("KIWOOM_LIVE_WS_URL", "wss://api.kiwoom.com:10000/api/dostk/websocket")
    mock_app_key: str = os.getenv("KIWOOM_MOCK_APP_KEY", "")
    mock_app_secret: str = os.getenv("KIWOOM_MOCK_APP_SECRET", "")
    live_app_key: str = os.getenv("KIWOOM_LIVE_APP_KEY", "")
    live_app_secret: str = os.getenv("KIWOOM_LIVE_APP_SECRET", "")
    mock_app_expires_at: str = os.getenv("KIWOOM_MOCK_APP_EXPIRES_AT", "")
    live_app_expires_at: str = os.getenv("KIWOOM_LIVE_APP_EXPIRES_AT", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_mock_token: str = os.getenv("TELEGRAM_MOCK_TOKEN", "")
    telegram_live_token: str = os.getenv("TELEGRAM_LIVE_TOKEN", "")
    fee_rate: float = float(os.getenv("QUANT_FEE_RATE", "0.00015") or 0.00015)
    tax_rate: float = float(os.getenv("QUANT_TAX_RATE", "0.0018") or 0.0018)
    daily_loss_limit: float = float(os.getenv("DAILY_LOSS_LIMIT", "0.02") or 0.02)
    auto_trade_enabled: bool = _env_bool("AUTO_TRADE_ENABLED", "true")
    emergency_stop: bool = _env_bool("EMERGENCY_STOP", "false")
    max_positions: int = int(os.getenv("MAX_POSITIONS", "20") or 20)
    per_trade_risk_rate: float = float(os.getenv("PER_TRADE_RISK_RATE", "0.005") or 0.005)
    target_investment_rate: float = float(os.getenv("TARGET_INVESTMENT_RATE", "0.90") or 0.90)
    max_target_investment_rate: float = float(os.getenv("MAX_TARGET_INVESTMENT_RATE", "0.95") or 0.95)
    rebalance_cycle: str = os.getenv("REBALANCE_CYCLE", "MONTHLY")
    selected_strategy_group: str = os.getenv("SELECTED_STRATEGY_GROUP", "FOUR_QUANT").upper()
    my_strategy_enhanced: bool = _env_bool("MY_STRATEGY_ENHANCED", "true")
    operating_flow: str = os.getenv("OPERATING_FLOW", "BACKTEST_TO_SELECTED_ACCOUNT_TO_REPORT")
    top_n_selection: int = int(os.getenv("TOP_N_SELECTION", "20") or 20)
    min_backtest_sharpe: float = float(os.getenv("MIN_BACKTEST_SHARPE", "0.8") or 0.8)
    max_mdd_limit: float = float(os.getenv("MAX_MDD_LIMIT", "0.20") or 0.20)
    volatility_cutoff_rate: float = float(os.getenv("VOLATILITY_CUTOFF_RATE", "0.035") or 0.035)

    @property
    def is_mock(self) -> bool:
        return self.active_profile == "MOCK"

    @property
    def profile_label(self) -> str:
        return "모의 투자" if self.is_mock else "실전 투자"

    @property
    def base_url(self) -> str:
        return self.mock_base_url if self.is_mock else self.live_base_url

    @property
    def ws_url(self) -> str:
        return self.mock_ws_url if self.is_mock else self.live_ws_url

    @property
    def app_key(self) -> str:
        return self.mock_app_key if self.is_mock else self.live_app_key

    @property
    def app_secret(self) -> str:
        return self.mock_app_secret if self.is_mock else self.live_app_secret

    @property
    def app_expires_at(self) -> str:
        return self.mock_app_expires_at if self.is_mock else self.live_app_expires_at

    @property
    def telegram_token(self) -> str:
        return self.telegram_mock_token if self.is_mock else self.telegram_live_token

    @property
    def domain(self) -> str:
        return self.base_url.replace("https://", "")

    @property
    def ws_display_url(self) -> str:
        return self.ws_url.replace("/api/dostk/websocket", "")

    def set_profile(self, profile: str) -> None:
        profile = profile.upper().strip()
        if profile not in {"MOCK", "LIVE"}:
            raise ValueError("profile은 MOCK 또는 LIVE만 가능합니다.")
        self.active_profile = profile
        _set_env_value("KIWOOM_ACTIVE_PROFILE", profile)

    def as_public_dict(self) -> dict:
        return {
            "active_profile": self.active_profile,
            "profile_label": self.profile_label,
            "base_url": self.base_url,
            "ws_url": self.ws_url,
            "ws_display_url": self.ws_display_url,
            "app_expires_at": self.app_expires_at,
            "telegram_enabled": bool(self.telegram_chat_id and self.telegram_token),
            "auto_trade_enabled": self.auto_trade_enabled,
            "emergency_stop": self.emergency_stop,
            "fee_rate": self.fee_rate,
            "tax_rate": self.tax_rate,
            "daily_loss_limit": self.daily_loss_limit,
            "max_positions": self.max_positions,
            "per_trade_risk_rate": self.per_trade_risk_rate,
            "target_investment_rate": self.target_investment_rate,
            "max_target_investment_rate": self.max_target_investment_rate,
            "rebalance_cycle": self.rebalance_cycle,
            "selected_strategy_group": self.selected_strategy_group,
            "my_strategy_enhanced": self.my_strategy_enhanced,
            "operating_flow": self.operating_flow,
            "top_n_selection": self.top_n_selection,
            "min_backtest_sharpe": self.min_backtest_sharpe,
            "max_mdd_limit": self.max_mdd_limit,
            "volatility_cutoff_rate": self.volatility_cutoff_rate,
        }

settings = QuantSettings()

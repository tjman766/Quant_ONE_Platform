@dataclass
class Settings:
    active_profile: str = "MOCK"

    mock_app_key: str = ""
    mock_app_secret: str = ""
    mock_app_expires_at: str = ""

    live_app_key: str = ""
    live_app_secret: str = ""
    live_app_expires_at: str = ""

    mock_base_url: str = "https://mockapi.kiwoom.com"
    live_base_url: str = "https://api.kiwoom.com"

    mock_ws_url: str = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
    live_ws_url: str = "wss://api.kiwoom.com:10000/api/dostk/websocket"

    telegram_chat_id: str = ""
    telegram_mock_token: str = ""
    telegram_live_token: str = ""

    quant_fee_rate: float = 0.00015
    quant_tax_rate: float = 0.0018

    daily_loss_limit: float = 0.02

    auto_trade_enabled: bool = True
    emergency_stop: bool = False

    max_positions: int = 20
    per_trade_risk_rate: float = 0.005

    target_investment_rate: float = 0.90
    max_target_investment_rate: float = 0.95

    rebalance_cycle: str = "MONTHLY"

    top_n_selection: int = 20

    min_backtest_sharpe: float = 0.8
    max_mdd_limit: float = 0.20
    volatility_cutoff_rate: float = 0.035

    selected_strategy_group: str = "FOUR_QUANT"
    my_strategy_enhanced: bool = True

    operating_flow: str = "BACKTEST_TO_SELECTED_ACCOUNT_TO_REPORT"
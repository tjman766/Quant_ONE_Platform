from __future__ import annotations
from collections import deque
from datetime import datetime, date
import time
from ..services.settings import settings

# 단일 진실 원천: 실제 Kiwoom REST/Realtime 수신값 + 사용자가 누른 운영 이벤트만 저장한다.
_positions: dict[str, dict] = {}
_account_summary: dict[str, int | float | str] = {}
_events = deque(maxlen=250)
_raw = deque(maxlen=500)
_auto_trades = deque(maxlen=200)
_equity_curve = deque(maxlen=720)
_indices: list[dict] = []
_sectors: list[dict] = []
_strategies: list[list] = [
    ['Trend Following', True, '대기', '0', 0, 0.0],
    ['Breakout', True, '대기', '0', 0, 0.0],
    ['Pullback', True, '대기', '0', 0, 0.0],
    ['Reversal/Contrarian', True, '대기', '0', 0, 0.0],
    ['Value Investing', True, '대기', '0', 0, 0.0],
    ['가치평가/배당', True, '대기', '0', 0, 0.0],
    ['Event Driven', True, '대기', '0', 0, 0.0],
    ['DCA', True, '대기', '0', 0, 0.0],
    ['알고리즘/메타전략', True, '대기', '0', 0, 0.0],
    ['Pair Trading', True, '대기', '0', 0, 0.0],
    ['Overnight', True, '대기', '0', 0, 0.0],
    ['재료/뉴스', True, '대기', '0', 0, 0.0],
]
_lifecycle_log = deque(maxlen=80)
_report_cards: list[dict] = []
_last_backup_time = datetime.now().strftime('%H:%M:%S')
_current_profile_marker = settings.active_profile

_MARKET_ITEM_LABELS = {
    '001': '코스피', '101': '코스닥', '201': '코스피200', '000': '전체',
    '002': '대형주', '003': '중형주', '004': '소형주',
    '301': '제조업', '302': '건설업', '303': '금융업', '304': '전기전자', '305': '화학',
}


EXCLUSION_CARDS = [
    {'key':'delisted','label':'상장폐지','enabled':True,'desc':'상장폐지/관리종목성 리스크 종목 자동 제외'},
    {'key':'theme','label':'테마주','enabled':False,'desc':'단기 테마 급등 종목 제외'},
    {'key':'penny','label':'동전주','enabled':False,'desc':'저가·저유동성 종목 제외'},
    {'key':'auto_adjust','label':'제외종목 자동 조정','enabled':True,'desc':'실시간 조건 변화에 따라 제외 여부 자동 갱신'},
    {'key':'watchlist','label':'관리종목','enabled':True,'desc':'거래소 관리/주의성 종목 제외'},
    {'key':'high_risk','label':'투자경고/위험','enabled':True,'desc':'투자주의·경고·위험 종목 제외'},
    {'key':'preferred','label':'우선주','enabled':True,'desc':'우선주 제외'},
    {'key':'collateral_block','label':'담보대출불가능종목','enabled':False,'desc':'담보대출 불가 종목 제외'},
    {'key':'margin100','label':'증거금 100% 종목','enabled':False,'desc':'현금증거금 100% 종목 제외'},
    {'key':'halt','label':'거래정지','enabled':True,'desc':'거래정지 종목 제외'},
    {'key':'invest_notice','label':'투자주의','enabled':True,'desc':'투자주의 종목 제외'},
    {'key':'hot','label':'환기종목','enabled':True,'desc':'환기종목 제외'},
    {'key':'cleanup','label':'정리매매','enabled':True,'desc':'정리매매 종목 제외'},
    {'key':'bad_disclosure','label':'불성실공시기업','enabled':True,'desc':'불성실공시 지정 기업 제외'},
    {'key':'overheat_short','label':'단기과열종목','enabled':False,'desc':'단기과열 완화장치 발동 종목 제외'},
    {'key':'shareable','label':'대주가능종목','enabled':False,'desc':'대주 가능 여부 조건'},
    {'key':'etf','label':'ETF','enabled':True,'desc':'ETF 매매 허용/제외 조건'},
    {'key':'spac','label':'스팩','enabled':False,'desc':'SPAC 종목 제외'},
    {'key':'etn','label':'ETN','enabled':True,'desc':'ETN 매매 허용/제외 조건'},
    {'key':'low_liquidity','label':'초저유동성종목','enabled':False,'desc':'거래량/대금 부족 종목 제외'},
    {'key':'dividend락','label':'배당락종목','enabled':False,'desc':'배당락 영향 구간 제외'},
    {'key':'rights락','label':'권리락종목','enabled':False,'desc':'권리락 영향 구간 제외'},
    {'key':'abnormal_surge','label':'이상급등종목','enabled':False,'desc':'비정상 급등 종목 제외'},
    {'key':'short_overheat','label':'공매도과열종목','enabled':False,'desc':'공매도 과열 지정 종목 제외'},
    {'key':'overheat_notice','label':'단기과열예고종목','enabled':False,'desc':'단기과열 예고 종목 제외'},
    {'key':'warning_notice','label':'경고예고종목','enabled':False,'desc':'투자경고 예고 종목 제외'},
]

INVESTMENT_TYPES = [
    {'유형':'초단타','기간':'≤ 5분','목표수익률':'≤ 1.5%','종목당비중':'1%','동시보유':'1~3개','현금비중':'90% 이상','매수금지':'수수료+세금+0.3% 이하'},
    {'유형':'단타','기간':'≤ 1일','목표수익률':'2~3%','종목당비중':'3%','동시보유':'3~5개','현금비중':'70% 이상','매수금지':'예상 수익 2.5% 이하'},
    {'유형':'단기','기간':'≤ 5일','목표수익률':'5~8%','종목당비중':'5%','동시보유':'5~10개','현금비중':'30~50%','매수금지':'예상 수익 4.5% 이하'},
    {'유형':'중단기','기간':'≤ 22일','목표수익률':'12~15%','종목당비중':'10%','동시보유':'7~10개','현금비중':'20%','매수금지':'예상 수익 7% 이하'},
    {'유형':'중장기','기간':'≤ 77일','목표수익률':'25~30%','종목당비중':'15%','동시보유':'5~7개','현금비중':'10%','매수금지':'예상 수익 12% 이하'},
    {'유형':'장기','기간':'≤ 156일','목표수익률':'40% 이상','종목당비중':'20%','동시보유':'4~5개','현금비중':'5%','매수금지':'예상 수익 20% 이하'},
]



AUTO_OPERATION_POLICY = [
    {'구분':'1. 운용 단계','적용':'백테스트 → 모의투자 계좌 주문 → 결과 리포트 또는 백테스트 → 실전투자 계좌 주문 → 결과 리포트','자동매매 메뉴':'운용 상태 통합표','판정':'모의/실전은 상단 전환 버튼(KIWOOM_ACTIVE_PROFILE)으로 사용자가 수동 선택'},
    {'구분':'2. 모의 실계좌 주문','적용':'KIWOOM_ACTIVE_PROFILE=MOCK이면 키움 모의투자 계좌에 kt10000/kt10001 주문 API를 실제 전송','자동매매 메뉴':'계좌 주문 실행 상태','판정':'주문차단 없는 모의/실전 프로필 기반 차단값 없이 모의투자 계좌 체결 흐름 검증'},
    {'구분':'3. 실전 투자 주문','적용':'KIWOOM_ACTIVE_PROFILE=LIVE이면 실전 계좌에 동일 구조로 주문 API 전송','자동매매 메뉴':'상단 모의/실전 전환 카드','판정':'모의와 실전의 프로그램 구조는 동일, 계좌/도메인만 전환'},
    {'구분':'4. 리밸런싱','적용':'월/분기/반기/연간/시즌제 중 선택한 주기로 보유 종목을 목표 포트폴리오와 다시 맞춤','자동매매 메뉴':'통합 운용 정책 표','판정':'상위 N 이탈·점수 하락·손절·비중 초과·주기 도래 시 교체'},
    {'구분':'5. 상위 N개 편입','적용':'유동성, 추세, 모멘텀, 퀄리티, 저변동성, 손익비 점수로 TOP_N_SELECTION개 후보 선정','자동매매 메뉴':'전략 비교/운용 상태 표','판정':'기본 20개, 급변장에는 신규 편입 축소 및 보유비중 감액'},
    {'구분':'6. 현금버퍼','적용':'총자산의 90~95%까지만 투자하고 5~10%는 미체결·추가매수·급락 대응 현금으로 남김','자동매매 메뉴':'자금/리스크 표','판정':'TARGET_INVESTMENT_RATE=0.90, MAX_TARGET_INVESTMENT_RATE=0.95'},
    {'구분':'7. 결과 리포트','적용':'백테스트/모의/실전 결과를 수익률, MDD, 승률, 손익비, 체결률, 리밸런싱 효과로 기록','자동매매 메뉴':'결과 리포트 상태','판정':'성과 기준 미달 전략은 감액 또는 중지'},
    {'구분':'8. 급변장 방어','적용':'지수/업종 급락, 변동성 3.5% 초과, WebSocket 지연 시 신규매수 차단·보유 축소','자동매매 메뉴':'리스크 경고 연계','판정':'급변장에는 수익 극대화보다 생존/손실 제한 우선'},
]

STRATEGY_COMPARE_POLICY = [
    {'항목':'전략 이름','내 전략':'내 전략','4대 퀀트 전략(기본)':'4대 퀀트 전략(기본)','비교 설명':'둘 중 하나를 선택해 운용하며 기본값은 4대 퀀트 전략'},
    {'항목':'전략 구조','내 전략':'장초반 갭·VWAP 눌림목·급락반등·종가베팅·모멘텀에 공통 리스크/리밸런싱 적용','4대 퀀트 전략(기본)':'모멘텀·가치·퀄리티·저변동성 4요소 점수 합산','비교 설명':'내 전략은 단기 매매형, 4대 퀀트는 포트폴리오 선별형'},
    {'항목':'상위 N 편입','내 전략':'O · 신호 발생 종목을 점수화해 TOP N만 편입','4대 퀀트 전략(기본)':'O · 4요소 종합점수 TOP N 편입','비교 설명':'둘 다 TOP_N_SELECTION 사용'},
    {'항목':'리밸런싱','내 전략':'O · 월/분기/반기/연간/시즌제 적용','4대 퀀트 전략(기본)':'O · 월/분기/반기/연간/시즌제 적용','비교 설명':'둘 다 같은 주기 엔진 사용'},
    {'항목':'현금버퍼','내 전략':'O · 총자산 90~95% 투자, 5~10% 현금 유지','4대 퀀트 전략(기본)':'O · 총자산 90~95% 투자, 5~10% 현금 유지','비교 설명':'급변장·미체결·추가매수 대응'},
    {'항목':'손절','내 전략':'O · 종목별 변동성/손익비 기반 손절','4대 퀀트 전략(기본)':'O · 변동성/점수훼손/MDD 기반 손절','비교 설명':'고정 손절보다 시장 상태 반영'},
    {'항목':'익절','내 전략':'O · 목표가/추세 둔화/거래량 약화 시 분할 익절','4대 퀀트 전략(기본)':'O · 목표수익·추세훼손·리밸런싱 시 익절','비교 설명':'둘 다 단순 고정 익절이 아니라 조건형'},
    {'항목':'시장필터','내 전략':'O · 지수/업종/변동성/거래대금 필터 적용','4대 퀀트 전략(기본)':'O · 지수/업종/변동성/거래대금 필터 적용','비교 설명':'급락장 신규매수 차단'},
    {'항목':'리스크관리','내 전략':'O · 일손실, 종목당 손실, 최대보유, 비중 제한','4대 퀀트 전략(기본)':'O · 일손실, 종목당 손실, 최대보유, 비중 제한','비교 설명':'주문 전 공통 게이트'},
    {'항목':'급락장 대응','내 전략':'O · 신규매수 축소, 손절 강화, 현금비중 확대','4대 퀀트 전략(기본)':'O · 신규매수 축소, 저변동성 비중 확대','비교 설명':'내 전략은 빠른 방어, 4대 퀀트는 포트폴리오 안정화'},
    {'항목':'급등장 대응','내 전략':'O · 추격매수 제한, 분할익절, 과열 필터','4대 퀀트 전략(기본)':'O · 과열 종목 제외, 점수 유지 종목만 보유','비교 설명':'과열 추격 방지'},
    {'항목':'전략점수','내 전략':'O · 신호강도+거래대금+추세+손익비+변동성','4대 퀀트 전략(기본)':'O · 모멘텀+가치+퀄리티+저변동성','비교 설명':'점수 기준은 다르지만 선별 방식은 동일'},
]

OPERATION_STATUS_POLICY = [
    {'구분':'선택 전략','내용':'내 전략 / 4대 퀀트 전략(기본) 중 선택, 기본값은 4대 퀀트 전략'},
    {'구분':'운용 단계 A','내용':'백테스트 → 모의투자 계좌 주문 → 결과 리포트'},
    {'구분':'운용 단계 B','내용':'백테스트 → 실전투자 계좌 주문 → 결과 리포트'},
    {'구분':'모의/실전 전환','내용':'상단 모의/실전 전환 버튼으로 수동 조정, 프로그램 구조는 동일'},
    {'구분':'리밸런싱','내용':'월 / 분기 / 반기 / 연간 / 시즌'},
    {'구분':'상위 N','내용':'10 / 20 / 30 / 사용자 지정'},
    {'구분':'현금버퍼','내용':'5~10% 현금 유지, 총자산 90~95%만 투자'},
    {'구분':'최대 보유종목','내용':'설정값 MAX_POSITIONS 기준'},
    {'구분':'종목당 비중','내용':'최대보유수와 리스크 허용폭으로 자동 계산'},
    {'구분':'현재 시장 상태','내용':'상승 / 횡보 / 하락 / 급락'},
    {'구분':'시장 필터','내용':'지수·업종·변동성·거래대금 필터 ON/OFF'},
    {'구분':'리스크 등급','내용':'낮음 / 보통 / 높음'},
    {'구분':'리밸런싱 상태','내용':'오늘 완료 / 예정 / 미도래'},
    {'구분':'다음 리밸런싱','내용':'선택 주기 기준 다음 예정일 표시'},
    {'구분':'현재 운용 서버','내용':'MOCK이면 모의투자 계좌, LIVE이면 실전투자 계좌'},
    {'구분':'결과 리포트','내용':'수익률, MDD, 승률, 손익비, 체결률, 리밸런싱 효과 기록'},
]

BUY_SELL_POLICY = [
    {'단계':'후보 선정','매수 기준':'내 전략 또는 4대 퀀트 전략의 전략점수 기준 상위 N개 후보 선정','매도 기준':'TOP N 이탈, 리밸런싱 주기 도래, 점수 훼손','리스크 반영':'관리/거래정지/저유동성/과열 종목 제외'},
    {'단계':'진입 검증','매수 기준':'목표가-매수가 대비 손절폭이 유리하고 현금버퍼 5~10% 유지 가능','매도 기준':'목표가 도달, 손절가 이탈, 일손실 제한 접근','리스크 반영':'종목당 손실한도 0.5%, 일손실 2%, 최대 20종목'},
    {'단계':'주문 실행','매수 기준':'AUTO_TRADE_ENABLED=true + 긴급중지 OFF + 상단 모의/실전 프로필 확인','매도 기준':'보유수량/주문가능수량 확인 후 매도','리스크 반영':'MOCK은 모의투자 계좌 주문, LIVE는 실전투자 계좌 주문'},
    {'단계':'운용 후 검증','매수 기준':'백테스트/모의/실전 결과 리포트가 기준 이상인 전략만 유지','매도 기준':'전략 성과 악화, MDD 확대, 연속 손실 발생 시 감액/중지','리스크 반영':'월/분기/반기/연간/시즌제 리밸런싱으로 구조적 교체'},
]

REALTIME_API_POLICY = [
    {'기능':'OAuth','API':'au10001 접근토큰 발급','용도':'토큰은 TokenManager 내부 자동 발급/갱신'},
    {'기능':'주문 상태','API':'00 주문체결','용도':'접수·체결·정정·취소·거부 실시간 반영'},
    {'기능':'보유 종목','API':'04 잔고','용도':'보유수량·매입단가·주문가능수량·손익률 반영'},
    {'기능':'실시간 시세','API':'0B 주식체결','용도':'현재가·등락률·거래량·체결강도 반영'},
    {'기능':'현재가 보정','API':'0A 주식기세','용도':'체결 없이 현재가 변동 시 보정'},
    {'기능':'최우선호가','API':'0C 주식우선호가','용도':'최우선 매도/매수호가 반영'},
    {'기능':'10호가','API':'0D 주식호가잔량','용도':'호가잔량·예상체결·잔량비율 반영'},
    {'기능':'시장 지수','API':'0J 업종지수','용도':'코스피·코스닥·코스피200 시장지수 반영'},
    {'기능':'업종 등락률','API':'0U 업종등락','용도':'업종 상승/하락 TOP5 반영'},
]

_state = {
    'ws': 'CONNECTING', 'ws_enabled': True, 'ws_message': '자동 연결 준비',
    'rest': '대기', 'token': 'TokenManager 자동', 'program': '정상', 'last_update': '-',
    'trade_count': 0, 'buy_count': 0, 'sell_count': 0, 'risk_score': 0, 'mdd': 0.0,
    'program_started': False, 'last_live_packet_ts': 0.0, 'last_rest_sync_ts': 0.0,
    'last_packet_visible': False, 'last_visible_reason': '-', 'last_ingest_type': '-',
}

def _now() -> str: return datetime.now().strftime('%H:%M:%S')
def _today() -> str: return datetime.now().strftime('%Y-%m-%d')

def _date_label(kind: str) -> str:
    now = datetime.now()
    if kind == 'daily': return now.strftime('%Y-%m-%d')
    if kind == 'weekly': return f"{now.strftime('%Y')}년 {now.isocalendar().week}주차"
    if kind == 'monthly': return now.strftime('%Y-%m')
    if kind == 'quarterly': return f"{now.year}년 {((now.month-1)//3)+1}분기"
    if kind == 'yearly': return str(now.year)
    return '전체'

def _number(v):
    try:
        if v in (None, ''): return None
        s = str(v).strip().replace(',', '')
        if s in {'-', '+', '00000000'}: return None
        return int(float(s.replace('+','')))
    except Exception: return None

def _float_number(v):
    try:
        if v in (None, ''): return None
        s = str(v).strip().replace(',', '').replace('%','')
        if s in {'-', '+', '00000000'}: return None
        return float(s.replace('+',''))
    except Exception:
        return None

def _abs_float(v):
    n = _float_number(v)
    return abs(n) if n is not None else None

def _abs_number(v):
    n = _number(v)
    return abs(n) if n is not None else None

def _rate(v):
    try:
        if v in (None, ''): return None
        s = str(v).strip().replace('%','').replace(',','').replace('+','')
        if s in {'-', '00000000'}: return None
        return float(s)
    except Exception: return None

def _meaningful(v) -> bool:
    if v in (None, '', '-', '00000000', '0000000'): return False
    try:
        return float(str(v).replace(',', '').replace('+','')) != 0
    except Exception:
        return str(v).strip() not in {'0','0.0','0.00'}

def _normalize_values(values):
    if values is None: return {}
    if isinstance(values, dict):
        for inner in ('values','output','data'):
            if inner in values and isinstance(values.get(inner), (dict, list)):
                base = {str(k).strip(): v for k,v in values.items() if k not in {'values','output','data'}}
                base.update(_normalize_values(values.get(inner)))
                return base
        return {str(k).strip(): v for k,v in values.items()}
    if isinstance(values, list):
        out = {}
        for row in values:
            if isinstance(row, dict):
                key = row.get('key') or row.get('fid') or row.get('id') or row.get('field') or row.get('name')
                val = row.get('value') if 'value' in row else row.get('val') if 'val' in row else row.get('data')
                if key is not None: out[str(key).strip()] = val
                else: out.update(_normalize_values(row))
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                out[str(row[0]).strip()] = row[1]
        return out
    return {}

def _first(values: dict, *keys):
    for k in keys:
        if str(k) in values and values.get(str(k)) not in (None, ''):
            return values.get(str(k))
    return None

def _clean_code(v) -> str:
    raw = str(v or '').strip()
    if raw.startswith(('A','J','Q')) and len(raw) >= 7: raw = raw[1:]
    return raw[-6:] if raw else ''

def add_event(kind: str, message: str) -> None:
    msg = str(message)
    if 'WebSocket 자동 재연결' in msg or '실시간 WebSocket 자동 재연결' in msg:
        _state['last_update'] = _now(); return
    _events.appendleft({'time': _now(), 'kind': kind, 'message': msg})
    _state['last_update'] = _now()

def set_ws_state(status: str, message: str = '', *, enabled: bool | None = None) -> None:
    normalized = 'MANUAL_OFF' if status == 'OFF' else status
    _state['ws'] = normalized
    if enabled is not None: _state['ws_enabled'] = bool(enabled)
    elif normalized != 'MANUAL_OFF': _state['ws_enabled'] = True
    _state['ws_message'] = message or normalized
    _state['last_update'] = _now()
    if message and not ('WebSocket 자동 재연결' in message): add_event('시스템', message)

def set_lifecycle(event_label: str, detail: str = '') -> None:
    _lifecycle_log.appendleft({'time': _now(), 'event': event_label, 'detail': detail})
    if event_label in {'운영 시장 시작','매매 시작'}:
        settings.auto_trade_enabled = True; _state['program_started'] = True
    elif event_label in {'매매 종료','운영 시장 종료'}:
        settings.auto_trade_enabled = False
    add_event('알림', f"{event_label}" + (f" · {detail}" if detail else ''))

def reset_for_profile_switch() -> None:
    global _current_profile_marker, _last_backup_time
    _current_profile_marker = settings.active_profile
    _raw.clear(); _equity_curve.clear(); _positions.clear(); _indices.clear(); _sectors.clear(); _account_summary.clear()
    _last_backup_time = _now()
    _state.update({'trade_count':0,'buy_count':0,'sell_count':0,'last_live_packet_ts':0.0,'last_rest_sync_ts':0.0,'last_packet_visible':False,'last_visible_reason':'프로필 전환 초기화','last_ingest_type':'-'})
    add_event('시스템', f'{settings.profile_label} 자료로 전환 · 이전 프로필 화면 자료 초기화')

def _build_report_cards(force: bool = False) -> None:
    if _report_cards and not force:
        return
    rows,total_eval,total_pnl,_,total_cost = _position_rows()
    total_eval = int(_account_summary.get('총평가금액') or total_eval)
    total_pnl = int(_account_summary.get('총평가손익') or total_pnl)
    orderable = int(_account_summary.get('주문가능금액') or 0)
    total_assets = int(_account_summary.get('총자산') or (orderable + total_eval))
    labels = [('daily','금일'),('weekly','금주'),('monthly','금월'),('quarterly','금분기'),('yearly','금년'),('all','전체')]
    _report_cards.clear()
    for kind,label in labels:
        _report_cards.append({'kind':kind,'label':label,'date':_date_label(kind),'total_assets':total_assets,'pnl':total_pnl,'trades':_state.get('trade_count',0),'buys':_state.get('buy_count',0),'sells':_state.get('sell_count',0),'positions':max(len(rows)-1,0),'generated_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

def mark_backup_now(reason: str = '자동') -> None:
    global _last_backup_time
    _last_backup_time = _now(); _build_report_cards(force=True); add_event('시스템', f'마지막 백업 시간 갱신 · {reason}')

def _position_rows():
    rows=[]; total_eval=0; total_pnl=0; total_orderable_value=0; total_cost=0
    base=[]
    for code,p in _positions.items():
        qty=int(p.get('qty') or 0); price=int(p.get('price') or 0); avg=int(p.get('avg') or 0)
        eval_amt=int(p.get('eval_amt') or qty*price); cost=int(p.get('total_buy') or qty*avg)
        pnl=int(p.get('pnl') if p.get('pnl') is not None else eval_amt-cost)
        orderable_qty=int(p.get('orderable_qty') or 0); fee_tax=int(abs(eval_amt)*(settings.fee_rate+settings.tax_rate)) if eval_amt else 0
        rate=float(p.get('rate') if p.get('rate') is not None else (pnl/cost*100 if cost else 0))
        base.append((code,p,qty,price,avg,eval_amt,cost,pnl,orderable_qty,fee_tax,rate))
        total_eval+=eval_amt; total_pnl+=pnl; total_orderable_value+=orderable_qty*price; total_cost+=cost
    for code,p,qty,price,avg,eval_amt,cost,pnl,orderable_qty,fee_tax,rate in base:
        # 잔고비중은 REST 원본의 정수/반올림값을 그대로 쓰면 소액 보유 종목이 0으로 보일 수 있어
        # 항상 현재 표의 총 평가금액 기준으로 재계산한다. 예: 35,250 / 8,142,050 * 100 = 0.43%.
        bal = (eval_amt / max(total_eval, 1) * 100) if total_eval else 0.0
        rows.append({'종목명':f"{p.get('name', code)}({code})",'보유수량':qty,'주문가능수량':orderable_qty,'매입단가':avg,'현재가':price,'총매입가':cost,'평가금액':eval_amt,'평가손익':pnl,'수익률':rate,'순손익':pnl-fee_tax,'잔고비중':round(float(bal), 2)})
    rows.sort(key=lambda r: float(r.get('순손익') or 0), reverse=True)
    if rows:
        rows.append({'종목명':'합계','보유수량':sum(int(p.get('qty') or 0) for p in _positions.values()),'주문가능수량':sum(int(p.get('orderable_qty') or 0) for p in _positions.values()),'매입단가':'','현재가':'','총매입가':total_cost,'평가금액':total_eval,'평가손익':total_pnl,'수익률':(total_pnl/max(total_cost,1))*100,'순손익':sum(int(r['순손익']) for r in rows),'잔고비중':100.0})
    return rows,total_eval,total_pnl,total_orderable_value,total_cost

def _upsert_position(code: str, name: str, qty: int, avg: int = 0, price: int = 0, total_buy: int | None = None, orderable_qty: int | None = None, eval_amt: int | None = None, pnl: int | None = None, rate: float | None = None, extras: dict | None = None, source: str='', balance_rate: float | None = None) -> bool:
    if not code or qty <= 0:
        if code and code in _positions:
            _positions.pop(code, None); add_event('잔고', f'잔고 제거/청산: {name or code}({code})')
            return True
        return False
    cost = total_buy if total_buy is not None else qty * avg
    ev = eval_amt if eval_amt is not None else qty * price
    pl = pnl if pnl is not None else (ev - cost if ev and cost else 0)
    _positions[code] = {'name': name or code, 'qty': qty, 'orderable_qty': orderable_qty or 0, 'avg': avg or 0, 'price': price or 0, 'total_buy': cost or 0, 'eval_amt': ev or 0, 'pnl': pl or 0, 'rate': rate, 'extras': extras or {}, 'balance_rate': balance_rate}
    rows,total_eval,_,_,_= _position_rows(); _equity_curve.append({'time': _now(), 'value': _account_summary.get('총자산') or total_eval})
    add_event('잔고', f'{source or "잔고"} 반영: {name or code}({code}) {qty:,}주')
    return True

def _upsert_index(name: str, price, change=None, rate=None, code: str='', rtype: str='') -> bool:
    if not (name or code or rtype):
        return False
    code = str(code or '').strip()
    label = str(name or '').strip()
    # 0J는 업종지수이며 item 코드가 지수 구분값이다. name이 단순 '업종지수'로만 오면 item 기준 한글명으로 치환한다.
    if rtype == '0J' or label in {'업종지수', '지수'}:
        label = _MARKET_ITEM_LABELS.get(code, label or code or '업종지수')
    is_index = (
        rtype == '0J'
        or any(k in str(label).lower() for k in ['kospi','kosdaq','코스피','코스닥','kospi200','지수'])
        or code in {'001','101','201','000'}
    )
    if not is_index:
        return False
    for idx in _indices:
        if idx.get('지수') == label or (code and idx.get('코드') == code):
            if price is not None:
                idx['현재'] = float(price)
            if change is not None:
                idx['등락'] = float(change)
            if rate is not None:
                idx['등락률'] = float(rate)
            idx['수신시각'] = _now()
            return True
    _indices.append({'지수': label or code, '코드': code, '현재': float(price or 0), '등락': float(change or 0), '등락률': float(rate or 0), '수신시각': _now()})
    return True

def _upsert_sector(name: str, rate, price=None, change=None, code: str='', rtype: str='') -> bool:
    if rate is None and price is None and change is None:
        return False
    code = str(code or '').strip()
    label = str(name or '').strip()
    if rtype == '0U' or label in {'업종등락', '업종'}:
        label = _MARKET_ITEM_LABELS.get(code, label or code or '업종등락')
    if not label:
        label = _MARKET_ITEM_LABELS.get(code, code or '업종')
    label = label.replace('업종등락','').replace('업종지수','').strip() or label
    for sec in _sectors:
        if sec.get('업종') == label or (code and sec.get('코드') == code):
            if rate is not None:
                sec['등락률'] = float(rate)
            if price is not None:
                sec['현재'] = float(price)
            if change is not None:
                sec['등락'] = float(change)
            sec['수신시각'] = _now()
            return True
    _sectors.append({'업종': label, '코드': code, '현재': float(price or 0), '등락': float(change or 0), '등락률': float(rate or 0), '수신시각': _now()})
    return True


def _strategy_name_for_code(code: str) -> str:
    if not code:
        return '-'
    try:
        idx = abs(hash(code)) % max(len(_strategies), 1)
        return _strategies[idx][0]
    except Exception:
        return '-'

def _update_strategy_from_trade(row: dict) -> None:
    name = row.get('전략') or '-'
    if name == '-' or name == '수동':
        return
    for s in _strategies:
        if s[0] == name:
            s[2] = str(row.get('상태') or '수신')
            s[3] = str(row.get('종목') or '0')
            return

def ingest_rest_market(api_id: str, payload: dict, source_code: str = '') -> None:
    data = payload.get('json', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return
    _raw.appendleft({'source':'REST','api_id':api_id,'json':data})
    rows = data.get('all_inds_idex') or data.get('전업종지수') or []
    visible = False
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        code = str(r.get('stk_cd') or r.get('종목코드') or '').strip()
        name = r.get('stk_nm') or r.get('종목명') or _MARKET_ITEM_LABELS.get(code, code)
        price = _abs_float(r.get('cur_prc') or r.get('현재가'))
        change = _float_number(r.get('pred_pre') or r.get('전일대비'))
        rate = _float_number(r.get('flu_rt') or r.get('등락률'))
        if code in {'001','101','201'} or name in {'종합(KOSPI)','종합(KOSDAQ)','코스피200'}:
            visible = _upsert_index(str(name).replace('종합(KOSPI)','코스피').replace('종합(KOSDAQ)','코스닥'), price, change, rate, code, 'ka20003') or visible
        else:
            visible = _upsert_sector(name, rate, price, change, code, 'ka20003') or visible
    if visible:
        _state['last_rest_sync_ts']=time.time(); _state['last_update']=_now(); add_event('시장', f'{api_id} 업종등락률/시장지수 반영 완료 · {source_code or "전체"}')

def ingest_realtime_packet(packet: dict) -> None:
    _state['ws']='CONNECTED'; _state['last_update']=_now(); _state['last_live_packet_ts']=time.time(); _raw.appendleft(packet)
    visible=False; types=[]
    if isinstance(packet.get('data'), list) and packet['data']:
        for item in packet['data']:
            if isinstance(item, dict):
                ok, rt = _ingest_values(item.get('values') or {}, item)
                visible = visible or ok; types.append(rt)
    else:
        ok, rt = _ingest_values(packet.get('values') if isinstance(packet.get('values'), dict) else packet, packet)
        visible = visible or ok; types.append(rt)
    _state['last_packet_visible'] = visible
    _state['last_visible_reason'] = '화면 반영 완료' if visible else f'표시 대상 필드 미검출: {types or ["-"]}'
    _state['last_ingest_type'] = ','.join([t for t in types if t]) or '-'
    if not visible:
        add_event('시스템', _state['last_visible_reason'])

def _ingest_values(values: dict, meta: dict) -> tuple[bool, str]:
    meta=meta or {}; values=_normalize_values(values)
    meta_fields=_normalize_values({k:v for k,v in meta.items() if k not in {'values','data'}})
    for k,v in meta_fields.items(): values.setdefault(k,v)
    rtype=str(meta.get('type') or values.get('type') or meta.get('api_id') or values.get('api_id') or '').strip()
    code=_clean_code(_first(values,'9001','종목코드','업종코드','item','code','stk_cd') or meta.get('item'))
    name=_first(values,'302','종목명','stk_nm','name','업종명','지수명','20') or meta.get('name') or ''
    price=_abs_float(_first(values,'10','현재가','price','cur_prc','910','체결가','현재','지수','업종지수')) or 0

    if rtype == 'manual_order_intent' or _first(values, 'side'):
        side_text = _first(values, 'side') or '-'
        qty = _abs_number(_first(values, 'qty')) or ''
        order_price = _abs_number(_first(values, 'price')) or ''
        trade_row = {'시간': _now(), '구분': '수동주문', '전략': '수동', '종목': f'{name or code}({code})' if code else (name or '-'), '매수매도': side_text, '수량': qty, '가격': order_price, '상태': '주문 의도 등록'}
        _auto_trades.appendleft(trade_row)
        add_event('주문', f'수동주문 의도: {trade_row["종목"]} {side_text} {qty}')
        return True, 'manual_order_intent'
    # 04 잔고
    if rtype=='04' or any(k in values for k in ('930','931','932','933','8019')):
        qty=_abs_number(_first(values,'930','보유수량')) or 0
        avg=_abs_number(_first(values,'931','매입단가')) or 0
        total_buy=_abs_number(_first(values,'932','총매입가','총매입가(당일누적)'))
        orderable=_abs_number(_first(values,'933','주문가능수량'))
        pnl=_number(_first(values,'950','당일총매도손익'))
        rate=_rate(_first(values,'8019','손익률','손익률(실현손익)'))
        extras={k:v for k,v in {'신용구분':_first(values,'917','신용구분'),'대출일':_first(values,'916','대출일'),'당일순매수량':_first(values,'945','당일순매수량'),'매도/매수구분':_first(values,'946','매도/매수구분'),'매도호가':_first(values,'27','매도호가'),'매수호가':_first(values,'28','매수호가'),'기준가':_first(values,'307','기준가'),'실현손익률':_first(values,'8019','손익률')}.items() if _meaningful(v)}
        return _upsert_position(code,name,qty,avg,price,total_buy,orderable,qty*price if qty and price else None,pnl,rate,extras,'04 잔고'), rtype or '04'
    # 00 주문체결
    order_state=_first(values,'913','주문상태'); side_text=_first(values,'905','주문구분','side')
    if order_state or side_text:
        _state['trade_count']+=1; side=str(side_text or '')
        if '매수' in side or side.upper()=='BUY': _state['buy_count']+=1
        if '매도' in side or side.upper()=='SELL': _state['sell_count']+=1
        trade_row = {'시간': _now(), '구분': rtype or '00', '전략': _strategy_name_for_code(code), '종목': f'{name or code}({code})' if code else (name or '-'), '매수매도': side_text or '-', '수량': _abs_number(_first(values,'900','911','주문수량','체결량')) or '', '가격': _abs_number(_first(values,'901','910','주문가격','체결가')) or '', '상태': order_state or '수신'}
        _auto_trades.appendleft(trade_row)
        _update_strategy_from_trade(trade_row)
        add_event('매매', f'[{order_state or "수신"}] {name or code} {side_text or ""}')
        return True, rtype or '00'
    # 0B 등: 보유종목 현재가 / 지수 / 업종 반영
    display=str(name or _first(values,'20','업종명','지수명','name','item_nm') or meta.get('name') or '')
    change=_number(_first(values,'11','전일대비','등락','change','대비기호'))
    rate=_rate(_first(values,'12','등락률','등락율','rate','전일대비율','업종등락률'))
    visible=False
    # 시장지수/업종 값은 실제 실시간 원문에서 들어오는 명칭·타입·코드를 최대한 넓게 인식한다.
    visible = _upsert_index(display, price, change, rate, code, rtype) or visible
    if (display or code) and rtype != '0J' and (rtype in {'0U','0g','0G'} or any(k in display for k in ['업종','테마','섹터','전기전자','금융','화학','운수','제조','코스피','코스닥','대형주','중형주','소형주'])):
        visible = _upsert_sector(display, rate, price, change, code, rtype) or visible
    if code and price and code in _positions:
        p=_positions[code]; qty=int(p.get('qty') or 0); cost=int(p.get('total_buy') or 0); ev=qty*price
        p.update({'price':price,'eval_amt':ev,'pnl':ev-cost if cost else p.get('pnl',0)})
        add_event('시세', f'보유종목 현재가 갱신: {p.get("name",code)}({code}) {price:,}원')
        visible=True
    if visible:
        rows,total_eval,_,_,_= _position_rows(); _equity_curve.append({'time': _now(), 'value': _account_summary.get('총자산') or total_eval})
    return visible, rtype

def ingest_rest_account(api_id: str, payload: dict) -> None:
    """REST 잔고/계좌 조회 결과를 웹창 상태 저장소에 직접 반영한다."""
    data = payload.get('json', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict): return
    _raw.appendleft({'source':'REST','api_id':api_id,'json':data}); _state['rest']='정상'; _state['last_rest_sync_ts']=time.time(); _state['last_update']=_now()
    visible=False
    if api_id == 'kt00018':
        m={'tot_pur_amt':'총매입금액','tot_evlt_amt':'총평가금액','tot_evlt_pl':'총평가손익','prsm_dpst_aset_amt':'총자산'}
        for k,ko in m.items():
            n=_number(data.get(k));
            if n is not None: _account_summary[ko]=n; visible=True
        rows=data.get('acnt_evlt_remn_indv_tot') or data.get('계좌평가잔고개별합산') or []
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict): continue
            code=_clean_code(r.get('stk_cd') or r.get('종목번호')); qty=_abs_number(r.get('rmnd_qty') or r.get('보유수량')) or 0
            if qty<=0: continue
            visible = _upsert_position(code, r.get('stk_nm') or r.get('종목명') or code, qty, _abs_number(r.get('pur_pric') or r.get('매입가')) or 0, _abs_number(r.get('cur_prc') or r.get('현재가')) or 0, _abs_number(r.get('pur_amt') or r.get('매입금액')), _abs_number(r.get('trde_able_qty') or r.get('매매가능수량')), _abs_number(r.get('evlt_amt') or r.get('평가금액')), _number(r.get('evltv_prft') or r.get('평가손익')), _rate(r.get('prft_rt') or r.get('수익률(%)')), {'신용구분명':r.get('crd_tp_nm')}, 'REST 계좌평가', _rate(r.get('poss_rt') or r.get('보유비중'))) or visible
    elif api_id == 'kt00005':
        m={'ord_alowa':'주문가능금액','evlt_amt_tot':'총평가금액','tot_pl_tot':'총평가손익','tot_re_buy_alowa':'재매수가능금액','stk_buy_tot_amt':'총매입금액'}
        for k,ko in m.items():
            n=_number(data.get(k));
            if n is not None: _account_summary[ko]=n; visible=True
        rows=data.get('stk_cntr_remn') or data.get('종목별체결잔고') or []
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict): continue
            code=_clean_code(r.get('stk_cd') or r.get('종목번호')); qty=_abs_number(r.get('cur_qty') or r.get('현재잔고') or r.get('setl_remn')) or 0
            if qty<=0: continue
            visible = _upsert_position(code, r.get('stk_nm') or r.get('종목명') or code, qty, _abs_number(r.get('buy_uv') or r.get('매입단가')) or 0, _abs_number(r.get('cur_prc') or r.get('현재가')) or 0, _abs_number(r.get('pur_amt') or r.get('매입금액')), None, _abs_number(r.get('evlt_amt') or r.get('평가금액')), _number(r.get('evltv_prft') or r.get('평가손익')), _rate(r.get('pl_rt') or r.get('손익률')), {'신용구분':r.get('crd_tp'),'대출일':r.get('loan_dt'),'만기일':r.get('expr_dt')}, 'REST 체결잔고') or visible
    if visible:
        rows,total_eval,_,_,_= _position_rows(); _equity_curve.append({'time':_now(), 'value':_account_summary.get('총자산') or total_eval})
        add_event('계좌', f'{api_id} REST 계좌/잔고 화면 반영 완료')

def _d_day(exp: str) -> str:
    if not exp: return '미설정'
    try:
        target=datetime.strptime(exp[:10], '%Y-%m-%d').date(); days=(target-date.today()).days
        return f'D-{days}' if days>=0 else f'D+{abs(days)}'
    except Exception: return '확인필요'

def _schedule_rows():
    now=datetime.now(); wd=now.weekday(); t=now.time()
    if wd>=5:
        return [['휴일/주말','종일','휴장','자동매매 진입 차단 · WebSocket/토큰은 대기 감시']]
    def st(start,end=None):
        h,m=map(int,start.split(':')); s=t.replace(hour=h,minute=m,second=0,microsecond=0)
        if end:
            eh,em=map(int,end.split(':')); e=t.replace(hour=eh,minute=em,second=0,microsecond=0)
            return '진행중' if s<=t<=e else ('완료' if t>e else '대기')
        return '완료' if t>=s else '대기'
    return [['장 시작','09:00 – 09:01',st('09:00','09:01'),'운영 시장 시작 알림'],['정규장','09:00 – 15:30',st('09:00','15:30'),'실시간 감시/전략 실행'],['장 종료','15:30 – 15:40',st('15:30','15:40'),'매매 종료 준비'],['일일 리포트','16:01 – 16:05',st('16:01','16:05'),'금일 리포트 발송'],['로그 압축','16:03 – 16:10',st('16:03','16:10'),'운영 로그 정리']]


def position_codes() -> list[str]:
    """현재 웹창 상태 저장소에 반영된 보유 종목 코드 목록."""
    return [c for c, p in _positions.items() if c and int(p.get('qty') or 0) > 0]

def ingest_rest_price(api_id: str, payload: dict, code_hint: str = '') -> None:
    """REST 현재가 보강값을 기존 보유종목에만 반영한다.
    샘플/가짜 종목은 만들지 않고, 보유 중인 코드의 현재가·평가손익만 갱신한다.
    """
    data = payload.get('json', payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return
    values = _normalize_values(data)
    code = _clean_code(_first(values, 'stk_cd', '종목코드', '9001') or code_hint)
    if not code or code not in _positions:
        return
    price = _abs_number(_first(values, 'cur_prc', '현재가', '10'))
    if not price:
        return
    p = _positions[code]
    qty = int(p.get('qty') or 0)
    cost = int(p.get('total_buy') or qty * int(p.get('avg') or 0))
    ev = qty * price
    p.update({'price': price, 'eval_amt': ev, 'pnl': ev - cost if cost else p.get('pnl', 0)})
    if cost:
        p['rate'] = (int(p.get('pnl') or 0) / max(cost, 1)) * 100
    _state['last_rest_sync_ts'] = time.time()
    _state['last_update'] = _now()
    _raw.appendleft({'source': 'REST', 'api_id': api_id, 'code': code, 'json': data})
    rows, total_eval, total_pnl, _, _ = _position_rows()
    if total_eval:
        _account_summary['총평가금액'] = total_eval
        _account_summary['총평가손익'] = total_pnl
    _equity_curve.append({'time': _now(), 'value': _account_summary.get('총자산') or total_eval})


def _backtest_summary(total_cost: int, total_pnl: int, total_eval: int) -> list[dict]:
    base = max(total_cost, 1)
    rt = (total_pnl / base) * 100 if total_cost else 0.0
    dd = float(_state.get('mdd') or 0)
    beta_warn = '감시' if _indices else '수신대기'
    return [
        {'검증':'Train/Validation/Test','상태':'대기' if not _equity_curve else '작동', '설명':'저장 틱/실시간 자산추이 기반 시간분할 검증 준비'},
        {'검증':'Walk-forward','상태':'대기' if len(_equity_curve) < 2 else '작동', '설명':'누적 자산 추이로 기간 이동형 재검증'},
        {'검증':'민감도/견고성','상태':'감시', '설명':f'현재 누적 수익률 {rt:+.2f}% 기준'},
        {'검증':'자산배분 리스크','상태':beta_warn, '설명':f'평가금액 {total_eval:,}원 · Drawdown {dd:.2f}% · 시장지수 {len(_indices)}개'},
    ]

def dashboard_snapshot() -> dict:
    rows,total_eval,total_pnl,total_orderable_value,total_cost=_position_rows()
    total_eval=int(_account_summary.get('총평가금액') or total_eval)
    total_pnl=int(_account_summary.get('총평가손익') or total_pnl)
    orderable=int(_account_summary.get('주문가능금액') or total_orderable_value)
    total_assets=int(_account_summary.get('총자산') or (orderable+total_eval))
    cash=int(_account_summary.get('예수금') or orderable)
    if (_state.get('last_live_packet_ts') or _state.get('last_rest_sync_ts')) and (not _equity_curve or _equity_curve[-1].get('value') != total_assets):
        _equity_curve.append({'time': _now(), 'value': total_assets})
    ws_connected=_state.get('ws') in {'CONNECTED','WAITING','ON'}; ws_on=bool(_state.get('ws_enabled')) and _state.get('ws')!='MANUAL_OFF'
    last_live_age=round(time.time()-_state.get('last_live_packet_ts',0.0),1) if _state.get('last_live_packet_ts') else None
    last_rest_age=round(time.time()-_state.get('last_rest_sync_ts',0.0),1) if _state.get('last_rest_sync_ts') else None
    app_expire=settings.app_expires_at or '미설정'
    if datetime.now().time().hour >= 16 or any(x.get('event') in {'운영 시장 종료','매매 종료'} for x in list(_lifecycle_log)[:5]):
        _build_report_cards(force=not bool(_report_cards))
    return {'time':_now(),'date':_today(),'version':'v27.40-sticky-title-mask-formula-align','mode':settings.profile_label,'active_profile':settings.active_profile,'domain':settings.base_url.replace('https://',''),'ws_url':settings.ws_display_url,'full_ws_url':settings.ws_url,'app_expire':app_expire,'d_day':_d_day(app_expire),'settings':settings.as_public_dict(),'status':{**_state,'market':'휴장' if datetime.now().weekday()>=5 else ('장중' if any(r[2]=='진행중' for r in _schedule_rows()) else '대기'),'auto':'ON' if settings.auto_trade_enabled else 'OFF','ws_on':ws_on,'ws_connected':ws_connected,'last_live_age':last_live_age,'last_rest_age':last_rest_age},'positions':rows,'position_count':f'{max(len(rows)-1,0)}/20','summary':{'총평가금액':total_eval,'총평가손익':total_pnl,'예수금':cash,'주문가능금액':orderable,'총자산':total_assets,'일일손익':total_pnl,'거래':_state['trade_count'],'매수':_state['buy_count'],'매도':_state['sell_count']},'strategies':[{'전략명':s[0],'상태':'ON' if s[1] else 'OFF','신호':s[2],'포지션':s[3],'금일 손익':s[4],'수익률':s[5],'금일손익':s[4],'최근성과':s[5]} for s in _strategies],'events':list(_events)[:30],'schedule':_schedule_rows(),'indices':_indices,'sectors_up':sorted(_sectors,key=lambda x:x['등락률'],reverse=True)[:5],'sectors_down':sorted(_sectors,key=lambda x:x['등락률'])[:5],'sectors':sorted(_sectors,key=lambda x:x['등락률'],reverse=True)[:5],'equity_curve':list(_equity_curve),'account':{'계좌번호':'실제 조회값만 표시','예수금':cash,'총매입금액':total_cost,'평가금액':total_eval,'총자산':total_assets,'수익률':(total_pnl/max(total_cost,1))*100,'출금가능금액':cash},'other':{'접속서버':settings.domain,'WebSocket':settings.ws_display_url,'DB상태':'연결됨','자동운영':'병용','DB버전':'v1','마지막백업':_last_backup_time},'lifecycle':list(_lifecycle_log)[:20],'report_cards':list(_report_cards),'rules':INVESTMENT_TYPES,'exclusions':EXCLUSION_CARDS,'api_policy':REALTIME_API_POLICY,'auto_trades':list(_auto_trades)[:50],'backtest_summary':_backtest_summary(total_cost,total_pnl,total_eval),'auto_operation_policy':AUTO_OPERATION_POLICY,'buy_sell_policy':BUY_SELL_POLICY,'strategy_compare_policy':STRATEGY_COMPARE_POLICY,'operation_status_policy':OPERATION_STATUS_POLICY,'raw':list(_raw)[:50]}

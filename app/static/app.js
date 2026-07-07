let last = {};
let lastEventKey = "";
let sectorMode = "up";
let selectedPositionKey = "";
let positionSortDir = "desc";
const positionPriceHistory = {};
const nf = new Intl.NumberFormat('ko-KR');
const tabs = document.querySelectorAll('.tab');
tabs.forEach(t => t.onclick = () => {
  tabs.forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.getElementById(t.dataset.tab).classList.remove('hidden');
  requestAnimationFrame(fitOneLineCards);
  setTimeout(fitOneLineCards, 80);
});
function money(v){ return nf.format(Math.round(Number(v || 0))); }
function pct(v){ v = Number(v || 0); return (v > 0 ? '+' : '') + v.toFixed(2) + '%'; }
function cls(v){ return Number(v) > 0 ? 'red' : Number(v) < 0 ? 'blue' : ''; }
function notice(msg){ toast.textContent = msg; toast.style.display = 'block'; setTimeout(()=>toast.style.display='none', 4200); }
function fmt(k,v){
  if(k === '상태') return `<span class="badge ${v === 'OFF' ? 'gray' : ''}">${v}</span>`;
  if(v === null || v === undefined || v === '' || v === '00000000') return '';
  if(typeof v === 'number'){
    const signKeys = ['평가손익','순손익','금일 손익','금일손익','등락','일일손익'];
    if(k === '잔고비중') return Number(v || 0).toFixed(2) + '%';
    if(v === 0 && !['종목명'].includes(k)) return '';
    if(k.includes('률') || k.includes('성과')) return pct(v);
    return (v > 0 && signKeys.some(x=>k.includes(x)) ? '+' : '') + money(v);
  }
  return v ?? '';
}
function rowValue(r,h){
  if(!r) return '';
  if(Object.prototype.hasOwnProperty.call(r,h)) return r[h];
  const key = Object.keys(r).find(k => k.replace(/\s+/g,'') === h.replace(/\s+/g,''));
  return key ? r[key] : '';
}
function splitStockLabel(label){
  const text = String(label || '');
  const m = text.match(/^(.*)\(([^()]+)\)$/);
  return {name: m ? m[1] : text, code: m ? m[2] : text};
}
function escAttr(v){ return String(v ?? '').replaceAll('&','&amp;').replaceAll('\"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
function capturePositionPrices(rows){
  (rows || []).forEach(r => {
    const label = rowValue(r,'종목명');
    if(!label || label === '합계') return;
    const {code,name} = splitStockLabel(label);
    const price = Number(rowValue(r,'현재가') || 0);
    if(!price) return;
    const key = code || name;
    if(!positionPriceHistory[key]) positionPriceHistory[key] = [];
    const arr = positionPriceHistory[key];
    const now = new Date();
    const t = now.toLocaleTimeString('ko-KR', {hour12:false});
    if(!arr.length || arr[arr.length-1].value !== price){
      arr.push({time:t, value:price, name, code});
      if(arr.length > 240) arr.shift();
    }
    if(!selectedPositionKey) selectedPositionKey = key;
  });
}
function selectPositionChart(key){ selectedPositionKey = key; renderPositionPriceChart(); }
function tableCellClass(id, r, h, v){
  if(id === 'positions' && h === '현재가'){
    const price = Number(v || 0);
    const avg = Number(rowValue(r, '매입단가') || 0);
    if(!price || !avg) return '';
    return price > avg ? 'red' : price < avg ? 'blue' : '';
  }
  if(typeof v === 'number' && ['평가손익','수익률','순손익','금일 손익','금일손익','최근성과','등락','등락률'].some(x=>h.includes(x))) return cls(v);
  if(h === '상태'){ const sv=String(v||''); if(['작동','ON','정상','체결','접수'].some(x=>sv.includes(x))) return 'green'; if(['감시','대기','수신대기'].some(x=>sv.includes(x))) return 'orange'; if(['오류','거부','실패'].some(x=>sv.includes(x))) return 'red'; }
  return '';
}

function positionRowsWithSummary(rows){
  const detail = (rows || []).filter(r => rowValue(r,'종목명') && rowValue(r,'종목명') !== '합계');
  detail.sort((a,b)=>{
    const av = Number(rowValue(a,'순손익') || 0);
    const bv = Number(rowValue(b,'순손익') || 0);
    return positionSortDir === 'asc' ? av - bv : bv - av;
  });
  const sum = (key) => detail.reduce((acc,r)=>acc + Number(rowValue(r,key) || 0), 0);
  const totalQty = sum('보유수량');
  const totalBuy = sum('총매입가');
  const totalEval = sum('평가금액');
  const totalEvalPnl = sum('평가손익');
  const totalNet = sum('순손익');
  const totalAvgPriceSum = sum('매입단가');
  const totalCurPriceSum = sum('현재가');
  const rate = totalBuy ? (totalEvalPnl / totalBuy) * 100 : 0;
  const summary = {
    종목명:'합계',
    보유수량:totalQty,
    매입단가:totalAvgPriceSum,
    현재가:totalCurPriceSum,
    총매입가:totalBuy,
    평가금액:totalEval,
    평가손익:totalEvalPnl,
    수익률:rate,
    순손익:totalNet,
    잔고비중:detail.length ? 100 : 0,
    _summary:true
  };
  return [summary, ...detail];
}
function togglePositionSort(){
  positionSortDir = positionSortDir === 'desc' ? 'asc' : 'desc';
  render(last);
}

function table(id, headers, rows){
  const el = document.getElementById(id); if(!el) return;
  const safeRows = id === 'positions' ? positionRowsWithSummary(rows || []) : (rows || []);
  const body = safeRows.map(r => `<tr class="${r && r._summary ? 'summary-row' : ''}">` + headers.map(h => {
    const v = rowValue(r,h);
    const klass = tableCellClass(id, r, h, v);
    let display = (['strategies2','autoPlanSummary','riskLinkTable'].includes(id) && (v === 0 || v === '0')) ? '0' : fmt(h,v);
    if(id === 'positions' && h === '종목명' && v && v !== '합계'){
      const info = splitStockLabel(v);
      const key = escAttr(info.code || info.name);
      display = `<span class="pos-link" onclick="selectPositionChart('${key}')" title="클릭하면 시간대별 현재가 선그래프 표시">${v}</span>`;
    }
    return `<td class="${klass}">${display}</td>`;
  }).join('') + '</tr>').join('');
  let filler = '';
  if(id === 'positions'){
    const targetRows = 20;
    const blanks = Math.max(0, targetRows - Math.max(0, safeRows.length - 1));
    filler = Array.from({length: blanks}, () => `<tr class="blank-row">${headers.map(()=>'<td>&nbsp;</td>').join('')}</tr>`).join('');
  }
  el.innerHTML = '<tr>' + headers.map(h=>`<th>${h}</th>`).join('') + '</tr>' + (body || `<tr><td colspan="${headers.length}" class="muted">실제 수신값 대기</td></tr>`) + filler;
}
async function api(path, body){
  const opt = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {method:'POST'};
  const r = await fetch(path, opt);
  const data = await r.json().catch(()=>({ok:false,message:'응답 파싱 실패'}));
  if(!r.ok) throw new Error(data.detail || data.message || '요청 실패');
  return data;
}
async function load(){ const r = await fetch('/api/dashboard', {cache:'no-store'}); last = await r.json(); render(last); }

function systemStatusText(d){
  if(d.status.ws_enabled === false) return 'WebSocket 중지';
  if(d.status.ws_connected) return '자동 연결 중';
  if(d.status.ws === 'RECONNECTING') return '자동 연결 중';
  if(d.status.ws === 'CONNECTING' || d.status.ws === 'ERROR') return '자동 연결 중';
  return '자동 연결 중';
}
function renderIndices(rows, targetId='indices'){
  const el=document.getElementById(targetId); if(!el) return;
  if(!rows || rows.length === 0){ el.innerHTML = '<div class="muted">실제 시장 지수 수신값 대기</div>'; return; }
  el.innerHTML = rows.map((r,i)=>{
    const v=Number(r.현재||0), ch=Number(r.등락||0), rate=Number(r.등락률||0);
    const color=rate<0?'#14a7ff':'#ff3838';
    const pts=Array.from({length:18},(_,n)=>{
      const y=18 - Math.sin((n+i)*0.75 + rate)*7 - (rate*2);
      const x=n*5.2; return `${x.toFixed(1)},${Math.max(3,Math.min(31,y)).toFixed(1)}`;
    }).join(' ');
    return `<div class="idx-row"><div class="idx-name">${r.지수}</div><div class="idx-val">${nf.format(v)}</div><div class="idx-chg ${rate<0?'blue':'red'}">${ch>0?'+':''}${ch.toFixed(2)} (${pct(rate)})</div><svg class="sparkline" viewBox="0 0 90 34"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2"/><path d="M0 34 L ${pts.replaceAll(' ',', L ')} L90 34 Z" fill="${color}" opacity="0.13"/></svg></div>`;
  }).join('');
}
function renderSectorList(rows, targetId='sectors'){
  const el=document.getElementById(targetId); if(!el) return;
  el.innerHTML = (rows || []).length ? (rows || []).map(s => `<div class="barrow"><div>${s.업종}</div><div class="barbox"><div class="bar" style="width:${Math.min(100,Math.max(6,Math.abs(Number(s.등락률||0))*50))}%"></div></div><div class="${Number(s.등락률)<0?'blue':'red'}">${pct(s.등락률)}</div><small class="muted">${s.현재?nf.format(Number(s.현재)):''}${s.수신시각?' · '+s.수신시각:''}</small></div>`).join('') : '<div class="muted">실제 업종 수신값 대기</div>';
}

function buildStrategyLiveRows(d){
  const positions=(d.positions||[]).filter(p=>p.종목명 && p.종목명!=='합계');
  return (d.strategies||[]).map((s,idx)=>{
    const signal=String(s.신호||'대기');
    const candidate=positions[idx % Math.max(positions.length,1)] || {};
    const hasHolding = positions.length && (signal==='매수' || String(s.포지션||'').includes('보유') || Number(s['금일 손익']||s.금일손익||0)!==0);
    const cur=hasHolding?Number(candidate.현재가||0):0;
    const avg=hasHolding?Number(candidate.매입단가||0):0;
    const qty=hasHolding?Number(candidate.보유수량||0):0;
    const target=cur?Math.round(cur*1.035):0;
    const stop=cur?Math.round(cur*0.968):0;
    return {
      '전략명':String(s.전략명||'').replace('내 전략','내 전략'),
      '상태':s.상태,
      '신호':signal,
      '포지션':hasHolding?'보유':'대기',
      '금일 손익':Number(s['금일 손익']||s.금일손익||0),
      '수익률':Number(s.수익률||s.최근성과||0),
      '목표 수익률': signal==='매수'?3.0:(signal==='매도'?0:2.0),
      '보유 기간':hasHolding?'실시간':'-',
      '진입 단가':avg||0,
      '현재가':cur||0,
      '목표가':target||0,
      '손절가':stop||0,
      '보유수량':qty||0,
      '매수 금액':cur&&qty?cur*qty:0
    };
  });
}


function cardSizeClass(title){
  const wide = ['총 자산'];
  const narrow = ['평가 손익','보유 종목','금일 매매','위험도','리스크 상태'];
  const medium = ['주문 가능','매매 현황','자동운영','WebSocket','시장 시간'];
  if(wide.includes(title)) return 'card-wide';
  if(narrow.includes(title)) return 'card-narrow';
  if(medium.includes(title)) return 'card-medium';
  return 'card-normal';
}


function fitOneLineCards(){
  const groups = [document.getElementById('cards'), document.getElementById('autoCards')].filter(Boolean);
  for(const group of groups){
    const items = Array.from(group.children || []);
    if(!items.length) continue;
    const rect = group.getBoundingClientRect();
    const available = Math.floor(group.clientWidth || rect.width || 0);
    if(available < 120) continue; // 숨김 탭/초기 렌더 보호
    const gap = parseFloat(getComputedStyle(group).columnGap || getComputedStyle(group).gap || '12') || 12;
    const count = items.length;
    const minCaptureWidth = group.id === 'autoCards' ? 170 : 190;

    // 가장 넓게 열린 컨테이너 폭을 기준으로 1줄 균등 폭을 산정한다.
    // 이후 창이 줄면 이 고정 폭은 유지하고, 들어가지 않는 카드만 다음 행으로 이동한다.
    const prevMax = Number(group.dataset.maxContainerWidth || 0);
    if(available >= prevMax || !group.dataset.baseCardWidth){
      group.dataset.maxContainerWidth = String(available);
      const equalWidth = Math.floor((available - gap * (count - 1)) / count);
      group.dataset.baseCardWidth = String(Math.max(minCaptureWidth, equalWidth));
    }
    const baseWidth = Number(group.dataset.baseCardWidth || minCaptureWidth);
    const cols = Math.max(1, Math.min(count, Math.floor((available + gap) / (baseWidth + gap))));
    group.style.setProperty('grid-template-columns', `repeat(${cols}, ${baseWidth}px)`, 'important');
    group.style.setProperty('--layout-card-width', `${baseWidth}px`);
    group.style.setProperty('justify-content', 'start', 'important');
    group.style.setProperty('gap', `${gap}px`, 'important');

    for(const card of items){
      card.style.setProperty('width', `${baseWidth}px`, 'important');
      card.style.setProperty('min-width', `${baseWidth}px`, 'important');
      card.style.setProperty('max-width', `${baseWidth}px`, 'important');
      card.style.setProperty('--card-local-scale', '1');

      const texts = Array.from(card.querySelectorAll('.title,.big,.sub,b,p,small'));
      let maxNeed = 1;
      for(const el of texts){
        const oldWhite = el.style.whiteSpace;
        el.style.whiteSpace = 'nowrap';
        maxNeed = Math.max(maxNeed, el.scrollWidth || 1);
        el.style.whiteSpace = oldWhite;
      }
      const safeWidth = Math.max(40, baseWidth - 24);
      const scale = Math.max(0.50, Math.min(1, safeWidth / maxNeed));
      card.style.setProperty('--card-local-scale', String(scale));

      const minH = card.classList.contains('auto-hero-card') ? 96 : 106;
      card.style.minHeight = `${minH}px`;
      card.style.height = 'auto';
    }
  }
}
window.addEventListener('resize', () => requestAnimationFrame(fitOneLineCards));

function renderAutoHeroCards(d){
  const el=document.getElementById('autoCards'); if(!el) return;
  const pnl=Number(d.summary?.총평가손익||0);
  const total=Number(d.summary?.총자산||0);
  const pos=(d.positions||[]).filter(x=>x.종목명 && x.종목명!=='합계').length;
  const strategyOn=(d.strategies||[]).filter(s=>s.상태==='ON').length;
  const riskOk=(Number(d.status?.risk_score||0)<=3);
  const marketText=(d.status?.market==='장중'?'09:00 ~ 15:20':'09:00 ~ 15:20');
  const liveAge=d.status?.last_live_age==null?'-':`${d.status.last_live_age}s`;
  const cards=[
    ['📶','WebSocket',d.status?.ws_enabled===false?'OFF':(d.status?.ws_connected?'연결/대기':'연결중'),liveAge,'cyan'],
    ['▶','자동운영',d.status?.auto||'-',d.mode||'-','cyan'],
    ['📊','금일 매매',`${d.summary?.거래||0}건`,`매수 ${d.summary?.매수||0} / 매도 ${d.summary?.매도||0}`,'cyan'],
    ['💰','금일 손익',`${pnl>0?'+':''}${money(pnl)}원`,pct(total? pnl/Math.max(total-pnl,1)*100:0),cls(pnl)||'white'],
    ['💼','보유 종목',`${pos} / 20`,`포지션 ${(d.strategies||[]).filter(s=>String(s.포지션||'').includes('보유')).length}`,'white'],
    ['◔','총 자산',`${money(total)}원`,`평가손익 ${pnl>0?'+':''}${money(pnl)}원`,cls(pnl)||'white'],
    ['🛡️','리스크 상태',riskOk?'정상':'주의',`경고 ${Number(d.status?.risk_score||0)} / 주의 1`,riskOk?'green':'orange'],
    ['🕘','시장 시간',marketText,`잔여 ${liveAge}`,'white']
  ];
  el.innerHTML=cards.map(c=>`<div class="auto-hero-card ${cardSizeClass(c[1])}"><div class="auto-hero-head"><span class="hero-ico">${c[0]}</span><b>${c[1]}</b></div><p class="${c[4]}">${c[2]}</p><small>${c[3]}</small></div>`).join('');
  requestAnimationFrame(fitOneLineCards);
}
function renderRiskLinkTable(d){
  const total=Number(d.summary?.총자산||0), exposure=Number(d.summary?.총평가금액||0), pnl=Number(d.summary?.총평가손익||0);
  const exposureRate=total? exposure/total*100:0;
  const rows=[
    {지표:'일 최대 손실 한도',현재:'-500,000원',상태:Math.abs(pnl)<500000?'여유':'주의'},
    {지표:'일 손실',현재:`${pnl<0?'-':''}${money(Math.abs(Math.min(pnl,0)))}원`,상태:pnl>=-500000?'여유':'초과'},
    {지표:'포지션 한도',현재:`${exposureRate.toFixed(2)}% / 80%`,상태:exposureRate<=80?'여유':'주의'},
    {지표:'종목당 한도',현재:'20% / 20%',상태:'정상'},
    {지표:'연속 손실',현재:'2 / 5',상태:'정상'},
    {지표:'MDD 근접',현재:`${Number(d.status?.mdd||0).toFixed(2)}% / 20%`,상태:Number(d.status?.mdd||0)<20?'정상':'주의'}
  ];
  table('riskLinkTable',['지표','현재','상태'],rows);
}
function renderAutoPlanSummary(d){
  const rows=[
    {상태:d.status?.auto==='ON'?'RUNNING':'대기','전략':`${(d.strategies||[]).filter(s=>s.상태==='ON').length} / ${(d.strategies||[]).length}`,'신호':(d.strategies||[]).filter(s=>['매수','매도'].includes(String(s.신호))).length,'매수':d.summary?.매수||0,'매도':d.summary?.매도||0,'포지션':(d.positions||[]).filter(x=>x.종목명 && x.종목명!=='합계').length,'리스크':d.status?.risk_score||0}
  ];
  table('autoPlanSummary',['상태','전략','신호','매수','매도','포지션','리스크'],rows);
}
function renderInvestmentTable(rows, targetId='autoInvestmentTable'){
  const el=document.getElementById(targetId); if(!el) return;
  table(targetId,['유형','기간','목표수익률','종목당비중','동시보유','현금비중','매수금지'],rows||[]);
  el.classList.add('settings-invest-table');
}
function renderBuyFormula(d){
  const total=Number(d.summary?.총자산||0);
  const riskRate=0.02;
  const first=(d.positions||[]).find(x=>x.종목명 && x.종목명!=='합계') || {};
  const buy=Number(first.현재가||first.매입단가||0);
  const stop=buy?Math.round(buy*0.968):0;
  const riskPerShare=Math.max(buy-stop,1);
  const amount=buy?Math.floor((total*riskRate)/riskPerShare)*buy:0;
  const rows=[{
    '계산식':'매수 금액 = (총 자산 × 리스크 허용 비율) ÷ (매수가 - 손절가)',
    '총 자산(원)':money(total),
    '리스크 허용 비율(%)':(riskRate*100).toFixed(2),
    '매수가(원)':buy?money(buy):'-',
    '손절가(원)':stop?money(stop):'-',
    '계산 매수 금액(원)':amount?money(amount):'-',
    '상태':amount?'자동 계산':'수신 대기'
  }];
  table('buyFormulaTable',['계산식','총 자산(원)','리스크 허용 비율(%)','매수가(원)','손절가(원)','계산 매수 금액(원)','상태'],rows);
}
function renderAutoScheduleMini(d){
  const rows=(d.schedule||[]).map(r=>({시장구분:r[0],시간:r[1],상태:r[2]}));
  table('autoScheduleMini',['시장구분','시간','상태'],rows);
}


function latestRawInfo(d){
  const raw = (d.raw || [])[0] || {};
  const data0 = Array.isArray(raw.data) && raw.data.length ? raw.data[0] : raw;
  const values = data0.values || raw.values || raw.json || {};
  const type = data0.type || raw.type || raw.api_id || '-';
  const keys = values && typeof values === 'object' ? Object.keys(values).length : 0;
  return {type, keys, source: raw.source || 'WS', visible: d.status?.last_packet_visible};
}
function renderRawSummary(d){
  const el = document.getElementById('rawSummary'); if(!el) return;
  const info = latestRawInfo(d);
  const liveAge = d.status?.last_live_age == null ? '-' : `${d.status.last_live_age}s 전`;
  const restAge = d.status?.last_rest_age == null ? '-' : `${d.status.last_rest_age}s 전`;
  const visible = info.visible ? '화면 반영' : (d.status?.last_visible_reason || '대기');
  el.innerHTML = [
    ['최근 수신', liveAge, `${info.source} · ${info.type}`],
    ['필드 수', `${info.keys}개`, '수신 원문 기준'],
    ['화면 반영', visible, d.status?.last_ingest_type || '-'],
    ['계좌 동기화', restAge, d.status?.rest || '-']
  ].map(x=>`<div class="raw-summary-card"><b>${x[0]}</b><p>${x[1]}</p><small>${x[2]}</small></div>`).join('');
}
function renderAutoTrades(d){
  const el = document.getElementById('autoTrades'); if(!el) return;
  const rows = d.auto_trades || d.trades || [];
  let sourceRows = rows;
  if(!sourceRows.length){
    sourceRows = (d.lifecycle || []).filter(x => ['매매 시작','매수','매도','매매 종료','주문','체결'].includes(x.event)).map(x => ({시간:x.time, 구분:x.event, 전략:'-', 종목:'-', 매수매도:x.event, 수량:'', 가격:'', 상태:x.detail || '대기'}));
  }
  if(!sourceRows.length && (d.events || []).length){
    sourceRows = (d.events || []).filter(e => ['매매','주문','체결'].includes(e.kind)).slice(0,10).map(e => ({시간:e.time, 구분:e.kind, 전략:'-', 종목:'-', 매수매도:'-', 수량:'', 가격:'', 상태:e.message}));
  }
  const headers = ['시간','구분','전략','종목','매수매도','수량','가격','상태'];
  table('autoTrades', headers, sourceRows);
}


function renderWsDetail(d){
  const el = document.getElementById('wsDetail'); if(!el) return;
  const liveAge = d.status?.last_live_age == null ? '-' : `${d.status.last_live_age}s 전`;
  const restAge = d.status?.last_rest_age == null ? '-' : `${d.status.last_rest_age}s 전`;
  const rawCount = Array.isArray(d.raw) ? d.raw.length : 0;
  const liveState = d.status?.ws_connected ? '수신/대기' : (d.status?.ws_enabled === false ? '수동 OFF' : '연결중');
  el.innerHTML = '<tr><th>항목</th><th>상태</th><th>설명</th></tr>' + [
    ['실시간 원문 수신', liveState, `최근 원문 ${rawCount}건 · ${d.status?.ws_message || d.status?.ws || '-'}`],
    ['최근수신 초수', liveAge, '마지막 WebSocket 패킷 기준'],
    ['REST 초', restAge, '마지막 REST 계좌/잔고 동기화 기준']
  ].map(r=>`<tr><td>${r[0]}</td><td class="cyan">${r[1]}</td><td class="left">${r[2]}</td></tr>`).join('');
}

function renderReportCards(d){
  const el = document.getElementById('reportCards'); if(!el) return;
  const cards = d.report_cards || [];
  if(!cards.length){ el.innerHTML = '<tr><td colspan="7" class="muted">장 종료 후 자동 리포트 생성 대기</td></tr>'; return; }
  el.innerHTML = '<tr><th>구분</th><th>날짜</th><th>총자산</th><th>손익</th><th>거래</th><th>보유</th><th>생성시각</th></tr>' + cards.map(c => `<tr><td>${c.label}</td><td>${c.date}</td><td>${money(c.total_assets)}원</td><td class="${cls(c.pnl)}">${c.pnl>0?'+':''}${money(c.pnl)}원</td><td>${c.trades}건<br><span class="muted">매수 ${c.buys||0} / 매도 ${c.sells||0}</span></td><td>${c.positions}종목</td><td>${c.generated_at || '-'}</td></tr>`).join('');
}


function minutesNow(){ const n=new Date(); return n.getHours()*60+n.getMinutes(); }
const EXCHANGE_ROWS = [
  {time:'08:00~08:30', start:480, end:510, krx:'장 마감', nxt:'프리마켓', engine:'NXT만 거래 가능', order:'NXT 가능 / KRX 불가', desc:'KRX는 주문 불가입니다. NXT는 프리마켓 실시간 접속매매가 가능하므로 NXT 전용 전략만 실행합니다.'},
  {time:'08:30~08:40', start:510, end:520, krx:'장전 시간외 종가', nxt:'프리마켓', engine:'KRX 장전종가 / NXT 가능', order:'KRX·NXT 가능', desc:'KRX는 전일 종가 기준으로 상대 잔량이 있으면 선착순 체결됩니다. NXT는 프리마켓 실시간 거래를 유지합니다.'},
  {time:'08:40~08:50', start:520, end:530, krx:'호가 접수', nxt:'프리마켓', engine:'KRX 대기', order:'KRX 접수 / NXT 가능', desc:'KRX는 호가만 접수되고 체결은 발생하지 않습니다. NXT는 계속 실시간 접속매매가 가능합니다.'},
  {time:'08:50~09:00', start:530, end:540, krx:'개장 동시호가', nxt:'예상체결가', engine:'주문만', order:'주문 가능 / 체결 대기', desc:'호가를 모아 09:00에 시가로 일괄 체결합니다. 신규 자동 진입은 제한하고 예상체결가 감시 중심으로 동작합니다.'},
  {time:'09:00~15:20', start:540, end:920, krx:'정규장', nxt:'메인마켓', engine:'자동매매', order:'주문 가능', desc:'KRX/NXT 모두 실시간 접속매매 구간입니다. 전략 판단, 주문, 체결, 잔고 갱신을 자동매매 엔진과 실시간 저장소에 반영합니다.'},
  {time:'15:20~15:30', start:920, end:930, krx:'마감 동시호가', nxt:'KRX 종가대기', engine:'주문 제한', order:'신규 진입 제한', desc:'종가 결정을 위한 동시호가 구간입니다. 신규 매수는 제한하고 청산·위험관리 주문만 허용하도록 운영합니다.'},
  {time:'15:30~15:40', start:930, end:940, krx:'장 마감', nxt:'장 마감', engine:'대기', order:'주문 불가', desc:'정규장 종료 후 체결이 없는 대기 구간입니다. 잔고 동기화, 체결 누락 확인, 리포트 준비를 수행합니다.'},
  {time:'15:40~16:00', start:940, end:960, krx:'장후 종가', nxt:'애프터마켓', engine:'자동매매', order:'주문 가능', desc:'KRX는 당일 종가 기준 선착순 체결, NXT는 애프터마켓 실시간 접속매매를 수행합니다.'},
  {time:'16:00~18:00', start:960, end:1080, krx:'시간외 단일가', nxt:'애프터마켓', engine:'자동매매', order:'주문 가능', desc:'KRX는 10분 단위 단일가로 총 12회 체결됩니다. NXT는 애프터마켓 실시간 접속매매를 유지합니다.'},
  {time:'18:00~20:00', start:1080, end:1200, krx:'종료', nxt:'애프터마켓', engine:'NXT만', order:'NXT만 가능', desc:'KRX는 종료, NXT 애프터마켓만 운영됩니다. NXT 지원 전략만 실행하고 KRX 주문은 차단합니다.'},
  {time:'20:00 이후', start:1200, end:1440, krx:'종료', nxt:'종료', engine:'종료', order:'주문 불가', desc:'전체 시장 종료입니다. WebSocket 감시는 유지할 수 있으나 주문·전략 실행은 종료하고 리포트 저장/알림을 수행합니다.'}
];
function currentExchangeRow(){ const m=minutesNow(); return EXCHANGE_ROWS.find(r=>m>=r.start && m<r.end) || EXCHANGE_ROWS[10]; }
function renderExchangeSchedule(d){
  const tableEl=document.getElementById('exchangeSchedule'); if(!tableEl) return;
  const statusEl=document.getElementById('exchangeStatus');
  const cur=currentExchangeRow();
  if(statusEl){
    statusEl.innerHTML = [
      ['현재 구간', cur.time, cur.engine],
      ['KRX', cur.krx, cur.order],
      ['NXT', cur.nxt, d?.status?.ws || '-'],
      ['자동매매', cur.engine, d?.status?.auto || '-']
    ].map(x=>`<div class="box"><b>${x[0]}</b><p class="cyan">${x[1]}</p><small>${x[2]}</small></div>`).join('');
  }
  tableEl.innerHTML = '<tr><th>시간</th><th>KRX</th><th>NXT</th><th>엔진 상태</th><th>주문</th><th>설명</th></tr>' + EXCHANGE_ROWS.map(r=>`<tr class="${r===cur?'active':''}"><td>${r.time}</td><td>${r.krx}</td><td>${r.nxt}</td><td>${r.engine}</td><td>${r.order}</td><td class="left">${r.desc}</td></tr>`).join('');
}

function renderExclusionCards(rows){
  const el=document.getElementById('excludeCards'); if(!el) return;
  el.innerHTML=(rows||[]).map(r=>`<div class="exclude-card" title="${r.desc||''}"><div class="exclude-title">${r.label||'-'} <span class="muted">?</span></div><div class="exclude-value">${r.enabled?'true':'false'}</div><span class="switch-mini ${r.enabled?'':'off'}">${r.enabled?'ON':'OFF'}</span></div>`).join('') || '<div class="muted">제외종목 설정값 대기</div>';
}
function renderInvestmentCards(rows){
  renderInvestmentTable(rows, 'investmentCards');
}


function renderAutoOperationPolicy(d){
  table('autoOperationPolicy',['구분','적용','자동매매 메뉴','판정'], d.auto_operation_policy || []);
}
function renderStrategySelector(d){
  const el=document.getElementById('strategySelector'); if(!el) return;
  const selected=(d.settings?.selected_strategy_group || 'FOUR_QUANT').toUpperCase();
  const options=[
    {key:'MY', title:'내 전략', desc:'기존 단기 전략에 상위 N·리밸런싱·현금버퍼·공통 리스크를 동일 적용'},
    {key:'FOUR_QUANT', title:'4대 퀀트 전략(기본)', desc:'모멘텀·가치·퀄리티·저변동성 점수 기반 기본 전략'}
  ];
  el.innerHTML=options.map(o=>`<div class="strategy-option ${selected===o.key?'active':''}"><b><span class="strategy-radio">${selected===o.key?'●':'○'}</span>${o.title}</b><small>${o.desc}</small></div>`).join('');
}
function renderStrategyComparePolicy(d){
  table('strategyComparePolicy',['항목','내 전략','4대 퀀트 전략(기본)','비교 설명'], d.strategy_compare_policy || []);
}
function renderOperationStatusPolicy(d){
  table('operationStatusPolicy',['구분','내용'], d.operation_status_policy || []);
}
function renderBuySellPolicy(d){
  table('buySellPolicy',['단계','매수 기준','매도 기준','리스크 반영'], d.buy_sell_policy || []);
}
function renderOrderExecutionStatus(d){
  const st=d.settings || {};
  const profile=d.active_profile==='LIVE'?'실전투자 계좌':'모의투자 계좌';
  const rows=[
    {'항목':'계좌 주문 실행','현재값':'ON','적용 위치':'app/services/order_executor.py','설명':`${profile}로 kt10000/kt10001 주문 API를 전송`},
    {'항목':'운용 프로필','현재값':d.active_profile==='LIVE'?'실전':'모의','적용 위치':'.env KIWOOM_ACTIVE_PROFILE / 상단 전환 버튼','설명':'MOCK은 키움 모의투자 계좌, LIVE는 실전투자 계좌 사용'},
    {'항목':'자동매매 스위치','현재값':st.auto_trade_enabled?'ON':'OFF','적용 위치':'.env AUTO_TRADE_ENABLED / settings','설명':'전략 실행 허용 여부'},
    {'항목':'현금버퍼','현재값':`${Math.round((1-Number(st.target_investment_rate||0.90))*100)}~${Math.round((1-Number(st.max_target_investment_rate||0.95))*100)}%`,'적용 위치':'.env TARGET/MAX_TARGET_INVESTMENT_RATE','설명':'총자산 90~95%까지만 투자하고 나머지는 현금 유지'},
    {'항목':'상위 N개 편입','현재값':`${st.top_n_selection||20}개`,'적용 위치':'.env TOP_N_SELECTION','설명':'선택 전략의 점수 상위 종목만 편입'},
    {'항목':'리밸런싱 주기','현재값':st.rebalance_cycle||'MONTHLY','적용 위치':'.env REBALANCE_CYCLE','설명':'MONTHLY/QUARTERLY/HALF_YEAR/YEARLY/SEASONAL 중 선택'},
    {'항목':'운용 흐름','현재값':'백테스트 → 선택 계좌 주문 → 결과 리포트','적용 위치':'자동매매 메뉴','설명':'모의/실전은 상단 전환 버튼으로 수동 선택, 구조는 동일'},
    {'항목':'주문 전 리스크','현재값':`일손실 ${Math.round(Number(st.daily_loss_limit||0.02)*100)}% · 종목손실 ${Number(st.per_trade_risk_rate||0.005)*100}%`,'적용 위치':'app/core/risk_engine.py','설명':'계좌 주문 전 공통 차단 게이트'}
  ];
  table('orderExecutionStatus',['항목','현재값','적용 위치','설명'],rows);
}

function renderApiPolicy(rows){
  const el=document.getElementById('apiPolicy'); if(!el) return;
  table('apiPolicy',['기능','API','용도'],rows||[]);
}

function render(d){
  expire.textContent = `${d.app_expire} (${d.d_day})`;
  ver.textContent = '버전: ' + d.version; footerMode.textContent = '모드: ' + d.mode; if(document.getElementById('footerAuto')) footerAuto.textContent = '자동운영: ' + (d.other?.자동운영 || '병용');
  poscount.textContent = d.position_count;
  dbState.textContent = 'DB: ' + (d.other?.DB상태 || '연결됨');
  footerServer.textContent = '서버: ' + (d.domain || '-');
  footerWs.textContent = 'WebSocket: ' + (d.ws_url || '-');
  footerDbVer.textContent = 'DB버전: ' + (d.other?.DB버전 || '-');
  lastBackup.textContent = '마지막 백업: ' + (d.other?.마지막백업 || '-');
  profileBtn.innerHTML = (d.active_profile === 'MOCK' ? '모의' : '실전') + ' <span class="dot"></span>';
  profileBtn.className = 'pill ' + (d.active_profile === 'LIVE' ? 'live' : '');
  const wsLabel = d.status.ws_enabled === false ? 'OFF' : (d.status.ws_connected ? '연결됨' : '연결중');
  wsToggle.innerHTML = `웹소켓 ${wsLabel} <span class="dot"></span>`;
  wsToggle.className = 'pill ' + (d.status.ws_enabled === false ? 'off' : '');

  const pnl = d.summary.총평가손익 || 0;
  const rate = (pnl / Math.max((d.summary.총평가금액 || 0) - pnl, 1)) * 100;
  cards.innerHTML = [
    ['💼','총 자산', money(d.summary.총자산)+' 원', `전일 대비 ${pnl>=0?'+':''}${money(pnl)} (${pct(rate)})`, ''],
    ['📈','평가 손익', `${pnl>0?'+':''}${money(pnl)} 원`, pct(rate), cls(pnl)],
    ['🧾','보유 종목', String((d.positions||[]).filter(x=>x.종목명!=='합계').length), '종목', ''],
    ['💵','주문 가능', money(d.summary.주문가능금액 || d.summary.예수금)+' 원', '04 잔고 주문가능수량 기준', ''],
    ['🛒','금일 매매', `${d.summary.거래} 건`, `매수 ${d.summary.매수} / 매도 ${d.summary.매도}`, ''],
    ['📡','매매 현황', d.status.auto === 'ON' ? '자동매매 ON' : '대기', `시장 ${d.status.market || '-'} · ${d.status.ws || '-'}`, 'cyan'],
    ['📍','위험도', '보통', `(${d.status.risk_score}/10)`, 'orange']
  ].map(c => `<div class="card ${cardSizeClass(c[1])}"><div class="card-head"><span class="ico">${c[0]}</span><span class="title">${c[1]}</span></div><div class="big ${c[4] || ''}">${c[2]}</div><div class="sub ${c[4] || ''}">${c[3]}</div></div>`).join('');
  requestAnimationFrame(fitOneLineCards);

  capturePositionPrices(d.positions || []);
  const sortBtn = document.getElementById('posSortBtn');
  if(sortBtn) sortBtn.textContent = positionSortDir === 'desc' ? '순손익 ▼' : '순손익 ▲';
  table('positions', ['종목명','보유수량','매입단가','현재가','총매입가','평가금액','평가손익','수익률','순손익','잔고비중'], d.positions);
  renderPositionPriceChart();
  table('strategies', ['전략명','상태','신호','금일 손익','수익률'], d.strategies);
  table('strategies2', ['전략명','상태','신호','포지션','금일 손익','수익률','목표 수익률','보유 기간','진입 단가','현재가','목표가','손절가','보유수량','매수 금액'], buildStrategyLiveRows(d));
  table('backtestSummary', ['검증','상태','설명'], d.backtest_summary || []);
  renderAutoTrades(d);
  renderIndices(d.indices || []);
  const schedHtml = '<tr><th>구분</th><th>시간</th><th>상태</th></tr>' + (d.schedule||[]).map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td class="${r[2]==='진행중'?'green':r[2]==='대기'?'orange':'green'}">${r[2]}</td></tr>`).join('');
  if(document.getElementById('schedule')) schedule.innerHTML = schedHtml;
  events.innerHTML = '<tr><th>시간</th><th>구분</th><th>메시지</th></tr>' + ((d.events||[]).length ? d.events.map(e=>`<tr><td>${e.time}</td><td><span class="badge ${e.kind==='리스크'?'redbg':''}">${e.kind}</span></td><td class="left">${e.message}</td></tr>`).join('') : '<tr><td colspan="3" class="muted">실제 이벤트 수신 대기</td></tr>');
  const firstEvent = (d.events || [])[0];
  if(firstEvent){
    const key = `${firstEvent.time}|${firstEvent.kind}|${firstEvent.message}`;
    if(lastEventKey && key !== lastEventKey && ['알림','매매','오류','시스템','주문'].includes(firstEvent.kind)){
      notice(`[${firstEvent.kind}] ${firstEvent.message}`);
    }
    lastEventKey = key;
  }
  const sectorRows = sectorMode === 'down' ? (d.sectors_down || []) : (d.sectors_up || d.sectors || []);
  if(document.getElementById('sectorUpBtn')){ sectorUpBtn.classList.toggle('active', sectorMode==='up'); sectorDownBtn.classList.toggle('active', sectorMode==='down'); }
  renderSectorList(sectorRows, 'sectors');
  renderAutoHeroCards(d);
  renderIndices(d.indices || [], 'autoIndices');
  renderSectorList(sectorRows, 'autoSectors');
  if(document.getElementById('autoSectorUpBtn')){ autoSectorUpBtn.classList.toggle('active', sectorMode==='up'); autoSectorDownBtn.classList.toggle('active', sectorMode==='down'); }
  renderRiskLinkTable(d);
  renderAutoPlanSummary(d);
  renderInvestmentTable(d.rules || [], 'autoInvestmentTable');
  renderBuyFormula(d);
  renderAutoScheduleMini(d);
  renderAutoOperationPolicy(d);
  renderStrategySelector(d);
  renderStrategyComparePolicy(d);
  renderOperationStatusPolicy(d);
  renderBuySellPolicy(d);
  renderOrderExecutionStatus(d);
  lifecycle.innerHTML = '<tr><th>시간</th><th>이벤트</th><th>내용</th></tr>' + (d.lifecycle || []).map(x=>`<tr><td>${x.time}</td><td>${x.event}</td><td class="left">${x.detail || '-'}</td></tr>`).join('');
  if((d.lifecycle || []).length === 0) lifecycle.innerHTML += '<tr><td>-</td><td>대기</td><td>프로그램/시장/매매 알림 대기</td></tr>';
  renderReportCards(d);
  renderExchangeSchedule(d);
  renderWsDetail(d);
  if(document.getElementById('raw')) raw.textContent = JSON.stringify(d.raw || [], null, 2);
  if(document.getElementById('envStatus')) envStatus.innerHTML = `<tr><th>항목</th><th>값</th></tr><tr><td>현재 프로필</td><td>${d.mode}</td></tr><tr><td>REST 도메인</td><td>${d.domain}</td></tr><tr><td>WebSocket</td><td>${d.full_ws_url}</td></tr><tr><td>텔레그램</td><td class="${d.settings.telegram_enabled?'green':'orange'}">${d.settings.telegram_enabled?'연동됨':'CHAT_ID 또는 현재 프로필 TOKEN 미설정'}</td></tr><tr><td>토큰</td><td>TokenManager 내부 자동 관리 / UI 비표시</td></tr>`;
  renderExclusionCards(d.exclusions || []);
  renderInvestmentCards(d.rules || []);
  renderApiPolicy(d.api_policy || []);
  drawEquity(d.equity_curve || []);
  requestAnimationFrame(markScrollablePanelsV2742);
}
function renderPositionPriceChart(){
  const el = document.getElementById('positionPriceChart'); if(!el) return;
  const title = document.getElementById('positionChartTitle');
  const keys = Object.keys(positionPriceHistory);
  const key = selectedPositionKey || keys[0] || '';
  const points = key ? (positionPriceHistory[key] || []) : [];
  const meta = points[points.length-1] || {};
  if(title) title.textContent = key ? `시간대별 현재가 선그래프 · ${meta.name || key}${meta.code ? '('+meta.code+')' : ''}` : '시간대별 현재가 선그래프';
  if(!points.length){
    el.innerHTML = '<div class="muted" style="padding:18px">보유 종목명을 클릭하면 현재가 선그래프가 생성됩니다.</div>';
    return;
  }
  const series = points.length < 2 ? [points[0], {...points[0], time:'현재'}] : points;
  const w = Math.max(500, el.clientWidth || 800), h = 250;
  const vals = series.map(p=>Number(p.value||0));
  const min = Math.min(...vals), max = Math.max(...vals), span = Math.max(max-min, 1);
  const xOf = i => 52 + i * (w-74)/Math.max(series.length-1,1);
  const yOf = v => 22 + (max-v) * (h-54)/span;
  let grid = '';
  for(let i=0;i<5;i++){ const y=22+i*(h-54)/4; grid += `<line x1="52" y1="${y}" x2="${w-14}" y2="${y}" stroke="#223a50" stroke-width="1"/>`; }
  const path = series.map((p,i)=>`${i===0?'M':'L'}${xOf(i).toFixed(1)},${yOf(Number(p.value||0)).toFixed(1)}`).join(' ');
  const lastPoint = series[series.length-1];
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <rect width="100%" height="100%" fill="#071522"/>${grid}
    <path d="${path} L${xOf(series.length-1).toFixed(1)},${h-24} L52,${h-24} Z" fill="#14a7ff" opacity="0.10"></path>
    <path d="${path}" fill="none" stroke="#14a7ff" stroke-width="2.4"/>
    <circle cx="${xOf(series.length-1).toFixed(1)}" cy="${yOf(Number(lastPoint.value||0)).toFixed(1)}" r="4" fill="#22d5ff"/>
    <text x="6" y="26" fill="#d9ecfa" font-size="12">${money(max)}</text>
    <text x="6" y="${h-24}" fill="#d9ecfa" font-size="12">${money(min)}</text>
    <text x="52" y="${h-5}" fill="#d9ecfa" font-size="12">${series[0].time || ''}</text>
    <text x="${w-85}" y="${h-5}" fill="#d9ecfa" font-size="12">${lastPoint.time || ''}</text>
  </svg>`;
}

function drawEquity(points){
  const el = document.getElementById('equityChart'); if(!el) return;
  const w = Math.max(500, el.clientWidth || 800), h = 300;
  if(!points || points.length < 1){
    el.innerHTML = '<div class="muted" style="padding:18px">실제 자산/보유종목 수신값 대기</div>';
    return;
  } else if(points.length < 2){
    points = [points[0], {time:'현재', value:points[0].value}];
  }
  const vals = points.map(p=>Number(p.value||0));
  const min = Math.min(...vals), max = Math.max(...vals), span = Math.max(max-min, 1);
  const xOf = i => 48 + i * (w-68)/Math.max(points.length-1,1);
  const yOf = v => 22 + (max-v) * (h-52)/span;
  let grid = '';
  for(let i=0;i<5;i++){ const y=22+i*(h-52)/4; grid += `<line x1="48" y1="${y}" x2="${w-14}" y2="${y}" stroke="#223a50" stroke-width="1"/>`; }
  const path = points.map((p,i)=>`${i===0?'M':'L'}${xOf(i).toFixed(1)},${yOf(Number(p.value||0)).toFixed(1)}`).join(' ');
  const area = path + ` L${xOf(points.length-1).toFixed(1)},${h-24} L48,${h-24} Z`;
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <rect width="100%" height="100%" fill="#071522"/>
    ${grid}
    <path d="${area}" fill="#14a7ff" opacity="0.12"></path>
    <path d="${path}" fill="none" stroke="#14a7ff" stroke-width="2.2"/>
    <text x="5" y="26" fill="#d9ecfa" font-size="12">${money(max)}</text>
    <text x="5" y="${h-24}" fill="#d9ecfa" font-size="12">${money(min)}</text>
    <text x="48" y="${h-5}" fill="#d9ecfa" font-size="12">09:00</text>
    <text x="${w*0.48}" y="${h-5}" fill="#d9ecfa" font-size="12">12:00</text>
    <text x="${w-48}" y="${h-5}" fill="#d9ecfa" font-size="12">15:00</text>
  </svg>`;
}


function markScrollablePanelsV2742(){
  const panels = Array.from(document.querySelectorAll('.panel'));
  for(const p of panels){
    const table = p.querySelector('table');
    if(!table){ p.classList.remove('needs-vscroll'); continue; }
    // requestAnimationFrame 이후 실제 렌더 높이를 기준으로, 세로 스크롤이 필요한 경우만 sticky 적용
    const needs = (p.scrollHeight - p.clientHeight) > 6 && p.clientHeight > 0;
    p.classList.toggle('needs-vscroll', needs);
  }
}

async function realtimeOn(){ try{ await api('/api/realtime/on'); notice('웹소켓 연결 시작'); load(); }catch(e){ notice('WebSocket ON 실패: '+e.message); } }
async function stopRealtime(){ try{ await api('/api/realtime/stop'); notice('웹소켓 중지'); load(); }catch(e){ notice(e.message); } }
async function toggleRealtime(){ if(last?.status?.ws_enabled !== false) await stopRealtime(); else await realtimeOn(); }
async function toggleProfile(){ const next = last.active_profile === 'MOCK' ? 'LIVE' : 'MOCK'; try{ const data = await api('/api/profile/switch',{profile:next}); notice(`${data.old} → ${data.new} 전환 완료`); load(); }catch(e){ notice('전환 실패: '+e.message); } }
async function manualOrder(){ const body={code:mcode.value,name:mname.value,side:mside.value,qty:+mqty.value,price:mprice.value?+mprice.value:null}; await fetch('/api/manual-order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); notice('수동 주문 의도 등록'); load(); }
async function sendLifecycle(event){ try{ await api('/api/notify/lifecycle/'+event); notice('알림 생성 완료'); load(); }catch(e){ notice(e.message); } }
async function makeReport(kind){ try{ const data=await api('/api/report',{kind,send_telegram:true}); if(document.getElementById('reportPreview')) reportPreview.textContent=data.title+'\n\n'+data.body.replaceAll('<b>','').replaceAll('</b>',''); if(data.snapshot){ last=data.snapshot; render(last); } notice('리포트 생성/알림 처리 완료'); }catch(e){ notice('리포트 실패: '+e.message); } }
function setSectorMode(mode){ sectorMode = mode; render(last); }
function settingsBoxes(){ const names=['일 손실 제한','수수료율','세금률','최대 보유 종목','종목당 최대 비중','신규매수 종료','리포트 발송','로그 압축']; setgrid.innerHTML=names.map((n,i)=>`<div class="box"><b>${n}</b><p class="cyan">실시간 반영</p><input class="input" value="${i+1}"><button>저장</button></div>`).join(''); }
function connectDashboardWs(){
  try{
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const sock = new WebSocket(`${proto}://${location.host}/ws/dashboard`);
    sock.onmessage = ev => { try{ last = JSON.parse(ev.data); render(last); }catch(e){} };
    sock.onopen = () => notice('웹창 실시간 표시 채널 연결');
    sock.onclose = () => setTimeout(connectDashboardWs, 1000);
    sock.onerror = () => { try{ sock.close(); }catch(e){} };
  }catch(e){ setTimeout(connectDashboardWs, 1000); }
}
async function syncAccount(){ try{ await api('/api/account/sync'); notice('계좌/잔고 실제 자료 동기화 완료'); load(); }catch(e){ notice('계좌 동기화 실패: '+e.message); } }
settingsBoxes(); connectDashboardWs(); setInterval(load, 3000); load();

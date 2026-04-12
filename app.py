<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OPTIONS FLOW — 옵션 거래량 분석기</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Bebas+Neue&family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg:#080c0f;--surface:#0d1318;--surface2:#121a21;--border:#1e2d38;
    --accent:#00e5a0;--accent2:#ff4d6d;--accent3:#f5a623;
    --text:#c8d8e4;--text-dim:#4a6374;--text-bright:#eaf4fc;
    --call:#00e5a0;--put:#ff4d6d;
    --mono:'Space Mono',monospace;--sans:'Noto Sans KR',sans-serif;--display:'Bebas Neue',sans-serif;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh;overflow-x:hidden}
  body::before{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,229,160,.015) 2px,rgba(0,229,160,.015) 4px);pointer-events:none;z-index:1000}
  body::after{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,229,160,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,160,.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}
  .wrapper{position:relative;z-index:1;max-width:1200px;margin:0 auto;padding:0 20px 60px}

  header{padding:30px 0 20px;display:flex;align-items:flex-end;gap:20px;border-bottom:1px solid var(--border);margin-bottom:24px;flex-wrap:wrap}
  .logo{font-family:var(--display);font-size:52px;letter-spacing:4px;color:var(--accent);text-shadow:0 0 30px rgba(0,229,160,.4);line-height:1}
  .logo span{color:var(--accent2)}
  .subtitle{font-family:var(--mono);font-size:11px;color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
  .live-badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;color:var(--accent);border:1px solid var(--accent);padding:3px 8px;letter-spacing:1px;margin-bottom:8px}
  .live-dot{width:6px;height:6px;background:var(--accent);border-radius:50%;animation:pulse 1.5s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}

  /* API Key Panel (로컬 실행 시에만 표시) */
  .apikey-panel{background:var(--surface);border:1px solid var(--accent3);padding:16px 20px;margin-bottom:24px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .apikey-panel.hidden{display:none}
  .apikey-panel label{font-family:var(--mono);font-size:10px;color:var(--accent3);letter-spacing:2px;text-transform:uppercase;white-space:nowrap}
  .apikey-panel input{flex:1;min-width:260px;background:var(--surface2);border:1px solid var(--border);color:var(--text-bright);font-family:var(--mono);font-size:12px;padding:10px 14px;outline:none;letter-spacing:1px}
  .apikey-panel input:focus{border-color:var(--accent3)}
  .apikey-save{background:var(--accent3);color:#000;border:none;font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:2px;padding:10px 18px;cursor:pointer;white-space:nowrap}
  .apikey-save:hover{background:#fff}
  .apikey-info{font-family:var(--mono);font-size:10px;color:var(--text-dim);width:100%;letter-spacing:1px;line-height:1.8}
  .apikey-ok{display:none;font-family:var(--mono);font-size:10px;color:var(--accent);letter-spacing:1px;align-items:center;gap:6px}
  .apikey-ok.show{display:flex}

  .search-section{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}
  .search-box{flex:1;min-width:240px}
  .search-box label{display:block;font-family:var(--mono);font-size:10px;color:var(--text-dim);letter-spacing:2px;margin-bottom:8px;text-transform:uppercase}
  .search-box input,.expiry-box select{width:100%;background:var(--surface);border:1px solid var(--border);color:var(--text-bright);font-family:var(--mono);padding:14px 18px;outline:none;transition:border-color .2s,box-shadow .2s}
  .search-box input{font-size:18px;letter-spacing:3px;text-transform:uppercase}
  .search-box input::placeholder{color:var(--text-dim);font-size:14px;letter-spacing:1px}
  .search-box input:focus,.expiry-box select:focus{border-color:var(--accent);box-shadow:0 0 20px rgba(0,229,160,.1)}
  .expiry-box{min-width:200px}
  .expiry-box select{font-size:13px;cursor:pointer;appearance:none}
  .search-btn{align-self:flex-end;background:var(--accent);color:#000;border:none;font-family:var(--mono);font-size:13px;font-weight:700;letter-spacing:2px;padding:14px 28px;cursor:pointer;text-transform:uppercase;transition:all .2s;white-space:nowrap}
  .search-btn:hover:not(:disabled){background:#fff;box-shadow:0 0 30px rgba(0,229,160,.3)}
  .search-btn:disabled{background:var(--border);color:var(--text-dim);cursor:not-allowed}

  .quick-tickers{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px;align-items:center}
  .quick-label{font-family:var(--mono);font-size:10px;color:var(--text-dim);letter-spacing:1px}
  .quick-btn{font-family:var(--mono);font-size:11px;padding:5px 12px;background:transparent;border:1px solid var(--border);color:var(--text-dim);cursor:pointer;letter-spacing:1px;transition:all .15s}
  .quick-btn:hover{border-color:var(--accent);color:var(--accent)}

  .stats-bar{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--border);margin-bottom:28px;border:1px solid var(--border)}
  .stat-cell{background:var(--surface);padding:16px 20px}
  .stat-label{font-family:var(--mono);font-size:9px;color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;margin-bottom:6px}
  .stat-value{font-family:var(--mono);font-size:20px;color:var(--text-bright);font-weight:700}
  .stat-value.call{color:var(--call)}.stat-value.put{color:var(--put)}.stat-value.neutral{color:var(--accent3)}

  .pcr-section{margin-bottom:28px;background:var(--surface);border:1px solid var(--border);padding:20px}
  .pcr-label{font-family:var(--mono);font-size:10px;color:var(--text-dim);letter-spacing:2px;margin-bottom:12px;text-transform:uppercase}
  .pcr-bar-wrap{display:flex;height:28px;overflow:hidden;border:1px solid var(--border)}
  .pcr-call-bar{background:linear-gradient(90deg,rgba(0,229,160,.6),rgba(0,229,160,.3));display:flex;align-items:center;padding-left:10px;font-family:var(--mono);font-size:11px;color:var(--call);font-weight:700;transition:width .8s cubic-bezier(.4,0,.2,1);min-width:60px}
  .pcr-put-bar{background:linear-gradient(90deg,rgba(255,77,109,.3),rgba(255,77,109,.6));flex:1;display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-family:var(--mono);font-size:11px;color:var(--put);font-weight:700}
  .pcr-legend{display:flex;justify-content:space-between;margin-top:8px}
  .pcr-legend span{font-family:var(--mono);font-size:10px;color:var(--text-dim)}

  .chart-section{margin-bottom:28px;background:var(--surface);border:1px solid var(--border);padding:20px}
  .section-title{font-family:var(--mono);font-size:10px;color:var(--text-dim);letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:10px}
  .section-title::after{content:'';flex:1;height:1px;background:var(--border)}
  #volumeChart{width:100%;height:180px}

  .table-section{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px}
  @media(max-width:768px){.table-section{grid-template-columns:1fr}}
  .options-table-wrap{background:var(--surface);border:1px solid var(--border);overflow:hidden}
  .table-header{padding:14px 16px;font-family:var(--mono);font-size:11px;letter-spacing:3px;text-transform:uppercase;font-weight:700;border-bottom:1px solid var(--border)}
  .table-header.call{color:var(--call);background:rgba(0,229,160,.05)}
  .table-header.put{color:var(--put);background:rgba(255,77,109,.05)}
  table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12px}
  thead th{padding:10px 12px;text-align:right;font-size:9px;letter-spacing:1px;color:var(--text-dim);text-transform:uppercase;border-bottom:1px solid var(--border);background:var(--surface2)}
  thead th:first-child{text-align:left}
  tbody tr{border-bottom:1px solid rgba(30,45,56,.5);transition:background .1s}
  tbody tr:hover{background:var(--surface2)}
  tbody td{padding:9px 12px;text-align:right;color:var(--text)}
  tbody td:first-child{text-align:left;color:var(--text-bright);font-weight:700}
  .vol-cell{position:relative}
  .vol-bar{position:absolute;left:0;top:0;bottom:0;opacity:.15}
  .vol-bar.call{background:var(--call)}.vol-bar.put{background:var(--put)}
  .vol-num{position:relative;z-index:1;font-weight:700}
  .vol-num.call{color:var(--call)}.vol-num.put{color:var(--put)}
  .itm-badge{font-size:8px;padding:1px 4px;border-radius:2px;margin-left:4px;font-weight:700;vertical-align:middle}
  .itm-badge.call-itm{background:rgba(0,229,160,.2);color:var(--call)}
  .itm-badge.put-itm{background:rgba(255,77,109,.2);color:var(--put)}

  .ai-prompt-section {
    margin-bottom:28px; background:rgba(0, 229, 160, 0.05); border:1px solid var(--accent); padding:20px;
    border-radius: 6px; display: flex; flex-direction: column; gap: 12px;
  }
  .ai-prompt-title {
    font-family: var(--sans); font-size: 16px; font-weight: 700; color: var(--text-bright);
    display: flex; align-items: center; gap: 8px;
  }
  .ai-prompt-desc {
    font-family: var(--sans); font-size: 12px; color: var(--text-dim); line-height: 1.6;
  }
  .ai-prompt-btn {
    align-self: flex-start; background: var(--accent); color: #000; border: none;
    font-family: var(--sans); font-size: 14px; font-weight: 700; padding: 12px 24px;
    border-radius: 4px; cursor: pointer; transition: all 0.2s;
    display: inline-flex; align-items: center; gap: 8px;
  }
  .ai-prompt-btn:hover {
    background: #fff; box-shadow: 0 0 20px rgba(0,229,160,.4);
  }

  .status-area{display:flex;align-items:center;justify-content:center;min-height:200px;flex-direction:column;gap:16px}
  .spinner{width:40px;height:40px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .status-text{font-family:var(--mono);font-size:12px;color:var(--text-dim);letter-spacing:2px;text-align:center;line-height:2}

  .error-box{background:rgba(255,77,109,.05);border:1px solid rgba(255,77,109,.3);padding:20px 24px;font-family:var(--mono);font-size:12px;color:var(--put);letter-spacing:1px;margin-bottom:20px;line-height:2}
  .hidden{display:none}

  .ticker-info{display:flex;align-items:center;gap:20px;margin-bottom:24px;flex-wrap:wrap}
  .ticker-name{font-family:var(--display);font-size:40px;letter-spacing:4px;color:var(--text-bright)}
  .ticker-price{font-family:var(--mono);font-size:28px;color:var(--text-bright);font-weight:700}
  .price-change{font-family:var(--mono);font-size:14px;padding:4px 10px;font-weight:700}
  .price-change.up{background:rgba(0,229,160,.15);color:var(--call)}
  .price-change.down{background:rgba(255,77,109,.15);color:var(--put)}

  .footnote{font-family:var(--mono);font-size:10px;color:var(--text-dim);letter-spacing:1px;margin-top:24px;padding-top:16px;border-top:1px solid var(--border);line-height:2}

  .welcome-box{text-align:center;padding:50px 20px;color:var(--text-dim)}
  .welcome-box .big{font-family:var(--display);font-size:64px;letter-spacing:8px;color:var(--surface2);margin-bottom:16px}
  .welcome-box p{font-family:var(--mono);font-size:12px;letter-spacing:1px;line-height:2.2}
</style>
</head>
<body>
<div class="wrapper">
  <header>
    <div><div class="logo">OPTIONS<span>FLOW</span></div></div>
    <div>
      <div class="live-badge"><div class="live-dot"></div>AI POWERED</div>
      <div class="subtitle">옵션 거래량 분석 시스템 · US &amp; KR Markets</div>
    </div>
  </header>

  <div class="apikey-panel" id="apikeyPanel">
    <label>🔑 ANTHROPIC API KEY</label>
    <input type="password" id="apikeyInput" placeholder="sk-ant-api03-..." autocomplete="off"/>
    <button class="apikey-save" onclick="saveApiKey()">저장</button>
    <div class="apikey-ok" id="apikeyOk">✓ API 키 설정됨 — 조회 가능합니다</div>
    <div class="apikey-info">
      로컬 파일 실행 시 Anthropic API 키가 필요합니다 ·
      <a href="https://console.anthropic.com/settings/keys" target="_blank" style="color:var(--accent3)">console.anthropic.com</a>에서 발급
      · 키는 브라우저 메모리에만 저장되며 전송되지 않습니다
    </div>
  </div>

  <div class="search-section">
    <div class="search-box">
      <label>티커 심볼 / TICKER SYMBOL</label>
      <input type="text" id="tickerInput" placeholder="AAPL · TSLA · 005930.KS" maxlength="20"/>
    </div>
    <div class="search-box expiry-box">
      <label>만기일 / EXPIRATION</label>
      <select id="expirySelect"><option value="0">-- 조회 후 선택 --</option></select>
    </div>
    <button class="search-btn" id="searchBtn" onclick="fetchOptions()">▶ 조회</button>
  </div>

  <div class="quick-tickers">
    <span class="quick-label">QUICK:</span>
    <button class="quick-btn" onclick="quickSearch('AAPL')">AAPL</button>
    <button class="quick-btn" onclick="quickSearch('TSLA')">TSLA</button>
    <button class="quick-btn" onclick="quickSearch('NVDA')">NVDA</button>
    <button class="quick-btn" onclick="quickSearch('SPY')">SPY</button>
    <button class="quick-btn" onclick="quickSearch('QQQ')">QQQ</button>
    <button class="quick-btn" onclick="quickSearch('AMZN')">AMZN</button>
    <button class="quick-btn" onclick="quickSearch('META')">META</button>
    <button class="quick-btn" onclick="quickSearch('005930.KS')">삼성전자</button>
    <button class="quick-btn" onclick="quickSearch('000660.KS')">SK하이닉스</button>
  </div>

  <div id="errorBox" class="error-box hidden"></div>

  <div id="loadingArea" class="status-area hidden">
    <div class="spinner"></div>
    <div class="status-text" id="loadingText">AI 백엔드 데이터 수신 중...<br><span style="font-size:10px;color:var(--text-dim)">Yahoo Finance 검색 → 파싱 (10~30초 소요)</span></div>
  </div>

  <div id="mainContent" class="hidden">
    <div class="ticker-info">
      <div class="ticker-name" id="dispTicker"></div>
      <div class="ticker-price" id="dispPrice"></div>
      <div class="price-change" id="dispChange"></div>
      <div style="font-family:var(--mono);font-size:11px;color:var(--text-dim)" id="dispName"></div>
    </div>
    
    <div class="stats-bar">
      <div class="stat-cell"><div class="stat-label">CALL 총 거래량</div><div class="stat-value call" id="statCallVol">—</div></div>
      <div class="stat-cell"><div class="stat-label">PUT 총 거래량</div><div class="stat-value put" id="statPutVol">—</div></div>
      <div class="stat-cell"><div class="stat-label">P/C RATIO</div><div class="stat-value neutral" id="statPCR">—</div></div>
      <div class="stat-cell"><div class="stat-label">CALL OI (미결제)</div><div class="stat-value call" id="statCallOI">—</div></div>
      <div class="stat-cell"><div class="stat-label">PUT OI (미결제)</div><div class="stat-value put" id="statPutOI">—</div></div>
      <div class="stat-cell"><div class="stat-label">만기일</div><div class="stat-value" id="statExpiry" style="font-size:14px">—</div></div>
    </div>

    <div class="pcr-section">
      <div class="pcr-label">CALL vs PUT 거래량 비율</div>
      <div class="pcr-bar-wrap">
        <div class="pcr-call-bar" id="pcrCallBar" style="width:50%">CALL</div>
        <div class="pcr-put-bar" id="pcrPutBar">PUT</div>
      </div>
      <div class="pcr-legend">
        <span id="pcrCallPct">CALL 50%</span>
        <span id="pcrSentiment">중립</span>
        <span id="pcrPutPct">PUT 50%</span>
      </div>
    </div>

    <div class="chart-section">
      <div class="section-title">행사가별 거래량 분포</div>
      <canvas id="volumeChart"></canvas>
    </div>

    <div class="table-section">
      <div class="options-table-wrap">
        <div class="table-header call">▲ CALLS — 콜옵션 (상승 베팅)</div>
        <div style="overflow-x:auto">
          <table><thead><tr><th>행사가</th><th>거래량</th><th>미결제</th><th>IV</th><th>프리미엄</th></tr></thead>
          <tbody id="callsBody"></tbody></table>
        </div>
      </div>
      <div class="options-table-wrap">
        <div class="table-header put">▼ PUTS — 풋옵션 (하락 베팅)</div>
        <div style="overflow-x:auto">
          <table><thead><tr><th>행사가</th><th>거래량</th><th>미결제</th><th>IV</th><th>프리미엄</th></tr></thead>
          <tbody id="putsBody"></tbody></table>
        </div>
      </div>
    </div>

    <div class="ai-prompt-section">
      <div class="ai-prompt-title">
        🤖 Gemini AI 심층 옵션 분석
      </div>
      <div class="ai-prompt-desc">
        수집된 실시간 방대한 옵션 데이터(최상위 거래량 행사가, 누적 미결제약정(OI), ATM 내재변동성, PCR 등)를 요약하여 <b>최고급 퀀트 수준의 분석 프롬프트</b>를 자동 작성합니다.<br>
        아래 버튼을 누르면 <b>프롬프트가 클립보드에 복사</b>되며, <b>Google Gemini 창이 열립니다.</b><br>
        입력창에 <code>[Ctrl+V]</code>를 눌러 붙여넣기만 하면 상세한 매매 전략과 지지/저항 리포트를 받을 수 있습니다.
      </div>
      <button class="ai-prompt-btn" onclick="openGeminiWithPrompt()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
        </svg>
        고급 분석 프롬프트 복사 & Gemini 열기
      </button>
    </div>

    <div class="footnote">
      ※ 데이터 출처: Yahoo Finance (Anthropic AI 서버 경유) · 실시간 데이터는 15분 지연될 수 있음<br>
      ※ 한국 개별 종목은 옵션 시장이 제한적 (KOSPI200 지수 옵션 중심)
    </div>
  </div>

  <div id="welcomeBox" class="welcome-box">
    <div class="big">OPTIONS</div>
    <p>
      티커를 입력하고 조회 버튼을 누르세요<br>
      미국 주식: AAPL, TSLA, NVDA, SPY, QQQ<br>
      한국 주식: 005930.KS (삼성전자), 000660.KS (SK하이닉스)<br><br>
      <span style="color:rgba(74,99,116,.6)">로컬 실행 시 상단 API 키 입력 필요</span>
    </p>
  </div>
</div>

<script>
let chartInstance = null;
let cachedData = null;
let allExpiryLabels = [];
let USER_API_KEY = '';

// ─── 환경 감지 ───────────────────────────────────────────
const isEmbedded = (function(){
  try {
    return window.self !== window.top ||
           location.hostname.includes('claude.ai') ||
           location.protocol === 'blob:' ||
           location.href.startsWith('blob:');
  } catch(e) { return true; }
})();

window.addEventListener('DOMContentLoaded', () => {
  if(isEmbedded){
    document.getElementById('apikeyPanel').classList.add('hidden');
  } else {
    const saved = sessionStorage.getItem('opt_apikey');
    if(saved){ USER_API_KEY = saved; showKeyOk(); }
  }
});

function saveApiKey(){
  const val = document.getElementById('apikeyInput').value.trim();
  if(!val.startsWith('sk-ant-')){
    alert('올바른 Anthropic API 키 형식이 아닙니다.\nsk-ant- 로 시작해야 합니다.');
    return;
  }
  USER_API_KEY = val;
  sessionStorage.setItem('opt_apikey', val);
  document.getElementById('apikeyInput').value = '•'.repeat(20);
  showKeyOk();
}

function showKeyOk(){
  document.getElementById('apikeyOk').classList.add('show');
}

// ─── 유틸 ────────────────────────────────────────────────
function fmt(n){
  if(n==null||isNaN(n)||n===0) return '—';
  if(n>=1e6) return (n/1e6).toFixed(1)+'M';
  if(n>=1e3) return (n/1e3).toFixed(1)+'K';
  return n.toLocaleString();
}

function quickSearch(t){ document.getElementById('tickerInput').value=t; fetchOptions(); }
document.getElementById('tickerInput').addEventListener('keydown',e=>{ if(e.key==='Enter') fetchOptions(); });
document.getElementById('expirySelect').addEventListener('change',()=>{
  if(!cachedData) return;
  const idx=parseInt(document.getElementById('expirySelect').value)||0;
  const label=allExpiryLabels[idx]||'';
  callApi(cachedData.symbol, `"${cachedData.symbol}" 티커의 만기일 "${label}" 옵션 체인 데이터를 Yahoo Finance에서 조회해줘.`, false);
});

// ─── API 호출 ────────────────────────────────────────────
const SYSTEM_PROMPT=`You are a precise financial data assistant. Search Yahoo Finance for options chain data and return ONLY a valid JSON object — absolutely no markdown, no fences, no explanation.

JSON structure:
{
  "symbol":"TICKER",
  "companyName":"Full Company Name",
  "currentPrice":123.45,
  "changePercent":1.23,
  "expirationLabels":["2025-04-17","2025-04-24"],
  "selectedExpiry":"2025-04-17",
  "calls":[{"strike":100.0,"volume":5000,"openInterest":12000,"impliedVolatility":0.35,"lastPrice":5.20}],
  "puts":[{"strike":100.0,"volume":3000,"openInterest":8000,"impliedVolatility":0.40,"lastPrice":3.10}]
}

Rules:
- All values must be numbers (not strings)
- impliedVolatility as decimal (0.35 = 35%)
- 15–25 strikes sorted ascending, within ±30% of spot price
- If no options exist: {"error":"No options market for this ticker"}
- Return ONLY the JSON object`;

async function fetchOptions(){
  let ticker=document.getElementById('tickerInput').value.trim().toUpperCase();
  if(!ticker) return;
  if(/^\d{6}$/.test(ticker)) ticker+='.KS';

  if(!isEmbedded && !USER_API_KEY){
    showError('API 키를 먼저 입력하고 저장 버튼을 눌러주세요.\n(상단 황색 패널에서 입력)');
    return;
  }

  const msg=`"${ticker}" 종목의 최신 옵션 체인 데이터를 Yahoo Finance에서 검색해서 JSON으로 반환해줘. 오늘 날짜(${new Date().toLocaleDateString('ko-KR')}) 기준 가장 가까운 만기일 데이터와 사용 가능한 만기일 목록도 포함해줘.`;
  await callApi(ticker, msg, true);
}

async function callApi(ticker, userMsg, isFirst){
  setLoading(true, 'Yahoo Finance 검색 중...\n(10~30초 소요)');
  clearError();

  const headers = { 'Content-Type': 'application/json' };
  if(!isEmbedded && USER_API_KEY){
    headers['x-api-key'] = USER_API_KEY;
    headers['anthropic-version'] = '2023-06-01';
    headers['anthropic-dangerous-direct-browser-access'] = 'true';
  }

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method:'POST',
      headers,
      body: JSON.stringify({
        model:'claude-sonnet-4-20250514',
        max_tokens:4000,
        system: SYSTEM_PROMPT,
        tools:[{type:'web_search_20250305',name:'web_search'}],
        messages:[{role:'user',content:userMsg}]
      })
    });

    if(!res.ok){
      const txt=await res.text();
      let hint='';
      if(res.status===401) hint='\n\n→ API 키가 잘못되었습니다. 다시 확인해주세요.';
      if(res.status===403) hint='\n\n→ 권한 오류. anthropic-dangerous-direct-browser-access 헤더 문제일 수 있습니다.';
      if(res.status===529) hint='\n\n→ Anthropic 서버 과부하. 잠시 후 다시 시도해주세요.';
      throw new Error(`HTTP ${res.status}${hint}\n\n${txt.slice(0,300)}`);
    }

    setLoading(true,'응답 파싱 중...');
    const apiData=await res.json();

    let rawText='';
    for(const block of (apiData.content||[])){
      if(block.type==='text') rawText+=block.text;
    }

    const match=rawText.match(/\{[\s\S]*\}/);
    if(!match) throw new Error('JSON 파싱 실패\n\n원본 응답:\n'+rawText.slice(0,400));

    const data=JSON.parse(match[0]);
    if(data.error) throw new Error(data.error);
    if(!data.calls||!data.puts) throw new Error('옵션 데이터 없음\n(이 종목은 옵션이 상장되지 않았을 수 있습니다)');

    cachedData=data;

    if(isFirst && data.expirationLabels?.length){
      allExpiryLabels=data.expirationLabels;
      const sel=document.getElementById('expirySelect');
      sel.innerHTML='';
      data.expirationLabels.forEach((l,i)=>{
        const o=document.createElement('option');
        o.value=i; o.textContent=l;
        if(i===0) o.selected=true;
        sel.appendChild(o);
      });
    }

    renderData(data);
    setLoading(false);

  } catch(err){
    setLoading(false);
    if(err.message.includes('Failed to fetch') || err.message.includes('NetworkError')){
      showError(
        'Failed to fetch — 네트워크 연결 실패\n\n' +
        '가능한 원인:\n' +
        '① 인터넷 연결 확인\n' +
        '② 로컬 파일 실행 시 API 키 미입력 (상단 황색 박스)\n' +
        '③ 브라우저 확장프로그램(광고차단기 등)이 api.anthropic.com 차단\n' +
        '④ 기업망/학교망 방화벽이 api.anthropic.com 차단\n\n' +
        '→ API 키를 입력했다면 브라우저 콘솔(F12)에서 오류를 확인하세요.'
      );
    } else {
      showError(err.message);
    }
  }
}

// ─── 렌더링 ──────────────────────────────────────────────
function renderData(data){
  const calls=data.calls||[], puts=data.puts||[], spot=data.currentPrice||0;
  const callVol=calls.reduce((s,c)=>s+(c.volume||0),0);
  const putVol =puts.reduce((s,c) =>s+(c.volume||0),0);
  const callOI =calls.reduce((s,c)=>s+(c.openInterest||0),0);
  const putOI  =puts.reduce((s,c) =>s+(c.openInterest||0),0);
  const pcr=callVol>0?putVol/callVol:0;
  const total=callVol+putVol;
  const callPct=total>0?callVol/total:0.5;

  document.getElementById('dispTicker').textContent=data.symbol||'—';
  document.getElementById('dispName').textContent=data.companyName||'';
  document.getElementById('dispPrice').textContent=spot?'$'+spot.toFixed(2):'—';

  const chg=data.changePercent||0;
  const chgEl=document.getElementById('dispChange');
  chgEl.textContent=(chg>=0?'+':'')+chg.toFixed(2)+'%';
  chgEl.className='price-change '+(chg>=0?'up':'down');

  document.getElementById('statCallVol').textContent=fmt(callVol);
  document.getElementById('statPutVol').textContent=fmt(putVol);
  document.getElementById('statPCR').textContent=pcr.toFixed(2);
  document.getElementById('statCallOI').textContent=fmt(callOI);
  document.getElementById('statPutOI').textContent=fmt(putOI);
  document.getElementById('statExpiry').textContent=data.selectedExpiry||'—';

  const cp=(callPct*100).toFixed(1)+'%', pp=((1-callPct)*100).toFixed(1)+'%';
  document.getElementById('pcrCallBar').style.width=cp;
  document.getElementById('pcrCallBar').textContent='CALL '+cp;
  document.getElementById('pcrPutBar').textContent='PUT '+pp;
  document.getElementById('pcrCallPct').textContent='CALL '+cp;
  document.getElementById('pcrPutPct').textContent='PUT '+pp;

  let s='중립 (NEUTRAL)';
  if(pcr>1.3)s='⚠ 하락 신호 (BEARISH)';
  else if(pcr>0.9)s='중립-하락 (SLIGHTLY BEARISH)';
  else if(pcr<0.5)s='✦ 상승 신호 (BULLISH)';
  else if(pcr<0.7)s='중립-상승 (SLIGHTLY BULLISH)';
  const se=document.getElementById('pcrSentiment');
  se.textContent=s; se.style.color=pcr>1?'var(--put)':pcr<0.7?'var(--call)':'var(--accent3)';

  const tC=[...calls].sort((a,b)=>(b.volume||0)-(a.volume||0)).slice(0,20);
  const tP=[...puts ].sort((a,b)=>(b.volume||0)-(a.volume||0)).slice(0,20);
  renderTable('callsBody',tC,Math.max(...tC.map(c=>c.volume||0),1),'call',spot);
  renderTable('putsBody', tP,Math.max(...tP.map(c=>c.volume||0),1),'put', spot);
  renderChart(calls,puts,spot);

  document.getElementById('welcomeBox').classList.add('hidden');
  document.getElementById('mainContent').classList.remove('hidden');
}

function renderTable(id,rows,maxVol,type,spot){
  const tb=document.getElementById(id); tb.innerHTML='';
  if(!rows.length){ tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:var(--text-dim);padding:20px">데이터 없음</td></tr>'; return; }
  rows.forEach(r=>{
    const str=r.strike||0,vol=r.volume||0,oi=r.openInterest||0,iv=r.impliedVolatility||0,lp=r.lastPrice||0;
    const pct=maxVol>0?vol/maxVol*100:0;
    const itm=type==='call'?str<=spot:str>=spot;
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>$${str.toFixed(1)}${itm?`<span class="itm-badge ${type}-itm">ITM</span>`:''}</td>
      <td class="vol-cell"><div class="vol-bar ${type}" style="width:${pct}%"></div><span class="vol-num ${type}">${fmt(vol)}</span></td>
      <td>${fmt(oi)}</td><td>${iv>0?(iv*100).toFixed(1)+'%':'—'}</td><td>${lp>0?'$'+lp.toFixed(2):'—'}</td>`;
    tb.appendChild(tr);
  });
}

function renderChart(calls,puts,spot){
  const lo=spot*.7,hi=spot*1.3;
  const cm={},pm={};
  calls.forEach(c=>cm[c.strike]=c.volume||0);
  puts.forEach(c=>pm[c.strike]=c.volume||0);
  const all=new Set([...calls.map(c=>c.strike),...puts.map(c=>c.strike)]);
  let stk=[...all].filter(s=>s>=lo&&s<=hi).sort((a,b)=>a-b).slice(0,30);
  if(!stk.length) stk=[...all].sort((a,b)=>a-b).slice(0,30);
  if(chartInstance) chartInstance.destroy();
  chartInstance=new Chart(document.getElementById('volumeChart').getContext('2d'),{
    type:'bar',
    data:{labels:stk.map(s=>'$'+s.toFixed(0)),datasets:[
      {label:'CALL 거래량',data:stk.map(s=>cm[s]||0),backgroundColor:'rgba(0,229,160,.5)',borderColor:'rgba(0,229,160,.8)',borderWidth:1},
      {label:'PUT 거래량', data:stk.map(s=>-(pm[s]||0)),backgroundColor:'rgba(255,77,109,.5)',borderColor:'rgba(255,77,109,.8)',borderWidth:1}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{labels:{color:'#4a6374',font:{family:'Space Mono',size:10}}},
        tooltip:{callbacks:{label:c=>' '+c.dataset.label+': '+Math.abs(c.raw).toLocaleString()}}},
      scales:{x:{ticks:{color:'#4a6374',font:{family:'Space Mono',size:9},maxRotation:45},grid:{color:'rgba(30,45,56,.5)'}},
        y:{ticks:{color:'#4a6374',font:{family:'Space Mono',size:9},callback:v=>fmt(Math.abs(v))},grid:{color:'rgba(30,45,56,.5)'}}}}
  });
}

// 💡 ── 한층 고도화된 고급 퀀트 프롬프트 생성 로직 ──
function openGeminiWithPrompt() {
  if (!cachedData) {
    alert("먼저 상단에서 티커를 조회해 주세요.");
    return;
  }

  // 1. 기본 데이터 추출
  const ticker = cachedData.symbol || 'N/A';
  const name = cachedData.companyName || ticker;
  const spot = cachedData.currentPrice || 0;
  const expiry = cachedData.selectedExpiry || 'N/A';
  
  const calls = cachedData.calls || [];
  const puts = cachedData.puts || [];
  
  // 2. 전체 요약 지표 계산
  const callVol = calls.reduce((s, c) => s + (c.volume || 0), 0);
  const putVol = puts.reduce((s, c) => s + (c.volume || 0), 0);
  const pcrVol = callVol > 0 ? (putVol / callVol).toFixed(2) : "0.00";
  
  const callOI = calls.reduce((s, c) => s + (c.openInterest || 0), 0);
  const putOI = puts.reduce((s, c) => s + (c.openInterest || 0), 0);
  const pcrOI = callOI > 0 ? (putOI / callOI).toFixed(2) : "0.00";

  // 3. 헬퍼 함수: 상위 N개 추출
  const getTopN = (arr, key, n) => [...arr].sort((a, b) => (b[key] || 0) - (a[key] || 0)).slice(0, n);
  
  const topCallVol = getTopN(calls, 'volume', 3);
  const topPutVol = getTopN(puts, 'volume', 3);
  const topCallOI = getTopN(calls, 'openInterest', 3);
  const topPutOI = getTopN(puts, 'openInterest', 3);

  // 4. ATM(등가격) 근처 옵션 찾기
  const getATM = (arr) => [...arr].sort((a, b) => Math.abs(a.strike - spot) - Math.abs(b.strike - spot)).slice(0, 1);
  const atmCall = getATM(calls)[0];
  const atmPut = getATM(puts)[0];

  // 5. 문자열 포맷팅 헬퍼
  const formatRow = (row) => {
    if(!row) return 'N/A';
    const iv = row.impliedVolatility ? (row.impliedVolatility * 100).toFixed(1) : 0;
    return `$${row.strike.toFixed(2)} (거래량: ${row.volume?.toLocaleString()||0} | 미결제: ${row.openInterest?.toLocaleString()||0} | 프리미엄: $${row.lastPrice?.toFixed(2)||0} | IV: ${iv}%)`;
  };

  // 6. 궁극의 프롬프트 조립
  const prompt = `[역할]
당신은 월스트리트의 수석 파생상품 애널리스트이자 퀀트 트레이더입니다. 
아래 제공된 방대하고 상세한 최신 옵션 체인 데이터를 바탕으로, 시장(스마트 머니)의 숨겨진 의도와 주가 방향성을 심층 분석해 주세요.

[종목 및 현재 정보]
- **티커**: ${ticker} (${name})
- **기초자산 현재가(Spot Price)**: $${spot.toFixed(2)}
- **옵션 만기일(Expiry)**: ${expiry}

[옵션 전체 수급 요약 (Macro View)]
- **콜옵션(Call)**: 총 거래량 ${callVol.toLocaleString()} / 총 미결제약정(OI) ${callOI.toLocaleString()}
- **풋옵션(Put)**: 총 거래량 ${putVol.toLocaleString()} / 총 미결제약정(OI) ${putOI.toLocaleString()}
- **Put/Call Ratio (거래량 기준)**: ${pcrVol}
- **Put/Call Ratio (미결제약정 기준)**: ${pcrOI}

[단기 수급 집중 매물대: 거래량 상위 3개 행사가]
**🟢 Call (상승 베팅 / 단기 저항선 역할):**
1. ${formatRow(topCallVol[0])}
2. ${formatRow(topCallVol[1])}
3. ${formatRow(topCallVol[2])}

**🔴 Put (하락 베팅 / 단기 지지선 역할):**
1. ${formatRow(topPutVol[0])}
2. ${formatRow(topPutVol[1])}
3. ${formatRow(topPutVol[2])}

[강력한 누적 포지션: 미결제약정(OI) 최고 행사가]
- **최대 Call 누적 저항선**: ${formatRow(topCallOI[0])}
- **최대 Put 누적 지지선**: ${formatRow(topPutOI[0])}

[ATM (현재가 근접) 가격 및 변동성 동향]
- **ATM Call** ($${atmCall ? atmCall.strike.toFixed(2) : 'N/A'}): 프리미엄 $${atmCall ? atmCall.lastPrice?.toFixed(2) : 0} / 내재변동성(IV) ${atmCall ? (atmCall.impliedVolatility*100).toFixed(1) : 0}%
- **ATM Put** ($${atmPut ? atmPut.strike.toFixed(2) : 'N/A'}): 프리미엄 $${atmPut ? atmPut.lastPrice?.toFixed(2) : 0} / 내재변동성(IV) ${atmPut ? (atmPut.impliedVolatility*100).toFixed(1) : 0}%

---
[📝 분석 지시사항 - 반드시 아래 내용에 답할 것]

1. **시장 심리 및 방향성 진단:** - 거래량 및 미결제약정 기준의 PCR(Put/Call Ratio)을 비교하여, 현재 트레이더들이 상승과 하락 중 어느 방향에 확신을 가지고 베팅하고 있는지 명확히 진단해 주세요.
   - 탐욕 상태인지, 공포 상태(헤징 수요 급증)인지 판단해 주세요.

2. **핵심 지지선 및 저항선 도출:** - 거래량 및 OI가 가장 많이 집중된 행사가(Strike) 데이터를 근거로, 이번 만기일까지 가장 유력한 **1차/2차 지지선과 저항선**을 가격대($)로 명확히 짚어주세요.

3. **내재변동성(IV) 및 프리미엄 분석:** - ATM 옵션의 IV 수치와 콜/풋 프리미엄 비대칭성을 통해, 시장이 큰 변동(실적발표 등 이벤트)을 예상하고 있는지, 아니면 횡보를 예상하고 있는지 해석해 주세요.

4. **실전 트레이딩 전략 제안:** - 위 수급 데이터에 근거하여 현 시점에서 개인 투자자가 취할 수 있는 구체적인 매매 시나리오를 제안해 주세요. 
   - (예: "$O.OO 이탈 시 강한 하방 압력 발생, 손절 요망", 또는 "옵션 매도자의 감마 스퀴즈 가능성" 등)

5. **출력 형식:** - 불필요한 서론 없이 바로 분석에 들어가며, **한글(Korean)**로 가독성 높은 마크다운(Markdown) 표와 글머리 기호를 활용해 전문적으로 작성해 주세요.`;

  // 7. 클립보드 복사 및 새 창 열기
  navigator.clipboard.writeText(prompt).then(() => {
    alert("✅ 고급 분석 프롬프트가 클립보드에 복사되었습니다!\n\n데이터 양이 많아 훨씬 깊이 있는 분석이 가능합니다.\nGemini 창이 열리면 대화창에 [Ctrl + V]를 눌러 붙여넣기 하세요.");
    window.open("https://gemini.google.com/", "_blank");
  }).catch(err => {
    alert("⚠️ 클립보드 복사에 실패했습니다. 브라우저 권한을 확인해주세요.");
    window.open("https://gemini.google.com/", "_blank");
  });
}

function setLoading(v,msg=''){
  document.getElementById('loadingArea').classList.toggle('hidden',!v);
  if(msg) document.getElementById('loadingText').innerHTML=msg.replace(/\n/g,'<br>');
  document.getElementById('searchBtn').disabled=v;
  if(v){ document.getElementById('mainContent').classList.add('hidden'); document.getElementById('welcomeBox').classList.add('hidden'); }
}
function showError(msg){
  const el=document.getElementById('errorBox');
  el.innerHTML='⚠ ERROR<br><br>'+msg.replace(/\n/g,'<br>');
  el.classList.remove('hidden');
  document.getElementById('welcomeBox').classList.remove('hidden');
}
function clearError(){ document.getElementById('errorBox').classList.add('hidden'); }
</script>
</body>
</html>

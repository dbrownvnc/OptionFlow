import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import sqlite3, time, json, os, requests
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="OPTIONS FLOW PRO", layout="wide", page_icon="📈")
st.markdown("""
<style>
.big-font{font-size:40px!important;font-weight:bold;color:#00e5a0;text-shadow:0 0 20px rgba(0,229,160,.2);}
.subtitle{font-size:16px;color:#a0a0a0;margin-bottom:25px;font-family:monospace;}
.report-box{background:#1e293b;padding:25px;border-radius:12px;border-left:5px solid #00e5a0;color:#f3f4f6;line-height:1.6;}
.signal-box{padding:14px 20px;border-radius:10px;margin:6px 0;font-size:14px;line-height:1.6;}
.signal-bull{background:rgba(0,229,160,.08);border-left:4px solid #00e5a0;}
.signal-bear{background:rgba(255,77,109,.08);border-left:4px solid #ff4d6d;}
.signal-neut{background:rgba(245,166,35,.08);border-left:4px solid #f5a623;}
.mcard{background:#111827;padding:18px;border-radius:12px;border:1px solid #1f2937;box-shadow:0 4px 6px rgba(0,0,0,.25);}
.mcard-label{color:#9ca3af;font-size:12px;font-weight:600;margin-bottom:6px;}
.mcard-value{font-size:26px;font-weight:800;}
.mcard-sub{font-size:12px;font-weight:700;margin-left:6px;}
.hcard{background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #334155;border-radius:16px;
       padding:26px 26px 20px;margin-bottom:16px;position:relative;overflow:hidden;}
.hcard::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
.hcard.pcr::before{background:linear-gradient(90deg,#00e5a0,#00b4d8);}
.hcard.uoa::before{background:linear-gradient(90deg,#f5a623,#ff6b6b);}
.hcard.voi::before{background:linear-gradient(90deg,#a78bfa,#60a5fa);}
.hcard.mp::before{background:linear-gradient(90deg,#fb923c,#f472b6);}
.hcard.db::before{background:linear-gradient(90deg,#34d399,#06b6d4);}
.hcard.warn::before{background:linear-gradient(90deg,#fbbf24,#f87171);}
.htitle{font-size:17px;font-weight:700;color:#f1f5f9;margin-bottom:10px;display:flex;align-items:center;gap:10px;}
.hbadge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;letter-spacing:.05em;}
.badge-pcr{background:rgba(0,229,160,.15);color:#00e5a0;}
.badge-uoa{background:rgba(245,166,35,.15);color:#f5a623;}
.badge-voi{background:rgba(167,139,250,.15);color:#a78bfa;}
.badge-mp{background:rgba(251,146,60,.15);color:#fb923c;}
.badge-db{background:rgba(52,211,153,.15);color:#34d399;}
.badge-warn{background:rgba(251,191,36,.15);color:#fbbf24;}
.hbody{color:#94a3b8;font-size:13px;line-height:1.75;}
.hbody strong{color:#e2e8f0;}
.htag{display:inline-block;background:#0f172a;border:1px solid #334155;border-radius:6px;
      padding:2px 9px;font-size:11px;font-family:monospace;margin:2px 3px 2px 0;color:#00e5a0;}
.tb-etf{background:rgba(96,165,250,.2);color:#60a5fa;border:1px solid #60a5fa;
        display:inline-block;font-size:11px;font-weight:700;padding:2px 10px;border-radius:12px;margin-left:8px;}
.tb-eq{background:rgba(0,229,160,.15);color:#00e5a0;border:1px solid #00e5a0;
       display:inline-block;font-size:11px;font-weight:700;padding:2px 10px;border-radius:12px;margin-left:8px;}
.tb-idx{background:rgba(167,139,250,.2);color:#a78bfa;border:1px solid #a78bfa;
        display:inline-block;font-size:11px;font-weight:700;padding:2px 10px;border-radius:12px;margin-left:8px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 v3.2 — 전면 3중 페일오버(Fail-over) 자동 복구 엔진 탑재</p>', unsafe_allow_html=True)

tab_analysis, tab_help = st.tabs(["📊 분석", "📖 도움말"])

with tab_help:
    st.markdown("## 📖 3중 데이터 자동 복구 엔진 가이드 (v3.2)")
    st.markdown("yfinance 접속 차단 방어를 위해, 만기일 조회부터 데이터 추출까지 모든 과정에 우회망이 적용되었습니다.")

# ══════════════════════════════════════════════════════════
# 강력한 데이터 수집기 (만기일 + 옵션 체인)
# ══════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def get_expirations_robust(ticker_symbol: str):
    """만기일(Expirations) 수집 전용 3중 우회 함수"""
    # 1. Raw API (가장 빠르고 확실함)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = f"https://query2.finance.yahoo.com/v7/finance/options/{ticker_symbol}"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            timestamps = data.get('optionChain', {}).get('result', [{}])[0].get('expirationDates', [])
            if timestamps:
                return [datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps]
    except: pass

    # 2. yfinance
    try:
        tk = yf.Ticker(ticker_symbol)
        exps = tk.options
        if exps: return list(exps)
    except: pass

    # 3. yahooquery
    try:
        from yahooquery import Ticker as yqTicker
        ytk = yqTicker(ticker_symbol)
        chain = ytk.option_chain
        if chain is not None and not chain.empty:
            df = chain.reset_index()
            return sorted(df['expiration'].astype(str).str[:10].unique().tolist())
    except: pass

    return []

@st.cache_data(ttl=300, show_spinner=False)
def fetch_options_chain_robust(ticker_symbol: str, exp_date: str):
    """옵션 체인 데이터 수집 3중 우회 함수"""
    # 1. yfinance
    try:
        tk = yf.Ticker(ticker_symbol)
        opt = tk.option_chain(exp_date)
        c, p = opt.calls.copy(), opt.puts.copy()
        if not c.empty and 'openInterest' in c.columns and c['openInterest'].sum() > 0:
            return c, p, "yfinance"
    except: pass

    # 2. yahooquery
    try:
        from yahooquery import Ticker as yqTicker
        ytk = yqTicker(ticker_symbol)
        chain = ytk.option_chain
        if chain is not None and not chain.empty:
            df = chain.reset_index()
            df['exp_str'] = df['expiration'].astype(str).str[:10]
            df_exp = df[df['exp_str'] == exp_date]
            if not df_exp.empty:
                c = df_exp[df_exp['optionType'] == 'calls'].copy()
                p = df_exp[df_exp['optionType'] == 'puts'].copy()
                if not c.empty and c.get('openInterest', pd.Series([0])).sum() > 0:
                    return c, p, "yahooquery"
    except: pass

    # 3. Raw JSON 직접 우회
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url_base = f"https://query2.finance.yahoo.com/v7/finance/options/{ticker_symbol}"
        res = requests.get(url_base, headers=headers, timeout=5)
        data = res.json()
        timestamps = data.get('optionChain', {}).get('result', [{}])[0].get('expirationDates', [])

        target_ts = None
        for ts in timestamps:
            dt_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
            if dt_str == exp_date:
                target_ts = ts
                break

        if target_ts:
            url_date = f"{url_base}?date={target_ts}"
            res_date = requests.get(url_date, headers=headers, timeout=5)
            opt_data = res_date.json().get('optionChain', {}).get('result', [{}])[0].get('options', [{}])[0]
            c = pd.DataFrame(opt_data.get('calls', []))
            p = pd.DataFrame(opt_data.get('puts', []))
            if not c.empty and 'openInterest' in c.columns:
                return c, p, "Raw API"
    except: pass

    return pd.DataFrame(), pd.DataFrame(), "수집 실패"

# ══════════════════════════════════════════════════════════
# 분석 탭 — 함수 정의
# ══════════════════════════════════════════════════════════
with tab_analysis:

    def calc_mid_price(row) -> float:
        bid = row.get('bid', 0) or 0
        ask = row.get('ask', 0) or 0
        if bid > 0 and ask > 0: return (bid + ask) / 2.0
        return row.get('lastPrice', 0) or 0

    def spread_ratio(row) -> float:
        bid = row.get('bid', 0) or 0
        ask = row.get('ask', 0) or 0
        mid = (bid + ask) / 2.0
        if mid <= 0: return 999.0
        return (ask - bid) / mid

    def get_atm_iv(calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> float:
        lo, hi = current_price * 0.95, current_price * 1.05
        atm_c = calls[(calls['strike'] >= lo) & (calls['strike'] <= hi)].copy()
        atm_p = puts [(puts ['strike'] >= lo) & (puts ['strike'] <= hi)].copy()
        combined = pd.concat([atm_c, atm_p])
        if combined.empty or 'impliedVolatility' not in combined.columns: return 0.0
        tmp = combined[['impliedVolatility','openInterest']].copy().replace(0, np.nan).dropna()
        tmp = tmp[(tmp['impliedVolatility'] >= 0.05) & (tmp['impliedVolatility'] <= 3.0)]
        if tmp.empty or tmp['openInterest'].sum() == 0: return 0.0
        return (tmp['impliedVolatility'] * tmp['openInterest']).sum() / tmp['openInterest'].sum()

    def expected_move_pct(current_price: float, atm_iv: float, dte: int) -> float:
        if atm_iv <= 0 or dte <= 0: return 3.0
        return atm_iv * np.sqrt(dte / 365.0) * 100

    def moneyness_dynamic(strike: float, current_price: float, side: str, em_pct: float) -> str:
        if current_price <= 0: return 'N/A'
        r = strike / current_price
        lo, hi = 1 - em_pct / 100, 1 + em_pct / 100
        if lo <= r <= hi: return 'ATM'
        if side == 'CALL': return 'ITM' if r < lo else 'OTM'
        else: return 'ITM' if r > hi else 'OTM'

    def iv_weighted(df: pd.DataFrame, weight_col: str = 'openInterest', iv_lo: float = 0.05, iv_hi: float = 3.0) -> float:
        if 'impliedVolatility' not in df.columns or weight_col not in df.columns: return 0.0
        tmp = df[['impliedVolatility', weight_col]].copy().replace(0, np.nan).dropna()
        tmp = tmp[(tmp['impliedVolatility'] >= iv_lo) & (tmp['impliedVolatility'] <= iv_hi)]
        total_w = tmp[weight_col].sum()
        if total_w == 0: return 0.0
        return (tmp['impliedVolatility'] * tmp[weight_col]).sum() / total_w

    DB_PATH = 'options_oi.db'
    def _get_db_conn():
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''CREATE TABLE IF NOT EXISTS oi_snap (
                    snap_date TEXT, ticker TEXT, exp_date TEXT, strike REAL, side TEXT,
                    oi REAL, volume REAL, last_price REAL, mid_price REAL,
                    PRIMARY KEY (snap_date, ticker, exp_date, strike, side))''')
            conn.commit()
            return conn
        except Exception: return None

    def save_oi_snapshot(ticker_str: str, exp_date: str, calls: pd.DataFrame, puts: pd.DataFrame):
        today = datetime.now().strftime('%Y-%m-%d')
        key   = f"{ticker_str}_{exp_date}_{today}"
        if 'oi_snaps' not in st.session_state: st.session_state['oi_snaps'] = {}
        if key in st.session_state['oi_snaps']: return
        rows = []
        for side, df in [('CALL', calls), ('PUT', puts)]:
            for _, r in df.iterrows():
                rows.append((today, ticker_str, exp_date, float(r['strike']), side,
                              float(r.get('openInterest', 0) or 0), float(r.get('volume', 0) or 0),
                              float(r.get('lastPrice', 0) or 0), float(calc_mid_price(r))))
        st.session_state['oi_snaps'][key] = rows
        conn = _get_db_conn()
        if conn:
            try:
                conn.executemany('INSERT OR IGNORE INTO oi_snap VALUES (?,?,?,?,?,?,?,?,?)', rows)
                conn.commit()
            except Exception: pass
            finally: conn.close()

    def get_delta_oi(ticker_str: str, exp_date: str, calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> pd.DataFrame:
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        prev_data = {}
        conn = _get_db_conn()
        if conn:
            try:
                cur = conn.execute('SELECT side,strike,oi,volume FROM oi_snap WHERE ticker=? AND exp_date=? AND snap_date=?', (ticker_str, exp_date, yesterday))
                for row in cur.fetchall(): prev_data[(row[0], row[1])] = {'oi': row[2], 'vol': row[3]}
            except Exception: pass
            finally: conn.close()
        if not prev_data:
            snaps = st.session_state.get('oi_snaps', {})
            prev_key = f"{ticker_str}_{exp_date}_{yesterday}"
            if prev_key in snaps:
                for row in snaps[prev_key]: prev_data[(row[4], row[3])] = {'oi': row[5], 'vol': row[6]}
        if not prev_data: return pd.DataFrame()

        lo, hi = (current_price * 0.7 if current_price > 0 else 0), (current_price * 1.3 if current_price > 0 else 1e9)
        records = []
        for side, df in [('CALL', calls), ('PUT', puts)]:
            df_f = df[(df['strike'] >= lo) & (df['strike'] <= hi)]
            for _, r in df_f.iterrows():
                k = (side, float(r['strike']))
                if k not in prev_data: continue
                oi_t, oi_p, vol = float(r.get('openInterest', 0) or 0), prev_data[k]['oi'], float(r.get('volume', 0) or 0)
                d = oi_t - oi_p
                if vol > oi_p * 0.5 and d > 0: sig = '🔥 신규 대형 베팅'
                elif vol > oi_p * 0.5 and d < 0: sig = '✂️ 대형 청산'
                elif d > oi_p * 0.1: sig = '📈 OI 증가'
                elif d < -oi_p * 0.1: sig = '📉 OI 감소'
                else: sig = '➖ 변화 미미'
                records.append({'side': side, 'strike': r['strike'], 'oi_today': oi_t, 'oi_prev': oi_p, 'delta_oi': d, 'volume': vol, 'signal': sig})
        if not records: return pd.DataFrame()
        return pd.DataFrame(records)[pd.DataFrame(records)['delta_oi'].abs() > 0].sort_values('delta_oi', ascending=False).head(20)

    def detect_uoa(df: pd.DataFrame, side: str, current_price: float, em_pct: float, voi_th: float = 5.0, min_premium: float = 10_000) -> pd.DataFrame:
        needed = [c for c in ['strike','volume','openInterest','lastPrice','bid','ask','impliedVolatility'] if c in df.columns]
        d = df[needed].copy()
        d['mid_price']      = d.apply(calc_mid_price, axis=1)
        d['spread_r']       = d.apply(spread_ratio,   axis=1)
        d['dollar_premium'] = d['mid_price'] * d.get('volume', 0) * 100
        d['V_OI']           = d['volume'] / d['openInterest'].replace(0, np.nan)
        d['moneyness']      = d['strike'].apply(lambda s: moneyness_dynamic(s, current_price, side, em_pct))
        d['spread_limit']   = d.apply(lambda row: 0.30 if row['moneyness'] == 'ATM' else 0.60, axis=1)
        filtered = d[(d['V_OI'] >= voi_th) & (d['dollar_premium'] >= min_premium) & (d['spread_r'] <= d['spread_limit'])].copy()
        filtered['side'] = side
        return filtered.sort_values('dollar_premium', ascending=False).head(5)

    def get_mp_band(dte: int) -> float:
        if dte <= 2: return 0.15
        elif dte <= 7: return 0.20
        elif dte <= 14: return 0.25
        elif dte <= 30: return 0.30
        else: return 0.40

    def calculate_max_pain(calls, puts, current_price: float = 0, dte: int = 60):
        band = get_mp_band(dte)
        if current_price > 0:
            lo_mp, hi_mp = current_price * (1 - band), current_price * (1 + band)
            calls = calls[(calls['strike'] >= lo_mp) & (calls['strike'] <= hi_mp)]
            puts  = puts [(puts ['strike'] >= lo_mp) & (puts ['strike'] <= hi_mp)]
        
        c_copy = calls.copy()
        p_copy = puts.copy()
        c_copy['openInterest'] = c_copy['openInterest'].fillna(0)
        p_copy['openInterest'] = p_copy['openInterest'].fillna(0)

        strikes = sorted(set(c_copy['strike'].tolist() + p_copy['strike'].tolist()))
        if not strikes or (c_copy['openInterest'].sum() == 0 and p_copy['openInterest'].sum() == 0):
            return 0.0
        
        pain = {}
        for s in strikes:
            cp = ((s - c_copy.loc[c_copy['strike']<s,'strike']) * c_copy.loc[c_copy['strike']<s,'openInterest']).sum()
            pp = ((p_copy.loc[p_copy['strike']>s,'strike'] - s) * p_copy.loc[p_copy['strike']>s,'openInterest']).sum()
            pain[s] = cp + pp
        return min(pain, key=pain.get) if pain else 0.0

    def get_pcr_thresholds(tt):
        if tt == 'ETF': return 1.5, 1.0
        if tt == 'INDEX': return 1.3, 0.85
        return 1.2, 0.7

    def pcr_divergence(pv, poi):
        if poi == 0: return 'signal-neut', 'PCR(OI)=0, 계산 불가'
        r = pv / poi
        if r > 1.5: return 'signal-bear', f"PCR(Vol)/PCR(OI) = <strong>{r:.2f}배</strong> → 단기 공포 이벤트"
        elif r < 0.67: return 'signal-bull', f"PCR(Vol)/PCR(OI) = <strong>{r:.2f}배</strong> → 단기 강세 모멘텀"
        return 'signal-neut', f"PCR(Vol)/PCR(OI) = {r:.2f}배 → 흐름 일치"

    def vol_oi_signal(cv, pv, coi, poi):
        if coi > poi and cv > pv: return 'bull', '📈 상승 추세 지속 가능'
        elif poi > coi and pv > cv: return 'bear', '📉 하락 추세/헤징 증가'
        elif coi > poi and pv > cv: return 'neut', '🔄 단기 조정 후 반등 가능성'
        else: return 'neut', '⚖️ 수급 혼재'

    def pcr_label(v, bth=1.2, blth=0.7):
        if v > bth: return 'signal-bull', f'PCR {v:.2f} — 공포(역발상 가능)'
        elif v < blth: return 'signal-bear', f'PCR {v:.2f} — 탐욕(조정 경계)'
        return 'signal-neut', f'PCR {v:.2f} — 중립'

    def add_vlines(fig, lines):
        for x_val, color, dash, label, yp in lines:
            fig.add_vline(x=x_val, line_dash=dash, line_color=color, line_width=1.5)
            if label:
                fig.add_annotation(x=x_val, y=yp, xref='x', yref='paper', text=label, showarrow=False,
                    font=dict(color=color, size=10, family='monospace'), bgcolor='rgba(15,23,42,.85)',
                    bordercolor=color, borderwidth=1, borderpad=3, xanchor='left', yanchor='top', xshift=5)

    def sig(css, label, body): return f'<div class="signal-box {css}"><strong>{label}</strong> &nbsp;·&nbsp; {body}</div>'
    def mc(label, value, color, sub='', sub_color='#9ca3af'):
        return f'<div class="mcard"><div class="mcard-label">{label}</div><div style="display:flex;align-items:baseline;"><span class="mcard-value" style="color:{color};">{value}</span><span class="mcard-sub" style="color:{sub_color};">{sub}</span></div></div>'
    def fmt_p(v):
        if v >= 1_000_000: return f'${v/1_000_000:.1f}M'
        if v >= 1_000: return f'${v/1_000:.0f}K'
        return f'${v:.0f}'

    def generate_with_fallback(prompt, api_key):
        genai.configure(api_key=api_key)
        for m in ['gemini-2.0-flash-lite-preview-02-05','gemini-1.5-pro','gemini-1.5-flash']:
            try: return genai.GenerativeModel(m).generate_content(prompt).text, m
            except: time.sleep(0.5)
        raise Exception('모든 모델 실패')

    # ══════════════════════════════════════════════════════
    # 사이드바 설정 
    # ══════════════════════════════════════════════════════
    api_key = st.secrets.get('GEMINI_API_KEY')
    has_api_key = api_key is not None
    if not has_api_key: st.sidebar.error('⚠️ API 키 없음')

    with st.sidebar:
        st.header('🔍 검색 설정')
        ticker_input = st.text_input('티커 심볼', value='AAPL').upper()
        
        # [NameError 방지] 모드를 먼저 선언
        analysis_mode = st.radio('분석 모드', ['단일 만기일 분석', '전체 기간 통합 분석 (단/중/장기)'])
        
        # [오류 해결] 만기일 리스트도 3중 엔진으로 로드
        expirations = get_expirations_robust(ticker_input)
        if not expirations:
            st.error('해당 종목의 옵션 데이터를 찾을 수 없습니다.')

        selected_expiry = None
        if expirations and analysis_mode == '단일 만기일 분석':
            selected_expiry = st.selectbox('만기일 선택', expirations)

        st.markdown('---')
        st.markdown('**💾 ΔOI 데이터베이스**')
        if os.path.exists(DB_PATH):
            try: 
                conn = _get_db_conn()
                cnt = conn.execute('SELECT COUNT(DISTINCT snap_date||ticker) FROM oi_snap').fetchone()[0]
                conn.close()
                st.success(f"로컬 DB 활성 · {cnt}개 스냅샷")
            except: pass

    # 종목 정보 및 현재가 역시 이중화(Fallback) 처리
    current_price = 0; name = ticker_input; ticker_type = 'EQUITY'
    if ticker_input and expirations:
        try:
            ticker = yf.Ticker(ticker_input)
            hist = ticker.history(period='1d')
            if not hist.empty: current_price = hist['Close'].iloc[-1]
            info = ticker.info
            name = info.get('longName', ticker_input) if info else ticker_input
            qt = info.get('quoteType', 'EQUITY').upper() if info else 'EQUITY'
            ticker_type = 'ETF' if qt == 'ETF' else ('INDEX' if qt in ('INDEX','MUTUALFUND') else 'EQUITY')
        except: pass
        
        # yfinance 실패 시 yahooquery로 현재가 긁어오기
        if current_price == 0:
            try:
                from yahooquery import Ticker as yqTicker
                price_data = yqTicker(ticker_input).price
                if type(price_data) is dict and ticker_input in price_data:
                    current_price = price_data[ticker_input].get('regularMarketPrice', 0)
                    name = price_data[ticker_input].get('shortName', ticker_input)
            except: pass

        bear_th, bull_th = get_pcr_thresholds(ticker_type)
        type_label = {'ETF':'ETF','INDEX':'INDEX','EQUITY':'개별주'}.get(ticker_type,'개별주')
        type_cls   = {'ETF':'tb-etf','INDEX':'tb-idx','EQUITY':'tb-eq'}.get(ticker_type,'tb-eq')
        st.markdown(f'<div style="display:flex;align-items:center;margin-bottom:8px;"><span style="font-size:1.25rem;font-weight:700;">📊 {name} ({ticker_input}) | ${current_price:,.2f}</span><span class="{type_cls}">{type_label}</span></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # 모드 1: 단일 만기일 분석
    # ══════════════════════════════════════════════════════
    if analysis_mode == '단일 만기일 분석' and selected_expiry:
        with st.spinner(f"데이터 수집 중... (다중 복구 엔진 동작)"):
            
            calls, puts, src_msg = fetch_options_chain_robust(ticker_input, selected_expiry)
            if src_msg != "yfinance" and src_msg != "수집 실패":
                st.toast(f"✅ yfinance 파서 오류 감지. 우회망({src_msg})으로 데이터를 성공적으로 복구했습니다.", icon="🛡️")
            elif src_msg == "수집 실패":
                st.error("🚨 3중 데이터 수집이 모두 실패했습니다. 야후 서버 점검 또는 상장 폐지 종목일 수 있습니다.")
                st.stop()

            dte_real = (datetime.strptime(selected_expiry,'%Y-%m-%d') - datetime.today()).days
            dte = max(dte_real, 1)

            atm_iv = get_atm_iv(calls, puts, current_price)
            em_pct = expected_move_pct(current_price, atm_iv, dte)
            em_source = 'ATM IV 기반' if atm_iv > 0 else '⚠️ Fallback(고정 3%)'

            save_oi_snapshot(ticker_input, selected_expiry, calls, puts)

            em_band = max(em_pct * 2, 15.0)
            lo = max(current_price * (1 - em_band / 100), current_price * 0.6) if current_price > 0 else 0
            hi = min(current_price * (1 + em_band / 100), current_price * 1.4) if current_price > 0 else 1e9
            cc = calls[(calls['strike']>=lo)&(calls['strike']<=hi)].copy()
            pc = puts [(puts ['strike']>=lo)&(puts ['strike']<=hi)].copy()

            cv, pv = calls['volume'].sum(), puts['volume'].sum()
            coi, poi = calls['openInterest'].fillna(0).sum(), puts['openInterest'].fillna(0).sum()
            pcr = pv/cv if cv>0 else 0
            pcr_oi = poi/coi if coi>0 else 0

            mp = calculate_max_pain(calls, puts, current_price, dte=dte_real)
            mp_gap = (mp - current_price) / current_price * 100 if current_price > 0 else 0

            max_call_oi = cc['openInterest'].fillna(0).max() if not cc.empty else 0
            max_put_oi  = pc['openInterest'].fillna(0).max() if not pc.empty else 0
            oi_wall_reliable = (max_call_oi >= 100 or max_put_oi >= 100)

            iv_oi_c, iv_vol_c = iv_weighted(cc, 'openInterest')*100, iv_weighted(cc, 'volume')*100
            iv_oi_p, iv_vol_p = iv_weighted(pc, 'openInterest')*100, iv_weighted(pc, 'volume')*100

            pcr_color = '#ff4d6d' if pcr>bear_th else ('#00e5a0' if pcr<bull_th else '#f5a623')
            mp_gap_color = '#ff4d6d' if mp_gap<-2 else ('#00e5a0' if mp_gap>2 else '#9ca3af')

            row1 = st.columns(4)
            with row1[0]: st.markdown(mc('CALL 거래량', f'{int(cv):,}', '#00e5a0'), unsafe_allow_html=True)
            with row1[1]: st.markdown(mc('PUT 거래량',  f'{int(pv):,}', '#ff4d6d'), unsafe_allow_html=True)
            with row1[2]: st.markdown(mc('PCR (Volume)', f'{pcr:.2f}', '#f3f4f6', '', pcr_color), unsafe_allow_html=True)
            with row1[3]: st.markdown(mc('Max Pain', f'${mp:,.0f}' if mp>0 else 'N/A', '#fb923c', f'({mp_gap:+.1f}%)', mp_gap_color), unsafe_allow_html=True)

            cc['openInterest'] = cc['openInterest'].fillna(0).round().astype(int)
            pc['openInterest'] = pc['openInterest'].fillna(0).round().astype(int)

            all_strikes = pd.concat([cc['strike'], pc['strike']])
            x_lo = max(all_strikes.min() - 2.5, lo - 2.5) if not all_strikes.empty else lo
            x_hi = min(all_strikes.max() + 2.5, hi + 2.5) if not all_strikes.empty else hi
            xaxis_cfg = dict(range=[x_lo, x_hi])

            fig = go.Figure()
            fig.add_trace(go.Bar(x=cc['strike'], y=cc['volume'], name='Call Vol', marker_color='#00e5a0'))
            fig.add_trace(go.Bar(x=pc['strike'], y=-pc['volume'], name='Put Vol', marker_color='#ff4d6d'))
            vl = [(current_price,'white','dash',f'현재가 ${current_price:,.2f}',0.97)] if current_price>0 else []
            if mp>0: vl.append((mp,'#fb923c','dot',f'Max Pain ${mp:,.0f}',0.82))
            add_vlines(fig, vl)
            fig.update_layout(title=f'① 행사가별 거래량 (데이터 소스: {src_msg})', barmode='relative', template='plotly_dark', height=400, xaxis=xaxis_cfg)
            st.plotly_chart(fig, use_container_width=True)

            if cc['openInterest'].sum() == 0 and pc['openInterest'].sum() == 0:
                st.error("🚨 **API 한계:** 장 시작 전이거나 얇은 유동성으로 인해 해당 만기일의 미결제약정(OI)이 모두 비어 있습니다. 그래프 표기가 불가능합니다.")
                oi_wall_reliable = False
            
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=cc['strike'], y=cc['openInterest'], name='Call OI', marker_color='rgba(0,229,160,.7)'))
            fig_oi.add_trace(go.Bar(x=pc['strike'], y=-pc['openInterest'], name='Put OI', marker_color='rgba(255,77,109,.7)'))
            add_vlines(fig_oi, vl)
            fig_oi.update_layout(title='② 행사가별 미결제약정 (OI Wall)', barmode='relative', template='plotly_dark', height=400, xaxis=xaxis_cfg)
            st.plotly_chart(fig_oi, use_container_width=True)

            st.markdown("### 🧠 옵션 이론 신호 분석")
            s1,m1_ = pcr_label(pcr, bear_th, bull_th)
            st.markdown(sig(s1,f'① PCR(Volume) [{type_label}기준 >{bear_th}/{bull_th}]',m1_), unsafe_allow_html=True)
            s2,m2_ = pcr_label(pcr_oi, bear_th, bull_th)
            st.markdown(sig(s2,'② PCR(OI) 누적 포지션',m2_), unsafe_allow_html=True)
            
            uoa_c = detect_uoa(cc,'CALL',current_price,em_pct)
            uoa_p = detect_uoa(pc,'PUT', current_price,em_pct)
            uoa_all = pd.concat([uoa_c,uoa_p]).sort_values('dollar_premium',ascending=False)
            if not uoa_all.empty:
                st.markdown(sig("signal-bull","⑧ UOA 스마트 머니 동향",f"스프레드 필터 통과 {len(uoa_all)}건 탐지됨"), unsafe_allow_html=True)
                st.dataframe(uoa_all[['side','moneyness','strike','mid_price','dollar_premium']], use_container_width=True)

            prompt = f"""당신은 파생상품 애널리스트입니다. {ticker_input}의 옵션 데이터를 분석하세요. (소스: {src_msg})\nPCR:{pcr:.2f} / MaxPain:${mp} / Call IV:{iv_vol_c:.1f}%"""

    # ══════════════════════════════════════════════════════
    # 모드 2: 전체 기간 분석
    # ══════════════════════════════════════════════════════
    elif analysis_mode == '전체 기간 통합 분석 (단/중/장기)' and expirations:
        with st.spinner('전체 만기일 데이터 수집 중... (3중 엔진 가동)'):
            TERMS = ['Short (단기/30일내)', 'Mid (중기/30~90일)', 'Long (장기/90일이상)']
            term_data = {t: dict(call_vol=0,put_vol=0,call_oi=0,put_oi=0,nearest_days=9999,nearest_exp=None) for t in TERMS}
            
            progress_bar = st.progress(0)
            fallback_count = 0

            for i, exp_date in enumerate(expirations):
                try:
                    days = (datetime.strptime(exp_date,'%Y-%m-%d') - datetime.today()).days
                    cat = TERMS[0] if days<=30 else TERMS[1] if days<=90 else TERMS[2]
                    td = term_data[cat]

                    c, p, src_msg = fetch_options_chain_robust(ticker_input, exp_date)
                    if src_msg != "yfinance": fallback_count += 1
                    
                    if c.empty and p.empty: continue

                    cv_ = c['volume'].sum() if 'volume' in c else 0
                    pv_ = p['volume'].sum() if 'volume' in p else 0
                    td['call_vol'] += cv_; td['put_vol'] += pv_
                    
                    if days>=0 and days<td['nearest_days']:
                        td['nearest_days']=days; td['nearest_exp']=exp_date
                except: pass
                progress_bar.progress((i+1)/len(expirations))
            progress_bar.empty()
            
            if fallback_count > 0:
                st.toast(f"✅ 데이터 다중화 엔진 동작 완료. {fallback_count}개의 만기일 데이터를 우회 통로로 성공적으로 복구했습니다.", icon="🛡️")

            st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
            df_terms = pd.DataFrame(term_data).T
            st.dataframe(df_terms[['call_vol','put_vol']], use_container_width=True)

    # ══════════════════════════════════════════════════════
    # 공통 AI 브리핑 버튼
    # ══════════════════════════════════════════════════════
    if ticker_input and expirations and ((analysis_mode == '단일 만기일 분석' and selected_expiry) or analysis_mode != '단일 만기일 분석'):
        st.divider()
        st.subheader('🤖 Gemini AI 옵션 시장 브리핑')
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('#### 옵션 1. 스트림릿에서 바로 분석')
            if st.button('✨ API 자동 분석 실행', type='primary', use_container_width=True):
                if has_api_key:
                    with st.spinner('AI 분석 중...'):
                        try:
                            result, used = generate_with_fallback(prompt, api_key)
                            st.success(f'완료 (모델: {used})')
                            st.markdown(f'<div class="report-box">{result}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f'오류: {e}')
                else:
                    st.error('API 키 없음')
        with col2:
            st.markdown('#### 옵션 2. Gemini 웹에서 분석')
            safe_prompt = json.dumps(prompt)
            components.html(f"""
            <button onclick="copyAndOpen()" style="background:#f5a623;color:#000;padding:12px 20px;
                border:none;border-radius:8px;font-weight:bold;font-size:15px;cursor:pointer;
                width:100%;box-shadow:0 4px 6px rgba(0,0,0,.1);">
                📋 프롬프트 복사 & Gemini 웹 열기
            </button>
            <script>
            function copyAndOpen(){{
                const t={safe_prompt};
                navigator.clipboard.writeText(t).then(()=>window.open('https://gemini.google.com/','_blank'))
                .catch(()=>{{const a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove();window.open('https://gemini.google.com/','_blank');}});
            }}
            </script>""", height=60)
        with st.expander('생성된 프롬프트 확인', expanded=False):
            st.code(prompt, language='text')

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import time
import json
import numpy as np
from datetime import datetime

st.set_page_config(page_title="OPTIONS FLOW PRO", layout="wide", page_icon="📈")
st.markdown("""
    <style>
    .big-font  { font-size:40px !important; font-weight:bold; color:#00e5a0;
                 text-shadow:0 0 20px rgba(0,229,160,0.2); }
    .subtitle  { font-size:16px; color:#a0a0a0; margin-bottom:25px; font-family:monospace; }
    .report-box{ background-color:#1e293b; padding:25px; border-radius:12px;
                 border-left:5px solid #00e5a0; color:#f3f4f6; line-height:1.6; }
    .signal-box { padding:14px 20px; border-radius:10px; margin:6px 0;
                  font-size:14px; line-height:1.6; }
    .signal-bull { background:rgba(0,229,160,0.08);  border-left:4px solid #00e5a0; }
    .signal-bear { background:rgba(255,77,109,0.08); border-left:4px solid #ff4d6d; }
    .signal-neut { background:rgba(245,166,35,0.08); border-left:4px solid #f5a623; }
    .mcard { background:#111827; padding:18px; border-radius:12px;
             border:1px solid #1f2937; box-shadow:0 4px 6px rgba(0,0,0,0.25); }
    .mcard-label { color:#9ca3af; font-size:13px; font-weight:600; margin-bottom:6px; }
    .mcard-value { font-size:28px; font-weight:800; }
    .mcard-sub   { font-size:13px; font-weight:700; margin-left:8px; }
    .hcard { background:linear-gradient(135deg,#0f172a,#1e293b);
             border:1px solid #334155; border-radius:16px;
             padding:26px 26px 20px; margin-bottom:16px;
             position:relative; overflow:hidden; }
    .hcard::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; }
    .hcard.pcr::before  { background:linear-gradient(90deg,#00e5a0,#00b4d8); }
    .hcard.uoa::before  { background:linear-gradient(90deg,#f5a623,#ff6b6b); }
    .hcard.voi::before  { background:linear-gradient(90deg,#a78bfa,#60a5fa); }
    .hcard.mp::before   { background:linear-gradient(90deg,#fb923c,#f472b6); }
    .hcard.warn::before { background:linear-gradient(90deg,#fbbf24,#f87171); }
    .htitle { font-size:18px; font-weight:700; color:#f1f5f9;
              margin-bottom:10px; display:flex; align-items:center; gap:10px; }
    .hbadge { font-size:11px; font-weight:700; padding:3px 10px;
              border-radius:20px; letter-spacing:.05em; }
    .badge-pcr  { background:rgba(0,229,160,.15);  color:#00e5a0; }
    .badge-uoa  { background:rgba(245,166,35,.15);  color:#f5a623; }
    .badge-voi  { background:rgba(167,139,250,.15); color:#a78bfa; }
    .badge-mp   { background:rgba(251,146,60,.15);  color:#fb923c; }
    .badge-warn { background:rgba(251,191,36,.15);  color:#fbbf24; }
    .hbody { color:#94a3b8; font-size:14px; line-height:1.75; }
    .hbody strong { color:#e2e8f0; }
    .htag { display:inline-block; background:#0f172a; border:1px solid #334155;
            border-radius:6px; padding:2px 9px; font-size:12px;
            font-family:monospace; margin:2px 3px 2px 0; color:#00e5a0; }
    .ticker-badge { display:inline-block; font-size:11px; font-weight:700;
                    padding:2px 10px; border-radius:12px; margin-left:10px; }
    .tb-etf  { background:rgba(96,165,250,.2);  color:#60a5fa; border:1px solid #60a5fa; }
    .tb-eq   { background:rgba(0,229,160,.15);  color:#00e5a0; border:1px solid #00e5a0; }
    .tb-idx  { background:rgba(167,139,250,.2); color:#a78bfa; border:1px solid #a78bfa; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (PRO 무결성 엔진 적용됨)</p>', unsafe_allow_html=True)

tab_analysis, tab_help = st.tabs(["📊 분석", "📖 도움말"])

# ══════════════════════════════════════════════════════════════
# 도움말 탭
# ══════════════════════════════════════════════════════════════
with tab_help:
    st.markdown("## 📖 옵션 데이터 활용 가이드 (PRO 엔진)")
    st.markdown("기존 옵션 분석 논리에 **스마트 머니 추적을 위한 데이터 정제 기술**이 추가되었습니다.")
    st.markdown("---")

    st.markdown("""
    <div class="hcard uoa">
      <div class="htitle">🔥 &nbsp;1. 비정상적 옵션 거래량 (UOA) - PRO 업데이트
        <span class="hbadge badge-uoa">정밀 필터 적용</span></div>
      <div class="hbody">
        <strong>⚡ Mid-Price 프리미엄 추정 & 호가 스프레드(Trim) 필터:</strong><br>
        단순 <code>Last Price × Volume</code>은 체결 공백으로 인한 허수를 만듭니다. 현재 <code>Mid-Price((Bid+Ask)/2)</code>를 기준으로 자금을 추정하며, 호가 스프레드가 30% 이상 벌어진 쓰레기 데이터는 자동 제외합니다.<br><br>
        <strong>⚡ ATR 동적 Moneyness:</strong><br>
        고정된 ±3%가 아닙니다. 최근 20일 변동성(ATR)을 자동 계산하여, 테슬라(TSLA)처럼 변동성이 큰 주식은 ATM 구간을 넓게, ETF는 좁게 동적 할당합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard mp">
      <div class="htitle">🎯 &nbsp;2. IV 가중평균 및 극단값 제거 - PRO 업데이트
        <span class="hbadge badge-mp">변동성 왜곡 방지</span></div>
      <div class="hbody">
        <strong>⚡ Volume 가중 평균 & 아웃라이어 제거:</strong><br>
        과거에 쌓인 OI 대신 <strong>오늘 활발하게 거래된 Volume</strong>을 가중치로 사용하여 당일 시장 심리를 더 정확히 반영합니다. 또한 yfinance 에러로 인한 IV 극단값(5% 미만, 300% 초과)은 꼬리 자르기(Trim) 처리하여 데이터를 보호합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard pcr">
      <div class="htitle">📊 &nbsp;3. 풋/콜 비율 (PCR) 다이버전스
        <span class="hbadge badge-pcr">역발상 지표</span></div>
      <div class="hbody">
        <strong>▸ 종목 유형별 임계값:</strong> ETF, INDEX, 개별주에 따라 기준(Bearish/Bullish) 자동 분기.<br>
        <strong>▸ PCR(Vol) / PCR(OI) 비율 비교:</strong> 누적 포지션 대비 당일 거래의 쏠림(다이버전스) 감지.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 분석 탭
# ══════════════════════════════════════════════════════════════
with tab_analysis:

    def detect_ticker_type(info: dict) -> str:
        qt = info.get('quoteType', '').upper()
        if qt == 'ETF':    return 'ETF'
        if qt in ('INDEX','MUTUALFUND'): return 'INDEX'
        return 'EQUITY'

    def get_pcr_thresholds(ticker_type: str):
        if ticker_type == 'ETF':   return 1.5, 1.0
        if ticker_type == 'INDEX': return 1.3, 0.85
        return 1.2, 0.7

    def pcr_divergence(pcr_vol, pcr_oi):
        if pcr_oi == 0: return "signal-neut", f"PCR(OI) = 0, 비율 계산 불가"
        ratio = pcr_vol / pcr_oi
        if ratio > 1.5:
            return "signal-bear", (f"PCR(Vol) {pcr_vol:.2f} / PCR(OI) {pcr_oi:.2f} = <strong>{ratio:.2f}배</strong> → 오늘 풋 거래 누적대비 급증 · 공포/헤징 주의")
        elif ratio < 0.67:
            return "signal-bull", (f"PCR(Vol) {pcr_vol:.2f} / PCR(OI) {pcr_oi:.2f} = <strong>{ratio:.2f}배</strong> → 오늘 콜 거래 누적대비 급증 · 강세 모멘텀 주의")
        else:
            return "signal-neut", (f"PCR(Vol) {pcr_vol:.2f} / PCR(OI) {pcr_oi:.2f} = {ratio:.2f}배 → 흐름 일치")

    # [핵심 수정] 동적 Moneyness 산출
    def moneyness(strike, current, side, atr_pct=0.03):
        if current <= 0: return 'N/A'
        r = strike / current
        if side == 'CALL':
            return 'ITM' if r < (1 - atr_pct) else ('OTM' if r > (1 + atr_pct) else 'ATM')
        else:
            return 'ITM' if r > (1 + atr_pct) else ('OTM' if r < (1 - atr_pct) else 'ATM')

    # [핵심 수정] Mid-Price 기반 프리미엄 & 스프레드 필터
    def detect_uoa(df: pd.DataFrame, side: str, current_price: float, atr_pct: float,
                   voi_threshold: float = 5.0, min_premium: float = 10_000) -> pd.DataFrame:
        needed = [c for c in ['strike','volume','openInterest','lastPrice','bid','ask'] if c in df.columns]
        d = df[needed].copy()
        
        # Mid-price 추정 및 스프레드율 산출
        if 'bid' in d.columns and 'ask' in d.columns:
            d['mid_price'] = (d['bid'] + d['ask']) / 2
            d['mid_price'] = d['mid_price'].replace(0, np.nan).fillna(d.get('lastPrice', 0))
            d['spread_pct'] = (d['ask'] - d['bid']) / d['mid_price'].replace(0, 1)
        else:
            d['mid_price'] = d.get('lastPrice', 0)
            d['spread_pct'] = 0.0

        d['V_OI'] = d['volume'] / d['openInterest'].replace(0, np.nan)
        d['dollar_premium'] = d['mid_price'] * d['volume'] * 100
        d['moneyness'] = d['strike'].apply(lambda s: moneyness(s, current_price, side, atr_pct))
        d['side'] = side
        
        # 필터링: 쓰레기 호가(스프레드 30% 이상) 제거
        filtered = d[(d['V_OI'] >= voi_threshold) & 
                     (d['dollar_premium'] >= min_premium) &
                     (d['spread_pct'] <= 0.30)].copy()
        return filtered.sort_values('dollar_premium', ascending=False).head(5)

    # [핵심 수정] Volume 가중 평균 IV (Outlier 제거)
    def iv_vol_weighted_avg(df: pd.DataFrame) -> float:
        if 'impliedVolatility' not in df.columns or 'volume' not in df.columns: return 0.0
        tmp = df[['impliedVolatility','volume']].copy().replace(0, np.nan).dropna()
        tmp = tmp[(tmp['impliedVolatility'] >= 0.05) & (tmp['impliedVolatility'] <= 3.00)]
        total_vol = tmp['volume'].sum()
        if total_vol == 0: return 0.0
        return (tmp['impliedVolatility'] * tmp['volume']).sum() / total_vol

    def generate_with_fallback(prompt, api_key):
        genai.configure(api_key=api_key)
        models = ["gemini-2.0-flash-lite-preview-02-05","gemini-1.5-pro","gemini-1.5-flash"]
        errs = []
        for m in models:
            try:
                r = genai.GenerativeModel(m).generate_content(prompt)
                return r.text, m
            except Exception as e:
                errs.append(f"[{m}: {str(e)[:80]}]"); time.sleep(0.5)
        raise Exception("모든 모델 실패: " + " / ".join(errs))

    def calculate_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
        strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
        pain = {}
        for s in strikes:
            c_pain = ((s - calls.loc[calls['strike']<s,'strike']) * calls.loc[calls['strike']<s,'openInterest'].fillna(0)).sum()
            p_pain = ((puts.loc[puts['strike']>s,'strike'] - s) * puts.loc[puts['strike']>s,'openInterest'].fillna(0)).sum()
            pain[s] = c_pain + p_pain
        return min(pain, key=pain.get) if pain else 0.0

    def vol_oi_signal(cv, pv, coi, poi):
        if coi > poi and cv > pv: return "bull", "📈 콜 OI 우세 + 콜 거래 활발 → 상승 추세 지속 가능"
        elif poi > coi and pv > cv: return "bear", "📉 풋 OI 우세 + 풋 거래 활발 → 하락 추세 지속 / 헤징 증가"
        elif coi > poi and pv > cv: return "neut", "🔄 콜 OI 우세 but 풋 거래 활발 → 단기 조정 후 반등 가능성"
        else: return "neut", "⚖️ 수급 혼재 → 방향성 불분명"

    def add_vlines(fig, lines: list):
        for x_val, color, dash, label, y_paper in lines:
            fig.add_vline(x=x_val, line_dash=dash, line_color=color, line_width=1.5)
            if label:
                fig.add_annotation(x=x_val, y=y_paper, xref="x", yref="paper", text=label, showarrow=False,
                    font=dict(color=color, size=11, family="monospace"), bgcolor="rgba(15,23,42,0.85)",
                    bordercolor=color, borderwidth=1, borderpad=4, xanchor="left", yanchor="top", xshift=6)

    def pcr_label(v, bear_th=1.2, bull_th=0.7):
        if v > bear_th: return "signal-bull", f"PCR {v:.2f} — 풋 과쏠림(공포) · 역발상 반등 가능"
        elif v < bull_th: return "signal-bear", f"PCR {v:.2f} — 콜 과쏠림(탐욕) · 조정 경계"
        else: return "signal-neut", f"PCR {v:.2f} — 중립 구간"

    def sig(css, label, body):
        return f'<div class="signal-box {css}"><strong>{label}</strong> &nbsp;·&nbsp; {body}</div>'

    def mc(label, value, color, sub="", sub_color="#9ca3af"):
        return (f'<div class="mcard"><div class="mcard-label">{label}</div><div style="display:flex;align-items:baseline;">'
                f'<span class="mcard-value" style="color:{color};">{value}</span><span class="mcard-sub" style="color:{sub_color};">{sub}</span></div></div>')

    def fmt_premium(v):
        if v >= 1_000_000: return f"${v/1_000_000:.1f}M"
        if v >= 1_000:     return f"${v/1_000:.0f}K"
        return f"${v:.0f}"

    api_key     = st.secrets.get("GEMINI_API_KEY")
    has_api_key = api_key is not None
    if not has_api_key: st.sidebar.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다.")

    with st.sidebar:
        st.header("🔍 검색 설정")
        ticker_input  = st.text_input("티커 심볼 (예: AAPL, NVDA, SPY)", value="AAPL").upper()
        analysis_mode = st.radio("분석 모드 선택", ["단일 만기일 분석", "전체 기간 통합 분석 (단/중/장기)"])
        ticker        = yf.Ticker(ticker_input)
        expirations   = []
        try:
            expirations = ticker.options
            if not expirations: st.error("옵션 데이터를 찾을 수 없는 티커입니다.")
        except: st.error("데이터 서버 연결에 문제가 발생했습니다.")
        selected_expiry = None
        if expirations and analysis_mode == "단일 만기일 분석":
            selected_expiry = st.selectbox("만기일 선택", expirations)

    current_price = 0; name = ticker_input; ticker_type = 'EQUITY'; atr_pct = 0.03
    if ticker_input and expirations:
        try:
            info          = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            hist          = ticker.history(period="20d")
            if not current_price and not hist.empty:
                current_price = hist['Close'].iloc[-1]
            name        = info.get('longName', ticker_input)
            ticker_type = detect_ticker_type(info)
            
            # ATR 기반 동적 Moneyness 산출
            if not hist.empty:
                atr_calc = ((hist['High'] - hist['Low']) / hist['Close']).mean()
                atr_pct = max(0.01, min(atr_calc, 0.10))
        except: pass

        bear_th, bull_th = get_pcr_thresholds(ticker_type)
        type_label  = {"ETF":"ETF","INDEX":"INDEX","EQUITY":"개별주"}.get(ticker_type,"개별주")
        type_cls    = {"ETF":"tb-etf","INDEX":"tb-idx","EQUITY":"tb-eq"}.get(ticker_type,"tb-eq")
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:8px;">'
            f'<span style="font-size:1.3rem;font-weight:700;">📊 {name} ({ticker_input}) | 현재가: ${current_price:,.2f}</span>'
            f'<span class="ticker-badge {type_cls}">{type_label} · 동적 ATR ±{atr_pct*100:.1f}% 적용</span>'
            f'</div>', unsafe_allow_html=True
        )

    # ══════════════════════════════════════════════════════════
    # 모드 1: 단일 만기일 분석
    # ══════════════════════════════════════════════════════════
    if analysis_mode == "단일 만기일 분석" and selected_expiry:
        with st.spinner(f"'{selected_expiry}' 만기 옵션 체인 분석 중..."):
            opt   = ticker.option_chain(selected_expiry)
            calls, puts = opt.calls.copy(), opt.puts.copy()
            lo, hi = (current_price*0.7, current_price*1.3) if current_price>0 else (0, 1e9)
            cc = calls[(calls['strike']>=lo)&(calls['strike']<=hi)].copy()
            pc = puts [(puts ['strike']>=lo)&(puts ['strike']<=hi)].copy()

            cv  = calls['volume'].sum();       pv  = puts['volume'].sum()
            coi = calls['openInterest'].fillna(0).sum(); poi = puts['openInterest'].fillna(0).sum()
            pcr    = pv/cv    if cv>0    else 0
            pcr_oi = poi/coi  if coi>0   else 0
            mp     = calculate_max_pain(calls, puts)
            mp_gap = (mp-current_price)/current_price*100 if current_price>0 else 0

            # [수정] Volume 가중평균 IV
            iv_call_vw = iv_vol_weighted_avg(cc) * 100
            iv_put_vw  = iv_vol_weighted_avg(pc) * 100

            pcr_color = "#ff4d6d" if pcr>bear_th else ("#00e5a0" if pcr<bull_th else "#f5a623")
            pcr_sub   = "Bearish ▼" if pcr>bear_th else ("Bullish ▲" if pcr<bull_th else "Neutral")
            mp_gap_color = "#ff4d6d" if mp_gap<-2 else ("#00e5a0" if mp_gap>2 else "#9ca3af")

            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.markdown(mc("CALL 거래량",    f"{int(cv):,}",    "#00e5a0"), unsafe_allow_html=True)
            with c2: st.markdown(mc("PUT 거래량",     f"{int(pv):,}",    "#ff4d6d"), unsafe_allow_html=True)
            with c3: st.markdown(mc("PCR (Volume)",   f"{pcr:.2f}",      "#f3f4f6", pcr_sub, pcr_color), unsafe_allow_html=True)
            with c4: st.markdown(mc("Max Pain",       f"${mp:,.0f}",     "#fb923c", f"({mp_gap:+.1f}%)", mp_gap_color), unsafe_allow_html=True)
            with c5: st.markdown(mc("IV Call (Vol가중)", f"{iv_call_vw:.1f}%","#00e5a0"), unsafe_allow_html=True)
            with c6: st.markdown(mc("IV Put (Vol가중)",  f"{iv_put_vw:.1f}%","#ff4d6d"), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=cc['strike'],y=cc['volume'],  name='Calls',marker_color='#00e5a0'))
            fig.add_trace(go.Bar(x=pc['strike'],y=-pc['volume'], name='Puts', marker_color='#ff4d6d'))
            vlines_v = []
            if current_price>0: vlines_v.append((current_price,"white","dash",f"현재가 ${current_price:,.2f}",0.97))
            if mp>0:             vlines_v.append((mp,"#fb923c","dot",f"Max Pain ${mp:,.0f}",0.82))
            add_vlines(fig, vlines_v)
            fig.update_layout(title=f"행사가별 거래량 (만기: {selected_expiry})", barmode='relative',template="plotly_dark",height=400,hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=cc['strike'],y=cc['openInterest'],   name='Call OI',marker_color='rgba(0,229,160,0.65)'))
            fig_oi.add_trace(go.Bar(x=pc['strike'],y=-pc['openInterest'],  name='Put OI', marker_color='rgba(255,77,109,0.65)'))
            vlines_o = []
            if current_price>0: vlines_o.append((current_price,"white","dash",f"현재가 ${current_price:,.2f}",0.97))
            if mp>0:             vlines_o.append((mp,"#fb923c","dot",f"Max Pain ${mp:,.0f}",0.82))
            if not cc.empty and not pc.empty:
                cow = cc.loc[cc['openInterest'].fillna(0).idxmax(),'strike']
                pow_ = pc.loc[pc['openInterest'].fillna(0).idxmax(),'strike']
                vlines_o.append((cow, "#00e5a0","dot",f"Call OI Wall(저항) ${cow:,.0f}",0.67))
                vlines_o.append((pow_,"#ff4d6d","dot",f"Put OI Wall(지지) ${pow_:,.0f}", 0.52))
            add_vlines(fig_oi, vlines_o)
            fig_oi.update_layout(title="행사가별 미결제약정 — OI Wall 지도 (Call OI Wall = 저항 / Put OI Wall = 지지)", barmode='relative',template="plotly_dark",height=400,hovermode="x unified")
            st.plotly_chart(fig_oi, use_container_width=True)

            st.markdown("### 🧠 옵션 이론 신호 분석")
            s1,m1_ = pcr_label(pcr, bear_th, bull_th)
            st.markdown(sig(s1,f"① PCR(Volume) [{type_label} 기준 >{bear_th}/{bull_th}]",m1_), unsafe_allow_html=True)
            s2,m2_ = pcr_label(pcr_oi, bear_th, bull_th)
            st.markdown(sig(s2,"② PCR(OI) 누적 포지션 신호",m2_), unsafe_allow_html=True)
            dc3,dm3 = pcr_divergence(pcr, pcr_oi)
            st.markdown(sig(dc3,"③ PCR 내부 다이버전스 (비율 기반)",dm3), unsafe_allow_html=True)

            if mp>0:
                mc4_ = "signal-bear" if mp_gap<-2 else ("signal-bull" if mp_gap>2 else "signal-neut")
                mb4  = (f"Max Pain ${mp:,.0f}이 현재가 대비 <strong>{mp_gap:.1f}%</strong> 아래 → 하락 수렴 압력" if mp_gap<-2 else (f"Max Pain ${mp:,.0f}이 현재가 대비 <strong>{mp_gap:+.1f}%</strong> 위 → 상승 수렴 압력" if mp_gap>2 else f"현재가 ≈ Max Pain ${mp:,.0f} → 만기일 횡보 압력 우세"))
                st.markdown(sig(mc4_,"④ Max Pain 수렴 신호",mb4), unsafe_allow_html=True)

            vc5,vm5 = vol_oi_signal(cv,pv,coi,poi)
            st.markdown(sig(f"signal-{vc5}","⑤ Volume × OI 교차 신호",vm5), unsafe_allow_html=True)

            if not cc.empty and not pc.empty:
                wc6  = "signal-bear" if current_price>cow else ("signal-bull" if current_price<pow_ else "signal-neut")
                wb6  = (f"Call OI Wall(저항): <strong>${cow:,.0f}</strong> &nbsp;·&nbsp; Put OI Wall(지지): <strong>${pow_:,.0f}</strong>" + (" &nbsp;·&nbsp; 현재가가 Call OI Wall 돌파 → 단기 상방 저항 약화" if current_price>cow else (" &nbsp;·&nbsp; 현재가가 Put OI Wall 하회 → 추가 하락 리스크" if current_price<pow_ else f" &nbsp;·&nbsp; 현재가 두 Wall 사이 → 범위 내 등락")))
                st.markdown(sig(wc6,"⑥ OI Wall 지지/저항 (Call OI Wall / Put OI Wall)",wb6), unsafe_allow_html=True)

            if iv_call_vw > 0 and iv_put_vw > 0:
                iv_skew = iv_put_vw - iv_call_vw
                iv_cls  = "signal-bear" if iv_skew>5 else ("signal-bull" if iv_skew<-3 else "signal-neut")
                iv_msg  = (f"IV Skew(Put-Call) = <strong>{iv_skew:+.1f}%p</strong> → 풋 프리미엄 높음, 하락 공포 내재" if iv_skew>5 else (f"IV Skew(Put-Call) = <strong>{iv_skew:+.1f}%p</strong> → 콜 프리미엄 높음, 상승 기대 내재" if iv_skew<-3 else f"IV Skew(Put-Call) = <strong>{iv_skew:+.1f}%p</strong> → 콜·풋 IV 균형"))
                st.markdown(sig(iv_cls,"⑦ IV Skew 해석 (Volume 가중평균 기반)",iv_msg), unsafe_allow_html=True)

            # [수정] UOA 탐지 (Mid-Price & ATR 적용)
            uoa_calls = detect_uoa(cc,"CALL",current_price, atr_pct)
            uoa_puts  = detect_uoa(pc,"PUT", current_price, atr_pct)
            uoa_all   = pd.concat([uoa_calls,uoa_puts]).sort_values('dollar_premium',ascending=False)
            if not uoa_all.empty:
                otm_calls = len(uoa_all[(uoa_all['side']=='CALL')&(uoa_all['moneyness']=='OTM')])
                otm_puts  = len(uoa_all[(uoa_all['side']=='PUT') &(uoa_all['moneyness']=='OTM')])
                u8_cls    = "signal-bull" if otm_calls>otm_puts else ("signal-bear" if otm_puts>otm_calls else "signal-neut")
                u8_msg    = (f"V/OI≥5 & 추정 Premium≥$10K 정밀 필터 통과 <strong>{len(uoa_all)}건</strong> · OTM콜 {otm_calls}건 / OTM풋 {otm_puts}건")
                st.markdown(sig(u8_cls,"⑧ UOA 스마트 머니 탐지 (Mid-Price 필터 적용)",u8_msg), unsafe_allow_html=True)
                ud = uoa_all[['side','moneyness','strike','volume','dollar_premium','spread_pct','mid_price']].copy()
                ud.columns = ['구분','Moneyness','행사가','거래량','추정 프리미엄','스프레드','Mid-Price']
                ud['추정 프리미엄'] = ud['추정 프리미엄'].apply(fmt_premium)
                ud['스프레드'] = ud['스프레드'].apply(lambda x: f"{x*100:.1f}%")
                ud['Mid-Price'] = ud['Mid-Price'].apply(lambda x: f"${x:.2f}")
                st.dataframe(ud, use_container_width=True)
            else:
                st.markdown(sig("signal-neut","⑧ UOA 경보","필터를 통과한 특이 동향 미감지"), unsafe_allow_html=True)

            cow_v  = cc.loc[cc['openInterest'].fillna(0).idxmax(),'strike'] if not cc.empty else 0
            pow_v_ = pc.loc[pc['openInterest'].fillna(0).idxmax(),'strike'] if not pc.empty else 0
            uoa_str = uoa_all[['side','moneyness','strike','dollar_premium']].to_string(index=False) if not uoa_all.empty else "없음"
            prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 기반으로 시장 심리를 분석하세요.
[분석 대상] {ticker_input} ({name}) | 종목유형: {type_label} | 만기일: {selected_expiry} | 현재가: ${current_price:,.2f}
[수급 데이터] 콜 거래량: {cv:,.0f} / 콜 OI: {coi:,.0f} | 풋 거래량: {pv:,.0f} / 풋 OI: {poi:,.0f}
PCR(Vol): {pcr:.2f} / PCR(OI): {pcr_oi:.2f} / 편차 비율: {pcr/pcr_oi:.2f}배
[IV (Vol 가중평균)] Call IV: {iv_call_vw:.1f}% / Put IV: {iv_put_vw:.1f}% / Skew: {iv_put_vw-iv_call_vw:+.1f}%p
[Max Pain & Wall] Max Pain: ${mp:,.2f} ({mp_gap:+.1f}%) | Call Wall: ${cow_v:,.0f} / Put Wall: ${pow_v_:,.0f}
[UOA (Mid-Price 추정)] {uoa_str}
지시사항: 단기 주가 방향과 핵심 가격 레벨을 한글 마크다운으로 정리하세요.
"""

    # ══════════════════════════════════════════════════════════
    # 모드 2: 전체 기간 통합 분석
    # ══════════════════════════════════════════════════════════
    elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:
        st.info(f"💡 **단/중/장기 통합** | 종목유형: **{type_label}** | 동적 ATR ±{atr_pct*100:.1f}% | IV Vol 가중평균 · Mid-Price UOA 필터 적용")

        with st.spinner("전체 만기일 데이터 수집 중... (10~30초 소요)"):
            today = datetime.today()
            TERMS = ["Short (단기/30일내)", "Mid (중기/30~90일)", "Long (장기/90일이상)"]
            term_data = {t: dict(call_vol=0,put_vol=0,call_oi=0,put_oi=0,
                                 iv_wsum_c=0.0, iv_wvol_c=0.0, iv_wsum_p=0.0, iv_wvol_p=0.0,
                                 nearest_days=9999,nearest_exp=None) for t in TERMS}
            strike_oi   = {}
            uoa_records = []
            expiry_pcr  = []
            progress_bar = st.progress(0)
            total_exps   = len(expirations)

            for i, exp_date in enumerate(expirations):
                try:
                    days = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                    cat  = TERMS[0] if days<=30 else TERMS[1] if days<=90 else TERMS[2]
                    td   = term_data[cat]

                    opt  = ticker.option_chain(exp_date)
                    c, p = opt.calls.copy(), opt.puts.copy()

                    cv_ = c['volume'].sum() if 'volume' in c else 0
                    pv_ = p['volume'].sum() if 'volume' in p else 0
                    coi_= c['openInterest'].fillna(0).sum() if 'openInterest' in c else 0
                    poi_= p['openInterest'].fillna(0).sum() if 'openInterest' in p else 0
                    td['call_vol']+=cv_; td['put_vol']+=pv_
                    td['call_oi'] +=coi_; td['put_oi'] +=poi_

                    # [수정] Volume 가중평균 누적 (극단값 제거)
                    if 'impliedVolatility' in c and 'volume' in c:
                        tmp = c[['impliedVolatility','volume']].replace(0,np.nan).dropna()
                        tmp = tmp[(tmp['impliedVolatility'] >= 0.05) & (tmp['impliedVolatility'] <= 3.0)]
                        td['iv_wsum_c'] += (tmp['impliedVolatility']*tmp['volume']).sum()
                        td['iv_wvol_c'] += tmp['volume'].sum()
                    if 'impliedVolatility' in p and 'volume' in p:
                        tmp = p[['impliedVolatility','volume']].replace(0,np.nan).dropna()
                        tmp = tmp[(tmp['impliedVolatility'] >= 0.05) & (tmp['impliedVolatility'] <= 3.0)]
                        td['iv_wsum_p'] += (tmp['impliedVolatility']*tmp['volume']).sum()
                        td['iv_wvol_p'] += tmp['volume'].sum()

                    if days>=0 and days<td['nearest_days']:
                        td['nearest_days']=days; td['nearest_exp']=exp_date

                    lo2,hi2 = current_price*0.7, current_price*1.3
                    c_w = c[(c['strike']>=lo2)&(c['strike']<=hi2)].copy() if current_price>0 else c.copy()
                    p_w = p[(p['strike']>=lo2)&(p['strike']<=hi2)].copy() if current_price>0 else p.copy()

                    for _, row in c_w.iterrows():
                        s=row['strike']; strike_oi.setdefault(s,[0,0])
                        strike_oi[s][0] += row.get('openInterest',0) or 0
                    for _, row in p_w.iterrows():
                        s=row['strike']; strike_oi.setdefault(s,[0,0])
                        strike_oi[s][1] += row.get('openInterest',0) or 0

                    # [수정] UOA 탐지
                    for side2, df_s in [("CALL",c_w),("PUT",p_w)]:
                        uoa_tmp = detect_uoa(df_s, side2, current_price, atr_pct)
                        for _, row in uoa_tmp.iterrows():
                            uoa_records.append({'exp_date':exp_date,'term':cat.split(' ')[0],'side':side2,
                                'moneyness':row['moneyness'],'strike':row['strike'],'volume':row.get('volume',0),
                                'V_OI':row['V_OI'],'dollar_premium':row['dollar_premium'],'spread_pct':row['spread_pct'],'days':days})

                    expiry_pcr.append({'exp_date':exp_date,'days':days,'term':cat.split(' ')[0],
                        'pcr_vol':pv_/cv_ if cv_>0 else np.nan, 'pcr_oi': poi_/coi_ if coi_>0 else np.nan})
                except: pass
                progress_bar.progress((i+1)/total_exps)
            progress_bar.empty()

            df_terms = pd.DataFrame(term_data).T
            df_terms['PCR (Volume)'] = df_terms['put_vol']/df_terms['call_vol']
            df_terms['PCR (OI)']     = df_terms['put_oi'] /df_terms['call_oi']
            df_terms['IV(Call) %'] = (df_terms['iv_wsum_c'] / df_terms['iv_wvol_c'].replace(0,np.nan) * 100).fillna(0)
            df_terms['IV(Put) %']  = (df_terms['iv_wsum_p'] / df_terms['iv_wvol_p'].replace(0,np.nan) * 100).fillna(0)
            df_terms['IV Skew']    = df_terms['IV(Put) %'] - df_terms['IV(Call) %']
            df_terms.fillna(0, inplace=True)

            mp_per_term = {}
            for t in TERMS:
                ne = term_data[t]['nearest_exp']
                if ne:
                    try: o2=ticker.option_chain(ne); mp_per_term[t]=calculate_max_pain(o2.calls,o2.puts)
                    except: mp_per_term[t]=0
                else: mp_per_term[t]=0

            df_wall = pd.DataFrame([(s,v[0],v[1]) for s,v in sorted(strike_oi.items())], columns=['strike','call_oi','put_oi'])
            cow_all = df_wall.loc[df_wall['call_oi'].idxmax(),'strike'] if not df_wall.empty else 0
            pow_all = df_wall.loc[df_wall['put_oi'].idxmax(), 'strike'] if not df_wall.empty else 0

            df_uoa = (pd.DataFrame(uoa_records).sort_values('dollar_premium',ascending=False).drop_duplicates(subset=['side','strike']).head(15) if uoa_records else pd.DataFrame())
            df_pcr_sc = pd.DataFrame(expiry_pcr).dropna(subset=['pcr_vol'])

            total_cv = df_terms['call_vol'].sum(); total_pv = df_terms['put_vol'].sum()
            total_coi= df_terms['call_oi'].sum();  total_poi= df_terms['put_oi'].sum()
            tot_pcr = total_pv/total_cv if total_cv>0 else 0
            tot_pcr_oi = total_poi/total_coi if total_coi>0 else 0

            pc_color = "#ff4d6d" if tot_pcr>bear_th else ("#00e5a0" if tot_pcr<bull_th else "#f5a623")
            pc_sub   = "Bearish ▼" if tot_pcr>bear_th else ("Bullish ▲" if tot_pcr<bull_th else "Neutral")

            m1,m2,m3,m4,m5 = st.columns(5)
            with m1: st.markdown(mc("전체 CALL 거래량",  f"{int(total_cv):,}",   "#00e5a0"), unsafe_allow_html=True)
            with m2: st.markdown(mc("전체 PUT 거래량",   f"{int(total_pv):,}",   "#ff4d6d"), unsafe_allow_html=True)
            with m3: st.markdown(mc("전체 PCR(Volume)",  f"{tot_pcr:.2f}",       "#f3f4f6", pc_sub, pc_color), unsafe_allow_html=True)
            with m4: st.markdown(mc("전체 PCR(OI)",      f"{tot_pcr_oi:.2f}",    "#a78bfa"), unsafe_allow_html=True)
            with m5: st.markdown(mc("Call OI Wall",      f"${cow_all:,.0f}",     "#fb923c", f"Put OI Wall ${pow_all:,.0f}","#ff4d6d"), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
            f1 = go.Figure()
            f1.add_trace(go.Bar(x=df_terms.index,y=df_terms['call_vol'],name='CALL 거래량',marker_color='#00e5a0'))
            f1.add_trace(go.Bar(x=df_terms.index,y=df_terms['put_vol'], name='PUT 거래량', marker_color='#ff4d6d'))
            f1.update_layout(barmode='group',template='plotly_dark',height=360,hovermode="x unified")
            st.plotly_chart(f1, use_container_width=True)

            f2 = go.Figure()
            f2.add_trace(go.Scatter(x=df_terms.index,y=df_terms['PCR (Volume)'],mode='lines+markers+text',name='PCR(Volume)',text=[f"{v:.2f}" for v in df_terms['PCR (Volume)']],textposition="top center",line=dict(color='#f5a623',width=3),marker=dict(size=10)))
            f2.add_trace(go.Scatter(x=df_terms.index,y=df_terms['PCR (OI)'],mode='lines+markers+text',name='PCR(OI)',text=[f"{v:.2f}" for v in df_terms['PCR (OI)']],textposition="bottom center",line=dict(color='#a78bfa',width=3,dash='dot'),marker=dict(size=10)))
            f2.add_hline(y=bear_th,line_dash="dash",line_color="#ff4d6d",annotation_text=f"Bearish({bear_th})")
            f2.add_hline(y=bull_th,line_dash="dash",line_color="#00e5a0",annotation_text=f"Bullish({bull_th})")
            f2.update_layout(title=f"기간별 PCR — {type_label} 기준 임계값 자동 적용",template='plotly_dark',height=380)
            st.plotly_chart(f2, use_container_width=True)

            if not df_wall.empty:
                st.markdown("#### 🏰 OI Wall — 전 만기 행사가별 OI 집중도")
                f3 = go.Figure()
                f3.add_trace(go.Bar(x=df_wall['strike'],y=df_wall['call_oi'],name='Call OI 합산',marker_color='rgba(0,229,160,0.7)'))
                f3.add_trace(go.Bar(x=df_wall['strike'],y=-df_wall['put_oi'],name='Put OI 합산', marker_color='rgba(255,77,109,0.7)'))
                vlines_w = []
                if current_price>0: vlines_w.append((current_price,"white","dash",f"현재가 ${current_price:,.2f}",0.97))
                vlines_w.append((cow_all,"#00e5a0","dot",f"Call OI Wall(저항) ${cow_all:,.0f}",0.82))
                vlines_w.append((pow_all,"#ff4d6d","dot",f"Put OI Wall(지지) ${pow_all:,.0f}", 0.67))
                add_vlines(f3, vlines_w)
                f3.update_layout(barmode='relative',template='plotly_dark',height=420,hovermode="x unified")
                st.plotly_chart(f3, use_container_width=True)

            iv_call_t = [df_terms.loc[t,'IV(Call) %'] for t in TERMS]
            iv_put_t  = [df_terms.loc[t,'IV(Put) %']  for t in TERMS]
            iv_skew_t = [df_terms.loc[t,'IV Skew']    for t in TERMS]
            if any(v>0 for v in iv_call_t):
                st.markdown("#### 📉 IV Term Structure (Volume 가중평균) — 극단값 Trim 적용됨")
                f4 = go.Figure()
                f4.add_trace(go.Scatter(x=TERMS,y=iv_call_t,mode='lines+markers+text',name='Call IV(Vol가중%)',text=[f"{v:.1f}%" for v in iv_call_t],textposition="top center",line=dict(color='#00e5a0',width=3),marker=dict(size=10)))
                f4.add_trace(go.Scatter(x=TERMS,y=iv_put_t,mode='lines+markers+text',name='Put IV(Vol가중%)',text=[f"{v:.1f}%" for v in iv_put_t],textposition="bottom center",line=dict(color='#ff4d6d',width=3,dash='dot'),marker=dict(size=10)))
                f4.add_trace(go.Scatter(x=TERMS,y=iv_skew_t,mode='lines+markers+text',name='IV Skew(Put-Call)',text=[f"{v:+.1f}%p" for v in iv_skew_t],textposition="top center",line=dict(color='#f5a623',width=2,dash='dash'),marker=dict(size=8)))
                f4.add_hline(y=0,line_dash="solid",line_color="#475569",line_width=1)
                f4.update_layout(title="Volume 가중평균 IV — Skew > 0: 풋 공포, Skew < 0: 콜 탐욕",template='plotly_dark',height=360)
                st.plotly_chart(f4, use_container_width=True)

            if not df_pcr_sc.empty:
                st.markdown("#### 🔵 만기별 PCR(Volume) 분포")
                color_map = {"Short":"#fb923c","Mid":"#a78bfa","Long":"#60a5fa"}
                f5 = go.Figure()
                for tk2,clr in color_map.items():
                    sub=df_pcr_sc[df_pcr_sc['term']==tk2]
                    if sub.empty: continue
                    f5.add_trace(go.Scatter(x=sub['days'],y=sub['pcr_vol'],mode='markers',name=tk2,marker=dict(color=clr,size=8,opacity=0.8),text=sub['exp_date'],hovertemplate="만기: %{text}<br>잔존일: %{x}일<br>PCR: %{y:.2f}<extra></extra>"))
                f5.add_hline(y=bear_th,line_dash="dash",line_color="#ff4d6d",annotation_text=f"Bearish({bear_th})")
                f5.add_hline(y=bull_th,line_dash="dash",line_color="#00e5a0",annotation_text=f"Bullish({bull_th})")
                f5.update_layout(xaxis_title="만기까지 잔존일수",yaxis_title="PCR(Volume)",template='plotly_dark',height=360)
                st.plotly_chart(f5, use_container_width=True)

            st.markdown("#### 🎯 기간별 Max Pain (최근접 만기 기준)")
            mp_cols = st.columns(3)
            for idx2,t2 in enumerate(TERMS):
                mpv=mp_per_term[t2]; gap2=(mpv-current_price)/current_price*100 if current_price>0 else 0
                gc2="#ff4d6d" if gap2<-2 else ("#00e5a0" if gap2>2 else "#f5a623")
                with mp_cols[idx2]: st.markdown(mc(f"Max Pain [{t2.split(' ')[0]}]",f"${mpv:,.0f}" if mpv>0 else "N/A",gc2,f"({gap2:+.1f}%)" if mpv>0 else "",gc2), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("#### 📑 기간별 데이터 요약")
            disp = df_terms[['call_vol','put_vol','call_oi','put_oi','PCR (Volume)','PCR (OI)','IV(Call) %','IV(Put) %','IV Skew']].copy()
            disp.columns=['Call 거래량','Put 거래량','Call OI','Put OI','PCR(Vol)','PCR(OI)','IV Call(Vol가중%)','IV Put(Vol가중%)','IV Skew']
            for c2 in ['Call 거래량','Put 거래량','Call OI','Put OI']: disp[c2]=disp[c2].apply(lambda x: f"{int(x):,}")
            for c2 in ['PCR(Vol)','PCR(OI)']: disp[c2]=disp[c2].apply(lambda x: f"{x:.2f}")
            for c2 in ['IV Call(Vol가중%)','IV Put(Vol가중%)']: disp[c2]=disp[c2].apply(lambda x: f"{x:.1f}%")
            disp['IV Skew']=disp['IV Skew'].apply(lambda x: f"{x:+.1f}%p")
            st.dataframe(disp, use_container_width=True)

            st.markdown("#### 🔥 UOA — 전 만기 스마트 머니 탐지 (Mid-Price 추정)")
            if not df_uoa.empty:
                ud2 = df_uoa[['term','side','moneyness','strike','days','dollar_premium','volume','spread_pct','V_OI']].copy()
                ud2.columns=['기간','구분','Moneyness','행사가','잔존일','추정 프리미엄','거래량','스프레드','V/OI']
                ud2['V/OI'] = ud2['V/OI'].apply(lambda x: f"{x:.1f}x")
                ud2['스프레드'] = ud2['스프레드'].apply(lambda x: f"{x*100:.1f}%")
                ud2['추정 프리미엄'] = ud2['추정 프리미엄'].apply(fmt_premium)
                st.dataframe(ud2, use_container_width=True)
            else:
                st.info("조건을 충족하는 이상 징후 없음")

            st.markdown("### 🧠 Term Structure 이론 신호 분석")
            short=df_terms.loc[TERMS[0]]; mid=df_terms.loc[TERMS[1]]; long_=df_terms.loc[TERMS[2]]
            pcr_s=short['PCR (Volume)']; pcr_m=mid['PCR (Volume)']; pcr_l=long_['PCR (Volume)']
            poi_s=short['PCR (OI)'];    poi_l=long_['PCR (OI)']

            s0,m0 = pcr_label(tot_pcr, bear_th, bull_th)
            st.markdown(sig(s0,f"① 전체 PCR(Volume) [{type_label} 기준]",m0), unsafe_allow_html=True)

            for lbl2,pv_ in [("단기",pcr_s),("중기",pcr_m),("장기",pcr_l)]:
                s_,m_=pcr_label(pv_, bear_th, bull_th)
                st.markdown(sig(s_,f"② PCR [{lbl2}]",m_), unsafe_allow_html=True)

            div_sl = pcr_l - pcr_s
            if abs(div_sl)>0.3:
                dc3="signal-bull" if div_sl<0 else "signal-bear"
                dm3=(f"단기 PCR({pcr_s:.2f}) > 장기 PCR({pcr_l:.2f}) → <strong>단기 공포/장기 낙관</strong> · 단기 조정 후 반등" if div_sl<0 else f"단기 PCR({pcr_s:.2f}) < 장기 PCR({pcr_l:.2f}) → <strong>단기 탐욕/장기 경계</strong> · 상승 후 조정 리스크")
            else:
                dc3="signal-neut"; dm3=f"단기·장기 PCR 차이 {abs(div_sl):.2f} → 기간별 심리 유사"
            st.markdown(sig(dc3,"③ PCR 기간별 다이버전스 (단기↔장기)",dm3), unsafe_allow_html=True)

            for lbl3,pv_,poi_ in [("단기",pcr_s,poi_s),("장기",pcr_l,poi_l)]:
                dc4,dm4 = pcr_divergence(pv_, poi_)
                st.markdown(sig(dc4,f"④ PCR 내부 다이버전스 (비율) [{lbl3}]",dm4), unsafe_allow_html=True)

            for lbl5,row5 in [("단기",short),("중기",mid),("장기",long_)]:
                vc5,vm5=vol_oi_signal(row5['call_vol'],row5['put_vol'],row5['call_oi'],row5['put_oi'])
                st.markdown(sig(f"signal-{vc5}",f"⑤ Volume × OI [{lbl5}]",vm5), unsafe_allow_html=True)

            for t6 in TERMS:
                mpv6=mp_per_term[t6]
                if mpv6>0 and current_price>0:
                    gap6=(mpv6-current_price)/current_price*100
                    mc6="signal-bear" if gap6<-2 else ("signal-bull" if gap6>2 else "signal-neut")
                    mb6=(f"Max Pain ${mpv6:,.0f} → 현재가 대비 <strong>{gap6:.1f}%</strong> 아래 · 하락 수렴" if gap6<-2 else (f"Max Pain ${mpv6:,.0f} → 현재가 대비 <strong>{gap6:+.1f}%</strong> 위 · 상승 수렴" if gap6>2 else f"Max Pain ${mpv6:,.0f} ≈ 현재가 · 횡보 압력"))
                    st.markdown(sig(mc6,f"⑥ Max Pain [{t6.split(' ')[0]}]",mb6), unsafe_allow_html=True)

            if cow_all>0 and pow_all>0:
                wc7="signal-bear" if current_price>cow_all else ("signal-bull" if current_price<pow_all else "signal-neut")
                wb7=(f"Call OI Wall(저항) <strong>${cow_all:,.0f}</strong> · Put OI Wall(지지) <strong>${pow_all:,.0f}</strong>" +(" · 현재가 돌파 → 저항 약화" if current_price>cow_all else (" · 현재가 하회 → 하락 리스크" if current_price<pow_all else f" · 현재가 범위 내 등락")))
                st.markdown(sig(wc7,"⑦ OI Wall 지지/저항 (전 만기 합산)",wb7), unsafe_allow_html=True)

            for lbl8,t8 in [("단기",TERMS[0]),("중기",TERMS[1]),("장기",TERMS[2])]:
                iv_c8=df_terms.loc[t8,'IV(Call) %']; iv_p8=df_terms.loc[t8,'IV(Put) %']
                sk8  =df_terms.loc[t8,'IV Skew']
                if iv_c8>0:
                    i8c="signal-bear" if sk8>5 else ("signal-bull" if sk8<-3 else "signal-neut")
                    i8m=(f"Call {iv_c8:.1f}% / Put {iv_p8:.1f}% | Skew <strong>{sk8:+.1f}%p</strong> → 풋 공포" if sk8>5 else (f"Call {iv_c8:.1f}% / Put {iv_p8:.1f}% | Skew <strong>{sk8:+.1f}%p</strong> → 콜 탐욕" if sk8<-3 else f"Call {iv_c8:.1f}% / Put {iv_p8:.1f}% | Skew {sk8:+.1f}%p → 균형"))
                    st.markdown(sig(i8c,f"⑧ IV Skew [{lbl8}] (Volume 가중평균)",i8m), unsafe_allow_html=True)

            if not df_uoa.empty:
                uc=len(df_uoa[df_uoa['side']=='CALL']); up=len(df_uoa[df_uoa['side']=='PUT'])
                otm_c=len(df_uoa[(df_uoa['side']=='CALL')&(df_uoa['moneyness']=='OTM')])
                otm_p=len(df_uoa[(df_uoa['side']=='PUT') &(df_uoa['moneyness']=='OTM')])
                top_prem=df_uoa.iloc[0]['dollar_premium'] if not df_uoa.empty else 0
                u9="signal-bull" if uc>up else ("signal-bear" if up>uc else "signal-neut")
                um9=(f"CALL {uc}건(OTM {otm_c}) / PUT {up}건(OTM {otm_p}) · 최대 단건 {fmt_premium(top_prem)} · " +("OTM콜 우세 → 상승 확신" if otm_c>otm_p else ("OTM풋 우세 → 하락 확신" if otm_p>otm_c else "OTM 균형 → 변동성 이벤트 대기")))
                st.markdown(sig(u9,"⑨ UOA 스마트 머니 (Mid-Price 기반 추정)",um9), unsafe_allow_html=True)

            uoa_top=df_uoa[['term','side','moneyness','strike','dollar_premium']].head(10).to_string(index=False) if not df_uoa.empty else "없음"
            iv_str="\n".join([f"  {t.split(' ')[0]}: Call IV {df_terms.loc[t,'IV(Call) %']:.1f}% / Put IV {df_terms.loc[t,'IV(Put) %']:.1f}% / Skew {df_terms.loc[t,'IV Skew']:+.1f}%p" for t in TERMS])
            mp_str="\n".join([f"  {t.split(' ')[0]}: ${mp_per_term[t]:,.0f} ({(mp_per_term[t]-current_price)/current_price*100 if current_price>0 else 0:+.1f}%)" for t in TERMS])

            prompt = f"""
당신은 월스트리트 시니어 파생상품 애널리스트입니다.
'{name} ({ticker_input})'의 전 만기 옵션 데이터를 분석하여 단/중/장기 종합 시나리오를 제시하세요.
[종목유형] {type_label} | 현재가: ${current_price:,.2f}
[기간별 수급 편차 (PCR)] 단기({pcr_s:.2f}) / 중기({pcr_m:.2f}) / 장기({pcr_l:.2f})
[IV Vol 가중평균 + IV Skew]
{iv_str}
[Max Pain]
{mp_str}
[UOA — Mid-Price 기반 추정 자금 Top10]
{uoa_top}
지시사항: 향후 1개월/3개월 Bull/Bear/Neutral 시나리오와 핵심 가격 레벨을 도출하세요.
"""

    if ticker_input and expirations and ((analysis_mode == "단일 만기일 분석" and selected_expiry) or analysis_mode != "단일 만기일 분석"):
        st.divider()
        st.subheader("🤖 Gemini AI 옵션 시장 브리핑")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.markdown("#### 옵션 1. 스트림릿에서 바로 분석")
            if st.button("✨ API 자동 분석 실행", type="primary", use_container_width=True):
                if has_api_key:
                    with st.spinner("AI가 데이터를 입체적으로 분석하고 있습니다..."):
                        try:
                            result, used_model = generate_with_fallback(prompt, api_key)
                            st.success(f"분석 완료! (모델: {used_model})")
                            st.markdown(f'<div class="report-box">{result}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"분석 오류: {e}")
                else:
                    st.error("API 키가 설정되지 않았습니다.")
        with col_btn2:
            st.markdown("#### 옵션 2. 무료 한도 초과 시 대안")
            safe_prompt = json.dumps(prompt)
            components.html(f"""
            <button onclick="copyAndOpen()" style="background-color:#f5a623;color:#000;padding:12px 20px; border:none;border-radius:8px;font-weight:bold;font-size:15px;cursor:pointer;width:100%;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                📋 프롬프트 복사 & Gemini 웹 열기
            </button>
            <script>
            function copyAndOpen() {{
                const text = {safe_prompt};
                navigator.clipboard.writeText(text).then(function() {{ window.open("https://gemini.google.com/", "_blank");
                }}).catch(function() {{ const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); window.open("https://gemini.google.com/", "_blank"); }});
            }}
            </script>
            """, height=60)
        with st.expander("생성된 고도화 분석 프롬프트 확인하기", expanded=False):
            st.code(prompt, language="text")

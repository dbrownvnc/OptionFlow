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

# ──────────────────────────────────────────────────────────────
# 1. 페이지 설정 & 글로벌 스타일
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")

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
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (단/중/장기 통합 지원)</p>', unsafe_allow_html=True)

tab_analysis, tab_help = st.tabs(["📊 분석", "📖 도움말"])

# ══════════════════════════════════════════════════════════════
# 도움말 탭
# ══════════════════════════════════════════════════════════════
with tab_help:
    st.markdown("## 📖 옵션 데이터 활용 가이드")
    st.markdown("옵션 거래량·미결제약정으로 **스마트 머니**의 방향을 읽는 4가지 핵심 이론입니다.")
    st.markdown("---")

    st.markdown("""
    <div class="hcard pcr">
      <div class="htitle">📊 &nbsp;1. 풋/콜 비율 (Put/Call Ratio, PCR)
        <span class="hbadge badge-pcr">역발상 지표</span></div>
      <div class="hbody">
        풋옵션(하락 베팅) 거래량 ÷ 콜옵션(상승 베팅) 거래량으로 산출합니다.<br><br>
        <strong>▸ PCR ≥ 1.2</strong> — 공포 쏠림 → <span class="htag">과매도 경계</span> 역발상 단기 반등 가능<br>
        <strong>▸ PCR &lt; 0.7</strong> — 탐욕 쏠림 → <span class="htag">과매수 경계</span> 조정·하락 리스크<br>
        <strong>▸ 0.7 ~ 1.2</strong> — 중립, 추가 지표 병행 필요<br><br>
        <strong>▸ PCR(Volume) vs PCR(OI) 내부 다이버전스:</strong><br>
        &nbsp;&nbsp;PCR(Vol) ≫ PCR(OI) → 오늘 갑자기 풋 매수 폭발 = 단기 공포 이벤트 가능성<br>
        &nbsp;&nbsp;PCR(OI) ≫ PCR(Vol) → 누적 풋 포지션 과잉 = 역발상 반등 에너지 축적 중<br><br>
        ⚡ 이 앱에서는 단기/중기/장기 기간별 PCR 신호와 내부 다이버전스를 모두 표시합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard uoa">
      <div class="htitle">🔥 &nbsp;2. 비정상적 옵션 거래량 (Unusual Options Activity, UOA)
        <span class="hbadge badge-uoa">스마트 머니 감지</span></div>
      <div class="hbody">
        <strong>V/OI 비율(거래량 ÷ 미결제약정) ≥ 5</strong>인 행사가를 자동 탐지합니다.<br><br>
        <strong>▸ OTM 콜 대량 유입</strong> → 단기 급등 확신 신호 (투기적 베팅)<br>
        <strong>▸ OTM 풋 대량 유입</strong> → 단기 급락 예측 또는 현물 포지션 헤징<br>
        <strong>▸ ATM 옵션 대량 유입</strong> → 방향성보다 변동성(이벤트) 베팅 가능성<br><br>
        ⚡ 이 앱에서는 <strong>전 만기 UOA를 통합 탐지</strong>하여 기간·행사가·방향별로 표시합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard voi">
      <div class="htitle">🔁 &nbsp;3. 거래량 × 미결제약정 교차 분석
        <span class="hbadge badge-voi">추세 신뢰도</span></div>
      <div class="hbody">
        <table style="width:100%;border-collapse:collapse;margin-top:4px;">
          <tr style="border-bottom:1px solid #334155;">
            <th style="text-align:left;padding:8px 12px;color:#64748b;font-size:12px;">거래량</th>
            <th style="text-align:left;padding:8px 12px;color:#64748b;font-size:12px;">미결제약정</th>
            <th style="text-align:left;padding:8px 12px;color:#64748b;font-size:12px;">해석</th>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px;color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px;color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px;color:#e2e8f0;">신규 자금 유입 → <strong>추세 강하게 지속</strong></td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px;color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px;color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px;color:#e2e8f0;">기존 포지션 청산 → <strong>추세 반전 경계</strong></td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px;color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px;color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px;color:#e2e8f0;">조용한 포지션 축적 → <strong>대기 매수 중</strong></td>
          </tr>
          <tr>
            <td style="padding:8px 12px;color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px;color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px;color:#e2e8f0;">추세 에너지 방전 → <strong>전환 임박</strong></td>
          </tr>
        </table><br>
        ⚡ 단기/중기/장기 <strong>각 기간별 V×OI 신호</strong>를 독립적으로 표시합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard mp">
      <div class="htitle">🎯 &nbsp;4. 맥스 페인 (Max Pain) & OI Wall
        <span class="hbadge badge-mp">만기일 자석 + 지지/저항</span></div>
      <div class="hbody">
        <strong>▸ Max Pain:</strong> 옵션 매수자의 손실이 최대화되는 행사가.
        만기일이 가까울수록 주가가 이 가격으로 수렴하는 경향.<br>
        &nbsp;&nbsp;<span class="htag">현재가 &gt; Max Pain</span> 하락 수렴 압력 ·
        <span class="htag">현재가 &lt; Max Pain</span> 상승 수렴 압력<br><br>
        <strong>▸ OI Wall (옵션 벽):</strong> 특정 행사가에 OI가 집중되면
        마켓 메이커의 델타 헤징으로 인해 해당 가격대가 <strong>지지·저항선</strong>으로 기능합니다.<br>
        &nbsp;&nbsp;최대 Call OI 행사가 → <strong>Gamma Wall (저항선)</strong><br>
        &nbsp;&nbsp;최대 Put OI 행사가  → <strong>Put Wall (지지선)</strong><br><br>
        ⚡ 전체기간 분석에서 <strong>전 만기 OI를 행사가별로 합산</strong>한 OI Wall 차트와
        기간별 Max Pain을 모두 제공합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard warn">
      <div class="htitle">⚠️ &nbsp;주의사항 — 헤징 vs 투기
        <span class="hbadge badge-warn">필독</span></div>
      <div class="hbody">
        <strong>풋옵션 매수 ≠ 무조건 하락 배팅.</strong>
        기관은 현물 보유분을 방어하기 위해 풋옵션을 대량 헤징 매수하기도 합니다.<br><br>
        옵션 데이터는 <strong>주가 차트 + 수급 + 거시 경제 상황</strong>과 조합했을 때
        신뢰도가 크게 높아집니다. 이 앱의 분석 결과는 <strong>투자 참고용</strong>입니다.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 분석 탭
# ══════════════════════════════════════════════════════════════
with tab_analysis:

    # ── 공통 유틸 ──────────────────────────────────────────────

    def generate_with_fallback(prompt, api_key):
        genai.configure(api_key=api_key)
        models = ["gemini-2.0-flash-lite-preview-02-05","gemini-1.5-pro",
                  "gemini-1.5-flash","gemini-1.5-flash-8b","gemini-flash-latest"]
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
            c_pain = ((s - calls.loc[calls['strike'] < s, 'strike'])
                      * calls.loc[calls['strike'] < s, 'openInterest']).sum()
            p_pain = ((puts.loc[puts['strike'] > s, 'strike'] - s)
                      * puts.loc[puts['strike'] > s, 'openInterest']).sum()
            pain[s] = c_pain + p_pain
        return min(pain, key=pain.get) if pain else 0.0

    def detect_uoa(df: pd.DataFrame, side: str, threshold: float = 5.0) -> pd.DataFrame:
        d = df[['strike','volume','openInterest','lastPrice']].copy()
        d['V_OI'] = d['volume'] / d['openInterest'].replace(0, np.nan)
        d = d[d['V_OI'] >= threshold].copy()
        d['side'] = side
        return d.sort_values('V_OI', ascending=False).head(5)

    def vol_oi_signal(cv, pv, coi, poi):
        if coi > poi and cv > pv:
            return "bull", "📈 신규 콜 포지션 유입 우세 → 상승 추세 강하게 지속 가능"
        elif poi > coi and pv > cv:
            return "bear", "📉 신규 풋 포지션 유입 우세 → 하락 추세 지속 / 헤징 증가"
        elif coi > poi and pv > cv:
            return "neut", "🔄 콜 OI 우세 but 풋 거래 활발 → 단기 조정 후 반등 패턴"
        else:
            return "neut", "⚖️ 콜·풋 수급 혼재 → 방향성 불분명, 추가 지표 필요"

    def pcr_label(v):
        if v > 1.2:   return "signal-bull", f"PCR {v:.2f} — 풋 과쏠림(공포) · 역발상 반등 가능"
        elif v < 0.7: return "signal-bear", f"PCR {v:.2f} — 콜 과쏠림(탐욕) · 조정 경계"
        else:         return "signal-neut", f"PCR {v:.2f} — 중립 구간"

    def sig(css, label, body):
        return f'<div class="signal-box {css}"><strong>{label}</strong> &nbsp;·&nbsp; {body}</div>'

    def mc(label, value, color, sub="", sub_color="#9ca3af"):
        return (f'<div class="mcard"><div class="mcard-label">{label}</div>'
                f'<div style="display:flex;align-items:baseline;">'
                f'<span class="mcard-value" style="color:{color};">{value}</span>'
                f'<span class="mcard-sub" style="color:{sub_color};">{sub}</span>'
                f'</div></div>')

    api_key     = st.secrets.get("GEMINI_API_KEY")
    has_api_key = api_key is not None
    if not has_api_key:
        st.sidebar.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다.")

    with st.sidebar:
        st.header("🔍 검색 설정")
        ticker_input  = st.text_input("티커 심볼 (예: AAPL, NVDA, SPY)", value="AAPL").upper()
        analysis_mode = st.radio("분석 모드 선택",
                                 ["단일 만기일 분석", "전체 기간 통합 분석 (단/중/장기)"])
        ticker        = yf.Ticker(ticker_input)
        expirations   = []
        try:
            expirations = ticker.options
            if not expirations: st.error("옵션 데이터를 찾을 수 없는 티커입니다.")
        except:
            st.error("데이터 서버 연결에 문제가 발생했습니다.")

        selected_expiry = None
        if expirations and analysis_mode == "단일 만기일 분석":
            selected_expiry = st.selectbox("만기일 선택", expirations)

    current_price = 0; name = ticker_input
    if ticker_input and expirations:
        try:
            info          = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            if not current_price:
                current_price = ticker.history(period="1d")['Close'].iloc[-1]
            name = info.get('longName', ticker_input)
        except: pass
        st.subheader(f"📊 {name} ({ticker_input}) | 현재가: ${current_price:,.2f}")

    # ══════════════════════════════════════════════════════════
    # 모드 1: 단일 만기일 분석
    # ══════════════════════════════════════════════════════════
    if analysis_mode == "단일 만기일 분석" and selected_expiry:
        with st.spinner(f"'{selected_expiry}' 만기 옵션 체인 분석 중..."):
            opt   = ticker.option_chain(selected_expiry)
            calls, puts = opt.calls, opt.puts
            lo, hi = (current_price*0.7, current_price*1.3) if current_price > 0 else (0, 1e9)
            cc = calls[(calls['strike']>=lo)&(calls['strike']<=hi)]
            pc = puts [(puts ['strike']>=lo)&(puts ['strike']<=hi)]

            cv = calls['volume'].sum(); pv = puts['volume'].sum()
            coi= calls['openInterest'].sum(); poi= puts['openInterest'].sum()
            pcr= pv/cv if cv>0 else 0; pcr_oi= poi/coi if coi>0 else 0
            mp = calculate_max_pain(calls, puts)
            mp_gap = (current_price-mp)/mp*100 if mp>0 else 0

            pcr_color = "#ff4d6d" if pcr>1.2 else ("#00e5a0" if pcr<0.7 else "#f5a623")
            pcr_sub   = "Bearish ▼" if pcr>1.2 else ("Bullish ▲" if pcr<0.7 else "Neutral")
            mp_gap_color = "#ff4d6d" if mp_gap>2 else ("#00e5a0" if mp_gap<-2 else "#9ca3af")

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(mc("CALL 거래량",f"{int(cv):,}","#00e5a0"), unsafe_allow_html=True)
            with c2: st.markdown(mc("PUT 거래량", f"{int(pv):,}","#ff4d6d"), unsafe_allow_html=True)
            with c3: st.markdown(mc("PCR (Volume)",f"{pcr:.2f}","#f3f4f6",pcr_sub,pcr_color), unsafe_allow_html=True)
            with c4: st.markdown(mc("Max Pain",f"${mp:,.0f}","#fb923c",f"({mp_gap:+.1f}%)",mp_gap_color), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=cc['strike'],y=cc['volume'],  name='Calls',marker_color='#00e5a0'))
            fig.add_trace(go.Bar(x=pc['strike'],y=-pc['volume'], name='Puts', marker_color='#ff4d6d'))
            if current_price>0: fig.add_vline(x=current_price,line_dash="dash",line_color="white",
                annotation_text=f"현재가 ${current_price:,.2f}",annotation_position="top right")
            if mp>0: fig.add_vline(x=mp,line_dash="dot",line_color="#fb923c",
                annotation_text=f"Max Pain ${mp:,.0f}",annotation_position="top left")
            fig.update_layout(title=f"행사가별 거래량 (만기: {selected_expiry})",
                barmode='relative',template="plotly_dark",height=400,hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=cc['strike'],y=cc['openInterest'],  name='Call OI',marker_color='rgba(0,229,160,0.65)'))
            fig_oi.add_trace(go.Bar(x=pc['strike'],y=-pc['openInterest'], name='Put OI', marker_color='rgba(255,77,109,0.65)'))
            if current_price>0: fig_oi.add_vline(x=current_price,line_dash="dash",line_color="white")
            if mp>0: fig_oi.add_vline(x=mp,line_dash="dot",line_color="#fb923c",
                annotation_text=f"Max Pain ${mp:,.0f}",annotation_position="top left")
            fig_oi.update_layout(title="행사가별 미결제약정 — OI Wall (지지·저항 지도)",
                barmode='relative',template="plotly_dark",height=380,hovermode="x unified")
            st.plotly_chart(fig_oi, use_container_width=True)

            st.markdown("### 🧠 옵션 이론 신호 분석")
            s,m = pcr_label(pcr)
            st.markdown(sig(s,"① PCR(Volume) 역발상 신호",m), unsafe_allow_html=True)
            s2,m2 = pcr_label(pcr_oi)
            st.markdown(sig(s2,"② PCR(OI) 누적 포지션 신호",m2), unsafe_allow_html=True)

            dv = pcr - pcr_oi
            if abs(dv)>0.3:
                dc = "signal-bear" if dv>0 else "signal-bull"
                dm = (f"PCR(Vol) {pcr:.2f} ≫ PCR(OI) {pcr_oi:.2f} → <strong>오늘 급격한 풋 유입</strong>, 단기 공포 이벤트 주의"
                      if dv>0 else
                      f"PCR(Vol) {pcr:.2f} ≪ PCR(OI) {pcr_oi:.2f} → <strong>누적 풋 과잉 vs 오늘 콜 우세</strong>, 역발상 반등 에너지")
            else:
                dc,dm = "signal-neut", f"PCR(Vol) {pcr:.2f} ≈ PCR(OI) {pcr_oi:.2f} → 당일 흐름과 누적 포지션 방향 일치"
            st.markdown(sig(dc,"③ PCR 내부 다이버전스",dm), unsafe_allow_html=True)

            if mp>0:
                mc_ = "signal-bear" if mp_gap>2 else ("signal-bull" if mp_gap<-2 else "signal-neut")
                mb  = (f"현재가 ${current_price:,.2f}가 Max Pain ${mp:,.0f}보다 <strong>{abs(mp_gap):.1f}% 위</strong> → 만기일 하락 수렴 압력"
                       if mp_gap>2 else
                       (f"현재가 ${current_price:,.2f}가 Max Pain ${mp:,.0f}보다 <strong>{abs(mp_gap):.1f}% 아래</strong> → 만기일 상승 수렴 압력"
                        if mp_gap<-2 else
                        f"현재가 ${current_price:,.2f} ≈ Max Pain ${mp:,.0f} → 만기일 횡보 압력 우세"))
                st.markdown(sig(mc_,"④ Max Pain 수렴 신호",mb), unsafe_allow_html=True)

            vc,vm = vol_oi_signal(cv,pv,coi,poi)
            st.markdown(sig(f"signal-{vc}","⑤ Volume × OI 교차 신호",vm), unsafe_allow_html=True)

            if not cc.empty and not pc.empty:
                gw = cc.loc[cc['openInterest'].idxmax(),'strike']
                pw = pc.loc[pc['openInterest'].idxmax(),'strike']
                wc = "signal-bear" if current_price>gw else ("signal-bull" if current_price<pw else "signal-neut")
                wb = (f"Gamma Wall(저항): <strong>${gw:,.0f}</strong> &nbsp;·&nbsp; Put Wall(지지): <strong>${pw:,.0f}</strong>"
                      + (" &nbsp;·&nbsp; 현재가가 Gamma Wall 돌파 → 상방 저항 없음 주의" if current_price>gw
                         else (" &nbsp;·&nbsp; 현재가가 Put Wall 하회 → 추가 하락 리스크" if current_price<pw
                               else f" &nbsp;·&nbsp; 현재가 ${current_price:,.2f}는 두 Wall 사이 → 지지·저항 범위 내 등락")))
                st.markdown(sig(wc,"⑥ OI Wall 지지/저항선",wb), unsafe_allow_html=True)

            uoa_all = pd.concat([detect_uoa(cc,"CALL"), detect_uoa(pc,"PUT")]).sort_values('V_OI',ascending=False)
            if not uoa_all.empty:
                st.markdown(sig("signal-neut","⑦ UOA 비정상 거래량 경보",
                    f"V/OI ≥ 5 행사가 <strong>{len(uoa_all)}건</strong> 감지 · 스마트 머니 선제 포지션 가능성 ↑"), unsafe_allow_html=True)
                ud = uoa_all.rename(columns={'side':'구분','strike':'행사가','volume':'거래량',
                    'openInterest':'OI','V_OI':'V/OI','lastPrice':'최근가'})
                ud['V/OI'] = ud['V/OI'].apply(lambda x: f"{x:.1f}x")
                st.dataframe(ud, use_container_width=True)
            else:
                st.markdown(sig("signal-neut","⑦ UOA 경보","V/OI ≥ 5 행사가 없음 — 스마트 머니 특이 동향 미감지"), unsafe_allow_html=True)

            gw_v = cc.loc[cc['openInterest'].idxmax(),'strike'] if not cc.empty else 0
            pw_v = pc.loc[pc['openInterest'].idxmax(),'strike'] if not pc.empty else 0
            prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 기반으로 시장 심리를 분석하세요.

[분석 대상]
- 티커: {ticker_input} ({name}) / 만기일: {selected_expiry} / 현재가: ${current_price:,.2f}

[수급 데이터]
- 콜 거래량: {cv:,.0f} / 콜 OI: {coi:,.0f}
- 풋 거래량: {pv:,.0f} / 풋 OI: {poi:,.0f}
- PCR(Volume): {pcr:.2f} / PCR(OI): {pcr_oi:.2f}
- PCR 내부 다이버전스: {pcr-pcr_oi:+.2f}

[Max Pain & OI Wall]
- Max Pain 가격: ${mp:,.2f} (현재가 대비 {mp_gap:+.1f}%)
- Gamma Wall(저항): ${gw_v:,.0f}
- Put Wall(지지): ${pw_v:,.0f}

[UOA]
- V/OI ≥ 5 감지 건수: {len(uoa_all)}건
{uoa_all[['side','strike','V_OI']].to_string(index=False) if not uoa_all.empty else '없음'}

[분석 지시사항]
1. PCR(Vol)과 PCR(OI) 내부 다이버전스가 의미하는 바를 해석하세요.
2. Max Pain 수렴 압력과 만기일 시나리오를 제시하세요.
3. Gamma Wall(저항)과 Put Wall(지지) 사이에서의 주가 움직임 시나리오를 설명하세요.
4. UOA 행사가가 있다면 스마트 머니의 의도를 추론하세요.
5. 종합 단기 주가 방향과 핵심 가격 레벨을 도출하세요.
친절한 한글 마크다운으로 정리하세요.
"""

    # ══════════════════════════════════════════════════════════
    # 모드 2: 전체 기간 통합 분석
    # ══════════════════════════════════════════════════════════
    elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:
        st.info("💡 **단기(≤30일) / 중기(30~90일) / 장기(≥90일)** 전 만기 데이터 수집 — PCR · UOA · OI Wall · Max Pain · IV 포함")

        with st.spinner("전체 만기일 데이터 수집 중... (10~30초 소요)"):
            today = datetime.today()
            TERMS = ["Short (단기/30일내)", "Mid (중기/30~90일)", "Long (장기/90일이상)"]

            term_data = {t: dict(call_vol=0,put_vol=0,call_oi=0,put_oi=0,
                                 iv_sum_c=0.0,iv_cnt_c=0,iv_sum_p=0.0,iv_cnt_p=0,
                                 nearest_days=9999,nearest_exp=None,exp_count=0)
                         for t in TERMS}

            strike_oi  = {}   # {strike: [call_oi, put_oi]}
            uoa_records = []
            expiry_pcr  = []

            progress_bar = st.progress(0)
            total_exps   = len(expirations)

            for i, exp_date in enumerate(expirations):
                try:
                    days = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                    cat  = TERMS[0] if days<=30 else TERMS[1] if days<=90 else TERMS[2]
                    td   = term_data[cat]; td['exp_count'] += 1

                    opt   = ticker.option_chain(exp_date)
                    c, p  = opt.calls.copy(), opt.puts.copy()

                    cv  = c['volume'].sum()        if 'volume'       in c else 0
                    pv  = p['volume'].sum()         if 'volume'       in p else 0
                    coi = c['openInterest'].sum()   if 'openInterest' in c else 0
                    poi = p['openInterest'].sum()   if 'openInterest' in p else 0
                    td['call_vol']+=cv; td['put_vol']+=pv
                    td['call_oi'] +=coi; td['put_oi'] +=poi

                    if 'impliedVolatility' in c:
                        vc_ = c['impliedVolatility'].replace(0,np.nan).dropna()
                        td['iv_sum_c']+=vc_.sum(); td['iv_cnt_c']+=len(vc_)
                    if 'impliedVolatility' in p:
                        vp_ = p['impliedVolatility'].replace(0,np.nan).dropna()
                        td['iv_sum_p']+=vp_.sum(); td['iv_cnt_p']+=len(vp_)

                    if days>=0 and days<td['nearest_days']:
                        td['nearest_days']=days; td['nearest_exp']=exp_date

                    lo2,hi2 = current_price*0.7, current_price*1.3
                    c_w = c[(c['strike']>=lo2)&(c['strike']<=hi2)] if current_price>0 else c
                    p_w = p[(p['strike']>=lo2)&(p['strike']<=hi2)] if current_price>0 else p

                    for _, row in c_w.iterrows():
                        s=row['strike']; strike_oi.setdefault(s,[0,0]); strike_oi[s][0]+=row.get('openInterest',0)
                    for _, row in p_w.iterrows():
                        s=row['strike']; strike_oi.setdefault(s,[0,0]); strike_oi[s][1]+=row.get('openInterest',0)

                    for side2, df_s in [("CALL",c_w),("PUT",p_w)]:
                        df_s2 = df_s.copy()
                        df_s2['V_OI'] = df_s2['volume']/df_s2['openInterest'].replace(0,np.nan)
                        for _, row in df_s2[df_s2['V_OI']>=5].nlargest(2,'V_OI').iterrows():
                            uoa_records.append({'exp_date':exp_date,'term':cat.split(' ')[0],
                                'side':side2,'strike':row['strike'],'volume':row.get('volume',0),
                                'openInterest':row.get('openInterest',0),'V_OI':row['V_OI'],
                                'lastPrice':row.get('lastPrice',0),'days':days})

                    expiry_pcr.append({'exp_date':exp_date,'days':days,'term':cat.split(' ')[0],
                        'pcr_vol':pv/cv if cv>0 else np.nan,
                        'pcr_oi': poi/coi if coi>0 else np.nan,
                        'call_vol':cv,'put_vol':pv})
                except: pass
                progress_bar.progress((i+1)/total_exps)
            progress_bar.empty()

            # 후처리
            df_terms = pd.DataFrame(term_data).T
            df_terms['PCR (Volume)'] = df_terms['put_vol']/df_terms['call_vol']
            df_terms['PCR (OI)']     = df_terms['put_oi'] /df_terms['call_oi']
            df_terms['IV(Call) %']   = (df_terms['iv_sum_c']/df_terms['iv_cnt_c'].replace(0,np.nan)*100).fillna(0)
            df_terms['IV(Put) %']    = (df_terms['iv_sum_p']/df_terms['iv_cnt_p'].replace(0,np.nan)*100).fillna(0)
            df_terms.fillna(0, inplace=True)

            mp_per_term = {}
            for t in TERMS:
                ne = term_data[t]['nearest_exp']
                if ne:
                    try:
                        o2 = ticker.option_chain(ne); mp_per_term[t] = calculate_max_pain(o2.calls, o2.puts)
                    except: mp_per_term[t] = 0
                else: mp_per_term[t] = 0

            df_wall = pd.DataFrame([(s,v[0],v[1]) for s,v in sorted(strike_oi.items())],
                                   columns=['strike','call_oi','put_oi'])
            gw_all = df_wall.loc[df_wall['call_oi'].idxmax(),'strike'] if not df_wall.empty else 0
            pw_all = df_wall.loc[df_wall['put_oi'].idxmax(), 'strike'] if not df_wall.empty else 0

            df_uoa = (pd.DataFrame(uoa_records).sort_values('V_OI',ascending=False)
                      .drop_duplicates(subset=['side','strike']).head(15)
                      if uoa_records else pd.DataFrame())

            df_pcr_sc = pd.DataFrame(expiry_pcr).dropna(subset=['pcr_vol'])

            total_cv  = df_terms['call_vol'].sum(); total_pv = df_terms['put_vol'].sum()
            total_coi = df_terms['call_oi'].sum();  total_poi= df_terms['put_oi'].sum()
            tot_pcr   = total_pv/total_cv   if total_cv>0  else 0
            tot_pcr_oi= total_poi/total_coi if total_coi>0 else 0

            pc_color = "#ff4d6d" if tot_pcr>1.2 else ("#00e5a0" if tot_pcr<0.7 else "#f5a623")
            pc_sub   = "Bearish ▼" if tot_pcr>1.2 else ("Bullish ▲" if tot_pcr<0.7 else "Neutral")

            # 메트릭 5개
            m1,m2,m3,m4,m5 = st.columns(5)
            with m1: st.markdown(mc("전체 CALL 거래량",f"{int(total_cv):,}","#00e5a0"), unsafe_allow_html=True)
            with m2: st.markdown(mc("전체 PUT 거래량", f"{int(total_pv):,}","#ff4d6d"), unsafe_allow_html=True)
            with m3: st.markdown(mc("전체 PCR(Volume)",f"{tot_pcr:.2f}","#f3f4f6",pc_sub,pc_color), unsafe_allow_html=True)
            with m4: st.markdown(mc("전체 PCR(OI)",    f"{tot_pcr_oi:.2f}","#a78bfa"), unsafe_allow_html=True)
            with m5: st.markdown(mc("Gamma Wall",f"${gw_all:,.0f}","#fb923c",f"Put Wall ${pw_all:,.0f}","#ff4d6d"), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # ── 차트 1: 기간별 거래량 ──
            st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
            f1 = go.Figure()
            f1.add_trace(go.Bar(x=df_terms.index,y=df_terms['call_vol'],name='CALL 거래량',marker_color='#00e5a0'))
            f1.add_trace(go.Bar(x=df_terms.index,y=df_terms['put_vol'], name='PUT 거래량', marker_color='#ff4d6d'))
            f1.update_layout(barmode='group',template='plotly_dark',height=360,hovermode="x unified")
            st.plotly_chart(f1, use_container_width=True)

            # ── 차트 2: PCR Term Structure ──
            f2 = go.Figure()
            f2.add_trace(go.Scatter(x=df_terms.index,y=df_terms['PCR (Volume)'],
                mode='lines+markers+text',name='PCR(Volume)',
                text=[f"{v:.2f}" for v in df_terms['PCR (Volume)']],textposition="top center",
                line=dict(color='#f5a623',width=3),marker=dict(size=10)))
            f2.add_trace(go.Scatter(x=df_terms.index,y=df_terms['PCR (OI)'],
                mode='lines+markers+text',name='PCR(OI)',
                text=[f"{v:.2f}" for v in df_terms['PCR (OI)']],textposition="bottom center",
                line=dict(color='#a78bfa',width=3,dash='dot'),marker=dict(size=10)))
            f2.add_hline(y=1.2,line_dash="dash",line_color="#ff4d6d",annotation_text="Bearish(1.2)")
            f2.add_hline(y=0.7,line_dash="dash",line_color="#00e5a0",annotation_text="Bullish(0.7)")
            f2.update_layout(title="기간별 PCR — PCR(Volume) vs PCR(OI) 내부 다이버전스",
                template='plotly_dark',height=380)
            st.plotly_chart(f2, use_container_width=True)

            # ── 차트 3: OI Wall ──
            if not df_wall.empty:
                st.markdown("#### 🏰 OI Wall — 전 만기 행사가별 OI 집중도 (지지·저항 지도)")
                f3 = go.Figure()
                f3.add_trace(go.Bar(x=df_wall['strike'],y=df_wall['call_oi'],
                    name='Call OI 합산',marker_color='rgba(0,229,160,0.7)'))
                f3.add_trace(go.Bar(x=df_wall['strike'],y=-df_wall['put_oi'],
                    name='Put OI 합산', marker_color='rgba(255,77,109,0.7)'))
                if current_price>0:
                    f3.add_vline(x=current_price,line_dash="dash",line_color="white",
                        annotation_text=f"현재가 ${current_price:,.2f}",annotation_position="top right")
                f3.add_vline(x=gw_all,line_dash="dot",line_color="#00e5a0",
                    annotation_text=f"Gamma Wall(저항) ${gw_all:,.0f}",annotation_position="top left")
                f3.add_vline(x=pw_all,line_dash="dot",line_color="#ff4d6d",
                    annotation_text=f"Put Wall(지지) ${pw_all:,.0f}",annotation_position="top right")
                f3.update_layout(barmode='relative',template='plotly_dark',height=420,hovermode="x unified")
                st.plotly_chart(f3, use_container_width=True)

            # ── 차트 4: IV Term Structure ──
            iv_call = [df_terms.loc[t,'IV(Call) %'] for t in TERMS]
            iv_put  = [df_terms.loc[t,'IV(Put) %']  for t in TERMS]
            if any(v>0 for v in iv_call):
                st.markdown("#### 📉 내재변동성(IV) Term Structure — 콜/풋 평균 IV")
                f4 = go.Figure()
                f4.add_trace(go.Scatter(x=TERMS,y=iv_call,mode='lines+markers+text',name='Call IV(%)',
                    text=[f"{v:.1f}%" for v in iv_call],textposition="top center",
                    line=dict(color='#00e5a0',width=3),marker=dict(size=10)))
                f4.add_trace(go.Scatter(x=TERMS,y=iv_put,mode='lines+markers+text',name='Put IV(%)',
                    text=[f"{v:.1f}%" for v in iv_put],textposition="bottom center",
                    line=dict(color='#ff4d6d',width=3,dash='dot'),marker=dict(size=10)))
                f4.update_layout(title="기간별 평균 IV — 단기 IV > 장기 IV → 이벤트 리스크 반영",
                    template='plotly_dark',height=340)
                st.plotly_chart(f4, use_container_width=True)

            # ── 차트 5: 만기별 PCR 산점도 ──
            if not df_pcr_sc.empty:
                st.markdown("#### 🔵 만기별 PCR(Volume) 분포 — 어느 만기가 가장 편향됐나?")
                color_map = {"Short":"#fb923c","Mid":"#a78bfa","Long":"#60a5fa"}
                f5 = go.Figure()
                for tk2, clr in color_map.items():
                    sub = df_pcr_sc[df_pcr_sc['term']==tk2]
                    if sub.empty: continue
                    f5.add_trace(go.Scatter(x=sub['days'],y=sub['pcr_vol'],mode='markers',name=tk2,
                        marker=dict(color=clr,size=8,opacity=0.8),text=sub['exp_date'],
                        hovertemplate="만기: %{text}<br>잔존일: %{x}일<br>PCR: %{y:.2f}<extra></extra>"))
                f5.add_hline(y=1.2,line_dash="dash",line_color="#ff4d6d",annotation_text="Bearish(1.2)")
                f5.add_hline(y=0.7,line_dash="dash",line_color="#00e5a0",annotation_text="Bullish(0.7)")
                f5.update_layout(xaxis_title="만기까지 잔존일수",yaxis_title="PCR(Volume)",
                    template='plotly_dark',height=360)
                st.plotly_chart(f5, use_container_width=True)

            # ── Max Pain 기간별 ──
            st.markdown("#### 🎯 기간별 Max Pain (최근접 만기 기준)")
            mp_cols = st.columns(3)
            for idx2, t2 in enumerate(TERMS):
                mpv = mp_per_term[t2]; gap2 = (current_price-mpv)/mpv*100 if mpv>0 else 0
                gc2 = "#ff4d6d" if gap2>2 else ("#00e5a0" if gap2<-2 else "#f5a623")
                with mp_cols[idx2]:
                    st.markdown(mc(f"Max Pain [{t2.split(' ')[0]}]",
                        f"${mpv:,.0f}" if mpv>0 else "N/A",gc2,
                        f"({gap2:+.1f}%)" if mpv>0 else "",gc2), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # ── 기간별 요약 테이블 ──
            st.markdown("#### 📑 기간별 데이터 요약")
            disp = df_terms[['call_vol','put_vol','call_oi','put_oi','PCR (Volume)','PCR (OI)','IV(Call) %','IV(Put) %']].copy()
            disp.columns=['Call 거래량','Put 거래량','Call OI','Put OI','PCR(Vol)','PCR(OI)','IV Call(%)','IV Put(%)']
            for c2 in ['Call 거래량','Put 거래량','Call OI','Put OI']:
                disp[c2] = disp[c2].apply(lambda x: f"{int(x):,}")
            for c2 in ['PCR(Vol)','PCR(OI)']:
                disp[c2] = disp[c2].apply(lambda x: f"{x:.2f}")
            for c2 in ['IV Call(%)','IV Put(%)']:
                disp[c2] = disp[c2].apply(lambda x: f"{x:.1f}%")
            st.dataframe(disp, use_container_width=True)

            # ── UOA 전 만기 ──
            st.markdown("#### 🔥 UOA — 전 만기 스마트 머니 탐지 Top 15")
            if not df_uoa.empty:
                ud2 = df_uoa[['term','side','strike','days','volume','openInterest','V_OI','lastPrice']].copy()
                ud2.columns=['기간','구분','행사가','잔존일','거래량','OI','V/OI','최근가']
                ud2['V/OI'] = ud2['V/OI'].apply(lambda x: f"{x:.1f}x")
                st.dataframe(ud2, use_container_width=True)
            else:
                st.info("V/OI ≥ 5 비정상 거래량 행사가 없음")

            # ── 이론 신호 패널 ──
            st.markdown("### 🧠 Term Structure 이론 신호 분석")

            short = df_terms.loc[TERMS[0]]; mid = df_terms.loc[TERMS[1]]; long_ = df_terms.loc[TERMS[2]]
            pcr_s=short['PCR (Volume)']; pcr_m=mid['PCR (Volume)']; pcr_l=long_['PCR (Volume)']
            poi_s=short['PCR (OI)']; poi_l=long_['PCR (OI)']

            # ① 전체 PCR
            s0,m0 = pcr_label(tot_pcr)
            st.markdown(sig(s0,"① 전체 PCR(Volume) 종합 신호",m0), unsafe_allow_html=True)

            # ② 기간별 PCR
            for lbl2, pv_ in [("단기",pcr_s),("중기",pcr_m),("장기",pcr_l)]:
                s_,m_ = pcr_label(pv_)
                st.markdown(sig(s_,f"② PCR [{lbl2}]",m_), unsafe_allow_html=True)

            # ③ 기간별 다이버전스 (단기 vs 장기)
            div_sl = pcr_l - pcr_s
            if abs(div_sl)>0.3:
                dc3 = "signal-bull" if div_sl<0 else "signal-bear"
                dm3 = (f"단기 PCR({pcr_s:.2f}) > 장기 PCR({pcr_l:.2f}) → <strong>단기 공포 / 장기 낙관</strong> · 단기 조정 후 중장기 반등 시나리오"
                       if div_sl<0 else
                       f"단기 PCR({pcr_s:.2f}) < 장기 PCR({pcr_l:.2f}) → <strong>단기 탐욕 / 장기 경계</strong> · 단기 상승 후 중장기 리스크 확대")
            else:
                dc3,dm3 = "signal-neut", f"단기·장기 PCR 차이 {abs(div_sl):.2f} → 기간별 심리 유사, 추세 일관성 있음"
            st.markdown(sig(dc3,"③ PCR 기간별 다이버전스 (단기↔장기)",dm3), unsafe_allow_html=True)

            # ④ 내부 다이버전스 (단기/장기)
            for lbl3, pv_, poi_ in [("단기",pcr_s,poi_s),("장기",pcr_l,poi_l)]:
                d4 = pv_-poi_
                if abs(d4)>0.3:
                    dc4 = "signal-bear" if d4>0 else "signal-bull"
                    dm4 = (f"PCR(Vol) {pv_:.2f} ≫ PCR(OI) {poi_:.2f} → 오늘 급격한 풋 유입, 단기 헤징/공포 이벤트"
                           if d4>0 else
                           f"PCR(Vol) {pv_:.2f} ≪ PCR(OI) {poi_:.2f} → 누적 풋 과잉 vs 오늘 콜 우세, 역발상 반등 에너지")
                else:
                    dc4 = "signal-neut"; dm4 = f"PCR(Vol) {pv_:.2f} ≈ PCR(OI) {poi_:.2f} → 당일 흐름과 누적 포지션 방향 일치"
                st.markdown(sig(dc4,f"④ PCR 내부 다이버전스 [{lbl3}]",dm4), unsafe_allow_html=True)

            # ⑤ Volume × OI 3개 기간
            for lbl5, row5 in [("단기",short),("중기",mid),("장기",long_)]:
                vc5,vm5 = vol_oi_signal(row5['call_vol'],row5['put_vol'],row5['call_oi'],row5['put_oi'])
                st.markdown(sig(f"signal-{vc5}",f"⑤ Volume × OI [{lbl5}]",vm5), unsafe_allow_html=True)

            # ⑥ Max Pain 기간별
            for t6 in TERMS:
                mpv6 = mp_per_term[t6]
                if mpv6>0 and current_price>0:
                    gap6 = (current_price-mpv6)/mpv6*100
                    mc6  = "signal-bear" if gap6>2 else ("signal-bull" if gap6<-2 else "signal-neut")
                    mb6  = (f"현재가 ${current_price:,.2f}가 Max Pain ${mpv6:,.0f}보다 <strong>{abs(gap6):.1f}% 위</strong> → 하락 수렴 압력"
                            if gap6>2 else
                            (f"현재가 ${current_price:,.2f}가 Max Pain ${mpv6:,.0f}보다 <strong>{abs(gap6):.1f}% 아래</strong> → 상승 수렴 압력"
                             if gap6<-2 else
                             f"현재가 Max Pain ${mpv6:,.0f} 근처 → 횡보 압력"))
                    st.markdown(sig(mc6,f"⑥ Max Pain [{t6.split(' ')[0]}]",mb6), unsafe_allow_html=True)

            # ⑦ OI Wall
            if gw_all>0 and pw_all>0:
                wc7 = "signal-bear" if current_price>gw_all else ("signal-bull" if current_price<pw_all else "signal-neut")
                wb7 = (f"Gamma Wall(저항) <strong>${gw_all:,.0f}</strong> · Put Wall(지지) <strong>${pw_all:,.0f}</strong>"
                       + (" · 현재가가 Gamma Wall 돌파 → 추가 저항 없음 주의" if current_price>gw_all
                          else (" · 현재가가 Put Wall 하회 → 추가 하락 리스크" if current_price<pw_all
                               else f" · 현재가 ${current_price:,.2f}는 두 Wall 사이 — 지지·저항 범위 내 등락")))
                st.markdown(sig(wc7,"⑦ OI Wall 지지/저항 (전 만기 합산)",wb7), unsafe_allow_html=True)

            # ⑧ IV Term Structure
            ivc_s = df_terms.loc[TERMS[0],'IV(Call) %']; ivc_l = df_terms.loc[TERMS[2],'IV(Call) %']
            if ivc_s>0 and ivc_l>0:
                if ivc_s>ivc_l*1.2:
                    ic8="signal-bear"; im8=f"단기 IV({ivc_s:.1f}%) ≫ 장기 IV({ivc_l:.1f}%) → <strong>단기 이벤트 리스크 반영</strong>, 시장 불안 고조"
                elif ivc_l>ivc_s*1.1:
                    ic8="signal-neut"; im8=f"장기 IV({ivc_l:.1f}%) > 단기 IV({ivc_s:.1f}%) → 중장기 불확실성 우세 (역전 현상)"
                else:
                    ic8="signal-neut"; im8=f"단기 IV({ivc_s:.1f}%) ≈ 장기 IV({ivc_l:.1f}%) → 기간별 변동성 예상 고른 수준"
                st.markdown(sig(ic8,"⑧ IV Term Structure 해석",im8), unsafe_allow_html=True)

            # ⑨ UOA 요약
            uc = len(df_uoa[df_uoa['side']=='CALL']) if not df_uoa.empty else 0
            up = len(df_uoa[df_uoa['side']=='PUT'])  if not df_uoa.empty else 0
            if not df_uoa.empty:
                u9  = "signal-bull" if uc>up else ("signal-bear" if up>uc else "signal-neut")
                um9 = (f"전 만기 UOA — CALL <strong>{uc}건</strong> / PUT <strong>{up}건</strong> · "
                       + ("콜 UOA 우세 → 스마트 머니 상승 배팅 가능성" if uc>up
                          else ("풋 UOA 우세 → 스마트 머니 하락 배팅 또는 대형 헤징" if up>uc
                                else "콜·풋 UOA 균형 → 방향성 불명, 변동성 이벤트 대기")))
                st.markdown(sig(u9,"⑨ 전체 UOA 스마트 머니 요약",um9), unsafe_allow_html=True)

            # ── AI 프롬프트 ──
            uoa_top_str = df_uoa[['term','side','strike','V_OI','days']].head(10).to_string(index=False) if not df_uoa.empty else "없음"
            iv_str = "\n".join([f"  {t.split(' ')[0]}: Call IV {df_terms.loc[t,'IV(Call) %']:.1f}% / Put IV {df_terms.loc[t,'IV(Put) %']:.1f}%" for t in TERMS])
            mp_str = "\n".join([f"  {t.split(' ')[0]}: ${mp_per_term[t]:,.0f} (현재가 대비 {(current_price-mp_per_term[t])/mp_per_term[t]*100 if mp_per_term[t]>0 else 0:+.1f}%)" for t in TERMS])

            prompt = f"""
당신은 월스트리트 시니어 파생상품 애널리스트입니다.
'{name} ({ticker_input})'의 전 만기 옵션 데이터를 분석하여 단/중/장기 종합 시나리오를 제시하세요.

[분석 대상]
- 현재가: ${current_price:,.2f}

[기간별 수급 (Volume / OI / PCR)]
1. 단기(≤30일): 콜Vol {short['call_vol']:,.0f} / 풋Vol {short['put_vol']:,.0f} / 콜OI {short['call_oi']:,.0f} / 풋OI {short['put_oi']:,.0f}
   PCR(Vol): {pcr_s:.2f} / PCR(OI): {poi_s:.2f} / 내부 다이버전스: {pcr_s-poi_s:+.2f}
2. 중기(30~90일): 콜Vol {mid['call_vol']:,.0f} / 풋Vol {mid['put_vol']:,.0f} / 콜OI {mid['call_oi']:,.0f} / 풋OI {mid['put_oi']:,.0f}
   PCR(Vol): {pcr_m:.2f} / PCR(OI): {mid['PCR (OI)']:.2f}
3. 장기(≥90일): 콜Vol {long_['call_vol']:,.0f} / 풋Vol {long_['put_vol']:,.0f} / 콜OI {long_['call_oi']:,.0f} / 풋OI {long_['put_oi']:,.0f}
   PCR(Vol): {pcr_l:.2f} / PCR(OI): {poi_l:.2f} / 내부 다이버전스: {pcr_l-poi_l:+.2f}

[Max Pain (기간별 최근접 만기)]
{mp_str}

[OI Wall — 전 만기 행사가별 OI 집중도]
- Gamma Wall (콜 OI 최대 / 저항선): ${gw_all:,.0f}
- Put Wall   (풋 OI 최대 / 지지선): ${pw_all:,.0f}
- 현재가 위치: Gamma Wall {'위' if current_price>gw_all else '아래'} / Put Wall {'위' if current_price>pw_all else '아래'}

[내재변동성(IV) Term Structure]
{iv_str}

[UOA — 전 만기 스마트 머니 감지 Top 10]
{uoa_top_str}
(콜 UOA {uc}건 / 풋 UOA {up}건)

[분석 지시사항]
1. **PCR Term Structure & 내부 다이버전스:** 단기·중기·장기 PCR 차이와 각 기간의 PCR(Vol) vs PCR(OI) 내부 다이버전스가 의미하는 심리 변화를 입체적으로 분석하세요.
2. **Max Pain 기간별 수렴 압력:** 각 기간의 Max Pain과 현재가 괴리율을 바탕으로 단기·중기·장기 만기일까지 예상되는 주가 움직임 시나리오를 제시하세요.
3. **OI Wall 지지/저항 분석:** Gamma Wall과 Put Wall 사이에서의 주가 행동 시나리오를 설명하고, 마켓 메이커 델타 헤징 관점을 포함하세요.
4. **IV Term Structure 해석:** 단기와 장기 IV의 기울기(콘탱고/백워데이션)가 이벤트 리스크 또는 안정화 신호 중 무엇을 반영하는지 해석하세요.
5. **UOA 스마트 머니 의도:** 콜/풋 UOA 건수 비율과 행사가 위치(OTM/ATM)를 기반으로 스마트 머니의 의도(투기 vs 헤징)를 추론하세요.
6. **Volume × OI 기간별 교차 신호:** 각 기간별 추세 신뢰도와 포지션 성격(신규 유입 vs 청산)을 평가하세요.
7. **종합 투자 시나리오:** 위 6가지를 통합하여 향후 1개월/3개월 주가 방향(Bull/Bear/Neutral) 시나리오와 핵심 가격 레벨을 도출하세요.
초보자도 이해할 수 있도록 친절한 한글 마크다운으로 정리하세요.
"""

    # ══════════════════════════════════════════════════════════
    # 공통 AI 분석 섹션
    # ══════════════════════════════════════════════════════════
    if ticker_input and expirations and (
        (analysis_mode == "단일 만기일 분석" and selected_expiry) or
        analysis_mode != "단일 만기일 분석"
    ):
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
                            st.success(f"분석 완료! (사용한 모델: {used_model})")
                            st.markdown(f'<div class="report-box">{result}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"분석 중 오류 발생: {e}")
                else:
                    st.error("API 키가 설정되지 않았습니다.")

        with col_btn2:
            st.markdown("#### 옵션 2. 무료 한도 초과 시 대안")
            safe_prompt = json.dumps(prompt)
            html_code = f"""
            <button onclick="copyAndOpen()" style="background-color:#f5a623;color:#000;padding:12px 20px;
                border:none;border-radius:8px;font-weight:bold;font-size:15px;cursor:pointer;
                width:100%;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                📋 프롬프트 복사 & Gemini 웹 열기
            </button>
            <script>
            function copyAndOpen() {{
                const text = {safe_prompt};
                navigator.clipboard.writeText(text).then(function() {{
                    window.open("https://gemini.google.com/", "_blank");
                }}).catch(function() {{
                    const ta = document.createElement("textarea");
                    ta.value = text; document.body.appendChild(ta);
                    ta.select(); document.execCommand("copy"); ta.remove();
                    window.open("https://gemini.google.com/", "_blank");
                }});
            }}
            </script>
            """
            components.html(html_code, height=60)

        with st.expander("생성된 고도화 분석 프롬프트 내용 확인하기", expanded=False):
            st.code(prompt, language="text")

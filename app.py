import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import google.generativeai as genai
import time
import json
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .big-font { font-size:40px !important; font-weight: bold; color: #00e5a0; text-shadow: 0 0 20px rgba(0,229,160,0.2); }
    .subtitle { font-size:16px; color: #a0a0a0; margin-bottom: 25px; font-family: 'monospace'; }
    .stMetric { background-color: #111827; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .report-box { background-color: #1e293b; padding: 25px; border-radius: 12px; border-left: 5px solid #00e5a0; color: #f3f4f6; line-height: 1.6; }
    .help-card  { background-color: #0f172a; padding: 22px 28px; border-radius: 14px; border-left: 5px solid #f5a623; color: #e2e8f0; line-height: 1.8; margin-bottom: 18px; }
    .help-title { font-size: 20px; font-weight: 800; color: #f5a623; margin-bottom: 10px; }
    .signal-green { color: #00e5a0; font-weight: 700; }
    .signal-red   { color: #ff4d6d; font-weight: 700; }
    .signal-gray  { color: #9ca3af; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (단/중/장기 통합 지원)</p>', unsafe_allow_html=True)

# --- 2. Gemini API 설정 ---
def generate_with_fallback(prompt, api_key):
    genai.configure(api_key=api_key)
    fallback_chain = [
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-flash-latest"
    ]
    last_errors = []
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name
        except Exception as e:
            last_errors.append(f"[{model_name} 실패: {str(e)[:100]}]")
            time.sleep(0.5)
            continue
    raise Exception(f"모든 모델 호출에 실패했습니다.\n사유: {' / '.join(last_errors)}")

api_key = st.secrets.get("GEMINI_API_KEY")
has_api_key = api_key is not None

if not has_api_key:
    st.sidebar.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다.")

# --- 3. 사이드바 검색 영역 ---
with st.sidebar:
    st.header("🔍 검색 설정")
    ticker_input = st.text_input("티커 심볼 (예: AAPL, NVDA, SPY)", value="AAPL").upper()
    
    analysis_mode = st.radio("분석 모드 선택", ["단일 만기일 분석", "전체 기간 통합 분석 (단/중/장기)"])
    
    ticker = yf.Ticker(ticker_input)
    expirations = []
    try:
        expirations = ticker.options
        if not expirations:
            st.error("옵션 데이터를 찾을 수 없는 티커입니다.")
    except:
        st.error("데이터 서버 연결에 문제가 발생했습니다.")
        
    selected_expiry = None
    if expirations and analysis_mode == "단일 만기일 분석":
        selected_expiry = st.selectbox("만기일 선택", expirations)

# --- 4. 공통 데이터 수집 ---
current_price = 0
name = ticker_input
if ticker_input and expirations:
    try:
        info = ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not current_price:
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
        name = info.get('longName', ticker_input)
    except:
        pass
    st.subheader(f"📊 {name} ({ticker_input}) | 현재가: ${current_price:,.2f}")

# ─────────────────────────────────────────────────────────────
# 헬퍼 함수들
# ─────────────────────────────────────────────────────────────
def get_metric_card(title, value, val_color, status="", stat_color="transparent"):
    return f"""
    <div style="background-color: #111827; padding: 20px; border-radius: 12px; border: 1px solid #1f2937; box-shadow: 0 4px 6px rgba(0,0,0,0.2); height: 100%;">
        <div style="color: #9ca3af; font-size: 15px; margin-bottom: 8px; font-weight: 600;">{title}</div>
        <div style="display: flex; align-items: baseline; gap: 12px;">
            <div style="color: {val_color}; font-size: 34px; font-weight: 800;">{value}</div>
            <div style="color: {stat_color}; font-size: 16px; font-weight: 700;">{status}</div>
        </div>
    </div>
    """

def pcr_signal(pcr):
    if pcr > 1.2:
        return "#ff4d6d", "⚠️ 하락 신호 (Bearish)", "풋옵션 몰림 → 공포 과잉 → 단기 반등 가능성"
    elif pcr > 1.0:
        return "#f5a623", "🔶 약세 (Mildly Bearish)", "풋 우세 → 시장 경계심 고조"
    elif pcr < 0.6:
        return "#00e5a0", "🚀 상승 신호 (Bullish)", "콜옵션 몰림 → 탐욕 과잉 → 조정 경계"
    elif pcr < 0.8:
        return "#a3e635", "✅ 약세 상승 (Mildly Bullish)", "콜 우세 → 낙관론 우세"
    else:
        return "#f3f4f6", "⚖️ 중립 (Neutral)", "특별한 편향 없음"

def calculate_max_pain(calls, puts):
    all_strikes = sorted(set(calls['strike']).union(set(puts['strike'])))
    min_pain_value = float('inf')
    max_pain_strike = all_strikes[len(all_strikes)//2]
    pain_values = []
    for s in all_strikes:
        call_pain = (calls[calls['strike'] <= s]['openInterest'] *
                     (s - calls[calls['strike'] <= s]['strike'])).sum()
        put_pain  = (puts[puts['strike'] >= s]['openInterest'] *
                     (puts[puts['strike'] >= s]['strike'] - s)).sum()
        total = call_pain + put_pain
        pain_values.append({"strike": s, "call_pain": call_pain, "put_pain": put_pain, "total_pain": total})
        if total < min_pain_value:
            min_pain_value = total
            max_pain_strike = s
    return max_pain_strike, pd.DataFrame(pain_values)

def detect_uoa(calls, puts, current_price, threshold=5, min_vol=100):
    uoa_rows = []
    for df, otype in [(calls, "CALL"), (puts, "PUT")]:
        for _, row in df.iterrows():
            oi  = row['openInterest'] if row['openInterest'] > 0 else 1
            vol = row['volume'] if pd.notna(row['volume']) else 0
            ratio = vol / oi
            if ratio < threshold or vol < min_vol:
                continue
            moneyness = ((row['strike'] / current_price) - 1) * 100 if current_price > 0 else 0
            if otype == "CALL":
                otm = "OTM 🔥" if row['strike'] > current_price else "ITM"
            else:
                otm = "OTM 🔥" if row['strike'] < current_price else "ITM"
            uoa_rows.append({
                "유형": otype, "행사가": row['strike'],
                "거래량": int(vol), "미결제약정": int(row['openInterest']),
                "V/OI 배율": round(ratio, 1),
                "현재가 대비": f"{moneyness:+.1f}%",
                "ATM여부": otm
            })
    df_out = pd.DataFrame(uoa_rows)
    if not df_out.empty:
        df_out = df_out.sort_values("V/OI 배율", ascending=False).reset_index(drop=True)
    return df_out


# ─────────────────────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────────────────────
if ticker_input and expirations:
    tab_main, tab_uoa, tab_voi, tab_maxpain, tab_help = st.tabs([
        "📊 메인 분석", "🔍 UOA 비정상 탐지", "📈 Volume × OI 교차", "🎯 맥스 페인", "❓ 도움말"
    ])
else:
    tab_main, tab_help = st.tabs(["📊 메인 분석", "❓ 도움말"])
    tab_uoa = tab_voi = tab_maxpain = None


# =====================================================================
# TAB 1: 메인 분석
# =====================================================================
with tab_main:
    prompt = None

    # ── 모드 1: 단일 만기일 ──
    if analysis_mode == "단일 만기일 분석" and selected_expiry and expirations:
        with st.spinner(f"'{selected_expiry}' 만기 옵션 체인 분석 중..."):
            opt_chain = ticker.option_chain(selected_expiry)
            calls, puts = opt_chain.calls, opt_chain.puts

            if current_price > 0:
                mn, mx = current_price * 0.7, current_price * 1.3
                calls_chart = calls[(calls['strike'] >= mn) & (calls['strike'] <= mx)]
                puts_chart  = puts[(puts['strike']  >= mn) & (puts['strike']  <= mx)]
            else:
                calls_chart, puts_chart = calls, puts

            call_vol = calls['volume'].fillna(0).sum()
            put_vol  = puts['volume'].fillna(0).sum()
            call_oi  = calls['openInterest'].fillna(0).sum()
            put_oi   = puts['openInterest'].fillna(0).sum()
            pcr      = put_vol / call_vol if call_vol > 0 else 0
            pcr_oi   = put_oi  / call_oi  if call_oi  > 0 else 0

            status_color, status_text, pcr_desc = pcr_signal(pcr)

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(get_metric_card("CALL 거래량",   f"{int(call_vol):,}", "#00e5a0"), unsafe_allow_html=True)
            with c2: st.markdown(get_metric_card("PUT 거래량",    f"{int(put_vol):,}",  "#ff4d6d"), unsafe_allow_html=True)
            with c3: st.markdown(get_metric_card("PCR (거래량)",  f"{pcr:.2f}", "#f3f4f6", status_text, status_color), unsafe_allow_html=True)
            with c4: st.markdown(get_metric_card("PCR (OI)",      f"{pcr_oi:.2f}", "#a78bfa"), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:#111827;border-radius:10px;padding:14px 20px;border-left:4px solid {status_color};margin-bottom:16px;">
                <span style="color:{status_color};font-weight:700;">📌 PCR 해석:</span>
                <span style="color:#e2e8f0;"> {pcr_desc}</span>
            </div>
            """, unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=calls_chart['strike'], y=calls_chart['volume'],  name='Calls', marker_color='#00e5a0'))
            fig.add_trace(go.Bar(x=puts_chart['strike'],  y=-puts_chart['volume'],  name='Puts',  marker_color='#ff4d6d'))
            fig.update_layout(title=f"행사가별 거래량 (만기: {selected_expiry})", barmode='relative',
                              template="plotly_dark", height=400, hovermode="x unified")
            if current_price > 0:
                fig.add_vline(x=current_price, line_dash="dash", line_color="white",
                              annotation_text=f"현재가 ${current_price:,.2f}", annotation_position="top right")
            st.plotly_chart(fig, use_container_width=True)

            prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 바탕으로 시장 심리를 분석하세요.
[분석 대상] {name} ({ticker_input}) / 만기일: {selected_expiry} / 현재가: ${current_price:,.2f}
- 콜옵션 거래량: {call_vol:,.0f} (OI: {call_oi:,.0f})
- 풋옵션 거래량: {put_vol:,.0f} (OI: {put_oi:,.0f})
- PCR(거래량): {pcr:.2f} / PCR(OI): {pcr_oi:.2f}
단기 주가 방향 예측 및 지지/저항선 도출, 한글 마크다운으로 요약하세요.
"""

    # ── 모드 2: 다중 기간 ──
    elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:
        st.info("💡 **단기(30일 이내), 중기(30~90일), 장기(90일 이상)** 만기일 옵션 데이터를 모두 수집하여 입체적으로 분석합니다.")

        with st.spinner("전체 만기일 데이터를 수집 중입니다..."):
            today = datetime.today()
            term_data = {
                "Short (단기/30일내)":  {"call_vol":0,"put_vol":0,"call_oi":0,"put_oi":0},
                "Mid (중기/30~90일)":   {"call_vol":0,"put_vol":0,"call_oi":0,"put_oi":0},
                "Long (장기/90일이상)": {"call_vol":0,"put_vol":0,"call_oi":0,"put_oi":0},
            }
            pb = st.progress(0)
            for i, exp_date in enumerate(expirations):
                try:
                    days = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                    cat = "Short (단기/30일내)" if days <= 30 else ("Mid (중기/30~90일)" if days <= 90 else "Long (장기/90일이상)")
                    opt = ticker.option_chain(exp_date)
                    term_data[cat]["call_vol"] += opt.calls['volume'].fillna(0).sum()
                    term_data[cat]["put_vol"]  += opt.puts['volume'].fillna(0).sum()
                    term_data[cat]["call_oi"]  += opt.calls['openInterest'].fillna(0).sum()
                    term_data[cat]["put_oi"]   += opt.puts['openInterest'].fillna(0).sum()
                except: pass
                pb.progress((i+1)/len(expirations))
            pb.empty()

        df_terms = pd.DataFrame(term_data).T
        df_terms['PCR (Volume)'] = df_terms['put_vol'] / df_terms['call_vol'].replace(0, np.nan)
        df_terms['PCR (OI)']     = df_terms['put_oi']  / df_terms['call_oi'].replace(0, np.nan)
        df_terms.fillna(0, inplace=True)

        st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_terms.index, y=df_terms['call_vol'], name='CALL 거래량', marker_color='#00e5a0'))
        fig2.add_trace(go.Bar(x=df_terms.index, y=df_terms['put_vol'],  name='PUT 거래량',  marker_color='#ff4d6d'))
        fig2.update_layout(barmode='group', template='plotly_dark', height=400, hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### 📌 기간별 PCR 신호 해석")
        pcr_cols = st.columns(3)
        for (term, col) in zip(df_terms.index, pcr_cols):
            pcr_v = df_terms.loc[term, 'PCR (Volume)']
            color, label, desc = pcr_signal(pcr_v)
            with col:
                st.markdown(f"""
                <div style="background:#111827;border-radius:10px;padding:14px;border-left:4px solid {color};margin-bottom:8px;">
                    <div style="color:#9ca3af;font-size:13px;">{term}</div>
                    <div style="color:{color};font-weight:700;font-size:18px;">{label}</div>
                    <div style="color:#e2e8f0;font-size:13px;margin-top:4px;">PCR: {pcr_v:.2f} — {desc}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("#### 📑 기간별 데이터 요약")
        disp = df_terms.copy()
        disp.columns = ['Call 거래량','Put 거래량','Call 미결제약정','Put 미결제약정','PCR(거래량)','PCR(미결제)']
        for c in ['Call 거래량','Put 거래량','Call 미결제약정','Put 미결제약정']:
            disp[c] = disp[c].apply(lambda x: f"{int(x):,}")
        for c in ['PCR(거래량)','PCR(미결제)']:
            disp[c] = disp[c].apply(lambda x: f"{x:.2f}")
        st.dataframe(disp, use_container_width=True)

        s = "Short (단기/30일내)"; m = "Mid (중기/30~90일)"; l = "Long (장기/90일이상)"
        prompt = f"""
당신은 월스트리트 시니어 파생상품 애널리스트입니다. '{name} ({ticker_input})' 기간별 옵션 수급 분석:
현재가: ${current_price:,.2f}
단기: 콜 {df_terms.loc[s,'call_vol']:,.0f} / 풋 {df_terms.loc[s,'put_vol']:,.0f} / PCR {df_terms.loc[s,'PCR (Volume)']:.2f}
중기: 콜 {df_terms.loc[m,'call_vol']:,.0f} / 풋 {df_terms.loc[m,'put_vol']:,.0f} / PCR {df_terms.loc[m,'PCR (Volume)']:.2f}
장기: 콜 {df_terms.loc[l,'call_vol']:,.0f} / 풋 {df_terms.loc[l,'put_vol']:,.0f} / PCR {df_terms.loc[l,'PCR (Volume)']:.2f}
1. 기간별 심리 차이(투기 vs 확신) 비교
2. 단기·장기 PCR 다이버전스 분석
3. 1~3개월 방향성 시나리오
초보자도 이해 가능한 한글 마크다운으로 정리하세요.
"""

    # ── 공통 AI 섹션 ──
    if prompt:
        st.divider()
        st.subheader("🤖 Gemini AI 옵션 시장 브리핑")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.markdown("#### 옵션 1. 스트림릿에서 바로 분석")
            if st.button("✨ API 자동 분석 실행", type="primary", use_container_width=True):
                if has_api_key:
                    with st.spinner("AI가 분석 중입니다..."):
                        try:
                            result, used_model = generate_with_fallback(prompt, api_key)
                            st.success(f"완료! (모델: {used_model})")
                            st.markdown(f'<div class="report-box">{result}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"오류: {e}")
                else:
                    st.error("API 키가 설정되지 않았습니다.")
        with col_btn2:
            st.markdown("#### 옵션 2. 무료 한도 초과 시 대안")
            safe_prompt = json.dumps(prompt)
            html_code = f"""
            <button onclick="copyAndOpen()" style="background-color:#f5a623;color:#000;padding:12px 20px;border:none;border-radius:8px;font-weight:bold;font-size:15px;cursor:pointer;width:100%;">
                📋 프롬프트 복사 & Gemini 웹 열기
            </button>
            <script>
            function copyAndOpen(){{
                const text={safe_prompt};
                navigator.clipboard.writeText(text).then(()=>window.open("https://gemini.google.com/","_blank"))
                .catch(()=>{{const t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();document.execCommand("copy");t.remove();window.open("https://gemini.google.com/","_blank");}});
            }}
            </script>"""
            components.html(html_code, height=60)
        with st.expander("분석 프롬프트 확인", expanded=False):
            st.code(prompt, language="text")


# =====================================================================
# TAB 2: UOA
# =====================================================================
if tab_uoa:
    with tab_uoa:
        st.markdown("### 🔍 UOA — 비정상 옵션 거래량 (Unusual Options Activity)")
        st.caption("평소보다 훨씬 많은 거래량이 몰린 옵션 = 스마트 머니가 움직인다는 신호")

        if analysis_mode != "단일 만기일 분석" or not selected_expiry:
            st.warning("⚠️ UOA 탐지는 **단일 만기일 분석** 모드에서만 사용 가능합니다.")
        else:
            c_th, c_mv = st.columns(2)
            with c_th: threshold = st.slider("V/OI 탐지 임계값 (배율)", 2, 20, 5)
            with c_mv: min_vol   = st.slider("최소 거래량 (계약수)",    50, 2000, 100, step=50)

            with st.spinner("비정상 거래량 탐지 중..."):
                opt_chain = ticker.option_chain(selected_expiry)
                uoa_df = detect_uoa(opt_chain.calls.fillna(0), opt_chain.puts.fillna(0),
                                    current_price, threshold, min_vol)

            if uoa_df.empty:
                st.info(f"현재 설정(V/OI ≥ {threshold}배, 거래량 ≥ {min_vol})에 해당하는 비정상 거래량이 없습니다. 임계값을 낮춰보세요.")
            else:
                st.success(f"🚨 {len(uoa_df)}건의 비정상 거래량 옵션 감지됨!")
                call_uoa = uoa_df[uoa_df["유형"]=="CALL"]
                put_uoa  = uoa_df[uoa_df["유형"]=="PUT"]

                col_c, col_p = st.columns(2)
                with col_c:
                    st.markdown(f"#### 🟢 CALL UOA ({len(call_uoa)}건)")
                    if not call_uoa.empty:
                        st.dataframe(call_uoa.drop(columns=["유형"]), use_container_width=True)
                        otm_c = call_uoa[call_uoa["ATM여부"].str.startswith("OTM")]
                        if not otm_c.empty:
                            st.markdown(f'<div style="background:#0f2d1e;border-left:4px solid #00e5a0;padding:12px 16px;border-radius:8px;">🔥 <strong style="color:#00e5a0;">OTM 콜 {len(otm_c)}건</strong> 대량 → 단기 급등 베팅 / 이벤트 선취매 의심</div>', unsafe_allow_html=True)
                    else:
                        st.caption("해당 없음")
                with col_p:
                    st.markdown(f"#### 🔴 PUT UOA ({len(put_uoa)}건)")
                    if not put_uoa.empty:
                        st.dataframe(put_uoa.drop(columns=["유형"]), use_container_width=True)
                        otm_p = put_uoa[put_uoa["ATM여부"].str.startswith("OTM")]
                        if not otm_p.empty:
                            st.markdown(f'<div style="background:#2d0f0f;border-left:4px solid #ff4d6d;padding:12px 16px;border-radius:8px;">🚨 <strong style="color:#ff4d6d;">OTM 풋 {len(otm_p)}건</strong> 대량 → 하락 베팅 또는 기관 헤징 의심</div>', unsafe_allow_html=True)
                    else:
                        st.caption("해당 없음")

                fig_uoa = go.Figure()
                if not call_uoa.empty:
                    fig_uoa.add_trace(go.Bar(x=call_uoa["행사가"].astype(str)+" C", y=call_uoa["V/OI 배율"], name="CALL UOA", marker_color="#00e5a0"))
                if not put_uoa.empty:
                    fig_uoa.add_trace(go.Bar(x=put_uoa["행사가"].astype(str)+" P",  y=put_uoa["V/OI 배율"],  name="PUT UOA",  marker_color="#ff4d6d"))
                fig_uoa.add_hline(y=threshold, line_dash="dot", line_color="#f5a623", annotation_text=f"기준({threshold}x)")
                fig_uoa.update_layout(title="비정상 거래량 옵션 V/OI 배율", template="plotly_dark", height=350, yaxis_title="V/OI 배율")
                st.plotly_chart(fig_uoa, use_container_width=True)
                st.caption("⚠️ OTM 풋 대량 = 반드시 하락 베팅이 아닐 수 있습니다. 기관 헤징일 수 있으므로 다른 지표와 함께 판단하세요.")


# =====================================================================
# TAB 3: Volume × OI
# =====================================================================
if tab_voi:
    with tab_voi:
        st.markdown("### 📈 Volume × OI 교차 분석")
        st.caption("거래량과 미결제약정의 변화 방향을 결합해 추세 지속/반전 신호를 포착합니다.")

        if analysis_mode != "단일 만기일 분석" or not selected_expiry:
            st.warning("⚠️ Volume × OI 탭은 **단일 만기일 분석** 모드에서만 사용 가능합니다.")
        else:
            with st.spinner("데이터 로딩 중..."):
                opt_chain = ticker.option_chain(selected_expiry)
                calls_r = opt_chain.calls.fillna(0).copy()
                puts_r  = opt_chain.puts.fillna(0).copy()
                calls_r['V_OI'] = calls_r['volume'] / calls_r['openInterest'].replace(0, np.nan)
                puts_r['V_OI']  = puts_r['volume']  / puts_r['openInterest'].replace(0, np.nan)
                calls_r['V_OI'].fillna(0, inplace=True)
                puts_r['V_OI'].fillna(0, inplace=True)
                if current_price > 0:
                    mn, mx = current_price * 0.8, current_price * 1.2
                    calls_f = calls_r[(calls_r['strike'] >= mn) & (calls_r['strike'] <= mx)]
                    puts_f  = puts_r[(puts_r['strike']  >= mn) & (puts_r['strike']  <= mx)]
                else:
                    calls_f, puts_f = calls_r, puts_r

            st.markdown("#### 📖 신호 해석 매트릭스")
            sc1, sc2, sc3, sc4 = st.columns(4)
            scenarios = [
                ("Vol↑ OI↑","🟢 추세 지속","신규 자금 유입 → 현재 방향 강화","#00e5a0"),
                ("Vol↑ OI↓","🔴 추세 소진","청산 러시 → 반전 임박","#ff4d6d"),
                ("Vol↓ OI↑","🟡 조용한 축적","시장 주목 없는 포지션 구축","#f5a623"),
                ("Vol↓ OI↓","⚪ 관망 국면","에너지 없음 → 방향 불명확","#9ca3af"),
            ]
            for col, (lbl, ttl, desc, color) in zip([sc1,sc2,sc3,sc4], scenarios):
                with col:
                    st.markdown(f'<div style="background:#111827;border-radius:10px;padding:14px;border-left:4px solid {color};text-align:center;"><div style="color:#9ca3af;font-size:13px;">{lbl}</div><div style="color:{color};font-weight:700;font-size:15px;margin:6px 0;">{ttl}</div><div style="color:#94a3b8;font-size:12px;">{desc}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            fig_voi = go.Figure()
            fig_voi.add_trace(go.Scatter(x=calls_f['strike'], y=calls_f['V_OI'], mode='lines+markers', name='CALL V/OI', line=dict(color='#00e5a0', width=2)))
            fig_voi.add_trace(go.Scatter(x=puts_f['strike'],  y=puts_f['V_OI'],  mode='lines+markers', name='PUT V/OI',  line=dict(color='#ff4d6d', width=2)))
            fig_voi.add_hline(y=1.0, line_dash="dot", line_color="#f5a623", annotation_text="V=OI 기준선(1.0)")
            if current_price > 0:
                fig_voi.add_vline(x=current_price, line_dash="dash", line_color="white", annotation_text=f"현재가 ${current_price:,.2f}")
            fig_voi.update_layout(title="행사가별 V/OI 비율 (1.0 초과 = 신규 포지션 활발)", template="plotly_dark", height=400, hovermode="x unified", yaxis_title="V/OI 비율")
            st.plotly_chart(fig_voi, use_container_width=True)

            st.markdown("#### 📑 V/OI 비율 상위 10개 행사가")
            combined = pd.concat([
                calls_f[['strike','volume','openInterest','V_OI']].assign(유형='CALL'),
                puts_f[['strike','volume','openInterest','V_OI']].assign(유형='PUT')
            ]).sort_values('V_OI', ascending=False).head(10)
            combined.columns = ['행사가','거래량','미결제약정','V/OI','유형']
            combined['거래량']    = combined['거래량'].apply(lambda x: f"{int(x):,}")
            combined['미결제약정'] = combined['미결제약정'].apply(lambda x: f"{int(x):,}")
            combined['V/OI']     = combined['V/OI'].apply(lambda x: f"{x:.2f}")
            st.dataframe(combined[['유형','행사가','거래량','미결제약정','V/OI']], use_container_width=True)
            st.caption("V/OI > 1.0 → 신규 포지션 유입 활발 / V/OI < 0.3 → 기존 포지션 청산 중")


# =====================================================================
# TAB 4: 맥스 페인
# =====================================================================
if tab_maxpain:
    with tab_maxpain:
        st.markdown("### 🎯 맥스 페인 (Max Pain) 분석")
        st.caption("옵션 만기일에 옵션 매수자들의 손실이 최대화되는 '자석 가격' 탐색")

        if analysis_mode != "단일 만기일 분석" or not selected_expiry:
            st.warning("⚠️ 맥스 페인은 **단일 만기일 분석** 모드에서만 사용 가능합니다.")
        else:
            with st.spinner("맥스 페인 계산 중..."):
                opt_chain = ticker.option_chain(selected_expiry)
                max_pain_price, pain_df = calculate_max_pain(opt_chain.calls.fillna(0), opt_chain.puts.fillna(0))

            diff = max_pain_price - current_price if current_price > 0 else 0
            diff_pct = (diff / current_price * 100) if current_price > 0 else 0
            diff_color = "#00e5a0" if diff > 0 else "#ff4d6d"

            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(get_metric_card("🎯 맥스 페인 가격", f"${max_pain_price:,.2f}", "#f5a623"), unsafe_allow_html=True)
            with c2: st.markdown(get_metric_card("현재가와의 거리", f"${diff:+,.2f}", diff_color, f"({diff_pct:+.1f}%)", diff_color), unsafe_allow_html=True)
            with c3: st.markdown(get_metric_card("만기일", selected_expiry, "#a78bfa"), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            if abs(diff_pct) <= 2:
                mp_msg, mp_color = "✅ 현재가 ≈ 맥스 페인 → 만기일까지 횡보 압력 지속 가능성 높음", "#f5a623"
            elif diff > 0:
                mp_msg, mp_color = f"⬆️ 맥스 페인이 ${diff:+.2f} 높음 → 만기일까지 상승 압력 존재 가능", "#00e5a0"
            else:
                mp_msg, mp_color = f"⬇️ 맥스 페인이 ${diff:.2f} 낮음 → 만기일까지 하락 압력 존재 가능", "#ff4d6d"

            st.markdown(f'<div style="background:#111827;border-radius:10px;padding:16px 20px;border-left:4px solid {mp_color};margin-bottom:16px;"><span style="color:{mp_color};font-weight:700;">📌 맥스 페인 해석:</span> <span style="color:#e2e8f0;">{mp_msg}</span></div>', unsafe_allow_html=True)

            if current_price > 0:
                pain_disp = pain_df[(pain_df['strike'] >= current_price*0.7) & (pain_df['strike'] <= current_price*1.3)]
            else:
                pain_disp = pain_df

            fig_mp = go.Figure()
            fig_mp.add_trace(go.Scatter(x=pain_disp['strike'], y=pain_disp['total_pain'], mode='lines+markers', name='Total Pain', line=dict(color='#a78bfa', width=2.5), fill='tozeroy', fillcolor='rgba(167,139,250,0.1)'))
            fig_mp.add_vline(x=max_pain_price, line_dash="dash", line_color="#f5a623", annotation_text=f"Max Pain ${max_pain_price:,.2f}", annotation_font_color="#f5a623")
            if current_price > 0:
                fig_mp.add_vline(x=current_price, line_dash="dot", line_color="white", annotation_text=f"현재가 ${current_price:,.2f}")
            fig_mp.update_layout(title=f"행사가별 옵션 매수자 총 손실 (만기: {selected_expiry})", template="plotly_dark", height=420, yaxis_title="매수자 총 손실(Pain)", hovermode="x unified")
            st.plotly_chart(fig_mp, use_container_width=True)

            fig_mp2 = go.Figure()
            fig_mp2.add_trace(go.Bar(x=pain_disp['strike'], y=pain_disp['call_pain'], name='콜 매수자 손실', marker_color='#00e5a0'))
            fig_mp2.add_trace(go.Bar(x=pain_disp['strike'], y=pain_disp['put_pain'],  name='풋 매수자 손실', marker_color='#ff4d6d'))
            fig_mp2.add_vline(x=max_pain_price, line_dash="dash", line_color="#f5a623")
            fig_mp2.update_layout(title="콜/풋 매수자 손실 분해", barmode='stack', template="plotly_dark", height=350, hovermode="x unified")
            st.plotly_chart(fig_mp2, use_container_width=True)
            st.caption("⚠️ Max Pain은 만기 1~2주 이내일 때 신뢰도 최대. 시장 충격·뉴스에 의해 무력화될 수 있습니다.")


# =====================================================================
# TAB 5: 도움말
# =====================================================================
with tab_help:
    st.markdown("## ❓ OPTIONS FLOW 활용 가이드")
    st.markdown("이 앱에 적용된 4가지 핵심 이론과 실전 활용법을 설명합니다.")
    st.divider()

    # ── 이론 1: PCR ──
    st.markdown("""
    <div class="help-card">
        <div class="help-title">① Put/Call Ratio (PCR) — 시장의 탐욕과 공포 측정계</div>
        <p>풋옵션(하락 베팅) 거래량 ÷ 콜옵션(상승 베팅) 거래량으로 산출합니다. <strong>역발상 지표</strong>로 활용합니다.</p>
        <table style="width:100%;border-collapse:collapse;margin-top:10px;">
            <tr style="background:#1e293b;">
                <th style="padding:8px;text-align:left;border-bottom:1px solid #334155;">PCR 값</th>
                <th style="padding:8px;text-align:left;border-bottom:1px solid #334155;">시장 심리</th>
                <th style="padding:8px;text-align:left;border-bottom:1px solid #334155;">해석 (역발상)</th>
            </tr>
            <tr><td style="padding:8px;color:#ff4d6d;font-weight:700;">1.2 이상</td><td style="padding:8px;">공포 극단</td><td style="padding:8px;">풋 매수 쏠림 → 과매도 → <span class="signal-green">단기 반등 신호</span></td></tr>
            <tr><td style="padding:8px;color:#f5a623;font-weight:700;">1.0 ~ 1.2</td><td style="padding:8px;">경계 구간</td><td style="padding:8px;">약세 심리 우세 → 관망 권고</td></tr>
            <tr><td style="padding:8px;color:#9ca3af;font-weight:700;">0.8 ~ 1.0</td><td style="padding:8px;">중립</td><td style="padding:8px;">특별한 방향성 없음</td></tr>
            <tr><td style="padding:8px;color:#a3e635;font-weight:700;">0.7 ~ 0.8</td><td style="padding:8px;">낙관 우세</td><td style="padding:8px;">콜 매수 증가 → 상승 기대감</td></tr>
            <tr><td style="padding:8px;color:#00e5a0;font-weight:700;">0.7 미만</td><td style="padding:8px;">탐욕 극단</td><td style="padding:8px;">콜 매수 쏠림 → 과매수 → <span class="signal-red">단기 조정 경계</span></td></tr>
        </table>
        <p style="margin-top:12px;color:#94a3b8;font-size:14px;">💡 <strong>실전 팁:</strong> 단기 PCR이 높고(공포) 장기 PCR이 낮다면(낙관) → 단기 조정 후 장기 우상향 가능성 높음</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 이론 2: UOA ──
    st.markdown("""
    <div class="help-card" style="border-left-color:#a78bfa;">
        <div class="help-title" style="color:#a78bfa;">② 비정상 옵션 거래량 (UOA) — 스마트 머니 추적</div>
        <p>평소 미결제약정(OI) 대비 <strong>수배 이상의 거래량(Volume)</strong>이 갑자기 터질 때 포착합니다.</p>
        <ul>
            <li><strong>왜 중요한가?</strong> 대규모 기관이나 내부자들이 실적 발표, M&A, FDA 승인 등 이벤트 전 선제적으로 포지션을 구축할 때 발생합니다.</li>
            <li><strong>OTM 콜 대량 발생:</strong> 현재가보다 높은 행사가에 콜 폭발 → 단기 급등 베팅 / 강한 상승 확신 신호</li>
            <li><strong>OTM 풋 대량 발생:</strong> 현재가보다 낮은 행사가에 풋 폭발 → 하락 베팅 <em>또는</em> 주식 헤징</li>
        </ul>
        <div style="background:#1e1333;padding:12px;border-radius:8px;margin-top:10px;">
            <strong style="color:#a78bfa;">🔍 앱에서의 활용법</strong><br>
            <span style="color:#e2e8f0;">UOA 탭 → 임계값 슬라이더로 V/OI 배율 조정 → <strong>OTM 🔥 배지</strong>가 붙은 항목 우선 확인</span>
        </div>
        <p style="margin-top:12px;color:#94a3b8;font-size:14px;">⚠️ OTM 풋 대량 = 반드시 하락 베팅이 아닙니다. 기관이 주식 헤징 목적으로 풋을 대량 매수하는 경우가 많습니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 이론 3: Volume × OI ──
    st.markdown("""
    <div class="help-card" style="border-left-color:#38bdf8;">
        <div class="help-title" style="color:#38bdf8;">③ Volume × OI 교차 분석 — 추세 강도 판단</div>
        <p>거래량(하루 동안 거래된 총량)과 미결제약정(청산되지 않고 남아있는 계약 수)의 변화 방향을 결합합니다.</p>
        <table style="width:100%;border-collapse:collapse;margin-top:10px;">
            <tr style="background:#1e293b;">
                <th style="padding:8px;border-bottom:1px solid #334155;">거래량</th>
                <th style="padding:8px;border-bottom:1px solid #334155;">미결제약정</th>
                <th style="padding:8px;border-bottom:1px solid #334155;">신호</th>
                <th style="padding:8px;border-bottom:1px solid #334155;">의미</th>
            </tr>
            <tr><td style="padding:8px;text-align:center;">📈</td><td style="padding:8px;text-align:center;">📈</td><td style="padding:8px;"><span class="signal-green">🟢 추세 지속</span></td><td style="padding:8px;">신규 자금 유입 → 현재 방향 강화 확인</td></tr>
            <tr><td style="padding:8px;text-align:center;">📈</td><td style="padding:8px;text-align:center;">📉</td><td style="padding:8px;"><span class="signal-red">🔴 반전 임박</span></td><td style="padding:8px;">청산 러시 → 추세 에너지 소진</td></tr>
            <tr><td style="padding:8px;text-align:center;">📉</td><td style="padding:8px;text-align:center;">📈</td><td style="padding:8px;"><span style="color:#f5a623;font-weight:700;">🟡 조용한 축적</span></td><td style="padding:8px;">시장 주목 없이 포지션 구축 → 추세 강화 잠재력</td></tr>
            <tr><td style="padding:8px;text-align:center;">📉</td><td style="padding:8px;text-align:center;">📉</td><td style="padding:8px;"><span class="signal-gray">⚪ 관망</span></td><td style="padding:8px;">에너지 소진 → 방향성 불명확</td></tr>
        </table>
        <div style="background:#0c1f2d;padding:12px;border-radius:8px;margin-top:10px;">
            <strong style="color:#38bdf8;">🔍 앱에서의 활용법</strong><br>
            <span style="color:#e2e8f0;">Volume×OI 탭 → <strong>V/OI 비율이 1.0 초과</strong>하는 행사가 집중 관찰 → 1.0 초과 = 신규 포지션 유입 활발</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 이론 4: Max Pain ──
    st.markdown("""
    <div class="help-card" style="border-left-color:#f5a623;">
        <div class="help-title">④ 맥스 페인 (Max Pain) — 만기일 자석 가격</div>
        <p>특정 행사가에서 <strong>옵션 매수자들의 손실이 최대화</strong>되고 매도자(주로 마켓 메이커)의 이익이 극대화되는 가격입니다.</p>
        <ul>
            <li><strong>계산 원리:</strong> 모든 행사가에서 콜+풋 매수자 총 손실 합계 계산 → 합계가 최솟값인 행사가 = Max Pain</li>
            <li><strong>자석 효과:</strong> 옵션 만기일(매월 3번째 금요일)이 다가올수록 주가가 Max Pain 주변으로 수렴하는 경향</li>
            <li><strong>왜 발생하는가?</strong> 대규모 옵션 매도자(마켓 메이커)들의 델타 헤징이 주가를 Max Pain 방향으로 자연스럽게 끌어당기기 때문</li>
        </ul>
        <div style="background:#2d1f00;padding:12px;border-radius:8px;margin-top:10px;">
            <strong style="color:#f5a623;">🔍 앱에서의 활용법</strong><br>
            <span style="color:#e2e8f0;">맥스 페인 탭 → 현재가와의 거리 확인 → 만기일이 가까울수록 신뢰도 ↑ → 단기 트레이딩 목표가로 활용</span>
        </div>
        <p style="margin-top:12px;color:#94a3b8;font-size:14px;">⚠️ 만기일이 멀수록(1개월 이상) Max Pain의 예측력이 떨어집니다. 만기 1~2주 이내 활용 시 가장 유효합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🗺️ 실전 분석 플로우")
    st.markdown("""
    <div style="background:#0f172a;border-radius:14px;padding:24px;color:#e2e8f0;line-height:2.2;">
        <div style="background:#1e293b;padding:12px 18px;border-radius:8px;border-left:4px solid #00e5a0;margin-bottom:8px;">
            <strong style="color:#00e5a0;">STEP 1</strong> — 메인 분석 탭 → <strong>PCR 확인</strong> → 시장 전반적 공포/탐욕 수준 파악
        </div>
        <div style="text-align:center;color:#475569;">▼</div>
        <div style="background:#1e293b;padding:12px 18px;border-radius:8px;border-left:4px solid #a78bfa;margin-bottom:8px;">
            <strong style="color:#a78bfa;">STEP 2</strong> — UOA 탭 → <strong>비정상 거래량 탐지</strong> → 스마트 머니 방향성 확인 (OTM 옵션 주목)
        </div>
        <div style="text-align:center;color:#475569;">▼</div>
        <div style="background:#1e293b;padding:12px 18px;border-radius:8px;border-left:4px solid #38bdf8;margin-bottom:8px;">
            <strong style="color:#38bdf8;">STEP 3</strong> — V×OI 탭 → <strong>추세 지속/반전 신호 확인</strong> → PCR 신호와 정합성 검증
        </div>
        <div style="text-align:center;color:#475569;">▼</div>
        <div style="background:#1e293b;padding:12px 18px;border-radius:8px;border-left:4px solid #f5a623;margin-bottom:8px;">
            <strong style="color:#f5a623;">STEP 4</strong> — 맥스 페인 탭 → <strong>단기 목표가 설정</strong> → 만기 1~2주 이내일 때 횡보 목표가로 활용
        </div>
        <div style="text-align:center;color:#475569;">▼</div>
        <div style="background:#1e293b;padding:12px 18px;border-radius:8px;border-left:4px solid #fb7185;">
            <strong style="color:#fb7185;">STEP 5</strong> — AI 브리핑 → <strong>Gemini 종합 분석</strong> → 단/중/장기 시나리오 도출
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 옵션 지표는 주가 차트, 거시 경제 데이터, 섹터 수급과 함께 **종합적 퍼즐의 한 조각**으로 활용하세요. 어떤 단일 지표도 완벽하지 않습니다.")

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

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');

    .big-font { font-size:40px !important; font-weight: bold; color: #00e5a0; text-shadow: 0 0 20px rgba(0,229,160,0.2); }
    .subtitle { font-size:16px; color: #a0a0a0; margin-bottom: 25px; font-family: monospace; }
    .stMetric { background-color: #111827; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .report-box { background-color: #1e293b; padding: 25px; border-radius: 12px; border-left: 5px solid #00e5a0; color: #f3f4f6; line-height: 1.6; }

    /* ── 도움말 카드 ── */
    .help-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 28px 28px 22px 28px;
        margin-bottom: 18px;
        position: relative;
        overflow: hidden;
    }
    .help-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }
    .help-card.pcr::before   { background: linear-gradient(90deg, #00e5a0, #00b4d8); }
    .help-card.uoa::before   { background: linear-gradient(90deg, #f5a623, #ff6b6b); }
    .help-card.voi::before   { background: linear-gradient(90deg, #a78bfa, #60a5fa); }
    .help-card.mp::before    { background: linear-gradient(90deg, #fb923c, #f472b6); }
    .help-card.warn::before  { background: linear-gradient(90deg, #fbbf24, #f87171); }

    .help-title {
        font-size: 19px;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .help-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 20px;
        letter-spacing: 0.05em;
    }
    .badge-pcr  { background: rgba(0,229,160,0.15);  color: #00e5a0; }
    .badge-uoa  { background: rgba(245,166,35,0.15); color: #f5a623; }
    .badge-voi  { background: rgba(167,139,250,0.15);color: #a78bfa; }
    .badge-mp   { background: rgba(251,146,60,0.15); color: #fb923c; }
    .badge-warn { background: rgba(251,191,36,0.15); color: #fbbf24; }

    .help-body { color: #94a3b8; font-size: 14px; line-height: 1.75; }
    .help-body strong { color: #e2e8f0; }
    .help-body .tag {
        display: inline-block;
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 2px 9px;
        font-size: 12px;
        font-family: monospace;
        margin: 2px 3px 2px 0;
        color: #00e5a0;
    }

    /* ── 신호 배지 (분석 화면) ── */
    .signal-box {
        padding: 14px 20px;
        border-radius: 10px;
        margin: 6px 0;
        font-size: 14px;
        line-height: 1.6;
    }
    .signal-bull { background: rgba(0,229,160,0.08); border-left: 4px solid #00e5a0; }
    .signal-bear { background: rgba(255,77,109,0.08); border-left: 4px solid #ff4d6d; }
    .signal-neut { background: rgba(245,166,35,0.08); border-left: 4px solid #f5a623; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (단/중/장기 통합 지원)</p>', unsafe_allow_html=True)

# =====================================================================
# 탭 구성 : 분석 | 도움말
# =====================================================================
tab_analysis, tab_help = st.tabs(["📊 분석", "📖 도움말"])

# =====================================================================
# 도움말 탭 (이론 설명)
# =====================================================================
with tab_help:
    st.markdown("## 📖 옵션 데이터 활용 가이드")
    st.markdown("옵션 거래량·미결제약정으로 **스마트 머니**의 방향을 읽는 4가지 핵심 이론입니다.")
    st.markdown("---")

    # ── 1. PCR ──
    st.markdown("""
    <div class="help-card pcr">
      <div class="help-title">
        📊 &nbsp;1. 풋/콜 비율 (Put/Call Ratio, PCR)
        <span class="help-badge badge-pcr">역발상 지표</span>
      </div>
      <div class="help-body">
        풋옵션(하락 베팅) 거래량 ÷ 콜옵션(상승 베팅) 거래량으로 산출합니다.<br><br>
        <strong>▸ PCR이 높다 (≥ 1.2)</strong> — 시장에 공포 심리가 팽배, 풋옵션 쏠림 현상.<br>
        &nbsp;&nbsp;→ <span class="tag">과매도 경계</span> 단기 반등 가능성 높음.<br><br>
        <strong>▸ PCR이 낮다 (&lt; 0.7)</strong> — 시장에 탐욕이 가득, 콜옵션 쏠림 현상.<br>
        &nbsp;&nbsp;→ <span class="tag">과매수 경계</span> 조정·하락 가능성 높음.<br><br>
        <strong>▸ 중립 (0.7 ~ 1.2)</strong> — 명확한 방향성 부재, 추가 지표와 결합하여 판단.<br><br>
        ⚡ 이 앱에서는 PCR을 실시간 산출하여 <strong>상단 지표 카드</strong>에 색상 신호로 표시합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 2. UOA ──
    st.markdown("""
    <div class="help-card uoa">
      <div class="help-title">
        🔥 &nbsp;2. 비정상적 옵션 거래량 (Unusual Options Activity, UOA)
        <span class="help-badge badge-uoa">스마트 머니 감지</span>
      </div>
      <div class="help-body">
        평소 거래량이나 미결제약정(OI)을 <strong>5배 이상 초과하는</strong> 대규모 주문을 탐지합니다.<br><br>
        <strong>▸ 발생 원인:</strong> 실적 발표, M&amp;A, 임상 결과 등 <strong>중요 이벤트 직전</strong>
        기관·내부 투자자가 선제적으로 포지션을 구축할 때 자주 관찰됩니다.<br><br>
        <strong>▸ 외가격(OTM) 콜옵션에 대량 유입</strong> → 단기 급등 확신 신호.<br>
        <strong>▸ 외가격(OTM) 풋옵션에 대량 유입</strong> → 단기 급락 또는 헤징 신호.<br><br>
        ⚡ 이 앱에서는 <strong>Volume ÷ OI 비율(V/OI Ratio)이 5 이상</strong>인 행사가를
        <strong>UOA 경보</strong>로 표시합니다. 단일 만기일 분석 모드에서 확인하세요.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 3. Volume × OI 교차 분석 ──
    st.markdown("""
    <div class="help-card voi">
      <div class="help-title">
        🔁 &nbsp;3. 거래량 × 미결제약정 교차 분석
        <span class="help-badge badge-voi">추세 신뢰도</span>
      </div>
      <div class="help-body">
        거래량(당일 계약 총량)과 미결제약정(청산되지 않고 남은 계약 수)을 결합하면<br>
        현재 추세의 <strong>신뢰도와 지속성</strong>을 판단할 수 있습니다.<br><br>
        <table style="width:100%; border-collapse:collapse; margin-top:4px;">
          <tr style="border-bottom:1px solid #334155;">
            <th style="text-align:left; padding:8px 12px; color:#64748b; font-size:12px;">거래량</th>
            <th style="text-align:left; padding:8px 12px; color:#64748b; font-size:12px;">미결제약정</th>
            <th style="text-align:left; padding:8px 12px; color:#64748b; font-size:12px;">해석</th>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px; color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px; color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px; color:#e2e8f0;">신규 자금 유입 → <strong>추세 강하게 지속</strong></td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px; color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px; color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px; color:#e2e8f0;">기존 포지션 청산 → <strong>추세 반전 경계</strong></td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px; color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px; color:#00e5a0;">↑ 증가</td>
            <td style="padding:8px 12px; color:#e2e8f0;">조용한 포지션 축적 → <strong>대기 중</strong></td>
          </tr>
          <tr>
            <td style="padding:8px 12px; color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px; color:#ff4d6d;">↓ 감소</td>
            <td style="padding:8px 12px; color:#e2e8f0;">추세 소진 → <strong>에너지 방전, 전환 임박</strong></td>
          </tr>
        </table><br>
        ⚡ 이 앱에서는 콜 OI와 풋 OI의 절대값 및 PCR(OI) 비교로 포지션 방향을 추론합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 4. Max Pain ──
    st.markdown("""
    <div class="help-card mp">
      <div class="help-title">
        🎯 &nbsp;4. 맥스 페인 (Max Pain) 이론
        <span class="help-badge badge-mp">만기일 자석 효과</span>
      </div>
      <div class="help-body">
        옵션 매도자(주로 마켓 메이커·기관)가 이익을 극대화하는 행사가, 즉
        <strong>옵션 매수자의 손실(Pain)이 최대화되는 가격</strong>을 맥스 페인이라 합니다.<br><br>
        <strong>▸ 만기일의 자석 효과:</strong> 만기일(매월 세 번째 금요일)이 가까워질수록
        주가가 맥스 페인 가격 근처로 수렴하는 경향이 있습니다.<br><br>
        <strong>▸ 산출 방법:</strong><br>
        &nbsp;&nbsp;각 행사가별로 "해당 가격이 만기가가 될 때 남는 모든 옵션의 내재가치 합계"를 계산 →
        그 합계가 <strong>최소가 되는 행사가 = 맥스 페인</strong>.<br><br>
        <strong>▸ 트레이딩 활용:</strong>
        <span class="tag">현재가 &gt; Max Pain</span> 하락 압력 ·
        <span class="tag">현재가 &lt; Max Pain</span> 상승 압력.<br><br>
        ⚡ 이 앱에서는 단일 만기일 분석 시 <strong>맥스 페인 가격을 자동 계산</strong>하여
        차트에 주황색 점선으로 표시합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 주의사항 ──
    st.markdown("""
    <div class="help-card warn">
      <div class="help-title">
        ⚠️ &nbsp;주의할 점 — 헤징(Hedging) vs 투기(Speculation)
        <span class="help-badge badge-warn">필독</span>
      </div>
      <div class="help-body">
        <strong>풋옵션 매수 ≠ 무조건 하락 배팅</strong>입니다.<br>
        기관 투자자는 수백만 주의 현물 주식을 보유하면서
        하락 방어를 위해 풋옵션을 <strong>대량으로 헤징 매수</strong>하기도 합니다.<br><br>
        옵션 데이터는 단독 사용보다 <strong>주가 차트 + 수급 + 거시 경제 상황</strong>과
        조합했을 때 신뢰도가 크게 높아집니다.<br><br>
        이 앱의 분석 결과는 <strong>투자 참고용</strong>이며, 최종 판단은 본인 책임 하에 이루어져야 합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# 분석 탭 (기존 로직 + 이론 적용 강화)
# =====================================================================
with tab_analysis:

    # --- Gemini API 설정 ---
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

    # --- 맥스 페인 계산 함수 ---
    def calculate_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
        """각 행사가별 옵션 매수자의 총 손실(내재가치 합)이 최대인 가격을 반환."""
        strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
        pain = {}
        for s in strikes:
            call_pain = calls[calls['strike'] < s].apply(
                lambda r: (s - r['strike']) * r.get('openInterest', 0), axis=1
            ).sum()
            put_pain = puts[puts['strike'] > s].apply(
                lambda r: (r['strike'] - s) * r.get('openInterest', 0), axis=1
            ).sum()
            pain[s] = call_pain + put_pain
        if not pain:
            return 0.0
        return min(pain, key=pain.get)

    # --- UOA 탐지 함수 ---
    def detect_uoa(df: pd.DataFrame, side: str, threshold: float = 5.0) -> pd.DataFrame:
        """V/OI 비율이 threshold 이상인 행 추출."""
        d = df.copy()
        d['V_OI_ratio'] = d['volume'] / d['openInterest'].replace(0, np.nan)
        uoa = d[d['V_OI_ratio'] >= threshold][['strike', 'volume', 'openInterest', 'V_OI_ratio', 'lastPrice']].copy()
        uoa['side'] = side
        return uoa.sort_values('V_OI_ratio', ascending=False).head(5)

    # --- Volume × OI 교차 해석 함수 ---
    def vol_oi_signal(vol_call, vol_put, oi_call, oi_put, prev_oi_call=None, prev_oi_put=None):
        """간단한 콜/풋 수급 신호 반환."""
        # OI 방향 추정: OI(Call) > OI(Put) → 신규 콜 포지션 우세 가정
        call_dominant = oi_call > oi_put
        put_dominant  = oi_put  > oi_call
        vol_call_dom  = vol_call > vol_put

        if call_dominant and vol_call_dom:
            return "bull", "📈 신규 콜 포지션 유입 우세 → 상승 추세 지속 가능성 높음"
        elif put_dominant and not vol_call_dom:
            return "bear", "📉 신규 풋 포지션 유입 우세 → 하락 추세 지속 또는 헤징 증가"
        elif call_dominant and not vol_call_dom:
            return "neut", "🔄 콜 OI 우세 but 오늘 풋 거래 활발 → 단기 조정 후 반등 패턴"
        else:
            return "neut", "⚖️ 콜·풋 수급 혼재 → 방향성 불분명, 추가 데이터 필요"

    # --- 사이드바 ---
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

    # --- 현재가 로드 ---
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

    # ==================================================================
    # 모드 1: 단일 만기일 분석
    # ==================================================================
    if analysis_mode == "단일 만기일 분석" and selected_expiry:
        with st.spinner(f"'{selected_expiry}' 만기 옵션 체인 분석 중..."):
            opt_chain = ticker.option_chain(selected_expiry)
            calls, puts = opt_chain.calls, opt_chain.puts

            if current_price > 0:
                min_strike, max_strike = current_price * 0.7, current_price * 1.3
                calls_chart = calls[(calls['strike'] >= min_strike) & (calls['strike'] <= max_strike)]
                puts_chart  = puts[(puts['strike']  >= min_strike) & (puts['strike']  <= max_strike)]
            else:
                calls_chart, puts_chart = calls, puts

            call_vol = calls['volume'].sum()
            put_vol  = puts['volume'].sum()
            call_oi  = calls['openInterest'].sum()
            put_oi   = puts['openInterest'].sum()
            pcr      = put_vol / call_vol if call_vol > 0 else 0

            # ── PCR 신호 ──
            status_color, status_text = "#f5a623", "중립 (Neutral)"
            if pcr > 1.2:
                status_color, status_text = "#ff4d6d", "⬇ 하락 신호 (Bearish)"
            elif pcr < 0.7:
                status_color, status_text = "#00e5a0", "⬆ 상승 신호 (Bullish)"

            def get_metric_card(title, value, val_color, status="", stat_color="transparent"):
                return f"""
                <div style="background-color:#111827;padding:20px;border-radius:12px;
                            border:1px solid #1f2937;box-shadow:0 4px 6px rgba(0,0,0,0.2);height:100%;">
                    <div style="color:#9ca3af;font-size:15px;margin-bottom:8px;font-weight:600;">{title}</div>
                    <div style="display:flex;align-items:baseline;gap:12px;">
                        <div style="color:{val_color};font-size:34px;font-weight:800;">{value}</div>
                        <div style="color:{stat_color};font-size:16px;font-weight:700;">{status}</div>
                    </div>
                </div>
                """

            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(get_metric_card("CALL 거래량", f"{int(call_vol):,}", "#00e5a0"), unsafe_allow_html=True)
            with c2: st.markdown(get_metric_card("PUT 거래량",  f"{int(put_vol):,}",  "#ff4d6d"), unsafe_allow_html=True)
            with c3: st.markdown(get_metric_card("Put/Call Ratio", f"{pcr:.2f}", "#f3f4f6", status_text, status_color), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # ── 맥스 페인 계산 ──
            max_pain_price = calculate_max_pain(calls, puts)

            # ── 차트 (거래량 + 맥스 페인 표시) ──
            fig = go.Figure()
            fig.add_trace(go.Bar(x=calls_chart['strike'], y=calls_chart['volume'],   name='Calls', marker_color='#00e5a0'))
            fig.add_trace(go.Bar(x=puts_chart['strike'],  y=-puts_chart['volume'],   name='Puts',  marker_color='#ff4d6d'))
            fig.update_layout(
                title=f"행사가별 거래량 (만기: {selected_expiry})",
                barmode='relative', template="plotly_dark", height=400, hovermode="x unified"
            )
            if current_price > 0:
                fig.add_vline(x=current_price, line_dash="dash", line_color="white",
                              annotation_text=f"현재가 ${current_price:,.2f}", annotation_position="top right")
            if max_pain_price > 0:
                fig.add_vline(x=max_pain_price, line_dash="dot", line_color="#fb923c",
                              annotation_text=f"Max Pain ${max_pain_price:,.0f}", annotation_position="top left")
            st.plotly_chart(fig, use_container_width=True)

            # ── OI 차트 ──
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=calls_chart['strike'], y=calls_chart['openInterest'],  name='Call OI', marker_color='rgba(0,229,160,0.6)'))
            fig_oi.add_trace(go.Bar(x=puts_chart['strike'],  y=-puts_chart['openInterest'],  name='Put OI',  marker_color='rgba(255,77,109,0.6)'))
            fig_oi.update_layout(
                title="행사가별 미결제약정 (Open Interest)",
                barmode='relative', template="plotly_dark", height=360, hovermode="x unified"
            )
            if current_price > 0:
                fig_oi.add_vline(x=current_price, line_dash="dash", line_color="white")
            if max_pain_price > 0:
                fig_oi.add_vline(x=max_pain_price, line_dash="dot", line_color="#fb923c")
            st.plotly_chart(fig_oi, use_container_width=True)

            # ── 이론 적용 신호 패널 ──
            st.markdown("### 🧠 옵션 이론 신호 분석")

            # 1) PCR 신호
            pcr_class = "signal-bull" if pcr < 0.7 else ("signal-bear" if pcr > 1.2 else "signal-neut")
            pcr_msg   = (
                f"<strong>PCR {pcr:.2f} → 과매도 구간</strong> · 역발상적으로 단기 반등 가능성을 염두에 두세요."
                if pcr > 1.2 else (
                f"<strong>PCR {pcr:.2f} → 과매수 구간</strong> · 조정 또는 단기 하락 리스크를 경계하세요."
                if pcr < 0.7 else
                f"<strong>PCR {pcr:.2f} → 중립</strong> · 뚜렷한 쏠림 없음. 다른 지표와 병행하여 판단하세요.")
            )
            st.markdown(f'<div class="signal-box {pcr_class}">① PCR 역발상 신호 &nbsp;·&nbsp; {pcr_msg}</div>', unsafe_allow_html=True)

            # 2) Max Pain 신호
            if max_pain_price > 0 and current_price > 0:
                gap_pct  = (current_price - max_pain_price) / max_pain_price * 100
                mp_class = "signal-bear" if gap_pct > 2 else ("signal-bull" if gap_pct < -2 else "signal-neut")
                mp_msg   = (
                    f"현재가(${current_price:,.2f})가 Max Pain(${max_pain_price:,.0f})보다 <strong>{abs(gap_pct):.1f}% 위</strong> → 하락 수렴 압력"
                    if gap_pct > 2 else (
                    f"현재가(${current_price:,.2f})가 Max Pain(${max_pain_price:,.0f})보다 <strong>{abs(gap_pct):.1f}% 아래</strong> → 상승 수렴 압력"
                    if gap_pct < -2 else
                    f"현재가(${current_price:,.2f})가 Max Pain(${max_pain_price:,.0f}) 근처 → 만기일까지 횡보 가능성")
                )
                st.markdown(f'<div class="signal-box {mp_class}">② Max Pain 수렴 신호 &nbsp;·&nbsp; {mp_msg}</div>', unsafe_allow_html=True)

            # 3) Volume × OI 교차 신호
            voi_cls, voi_msg = vol_oi_signal(call_vol, put_vol, call_oi, put_oi)
            st.markdown(f'<div class="signal-box signal-{voi_cls}">③ Volume × OI 교차 신호 &nbsp;·&nbsp; {voi_msg}</div>', unsafe_allow_html=True)

            # 4) UOA 탐지
            uoa_calls = detect_uoa(calls_chart, "CALL")
            uoa_puts  = detect_uoa(puts_chart,  "PUT")
            uoa_all   = pd.concat([uoa_calls, uoa_puts]).sort_values('V_OI_ratio', ascending=False)
            if not uoa_all.empty:
                st.markdown(f'<div class="signal-box signal-neut">④ UOA 경보 &nbsp;·&nbsp; <strong>V/OI ≥ 5</strong>인 비정상 거래량 행사가 {len(uoa_all)}건 감지됨. 하단 표 참고.</div>', unsafe_allow_html=True)
                uoa_display = uoa_all[['side', 'strike', 'volume', 'openInterest', 'V_OI_ratio', 'lastPrice']].copy()
                uoa_display.columns = ['구분', '행사가', '거래량', 'OI', 'V/OI 비율', '최근가']
                uoa_display['V/OI 비율'] = uoa_display['V/OI 비율'].apply(lambda x: f"{x:.1f}x")
                st.dataframe(uoa_display, use_container_width=True)
            else:
                st.markdown('<div class="signal-box signal-neut">④ UOA 경보 &nbsp;·&nbsp; 비정상 거래량(V/OI ≥ 5) 행사가 없음. 스마트 머니 특이 동향 미감지.</div>', unsafe_allow_html=True)

            # ── AI 프롬프트 생성 ──
            prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 바탕으로 시장 심리를 분석하세요.
[분석 대상] {name} ({ticker_input}) / 만기일: {selected_expiry} / 현재가: ${current_price:,.2f}

[단일 만기일 수급]
- 콜옵션 거래량: {call_vol:,.0f} (OI: {call_oi:,.0f})
- 풋옵션 거래량: {put_vol:,.0f} (OI: {put_oi:,.0f})
- PCR (Volume): {pcr:.2f}
- Max Pain 가격: ${max_pain_price:,.2f}
- 현재가와 Max Pain 괴리율: {((current_price - max_pain_price) / max_pain_price * 100) if max_pain_price else 0:.1f}%
- UOA 감지 건수: {len(uoa_all)}건

[분석 지시사항]
1. PCR 역발상 신호 해석
2. Max Pain 수렴 압력 분석 (만기일까지 남은 기간 고려)
3. Volume × OI 교차 신호로 추세 신뢰도 평가
4. UOA 감지 시 스마트 머니 의도 추론
5. 단기 주가 방향 예측 및 지지/저항선 도출
한글 마크다운으로 요약하세요.
"""

    # ==================================================================
    # 모드 2: 전체 기간 통합 분석
    # ==================================================================
    elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:
        st.info("💡 **단기(30일 이내), 중기(30~90일), 장기(90일 이상)** 만기일 옵션 데이터를 모두 수집하여 입체적으로 분석합니다.")

        with st.spinner("전체 만기일 데이터를 수집 중입니다... (만기일이 많을 경우 10~30초 소요)"):
            today = datetime.today()

            term_data = {
                "Short (단기/30일내)":  {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
                "Mid (중기/30~90일)":   {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
                "Long (장기/90일이상)": {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0}
            }

            progress_bar = st.progress(0)
            total_exps   = len(expirations)

            for i, exp_date in enumerate(expirations):
                try:
                    days_to_exp = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                    if   days_to_exp <= 30: category = "Short (단기/30일내)"
                    elif days_to_exp <= 90: category = "Mid (중기/30~90일)"
                    else:                   category = "Long (장기/90일이상)"

                    opt = ticker.option_chain(exp_date)
                    term_data[category]["call_vol"] += opt.calls['volume'].sum()       if 'volume'       in opt.calls else 0
                    term_data[category]["put_vol"]  += opt.puts['volume'].sum()        if 'volume'       in opt.puts  else 0
                    term_data[category]["call_oi"]  += opt.calls['openInterest'].sum() if 'openInterest' in opt.calls else 0
                    term_data[category]["put_oi"]   += opt.puts['openInterest'].sum()  if 'openInterest' in opt.puts  else 0
                except:
                    pass
                progress_bar.progress((i + 1) / total_exps)

            progress_bar.empty()

            df_terms = pd.DataFrame(term_data).T
            df_terms['PCR (Volume)'] = df_terms['put_vol'] / df_terms['call_vol']
            df_terms['PCR (OI)']     = df_terms['put_oi']  / df_terms['call_oi']
            df_terms.fillna(0, inplace=True)

            # ── 차트 ──
            st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=df_terms.index, y=df_terms['call_vol'], name='CALL 거래량', marker_color='#00e5a0'))
            fig2.add_trace(go.Bar(x=df_terms.index, y=df_terms['put_vol'],  name='PUT 거래량',  marker_color='#ff4d6d'))
            fig2.update_layout(barmode='group', template='plotly_dark', height=400, hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True)

            # PCR Term Structure 차트
            fig_pcr = go.Figure()
            fig_pcr.add_trace(go.Scatter(
                x=df_terms.index, y=df_terms['PCR (Volume)'],
                mode='lines+markers+text', name='PCR(Volume)',
                text=[f"{v:.2f}" for v in df_terms['PCR (Volume)']],
                textposition="top center",
                line=dict(color='#f5a623', width=3),
                marker=dict(size=10)
            ))
            fig_pcr.add_trace(go.Scatter(
                x=df_terms.index, y=df_terms['PCR (OI)'],
                mode='lines+markers+text', name='PCR(OI)',
                text=[f"{v:.2f}" for v in df_terms['PCR (OI)']],
                textposition="bottom center",
                line=dict(color='#a78bfa', width=3, dash='dot'),
                marker=dict(size=10)
            ))
            fig_pcr.add_hline(y=1.2, line_dash="dash", line_color="#ff4d6d", annotation_text="베어리시 경계(1.2)")
            fig_pcr.add_hline(y=0.7, line_dash="dash", line_color="#00e5a0", annotation_text="불리시 경계(0.7)")
            fig_pcr.update_layout(
                title="기간별 Put/Call Ratio (PCR) — Term Structure",
                template='plotly_dark', height=360
            )
            st.plotly_chart(fig_pcr, use_container_width=True)

            # ── 데이터 테이블 ──
            st.markdown("#### 📑 기간별 데이터 요약")
            display_df = df_terms.copy()
            display_df.columns = ['Call 거래량', 'Put 거래량', 'Call 미결제약정', 'Put 미결제약정', 'PCR(거래량)', 'PCR(미결제)']
            for col in ['Call 거래량', 'Put 거래량', 'Call 미결제약정', 'Put 미결제약정']:
                display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}")
            for col in ['PCR(거래량)', 'PCR(미결제)']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")
            st.dataframe(display_df, use_container_width=True)

            # ── 이론 적용 신호 패널 (다중 기간) ──
            st.markdown("### 🧠 Term Structure 이론 신호 분석")

            short = df_terms.loc["Short (단기/30일내)"]
            long_ = df_terms.loc["Long (장기/90일이상)"]
            pcr_short = short['PCR (Volume)']
            pcr_long  = long_['PCR (Volume)']

            # PCR 다이버전스
            divergence = pcr_long - pcr_short
            if abs(divergence) > 0.3:
                div_class = "signal-bull" if divergence < 0 else "signal-bear"
                div_msg   = (
                    f"단기 PCR({pcr_short:.2f}) > 장기 PCR({pcr_long:.2f}) → "
                    f"<strong>단기 공포 / 장기 낙관</strong> · 단기 조정 후 중장기 반등 시나리오"
                    if divergence < 0 else
                    f"단기 PCR({pcr_short:.2f}) < 장기 PCR({pcr_long:.2f}) → "
                    f"<strong>단기 탐욕 / 장기 경계</strong> · 단기 상승 후 중장기 리스크 확대"
                )
            else:
                div_class = "signal-neut"
                div_msg   = f"단기·장기 PCR 차이({abs(divergence):.2f}) 미미 → 기간별 심리 유사, 뚜렷한 다이버전스 없음"

            st.markdown(f'<div class="signal-box {div_class}">① PCR 기간별 다이버전스 &nbsp;·&nbsp; {div_msg}</div>', unsafe_allow_html=True)

            # 단기 Volume × OI
            voi_cls, voi_msg = vol_oi_signal(short['call_vol'], short['put_vol'], short['call_oi'], short['put_oi'])
            st.markdown(f'<div class="signal-box signal-{voi_cls}">② 단기 Volume × OI 신호 &nbsp;·&nbsp; {voi_msg}</div>', unsafe_allow_html=True)

            # 장기 Volume × OI
            voi_cls_l, voi_msg_l = vol_oi_signal(long_['call_vol'], long_['put_vol'], long_['call_oi'], long_['put_oi'])
            st.markdown(f'<div class="signal-box signal-{voi_cls_l}">③ 장기 Volume × OI 신호 &nbsp;·&nbsp; {voi_msg_l}</div>', unsafe_allow_html=True)

            # ── AI 프롬프트 ──
            prompt = f"""
당신은 월스트리트의 시니어 파생상품 애널리스트입니다. 제공된 '{name} ({ticker_input})'의
[기간별(Term Structure) 옵션 수급 데이터]를 바탕으로 단기·중기·장기 시나리오를 입체적으로 분석하세요.

[분석 대상]
- 티커: {ticker_input} ({name})
- 현재가: ${current_price:,.2f}

[기간별 수급 데이터 (Volume & Open Interest)]
1. 단기 (30일 이내):
   - 콜 거래량: {df_terms.loc['Short (단기/30일내)']['call_vol']:,.0f} / 콜 OI: {df_terms.loc['Short (단기/30일내)']['call_oi']:,.0f}
   - 풋 거래량: {df_terms.loc['Short (단기/30일내)']['put_vol']:,.0f} / 풋 OI: {df_terms.loc['Short (단기/30일내)']['put_oi']:,.0f}
   - PCR(Volume): {df_terms.loc['Short (단기/30일내)']['PCR (Volume)']:.2f} / PCR(OI): {df_terms.loc['Short (단기/30일내)']['PCR (OI)']:.2f}

2. 중기 (30일 ~ 90일):
   - 콜 거래량: {df_terms.loc['Mid (중기/30~90일)']['call_vol']:,.0f} / 콜 OI: {df_terms.loc['Mid (중기/30~90일)']['call_oi']:,.0f}
   - 풋 거래량: {df_terms.loc['Mid (중기/30~90일)']['put_vol']:,.0f} / 풋 OI: {df_terms.loc['Mid (중기/30~90일)']['put_oi']:,.0f}
   - PCR(Volume): {df_terms.loc['Mid (중기/30~90일)']['PCR (Volume)']:.2f} / PCR(OI): {df_terms.loc['Mid (중기/30~90일)']['PCR (OI)']:.2f}

3. 장기 (90일 이상):
   - 콜 거래량: {df_terms.loc['Long (장기/90일이상)']['call_vol']:,.0f} / 콜 OI: {df_terms.loc['Long (장기/90일이상)']['call_oi']:,.0f}
   - 풋 거래량: {df_terms.loc['Long (장기/90일이상)']['put_vol']:,.0f} / 풋 OI: {df_terms.loc['Long (장기/90일이상)']['put_oi']:,.0f}
   - PCR(Volume): {df_terms.loc['Long (장기/90일이상)']['PCR (Volume)']:.2f} / PCR(OI): {df_terms.loc['Long (장기/90일이상)']['PCR (OI)']:.2f}

[분석 지시사항]
1. **기간별 심리 변화(Term Structure):** 단기 트레이더와 중장기 투자자의 포지션 온도 차이를 비교하세요.
2. **다이버전스 캐치:** 단기 PCR과 장기 PCR이 크게 다르다면, 그 의미(단기 조정 후 장기 상승 or 반대)를 통찰력 있게 설명하세요.
3. **Volume × OI 교차 신호:** 각 기간의 거래량과 OI를 결합하여 추세의 신뢰도를 평가하세요.
4. **종합 결론:** 향후 1~3개월 주가 방향성 시나리오를 도출하세요.
초보자도 이해할 수 있도록 친절한 한글 마크다운으로 정리하세요.
"""

    # ==================================================================
    # 공통 AI 분석 섹션
    # ==================================================================
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
                width:100%;box-shadow:0 4px 6px rgba(0,0,0,0.1);transition:0.2s;">
                📋 프롬프트 복사 & Gemini 웹 열기
            </button>
            <script>
            function copyAndOpen() {{
                const text = {safe_prompt};
                navigator.clipboard.writeText(text).then(function() {{
                    window.open("https://gemini.google.com/", "_blank");
                }}).catch(function() {{
                    const ta = document.createElement("textarea");
                    ta.value = text;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    ta.remove();
                    window.open("https://gemini.google.com/", "_blank");
                }});
            }}
            </script>
            """
            components.html(html_code, height=60)

        with st.expander("생성된 고도화 분석 프롬프트 내용 확인하기", expanded=False):
            st.code(prompt, language="text")

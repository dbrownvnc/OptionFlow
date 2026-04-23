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

# =============================================================================
# 페이지 설정
# =============================================================================
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")
st.markdown("""
    <style>
    .big-font { font-size:40px !important; font-weight: bold; color: #00e5a0;
                text-shadow: 0 0 20px rgba(0,229,160,0.2); }
    .subtitle  { font-size:16px; color: #a0a0a0; margin-bottom: 25px; font-family: monospace; }
    .report-box{ background-color: #1e293b; padding: 25px; border-radius: 12px;
                 border-left: 5px solid #00e5a0; color: #f3f4f6; line-height: 1.6; }
    .warn-box  { background-color: #2d1a00; padding: 10px 15px; border-radius: 8px;
                 border-left: 4px solid #f5a623; color: #fbbf24; font-size: 13px; margin-bottom: 8px; }
    .info-box  { background-color: #0f2235; padding: 10px 15px; border-radius: 8px;
                 border-left: 4px solid #3b82f6; color: #93c5fd; font-size: 13px; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (단/중/장기 통합 지원)</p>', unsafe_allow_html=True)


# =============================================================================
# ① 핵심 유틸리티 함수
# =============================================================================

def safe_float(val, default=0.0):
    """None / NaN / 변환 실패 → default 반환"""
    try:
        v = float(val)
        return default if (np.isnan(v) or np.isinf(v)) else v
    except Exception:
        return default


def safe_int(val, default=0):
    try:
        return int(float(val))
    except Exception:
        return default


def safe_pcr(put_val, call_val):
    """0 나누기 방지 PCR"""
    try:
        c = float(call_val)
        return round(float(put_val) / c, 3) if c > 0 else 0.0
    except Exception:
        return 0.0


def clean_option_df(df):
    """옵션 체인 DataFrame NaN 정규화"""
    numeric_cols = ['volume', 'openInterest', 'bid', 'ask', 'lastPrice',
                    'impliedVolatility', 'strike']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df


# ── 방향성 추론 ────────────────────────────────────────────────────────────
def infer_direction(row):
    """
    Bid/Ask 대비 체결가(lastPrice)로 공격적 매수/매도 추론.
    - lastPrice ≥ ask×0.97  →  공격적 BUY  (Ask 쪽 체결)
    - lastPrice ≤ bid×1.03  →  공격적 SELL (Bid 쪽 체결)
    - spread > mid×50%      →  ILLIQUID    (신뢰 불가)
    반환: (direction_str, emoji)
    """
    try:
        bid  = safe_float(row.get('bid', 0))
        ask  = safe_float(row.get('ask', 0))
        last = safe_float(row.get('lastPrice', 0))

        if bid <= 0 or ask <= 0 or last <= 0:
            return 'ILLIQUID', '⚫'

        mid    = (bid + ask) / 2
        spread = ask - bid

        # 스프레드가 중간값의 50% 초과 → 비유동성
        if mid > 0 and (spread / mid) > 0.50:
            return 'ILLIQUID', '⚫'

        if last >= ask * 0.97:
            return 'BUY',     '🟢'
        elif last <= bid * 1.03:
            return 'SELL',    '🔴'
        else:
            return 'NEUTRAL', '🟡'
    except Exception:
        return 'ILLIQUID', '⚫'


# ── 프리미엄 계산 ──────────────────────────────────────────────────────────
def calc_mid_premium(row):
    """
    Bid/Ask 중간값 기반 프리미엄 계산.
    Bid/Ask 없으면 lastPrice 폴백 (품질 태그 'STALE' 반환).
    반환: (premium_dollars, quality_tag)
    """
    try:
        bid  = safe_float(row.get('bid',       0))
        ask  = safe_float(row.get('ask',       0))
        last = safe_float(row.get('lastPrice', 0))
        vol  = safe_int(row.get('volume',      0))

        if vol <= 0:
            return 0, 'NO_VOL'

        if bid > 0 and ask > 0:
            price   = (bid + ask) / 2
            quality = 'MID'
        elif last > 0:
            price   = last
            quality = 'STALE'   # 체결가가 오래됐을 수 있음
        else:
            return 0, 'NO_DATA'

        return round(price * vol * 100), quality
    except Exception:
        return 0, 'ERROR'


# ── IV 품질 필터링 ─────────────────────────────────────────────────────────
def get_volume_weighted_iv(df):
    """
    이상치 제거 후 거래량 가중 평균 IV 계산.
    필터: 0.01 < IV < 5.0,  volume > 0,  bid > 0  (유동성 확보)
    반환: (iv_percent or None, valid_count)
    """
    try:
        required = {'impliedVolatility', 'volume', 'bid'}
        if not required.issubset(df.columns):
            return None, 0

        iv  = df['impliedVolatility'].fillna(0).astype(float)
        vol = df['volume'].fillna(0).astype(float)
        bid = df['bid'].fillna(0).astype(float)

        mask = (iv > 0.01) & (iv < 5.0) & (vol > 0) & (bid > 0)
        if mask.sum() == 0 or vol[mask].sum() == 0:
            return None, 0

        vw_iv = (iv[mask] * vol[mask]).sum() / vol[mask].sum()
        return round(float(vw_iv) * 100, 2), int(mask.sum())
    except Exception:
        return None, 0


# ── Smart Money Flow 테이블 ────────────────────────────────────────────────
def build_flow_df(df, option_type):
    """
    방향성 추론 + 프리미엄 계산으로 Smart Flow 테이블 생성.
    필터: 거래량 ≥ 100, 방향 ≠ ILLIQUID, 프리미엄 > 0
    """
    rows = []
    for _, row in df.iterrows():
        try:
            vol = safe_int(row.get('volume', 0))
            if vol < 100:
                continue

            direction, emoji = infer_direction(row)
            if direction == 'ILLIQUID':
                continue

            premium, quality = calc_mid_premium(row)
            if premium <= 0:
                continue

            iv_raw = safe_float(row.get('impliedVolatility', 0))
            iv_pct = round(iv_raw * 100, 1) if 0.01 < iv_raw < 5.0 else None

            oi          = safe_int(row.get('openInterest', 0))
            vol_oi      = round(vol / oi, 2) if oi > 0 else None
            strike      = safe_float(row.get('strike', 0))
            bid_v       = round(safe_float(row.get('bid', 0)), 2)
            ask_v       = round(safe_float(row.get('ask', 0)), 2)
            last_v      = round(safe_float(row.get('lastPrice', 0)), 2)

            rows.append({
                '방향':         emoji,
                '_direction':   direction,    # 필터용 (표시 안 함)
                '종류':         option_type,
                '행사가':        strike,
                '거래량':        vol,
                'OI(전일기준)':  oi,
                'Vol/OI':       vol_oi,
                '프리미엄($)':   premium,
                'IV(%)':        iv_pct,
                '가격기준':      quality,
                'Bid':          bid_v,
                'Ask':          ask_v,
                '체결가':        last_v,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df_out = pd.DataFrame(rows).sort_values('프리미엄($)', ascending=False).reset_index(drop=True)
    return df_out


def format_flow_display(df):
    """표시용 DataFrame 포맷 (숫자 포맷팅)"""
    if df.empty:
        return df
    display_cols = ['방향', '종류', '행사가', '거래량', 'OI(전일기준)',
                    'Vol/OI', '프리미엄($)', 'IV(%)', '가격기준', 'Bid', 'Ask', '체결가']
    d = df[[c for c in display_cols if c in df.columns]].copy()
    if '프리미엄($)' in d.columns:
        d['프리미엄($)'] = d['프리미엄($)'].apply(lambda x: f"${x:,.0f}")
    if '거래량' in d.columns:
        d['거래량'] = d['거래량'].apply(lambda x: f"{x:,}")
    if 'OI(전일기준)' in d.columns:
        d['OI(전일기준)'] = d['OI(전일기준)'].apply(lambda x: f"{x:,}")
    return d


# ── UI 컴포넌트 ────────────────────────────────────────────────────────────
def metric_card(title, value, val_color, status="", stat_color="transparent"):
    return f"""
    <div style="background-color:#111827;padding:20px;border-radius:12px;
                border:1px solid #1f2937;box-shadow:0 4px 6px rgba(0,0,0,.2);height:100%;">
      <div style="color:#9ca3af;font-size:15px;margin-bottom:8px;font-weight:600;">{title}</div>
      <div style="display:flex;align-items:baseline;gap:12px;">
        <div style="color:{val_color};font-size:32px;font-weight:800;">{value}</div>
        <div style="color:{stat_color};font-size:14px;font-weight:700;">{status}</div>
      </div>
    </div>"""


def warn_box(html):
    st.markdown(f'<div class="warn-box">{html}</div>', unsafe_allow_html=True)


def info_box(html):
    st.markdown(f'<div class="info-box">{html}</div>', unsafe_allow_html=True)


# =============================================================================
# ② Gemini API
# =============================================================================
def generate_with_fallback(prompt, api_key):
    genai.configure(api_key=api_key)
    models = [
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ]
    errors = []
    for m in models:
        try:
            resp = genai.GenerativeModel(m).generate_content(prompt)
            return resp.text, m
        except Exception as e:
            errors.append(f"[{m}: {str(e)[:80]}]")
            time.sleep(0.5)
    raise Exception("모든 모델 호출 실패: " + " | ".join(errors))


api_key     = st.secrets.get("GEMINI_API_KEY")
has_api_key = api_key is not None
if not has_api_key:
    st.sidebar.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY' 미설정")


# =============================================================================
# ③ 사이드바
# =============================================================================
with st.sidebar:
    st.header("🔍 검색 설정")
    ticker_input = st.text_input("티커 심볼 (예: AAPL, NVDA, SPY)", value="AAPL").upper().strip()
    analysis_mode = st.radio(
        "분석 모드 선택",
        ["단일 만기일 분석", "전체 기간 통합 분석 (단/중/장기)"]
    )

    ticker      = yf.Ticker(ticker_input)
    expirations = []
    try:
        raw = ticker.options
        expirations = list(raw) if raw else []
        if not expirations:
            st.error("옵션 데이터 없음 (상장 옵션이 없는 티커)")
    except Exception as e:
        st.error(f"서버 연결 오류: {str(e)[:100]}")

    selected_expiry = None
    if expirations and analysis_mode == "단일 만기일 분석":
        selected_expiry = st.selectbox("만기일 선택", expirations)


# =============================================================================
# ④ 현재가 수집
# =============================================================================
current_price = 0.0
name          = ticker_input

if ticker_input and expirations:
    try:
        info          = ticker.info or {}
        current_price = safe_float(
            info.get('currentPrice') or info.get('regularMarketPrice')
        )
        if current_price <= 0:
            hist = ticker.history(period="2d")
            if not hist.empty:
                current_price = safe_float(hist['Close'].iloc[-1])
        name = info.get('longName', ticker_input)
    except Exception as e:
        st.warning(f"현재가 조회 실패: {str(e)[:100]}")

    st.subheader(f"📊 {name} ({ticker_input}) | 현재가: ${current_price:,.2f}")


# =============================================================================
# ⑤ 모드 1: 단일 만기일 분석 (Enhanced)
# =============================================================================
prompt = ""

if analysis_mode == "단일 만기일 분석" and selected_expiry and expirations:

    with st.spinner(f"'{selected_expiry}' 만기 옵션 체인 수집 중..."):
        try:
            chain = ticker.option_chain(selected_expiry)
            calls = clean_option_df(chain.calls.copy())
            puts  = clean_option_df(chain.puts.copy())
        except Exception as e:
            st.error(f"옵션 체인 수집 실패: {e}")
            st.stop()

    # ── 기본 지표 ────────────────────────────────────────────────────────
    call_vol = float(calls['volume'].sum())
    put_vol  = float(puts['volume'].sum())
    call_oi  = float(calls['openInterest'].sum())
    put_oi   = float(puts['openInterest'].sum())
    pcr_vol  = safe_pcr(put_vol,  call_vol)
    pcr_oi   = safe_pcr(put_oi,   call_oi)

    # IV 가중 평균 (거래량 가중, 이상치 제거)
    call_iv, call_iv_n = get_volume_weighted_iv(calls)
    put_iv,  put_iv_n  = get_volume_weighted_iv(puts)

    # PCR 기반 신호
    if pcr_vol > 1.2:
        sig_color, sig_text = "#ff4d6d", "하락 신호 (Bearish)"
    elif pcr_vol < 0.7:
        sig_color, sig_text = "#00e5a0", "상승 신호 (Bullish)"
    else:
        sig_color, sig_text = "#f5a623", "중립 (Neutral)"

    # ── 메트릭 카드 (4개) ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("CALL 거래량", f"{int(call_vol):,}", "#00e5a0"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("PUT 거래량",  f"{int(put_vol):,}", "#ff4d6d"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("PCR (거래량)", f"{pcr_vol:.2f}",
                                "#f3f4f6", sig_text, sig_color),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("PCR (OI) ⚠️전일기준", f"{pcr_oi:.2f}",
                                "#9ca3af", "", "transparent"),
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── OI 경고 ──────────────────────────────────────────────────────────
    warn_box(
        "⚠️ <b>OI(미결제약정)는 전일 장 마감 기준</b>입니다. "
        "장중 Volume과 직접 비교하면 오류가 발생합니다. "
        "장중에는 <b>PCR(거래량)</b> 위주로 참고하세요."
    )

    # ── IV 가중 평균 ──────────────────────────────────────────────────────
    iv_col1, iv_col2 = st.columns(2)
    with iv_col1:
        if call_iv is not None:
            st.metric(
                f"콜 IV 거래량 가중평균 ({call_iv_n}개 유동성 행사가)",
                f"{call_iv:.1f}%"
            )
        else:
            st.metric("콜 IV 가중평균", "산출 불가 (유동성 부족)")
    with iv_col2:
        if put_iv is not None:
            st.metric(
                f"풋 IV 거래량 가중평균 ({put_iv_n}개 유동성 행사가)",
                f"{put_iv:.1f}%"
            )
        else:
            st.metric("풋 IV 가중평균", "산출 불가 (유동성 부족)")

    info_box(
        "ℹ️ <b>IV 필터:</b> 0.01 < IV < 500%, 거래량 > 0, Bid > 0 조건을 모두 충족한 "
        "행사가만 포함합니다. 비유동성 Deep OTM/ITM의 이상치(0% 또는 1000%)는 자동 제외됩니다."
    )

    # ── 거래량 차트 (현재가 ±30% 범위) ──────────────────────────────────
    if current_price > 0:
        min_s, max_s   = current_price * 0.70, current_price * 1.30
        calls_c = calls[(calls['strike'] >= min_s) & (calls['strike'] <= max_s)]
        puts_c  = puts[(puts['strike']  >= min_s) & (puts['strike']  <= max_s)]
    else:
        calls_c, puts_c = calls, puts

    fig = go.Figure()
    fig.add_trace(go.Bar(x=calls_c['strike'], y=calls_c['volume'],
                         name='Calls', marker_color='#00e5a0'))
    fig.add_trace(go.Bar(x=puts_c['strike'],  y=-puts_c['volume'],
                         name='Puts',  marker_color='#ff4d6d'))
    if current_price > 0:
        fig.add_vline(x=current_price, line_dash="dash", line_color="white",
                      annotation_text=f"현재가 ${current_price:.2f}",
                      annotation_position="top left")
    fig.update_layout(
        title=f"행사가별 거래량 (만기: {selected_expiry})",
        barmode='relative', template="plotly_dark",
        height=400, hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── IV Skew 차트 (유동성 필터 적용) ──────────────────────────────────
    st.markdown("#### 📉 IV Skew (유동성 필터 적용)")

    def get_iv_skew(df_opt):
        """유동성 있는 행사가만 추출하여 IV Skew 데이터 반환"""
        iv  = df_opt['impliedVolatility'].astype(float)
        vol = df_opt['volume'].fillna(0).astype(float)
        bid = df_opt['bid'].fillna(0).astype(float)
        mask = (iv > 0.01) & (iv < 5.0) & (vol > 0) & (bid > 0)
        filtered = df_opt[mask].copy()
        if filtered.empty:
            return None
        filtered = filtered.sort_values('strike')
        filtered['iv_pct'] = filtered['impliedVolatility'] * 100
        return filtered

    if current_price > 0:
        call_skew = get_iv_skew(calls_c)
        put_skew  = get_iv_skew(puts_c)

        if call_skew is not None or put_skew is not None:
            fig_iv = go.Figure()
            if call_skew is not None:
                fig_iv.add_trace(go.Scatter(
                    x=call_skew['strike'], y=call_skew['iv_pct'],
                    mode='lines+markers', name='Call IV',
                    line=dict(color='#00e5a0', width=2),
                    hovertemplate='행사가: $%{x}<br>IV: %{y:.1f}%<extra></extra>'
                ))
            if put_skew is not None:
                fig_iv.add_trace(go.Scatter(
                    x=put_skew['strike'], y=put_skew['iv_pct'],
                    mode='lines+markers', name='Put IV',
                    line=dict(color='#ff4d6d', width=2),
                    hovertemplate='행사가: $%{x}<br>IV: %{y:.1f}%<extra></extra>'
                ))
            fig_iv.add_vline(x=current_price, line_dash="dash", line_color="white")
            fig_iv.update_layout(
                title="IV Skew (비유동성 이상치 제거 후)",
                template="plotly_dark", height=350,
                xaxis_title="행사가", yaxis_title="내재변동성 (%)"
            )
            st.plotly_chart(fig_iv, use_container_width=True)
        else:
            st.info("IV Skew 차트를 그릴 유동성 데이터가 없습니다.")

    # ── Smart Money Flow ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🕵️ Smart Money Flow  (Bid/Ask 방향성 추론)")

    warn_box(
        "⚠️ <b>방법론 한계:</b> 이 방향성 추론은 EOD(일 마감) 데이터 기반으로, "
        "실시간 체결 테이프(FlowAlgo 등)와 다릅니다. "
        "거래량 ≥ 100 & Bid/Ask 스프레드 < 중간값의 50% 조건을 충족한 옵션만 표시합니다. "
        "<b>투자 참고용으로만 사용하세요.</b>"
    )
    st.markdown("<br>", unsafe_allow_html=True)

    call_flow = build_flow_df(calls, 'CALL')
    put_flow  = build_flow_df(puts,  'PUT')
    all_flow  = pd.concat([call_flow, put_flow], ignore_index=True)

    if not all_flow.empty:
        all_flow = all_flow.sort_values('프리미엄($)', ascending=False).reset_index(drop=True)

        tab_all, tab_buy, tab_sell, tab_neutral = st.tabs([
            "전체 플로우", "🟢 공격적 BUY", "🔴 공격적 SELL", "🟡 중립"
        ])

        with tab_all:
            st.caption(f"상위 20건 표시 (전체 {len(all_flow)}건)")
            st.dataframe(format_flow_display(all_flow.head(20)),
                         use_container_width=True, hide_index=True)

        with tab_buy:
            buy_df = all_flow[all_flow['_direction'] == 'BUY']
            if buy_df.empty:
                st.info("공격적 BUY 신호가 없습니다. (Ask 근처 체결 없음)")
            else:
                st.caption(f"Ask 근처 체결 옵션 {len(buy_df)}건")
                st.dataframe(format_flow_display(buy_df.head(15)),
                             use_container_width=True, hide_index=True)

        with tab_sell:
            sell_df = all_flow[all_flow['_direction'] == 'SELL']
            if sell_df.empty:
                st.info("공격적 SELL 신호가 없습니다. (Bid 근처 체결 없음)")
            else:
                st.caption(f"Bid 근처 체결 옵션 {len(sell_df)}건")
                st.dataframe(format_flow_display(sell_df.head(15)),
                             use_container_width=True, hide_index=True)

        with tab_neutral:
            neu_df = all_flow[all_flow['_direction'] == 'NEUTRAL']
            if neu_df.empty:
                st.info("중립 체결 옵션이 없습니다.")
            else:
                st.dataframe(format_flow_display(neu_df.head(15)),
                             use_container_width=True, hide_index=True)

        # 방향성 집계 요약
        st.markdown("##### 📊 방향성 집계 요약")
        dir_summary = (
            all_flow.groupby('_direction', sort=False)
            .agg(건수=('프리미엄($)', 'count'), 총프리미엄=('프리미엄($)', 'sum'))
            .reset_index()
            .rename(columns={'_direction': '방향'})
        )
        dir_summary['총프리미엄'] = dir_summary['총프리미엄'].apply(lambda x: f"${x:,.0f}")
        dir_summary = dir_summary.sort_values('건수', ascending=False)
        st.dataframe(dir_summary, use_container_width=True, hide_index=True)

        # AI 프롬프트용 상위 플로우 요약
        def flow_summary_text(df, direction, n=5):
            sub = df[df['_direction'] == direction].head(n)
            if sub.empty:
                return "  없음"
            lines = []
            for _, r in sub.iterrows():
                lines.append(
                    f"  {r['종류']} {r['행사가']} | 거래량 {r['거래량']:,} | "
                    f"프리미엄 ${r['프리미엄($)']:,} | IV {r['IV(%)']}%"
                )
            return "\n".join(lines)

        buy_text  = flow_summary_text(all_flow, 'BUY')
        sell_text = flow_summary_text(all_flow, 'SELL')

    else:
        st.info(
            "방향성 추론 가능한 옵션이 없습니다. "
            "(거래량 < 100 이거나 Bid/Ask 데이터 부재)"
        )
        buy_text  = "데이터 없음"
        sell_text = "데이터 없음"

    # ── 프롬프트 생성 ──────────────────────────────────────────────────────
    iv_line = (
        f"콜 IV(거래량가중): {call_iv:.1f}%,  풋 IV(거래량가중): {put_iv:.1f}%"
        if call_iv and put_iv else "IV 데이터 부족"
    )
    prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 분석하세요.

[분석 대상]
- 티커: {name} ({ticker_input}) | 만기: {selected_expiry} | 현재가: ${current_price:,.2f}

[수급 지표]
- 콜 거래량: {int(call_vol):,}  /  풋 거래량: {int(put_vol):,}
- PCR(거래량): {pcr_vol:.2f} → {sig_text}
- PCR(OI, ※전일기준): {pcr_oi:.2f}  ← 장중 참고 불가
- {iv_line}

[Smart Money 방향성 (Bid/Ask 추론, EOD 기반 참고용)]
▶ 공격적 BUY 상위 5건:
{buy_text}

▶ 공격적 SELL 상위 5건:
{sell_text}

[분석 지시사항]
1. PCR(거래량)과 Smart Money 방향성을 종합하여 단기 주가 방향을 예측하세요.
2. BUY/SELL이 집중된 행사가를 근거로 주요 지지/저항선을 도출하세요.
3. EOD 데이터 한계를 감안한 신중한 톤을 유지하세요.
4. 한글 마크다운으로 간결하게 정리하세요.
"""


# =============================================================================
# ⑥ 모드 2: 전체 기간 통합 분석 (Enhanced)
# =============================================================================
elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:

    st.info("💡 **단기(30일 이내), 중기(30~90일), 장기(90일 이상)** 만기일을 통합 분석합니다.")
    warn_box(
        "⚠️ <b>OI(미결제약정)는 전일 장 마감 기준</b>입니다. "
        "모든 PCR(OI) 수치는 참고용이며, 장중에는 PCR(거래량) 우선 사용을 권장합니다."
    )
    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner("전체 만기일 데이터 수집 중... (10~30초 소요)"):
        today = datetime.today()

        term_data = {
            "Short (단기/30일내)":   {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
            "Mid (중기/30~90일)":    {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
            "Long (장기/90일이상)":  {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
        }

        def safe_col_sum(df_opt, col):
            if df_opt is None or col not in df_opt.columns:
                return 0.0
            return float(pd.to_numeric(df_opt[col], errors='coerce').fillna(0).sum())

        progress_bar  = st.progress(0)
        status_holder = st.empty()
        total_exps    = len(expirations)
        error_count   = 0

        for i, exp_date in enumerate(expirations):
            cat = None
            try:
                days = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                if days <= 0:
                    continue  # 이미 만료된 만기일 스킵

                if   days <= 30:  cat = "Short (단기/30일내)"
                elif days <= 90:  cat = "Mid (중기/30~90일)"
                else:             cat = "Long (장기/90일이상)"

                status_holder.text(f"수집 중: {exp_date}  ({i+1}/{total_exps})")
                opt = ticker.option_chain(exp_date)

                term_data[cat]["call_vol"] += safe_col_sum(opt.calls, 'volume')
                term_data[cat]["put_vol"]  += safe_col_sum(opt.puts,  'volume')
                term_data[cat]["call_oi"]  += safe_col_sum(opt.calls, 'openInterest')
                term_data[cat]["put_oi"]   += safe_col_sum(opt.puts,  'openInterest')

            except Exception:
                error_count += 1
            finally:
                progress_bar.progress((i + 1) / total_exps)

        progress_bar.empty()
        status_holder.empty()

        if error_count > 0:
            warn_box(
                f"⚠️ {error_count}개 만기일 데이터 수집 실패 (네트워크 오류 등). "
                "나머지 데이터로 분석합니다."
            )

    # 데이터프레임 변환
    df_terms = pd.DataFrame(term_data).T
    df_terms['PCR (Volume)'] = df_terms.apply(
        lambda r: safe_pcr(r['put_vol'], r['call_vol']), axis=1)
    df_terms['PCR (OI)'] = df_terms.apply(
        lambda r: safe_pcr(r['put_oi'], r['call_oi']), axis=1)

    # 유효 데이터만 표시 (call_vol + put_vol > 0)
    valid = df_terms[(df_terms['call_vol'] + df_terms['put_vol']) > 0]

    if valid.empty:
        st.error("수집된 유효 데이터가 없습니다. 티커를 확인하거나 잠시 후 재시도하세요.")
        st.stop()

    # 차트
    st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=valid.index, y=valid['call_vol'],
                          name='CALL 거래량', marker_color='#00e5a0'))
    fig2.add_trace(go.Bar(x=valid.index, y=valid['put_vol'],
                          name='PUT 거래량',  marker_color='#ff4d6d'))
    fig2.update_layout(
        barmode='group', template='plotly_dark', height=400, hovermode="x unified"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 요약 테이블
    st.markdown("#### 📑 기간별 데이터 요약")
    st.caption("⚠️ OI 컬럼은 전일 기준. PCR(거래량) 위주 해석 권장.")
    disp = valid[['call_vol', 'put_vol', 'call_oi', 'put_oi',
                  'PCR (Volume)', 'PCR (OI)']].copy()
    disp.columns = ['Call 거래량', 'Put 거래량',
                    'Call OI(전일⚠️)', 'Put OI(전일⚠️)',
                    'PCR(거래량)', 'PCR(OI⚠️)']
    for col in ['Call 거래량', 'Put 거래량', 'Call OI(전일⚠️)', 'Put OI(전일⚠️)']:
        disp[col] = disp[col].apply(lambda x: f"{int(x):,}")
    for col in ['PCR(거래량)', 'PCR(OI⚠️)']:
        disp[col] = disp[col].apply(lambda x: f"{x:.2f}")
    st.dataframe(disp, use_container_width=True)

    # 프롬프트 생성
    rows_text = []
    for term_name in valid.index:
        r = valid.loc[term_name]
        rows_text.append(
            f"\n{term_name}:\n"
            f"  콜 거래량: {int(r['call_vol']):,}  /  풋 거래량: {int(r['put_vol']):,}\n"
            f"  PCR(거래량): {r['PCR (Volume)']:.2f}  |  PCR(OI/전일기준): {r['PCR (OI)']:.2f}"
        )

    prompt = f"""
당신은 월스트리트 시니어 파생상품 애널리스트입니다.

[분석 대상]
- 티커: {ticker_input} ({name}) | 현재가: ${current_price:,.2f}

[기간별 옵션 Term Structure]
{''.join(rows_text)}

※ OI는 전일 기준이므로 PCR(거래량) 위주로 분석하세요.

[분석 지시사항]
1. 단기/중기/장기 PCR(거래량) 변화로 시장 심리 Term Structure를 분석하세요.
2. 기간 간 다이버전스(단기 Bearish + 장기 Bullish 등)가 있다면 그 함의를 해석하세요.
3. 향후 1~3개월 주가 방향성 시나리오를 도출하세요.
4. 초보자도 이해할 수 있도록 한글 마크다운으로 작성하세요.
"""


# =============================================================================
# ⑦ 공통 AI 분석 섹션
# =============================================================================
can_run_ai = (
    ticker_input and expirations and prompt and (
        (analysis_mode == "단일 만기일 분석" and selected_expiry) or
        (analysis_mode != "단일 만기일 분석")
    )
)

if can_run_ai:
    st.divider()
    st.subheader("🤖 Gemini AI 옵션 시장 브리핑")

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        st.markdown("#### 옵션 1. 스트림릿에서 바로 분석")
        if st.button("✨ API 자동 분석 실행", type="primary", use_container_width=True):
            if has_api_key:
                with st.spinner("AI 분석 중..."):
                    try:
                        result, used_model = generate_with_fallback(prompt, api_key)
                        st.success(f"분석 완료! (모델: {used_model})")
                        st.markdown(f'<div class="report-box">{result}</div>',
                                    unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"분석 오류: {e}")
            else:
                st.error("Gemini API 키가 설정되지 않았습니다.")

    with col_btn2:
        st.markdown("#### 옵션 2. 무료 한도 초과 시 대안")
        safe_prompt = json.dumps(prompt)
        html_code = f"""
        <button onclick="copyAndOpen()"
          style="background-color:#f5a623;color:#000;padding:12px 20px;
                 border:none;border-radius:8px;font-weight:bold;font-size:15px;
                 cursor:pointer;width:100%;box-shadow:0 4px 6px rgba(0,0,0,.1);">
          📋 프롬프트 복사 &amp; Gemini 웹 열기
        </button>
        <script>
        function copyAndOpen() {{
            const text = {safe_prompt};
            navigator.clipboard.writeText(text)
              .then(() => window.open("https://gemini.google.com/","_blank"))
              .catch(() => {{
                  const ta = document.createElement("textarea");
                  ta.value = text; document.body.appendChild(ta);
                  ta.select(); document.execCommand("copy"); ta.remove();
                  window.open("https://gemini.google.com/","_blank");
              }});
        }}
        </script>
        """
        components.html(html_code, height=60)

    with st.expander("생성된 분석 프롬프트 확인", expanded=False):
        st.code(prompt, language="text")

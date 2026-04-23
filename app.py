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
    .big-font  { font-size:40px !important; font-weight:bold; color:#00e5a0;
                 text-shadow:0 0 20px rgba(0,229,160,.2); }
    .subtitle  { font-size:16px; color:#a0a0a0; margin-bottom:25px; font-family:monospace; }
    .report-box{ background:#1e293b; padding:25px; border-radius:12px;
                 border-left:5px solid #00e5a0; color:#f3f4f6; line-height:1.6; }
    .warn-box  { background:#2d1a00; padding:10px 15px; border-radius:8px;
                 border-left:4px solid #f5a623; color:#fbbf24; font-size:13px; margin-bottom:8px; }
    .info-box  { background:#0f2235; padding:10px 15px; border-radius:8px;
                 border-left:4px solid #3b82f6; color:#93c5fd; font-size:13px; margin-bottom:8px; }
    .dte-box   { background:#1a0a2d; padding:10px 15px; border-radius:8px;
                 border-left:4px solid #a855f7; color:#d8b4fe; font-size:13px; margin-bottom:8px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (단/중/장기 통합 지원)</p>',
            unsafe_allow_html=True)


# =============================================================================
# ① 핵심 유틸리티
# =============================================================================

def safe_float(val, default=0.0):
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
    try:
        c = float(call_val)
        return round(float(put_val) / c, 3) if c > 0 else 0.0
    except Exception:
        return 0.0

def clean_option_df(df):
    for col in ['volume','openInterest','bid','ask','lastPrice','impliedVolatility','strike']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

def days_to_expiry(exp_date_str):
    try:
        return (datetime.strptime(exp_date_str, "%Y-%m-%d") - datetime.today()).days
    except Exception:
        return -1


# ── 유동성 판별 ───────────────────────────────────────────────────────────────
# 문제의 원인:
#   근만기(0~2DTE) OTM 옵션은 시장조성자가 Bid를 제시하지 않는 경우가 정상.
#   기존 'bid > 0' 필터가 이를 모두 제거해서 IV/SmartFlow 데이터가 비어버림.
#   → bid=0이어도 ask > 0 AND lastPrice > 0이면 여전히 거래 중인 옵션으로 허용.
# ------------------------------------------------------------------------------
def is_liquid(bid, ask, last, vol, min_vol=10):
    if vol < min_vol:
        return False
    if bid > 0 and ask > 0:
        return True
    if bid == 0 and ask > 0 and last > 0:
        return True   # 근만기 OTM 허용
    return False


def get_spread_quality(bid, ask):
    """스프레드 품질 태그 반환"""
    if bid > 0 and ask > 0:
        mid = (bid + ask) / 2
        return 'WIDE' if (mid > 0 and (ask - bid) / mid > 0.50) else 'GOOD'
    if bid == 0 and ask > 0:
        return 'BID_ZERO'   # bid=0 케이스 명시
    return 'WIDE'


# ── 방향성 추론 ───────────────────────────────────────────────────────────────
# bid > 0 정상 케이스: ask/bid 기준 추론
# bid = 0 근만기 케이스: ask 단독 기준 추론 (정밀도 낮음, BID_ZERO 태그 표시)
# ------------------------------------------------------------------------------
def infer_direction(row):
    try:
        bid  = safe_float(row.get('bid',  0))
        ask  = safe_float(row.get('ask',  0))
        last = safe_float(row.get('lastPrice', 0))

        if ask <= 0 or last <= 0:
            return 'ILLIQUID', '⚫'

        if bid > 0:
            mid = (bid + ask) / 2
            if mid > 0 and (ask - bid) / mid > 0.50:
                return 'ILLIQUID', '⚫'
            if last >= ask * 0.97:
                return 'BUY',     '🟢'
            elif last <= bid * 1.03:
                return 'SELL',    '🔴'
            else:
                return 'NEUTRAL', '🟡'
        else:
            # bid=0: ask 기준으로만 추론
            if last >= ask * 0.90:
                return 'BUY',     '🟢'
            elif last <= ask * 0.30:
                return 'SELL',    '🔴'
            else:
                return 'NEUTRAL', '🟡'
    except Exception:
        return 'ILLIQUID', '⚫'


# ── 프리미엄 계산 ─────────────────────────────────────────────────────────────
# bid > 0  → (bid+ask)/2 × vol × 100   (MID)
# bid = 0  → ask × vol × 100            (ASK_ONLY)
# 그 외    → lastPrice × vol × 100      (STALE)
# ------------------------------------------------------------------------------
def calc_mid_premium(row):
    try:
        bid  = safe_float(row.get('bid',  0))
        ask  = safe_float(row.get('ask',  0))
        last = safe_float(row.get('lastPrice', 0))
        vol  = safe_int(row.get('volume', 0))

        if vol <= 0:
            return 0, 'NO_VOL'
        if bid > 0 and ask > 0:
            return round((bid + ask) / 2 * vol * 100), 'MID'
        elif bid == 0 and ask > 0:
            return round(ask * vol * 100), 'ASK_ONLY'
        elif last > 0:
            return round(last * vol * 100), 'STALE'
        return 0, 'NO_DATA'
    except Exception:
        return 0, 'ERROR'


# ── IV 거래량 가중 평균 ───────────────────────────────────────────────────────
# 기존: bid > 0 필수 → 근만기에서 모두 탈락
# 수정: bid=0이어도 ask>0 & last>0 이면 허용 (is_near_expiry=True시 더 완화)
# ------------------------------------------------------------------------------
def get_volume_weighted_iv(df, is_near_expiry=False):
    try:
        if 'impliedVolatility' not in df.columns or 'volume' not in df.columns:
            return None, 0, 0

        iv   = df['impliedVolatility'].fillna(0).astype(float)
        vol  = df['volume'].fillna(0).astype(float)
        bid  = df['bid'].fillna(0).astype(float)  if 'bid'  in df.columns else pd.Series(0, index=df.index)
        ask  = df['ask'].fillna(0).astype(float)  if 'ask'  in df.columns else pd.Series(0, index=df.index)
        last = df['lastPrice'].fillna(0).astype(float) if 'lastPrice' in df.columns else pd.Series(0, index=df.index)

        liquid = (bid > 0) | ((ask > 0) & (last > 0))
        if is_near_expiry:
            liquid = liquid | (vol >= 10)  # 근만기: 거래량만 있어도 허용

        mask           = (iv > 0.01) & (iv < 5.0) & (vol > 0) & liquid
        total_liquid_n = int(liquid.sum())

        if mask.sum() == 0 or vol[mask].sum() == 0:
            return None, 0, total_liquid_n

        vw = (iv[mask] * vol[mask]).sum() / vol[mask].sum()
        return round(float(vw) * 100, 2), int(mask.sum()), total_liquid_n
    except Exception:
        return None, 0, 0


# ── Smart Money Flow 테이블 ───────────────────────────────────────────────────
def build_flow_df(df, option_type, is_near_expiry=False):
    min_vol = 10 if is_near_expiry else 100
    rows    = []
    for _, row in df.iterrows():
        try:
            vol  = safe_int(row.get('volume', 0))
            bid  = safe_float(row.get('bid',  0))
            ask  = safe_float(row.get('ask',  0))
            last = safe_float(row.get('lastPrice', 0))

            if not is_liquid(bid, ask, last, vol, min_vol=min_vol):
                continue

            direction, emoji = infer_direction(row)
            if direction == 'ILLIQUID':
                continue

            premium, quality = calc_mid_premium(row)
            if premium <= 0:
                continue

            iv_raw = safe_float(row.get('impliedVolatility', 0))
            iv_pct = round(iv_raw * 100, 1) if 0.01 < iv_raw < 5.0 else None
            oi     = safe_int(row.get('openInterest', 0))
            sq     = get_spread_quality(bid, ask)

            rows.append({
                '방향':        emoji,
                '_direction':  direction,
                '종류':        option_type,
                '행사가':       safe_float(row.get('strike', 0)),
                '거래량':       vol,
                'OI(전일)':    oi,
                'Vol/OI':      round(vol / oi, 2) if oi > 0 else None,
                '프리미엄($)':  premium,
                'IV(%)':       iv_pct,
                '가격기준':     quality,
                '스프레드':     sq,
                'Bid':         round(bid,  2),
                'Ask':         round(ask,  2),
                '체결가':       round(last, 2),
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    return (pd.DataFrame(rows)
              .sort_values('프리미엄($)', ascending=False)
              .reset_index(drop=True))


def format_flow_display(df):
    if df.empty:
        return df
    cols = ['방향','종류','행사가','거래량','OI(전일)','Vol/OI',
            '프리미엄($)','IV(%)','가격기준','스프레드','Bid','Ask','체결가']
    d = df[[c for c in cols if c in df.columns]].copy()
    if '프리미엄($)' in d.columns:
        d['프리미엄($)'] = d['프리미엄($)'].apply(lambda x: f"${x:,.0f}")
    if '거래량' in d.columns:
        d['거래량'] = d['거래량'].apply(lambda x: f"{x:,}")
    if 'OI(전일)' in d.columns:
        d['OI(전일)'] = d['OI(전일)'].apply(lambda x: f"{x:,}")
    return d


# ── Max Pain 계산 ─────────────────────────────────────────────────────────────
# [버그 원인]
#   기존 코드는 ALL 행사가(원거리 포함)의 OI를 그대로 사용.
#   yfinance는 0DTE 당일에도 전일(T-1) 기준 OI를 반환하는데,
#   일부 조건에서 ATM 근처는 OI=0이지만, 현재가와 동떨어진 원거리 행사가
#   (예: NVDA $340 콜)에 전일 잔존 OI가 남아 있을 수 있음.
#   → 이 원거리 OI가 Pain 계산을 지배 → Max Pain이 현재가와 동떨어진 값으로 출력.
#
# [수정 내용]
#   1. current_price ±PRICE_RANGE(기본 40%) 이내 행사가만 사용 (원거리 이상치 제거)
#   2. 필터 후에도 OI=0이면 None 반환
#   3. 계산 결과가 현재가 ±40% 벗어나면 "비정상 결과"로 None 반환
#      (데이터 오염이 필터를 통과한 edge case 방어)
# -----------------------------------------------------------------------------
def calc_max_pain(calls, puts, current_price=0.0, price_range=0.40):
    """
    반환: (max_pain_strike, reason_str)
      - (float, None)   : 정상 산출
      - (None, str)     : 산출 불가 사유 포함
    """
    try:
        c = calls.copy()
        p = puts.copy()

        # ① 현재가 기준 ±40% 범위로 행사가 필터 (원거리 이상치 OI 제거)
        if current_price > 0:
            lo = current_price * (1 - price_range)
            hi = current_price * (1 + price_range)
            c  = c[(c['strike'] >= lo) & (c['strike'] <= hi)]
            p  = p[(p['strike'] >= lo) & (p['strike'] <= hi)]

        oi_total = float(c['openInterest'].sum() + p['openInterest'].sum())
        if oi_total == 0:
            return None, "OI 미산출 (0DTE T+1 규정)"

        strikes = sorted(set(c['strike'].tolist() + p['strike'].tolist()))
        if not strikes:
            return None, "유효 행사가 없음"

        pain = []
        for s in strikes:
            cp = float(((c['strike'] - s).clip(lower=0) * c['openInterest']).sum())
            pp = float(((s - p['strike']).clip(lower=0) * p['openInterest']).sum())
            pain.append(cp + pp)

        result = strikes[pain.index(min(pain))]

        # ② 결과 유효성 검증: 현재가 ±40% 벗어나면 데이터 오염으로 간주
        if current_price > 0:
            if result > current_price * 1.40 or result < current_price * 0.60:
                return None, f"결과값(${result:.0f})이 현재가 대비 ±40% 초과 → 데이터 오염 의심"

        return result, None   # (정상값, 사유없음)

    except Exception as e:
        return None, f"계산 오류: {str(e)[:60]}"


# ── 상위 거래량 행사가 ────────────────────────────────────────────────────────
def get_top_strikes(df, n=5):
    try:
        if df.empty or 'volume' not in df.columns:
            return []
        top = df[df['volume'] > 0].nlargest(n, 'volume')[['strike','volume','openInterest']].copy()
        return [{'strike': r['strike'],
                 'volume': safe_int(r['volume']),
                 'oi':     safe_int(r.get('openInterest', 0))}
                for _, r in top.iterrows()]
    except Exception:
        return []

def strikes_to_text(lst):
    if not lst:
        return "  데이터 없음"
    return "\n".join(
        f"  ${r['strike']:.0f} | 거래량 {r['volume']:,} | OI {r['oi']:,}"
        for r in lst
    )


# ── UI 헬퍼 ──────────────────────────────────────────────────────────────────
def metric_card(title, value, val_color, status="", stat_color="transparent"):
    return f"""
    <div style="background:#111827;padding:18px;border-radius:12px;
                border:1px solid #1f2937;box-shadow:0 4px 6px rgba(0,0,0,.2);height:100%;">
      <div style="color:#9ca3af;font-size:13px;margin-bottom:8px;font-weight:600;">{title}</div>
      <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;">
        <div style="color:{val_color};font-size:28px;font-weight:800;">{value}</div>
        <div style="color:{stat_color};font-size:12px;font-weight:700;">{status}</div>
      </div>
    </div>"""

def warn_box(html):
    st.markdown(f'<div class="warn-box">{html}</div>', unsafe_allow_html=True)
def info_box(html):
    st.markdown(f'<div class="info-box">{html}</div>', unsafe_allow_html=True)
def dte_box(html):
    st.markdown(f'<div class="dte-box">{html}</div>', unsafe_allow_html=True)


# =============================================================================
# ② Gemini API
# =============================================================================
def generate_with_fallback(prompt, api_key):
    genai.configure(api_key=api_key)
    for m in ["gemini-2.0-flash-lite-preview-02-05","gemini-1.5-pro",
              "gemini-1.5-flash","gemini-1.5-flash-8b"]:
        try:
            return genai.GenerativeModel(m).generate_content(prompt).text, m
        except Exception as e:
            time.sleep(0.5)
    raise Exception("모든 Gemini 모델 호출 실패")


api_key     = st.secrets.get("GEMINI_API_KEY")
has_api_key = api_key is not None
if not has_api_key:
    st.sidebar.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY' 미설정")


# =============================================================================
# ③ 사이드바
# =============================================================================
with st.sidebar:
    st.header("🔍 검색 설정")
    ticker_input  = st.text_input("티커 심볼 (예: AAPL, NVDA, SPY)", value="AAPL").upper().strip()
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
            st.error("옵션 데이터 없음")
    except Exception as e:
        st.error(f"서버 연결 오류: {str(e)[:100]}")

    selected_expiry = None
    if expirations and analysis_mode == "단일 만기일 분석":
        selected_expiry = st.selectbox("만기일 선택", expirations)


# =============================================================================
# ④ 현재가 수집 (장 상태 감지 + 장외 가격 포함)
# =============================================================================
current_price  = 0.0   # 옵션 계산용 기준가 (정규장 우선)
display_price  = 0.0   # 화면 표시용 (장외 있으면 장외가)
name           = ticker_input
market_state   = "UNKNOWN"   # REGULAR / PRE / POST / CLOSED
ext_price      = 0.0         # 장외 가격
ext_change_pct = 0.0         # 장외 등락률
ext_label      = ""          # "장전" / "장후"

if ticker_input and expirations:
    try:
        info = ticker.info or {}
        name = info.get('longName', ticker_input)

        # ① 정규장 기준가 (옵션 행사가 비교용으로 항상 사용)
        current_price = safe_float(
            info.get('currentPrice') or info.get('regularMarketPrice')
        )
        if current_price <= 0:
            hist = ticker.history(period="2d")
            if not hist.empty:
                current_price = safe_float(hist['Close'].iloc[-1])

        # ② 장 상태 감지
        market_state = info.get('marketState', 'UNKNOWN').upper()
        # marketState 값 예시: REGULAR, PRE, PREPRE, POST, POSTPOST, CLOSED

        # ③ 장외 가격 수집
        if market_state in ('POST', 'POSTPOST'):
            ext_price      = safe_float(info.get('postMarketPrice', 0))
            ext_change_pct = safe_float(info.get('postMarketChangePercent', 0))
            ext_label      = "장후(AH)"
        elif market_state in ('PRE', 'PREPRE'):
            ext_price      = safe_float(info.get('preMarketPrice', 0))
            ext_change_pct = safe_float(info.get('preMarketChangePercent', 0))
            ext_label      = "장전(PM)"

        # ④ 표시용 가격: 장외 있으면 장외가, 없으면 정규장가
        display_price = ext_price if ext_price > 0 else current_price

    except Exception as e:
        st.warning(f"현재가 조회 실패: {str(e)[:100]}")

    # ── 가격 헤더 표시 ──────────────────────────────────────────────────────
    if ext_price > 0:
        # 장외 등락 방향 색상
        ext_color = "#00e5a0" if ext_change_pct >= 0 else "#ff4d6d"
        ext_sign  = "▲" if ext_change_pct >= 0 else "▼"
        ext_delta = abs(ext_change_pct * 100) if abs(ext_change_pct) < 1 else abs(ext_change_pct)
        # yfinance는 소수(0.012 = 1.2%)로 주는 경우와 퍼센트(1.2)로 주는 경우 혼재
        # → 절대값 1 미만이면 소수형으로 간주해 ×100
        ext_pct_str = f"{ext_delta:.2f}%"

        st.markdown(
            f"<div style='display:flex;align-items:baseline;gap:16px;margin-bottom:8px;'>"
            f"<span style='font-size:20px;font-weight:700;color:#f3f4f6;'>"
            f"📊 {name} ({ticker_input})</span>"
            f"<span style='font-size:15px;color:#9ca3af;'>정규장 종가</span>"
            f"<span style='font-size:22px;font-weight:800;color:#f3f4f6;'>${current_price:,.2f}</span>"
            f"<span style='font-size:13px;background:#1f2937;padding:3px 10px;"
            f"border-radius:12px;color:#a855f7;font-weight:700;'>{ext_label}</span>"
            f"<span style='font-size:22px;font-weight:800;color:{ext_color};'>${ext_price:,.2f}</span>"
            f"<span style='font-size:14px;color:{ext_color};font-weight:700;'>"
            f"{ext_sign} {ext_pct_str}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        info_box(
            f"ℹ️ <b>{ext_label} 가격 표시 중</b> (marketState: {market_state}). "
            f"옵션 행사가 비교·Max Pain 계산은 <b>정규장 종가 ${current_price:,.2f}</b> 기준으로 유지됩니다. "
            f"장외 가격은 유동성이 낮아 옵션 분석의 기준가로 적합하지 않습니다."
        )
    else:
        # 정규장 중 또는 장외 데이터 없음
        state_label = {
            "REGULAR": "🟢 정규장",
            "PRE":     "🟡 장전",
            "PREPRE":  "🟡 장전",
            "POST":    "🟠 장후",
            "POSTPOST":"🟠 장후",
            "CLOSED":  "⚫ 장외시간",
        }.get(market_state, f"⚪ {market_state}")

        st.subheader(
            f"📊 {name} ({ticker_input})  |  {state_label}  |  ${current_price:,.2f}"
        )


# =============================================================================
# ⑤ 모드 1: 단일 만기일 분석
# =============================================================================
prompt = ""

if analysis_mode == "단일 만기일 분석" and selected_expiry and expirations:

    dte      = days_to_expiry(selected_expiry)
    is_near  = dte <= 2   # 0DTE / 1DTE / 2DTE

    with st.spinner(f"'{selected_expiry}' 옵션 체인 수집 중..."):
        try:
            chain = ticker.option_chain(selected_expiry)
            calls = clean_option_df(chain.calls.copy())
            puts  = clean_option_df(chain.puts.copy())
        except Exception as e:
            st.error(f"옵션 체인 수집 실패: {e}")
            st.stop()

    # ── 근만기 안내 ──────────────────────────────────────────────────────
    if is_near:
        label = "0DTE (당일 만기)" if dte <= 0 else f"{dte}DTE (초근만기)"
        dte_box(
            f"🕐 <b>{label} 옵션 선택됨</b> — 아래 지표들이 평소와 다르게 표시될 수 있습니다:<br>"
            f"&nbsp;&nbsp;• <b>OI = 0</b>: 당일 신규 포지션은 다음날 아침에 반영 (T+1 규정)<br>"
            f"&nbsp;&nbsp;• <b>Bid = 0</b>: OTM 옵션에서 시장조성자가 Bid 미제시 → 정상 현상<br>"
            f"&nbsp;&nbsp;• IV · Smart Money: bid=0 허용 완화 필터를 자동 적용합니다"
        )

    # ── 기본 지표 ────────────────────────────────────────────────────────
    call_vol = float(calls['volume'].sum())
    put_vol  = float(puts['volume'].sum())
    call_oi  = float(calls['openInterest'].sum())
    put_oi   = float(puts['openInterest'].sum())
    pcr_vol  = safe_pcr(put_vol, call_vol)
    pcr_oi   = safe_pcr(put_oi,  call_oi)

    call_iv, call_iv_n, call_liq = get_volume_weighted_iv(calls, is_near_expiry=is_near)
    put_iv,  put_iv_n,  put_liq  = get_volume_weighted_iv(puts,  is_near_expiry=is_near)
    max_pain, mp_reason = calc_max_pain(calls, puts, current_price=current_price)
    top_calls = get_top_strikes(calls, n=5)
    top_puts  = get_top_strikes(puts,  n=5)

    if pcr_vol > 1.2:
        sig_color, sig_text = "#ff4d6d", "하락 신호 (Bearish)"
    elif pcr_vol < 0.7:
        sig_color, sig_text = "#00e5a0", "상승 신호 (Bullish)"
    else:
        sig_color, sig_text = "#f5a623", "중립 (Neutral)"

    # ── 메트릭 카드 (5개) ────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(metric_card("CALL 거래량", f"{int(call_vol):,}", "#00e5a0"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("PUT 거래량",  f"{int(put_vol):,}",  "#ff4d6d"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("PCR (거래량)", f"{pcr_vol:.2f}",
                                "#f3f4f6", sig_text, sig_color),
                    unsafe_allow_html=True)
    with c4:
        # OI 신뢰도 평가: OI 총량이 거래량의 1% 미만이면 낮음으로 표시
        oi_total = call_oi + put_oi
        vol_total = call_vol + put_vol
        oi_reliability = (oi_total / vol_total) if vol_total > 0 else 0
        if oi_total == 0:
            oi_val, oi_col = "미산출(0DTE)", "#f5a623"
        elif oi_reliability < 0.01:
            oi_val, oi_col = f"{pcr_oi:.2f} ⚠️낮음", "#f5a623"
        else:
            oi_val, oi_col = f"{pcr_oi:.2f}", "#9ca3af"
        st.markdown(metric_card("PCR (OI) ⚠️전일", oi_val, oi_col),
                    unsafe_allow_html=True)
    with c5:
        if max_pain:
            mp_val, mp_col = f"${max_pain:,.0f}", "#a855f7"
        else:
            # 사유 축약 표시
            mp_short = "미산출" if not mp_reason else (
                "0DTE미산출" if "T+1" in mp_reason else
                "데이터오염" if "오염" in mp_reason else "미산출"
            )
            mp_val, mp_col = mp_short, "#f5a623"
        st.markdown(metric_card("Max Pain", mp_val, mp_col),
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if oi_reliability < 0.01 and oi_total > 0:
        warn_box(
            "⚠️ <b>OI 신뢰도 낮음:</b> 전체 OI가 당일 거래량의 1% 미만입니다. "
            "소수의 원거리 행사가에 잔존 OI가 있을 가능성이 높습니다. "
            "PCR(OI)와 Max Pain은 참고용으로만 사용하세요. "
            "장중에는 <b>PCR(거래량)과 거래량 집중 행사가</b>를 우선 참고하세요."
        )
    else:
        warn_box(
            "⚠️ <b>OI(미결제약정)는 전일 장 마감 기준</b>입니다. "
            "장중 Volume과 직접 비교하면 오류가 발생합니다. "
            "장중에는 <b>PCR(거래량)</b> 위주로 참고하세요."
        )

    # ── IV 가중 평균 ─────────────────────────────────────────────────────
    iv_col1, iv_col2 = st.columns(2)
    with iv_col1:
        if call_iv is not None:
            st.metric(f"콜 IV 거래량가중 ({call_iv_n}/{call_liq}개 유동 행사가)",
                      f"{call_iv:.1f}%")
        else:
            reason = ("근만기 특성: yfinance가 IV를 0으로 반환" if is_near else "유동성 부족")
            st.metric("콜 IV 가중평균", f"산출 불가 — {reason}")
    with iv_col2:
        if put_iv is not None:
            st.metric(f"풋 IV 거래량가중 ({put_iv_n}/{put_liq}개 유동 행사가)",
                      f"{put_iv:.1f}%")
        else:
            reason = ("근만기 특성: yfinance가 IV를 0으로 반환" if is_near else "유동성 부족")
            st.metric("풋 IV 가중평균", f"산출 불가 — {reason}")

    if is_near:
        info_box(
            "ℹ️ <b>근만기 IV 신뢰도 주의:</b> bid=0이어도 ask>0 & lastPrice>0이면 계산에 포함합니다. "
            "단, 0DTE 옵션은 잔존 시간가치(T→0)로 인해 Black-Scholes 기반 yfinance IV 계산이 "
            "불안정합니다. 표시된 IV값(예: 8~15%)은 과소 추정일 가능성이 있으므로 "
            "절대값보다 <b>콜/풋 IV 간 상대적 차이(Put IV > Call IV → 하방 헤징 심리)</b>를 참고하세요."
        )
    else:
        info_box(
            "ℹ️ <b>IV 필터:</b> 0.01 < IV < 500%,  거래량>0,  "
            "bid>0 또는 (ask>0 & last>0) 조건 충족 행사가만 포함합니다."
        )

    # ── 거래량 차트 ──────────────────────────────────────────────────────
    if current_price > 0:
        min_s, max_s = current_price * 0.70, current_price * 1.30
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
    if max_pain:
        fig.add_vline(x=max_pain, line_dash="dot", line_color="#a855f7",
                      annotation_text=f"Max Pain ${max_pain:.0f}",
                      annotation_position="top right")
    fig.update_layout(
        title=f"행사가별 거래량  (만기: {selected_expiry}  |  잔존 {dte}일)",
        barmode='relative', template="plotly_dark",
        height=420, hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── IV Skew 차트 ─────────────────────────────────────────────────────
    st.markdown("#### 📉 IV Skew (유동성 필터 적용)")

    def get_iv_skew(df_opt, near=False):
        iv   = df_opt['impliedVolatility'].astype(float)
        vol  = df_opt['volume'].fillna(0).astype(float)
        bid  = df_opt['bid'].fillna(0).astype(float)  if 'bid'  in df_opt.columns else pd.Series(0, index=df_opt.index)
        ask  = df_opt['ask'].fillna(0).astype(float)  if 'ask'  in df_opt.columns else pd.Series(0, index=df_opt.index)
        last = df_opt['lastPrice'].fillna(0).astype(float) if 'lastPrice' in df_opt.columns else pd.Series(0, index=df_opt.index)
        liquid = (bid > 0) | ((ask > 0) & (last > 0))
        if near:
            liquid = liquid | (vol >= 10)
        mask = (iv > 0.01) & (iv < 5.0) & (vol > 0) & liquid
        filtered = df_opt[mask].copy()
        if filtered.empty:
            return None
        filtered = filtered.sort_values('strike')
        filtered['iv_pct'] = filtered['impliedVolatility'] * 100
        return filtered

    if current_price > 0:
        cs = get_iv_skew(calls_c, is_near)
        ps = get_iv_skew(puts_c,  is_near)
        if cs is not None or ps is not None:
            fig_iv = go.Figure()
            if cs is not None:
                fig_iv.add_trace(go.Scatter(
                    x=cs['strike'], y=cs['iv_pct'], mode='lines+markers',
                    name='Call IV', line=dict(color='#00e5a0', width=2),
                    hovertemplate='$%{x}<br>IV %{y:.1f}%<extra></extra>'
                ))
            if ps is not None:
                fig_iv.add_trace(go.Scatter(
                    x=ps['strike'], y=ps['iv_pct'], mode='lines+markers',
                    name='Put IV',  line=dict(color='#ff4d6d', width=2),
                    hovertemplate='$%{x}<br>IV %{y:.1f}%<extra></extra>'
                ))
            fig_iv.add_vline(x=current_price, line_dash="dash", line_color="white")
            if max_pain:
                fig_iv.add_vline(x=max_pain, line_dash="dot", line_color="#a855f7")
            fig_iv.update_layout(
                title="IV Skew (비유동성 이상치 제거)",
                template="plotly_dark", height=350,
                xaxis_title="행사가", yaxis_title="내재변동성 (%)"
            )
            st.plotly_chart(fig_iv, use_container_width=True)
        else:
            msg = ("근만기 OTM 옵션의 IV를 yfinance가 0으로 반환 중입니다. "
                   "거래량 차트의 집중 행사가를 지지/저항선으로 참고하세요.") if is_near else \
                  "IV Skew 차트를 그릴 유동성 데이터가 없습니다."
            st.info(msg)

    # ── Smart Money Flow ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🕵️ Smart Money Flow  (Bid/Ask 방향성 추론)")

    if is_near:
        warn_box(
            "⚠️ <b>근만기 완화 모드:</b> bid=0인 옵션도 ask>0 & 거래량≥10이면 포함합니다. "
            "스프레드 품질 '스프레드' 컬럼에서 <b>BID_ZERO</b>로 표시된 행은 신뢰도 낮음."
        )
    else:
        warn_box(
            "⚠️ <b>방법론 한계:</b> EOD(일 마감) 데이터 기반. 실시간 플로우 툴 대비 정밀도 낮음. "
            "거래량≥100 & 스프레드 양호 조건 충족 옵션만 표시합니다."
        )
    st.markdown("<br>", unsafe_allow_html=True)

    call_flow = build_flow_df(calls, 'CALL', is_near_expiry=is_near)
    put_flow  = build_flow_df(puts,  'PUT',  is_near_expiry=is_near)
    all_flow  = pd.concat([call_flow, put_flow], ignore_index=True)

    flow_buy_text  = "데이터 없음"
    flow_sell_text = "데이터 없음"

    if not all_flow.empty:
        all_flow = all_flow.sort_values('프리미엄($)', ascending=False).reset_index(drop=True)

        tab_all, tab_buy, tab_sell, tab_neutral = st.tabs([
            "전체 플로우", "🟢 공격적 BUY", "🔴 공격적 SELL", "🟡 중립"
        ])
        with tab_all:
            st.caption(f"상위 20건 (전체 {len(all_flow)}건)")
            st.dataframe(format_flow_display(all_flow.head(20)),
                         use_container_width=True, hide_index=True)
        with tab_buy:
            b = all_flow[all_flow['_direction'] == 'BUY']
            if b.empty:
                st.info("공격적 BUY 신호가 없습니다.")
            else:
                st.dataframe(format_flow_display(b.head(15)), use_container_width=True, hide_index=True)
        with tab_sell:
            s = all_flow[all_flow['_direction'] == 'SELL']
            if s.empty:
                st.info("공격적 SELL 신호가 없습니다.")
            else:
                st.dataframe(format_flow_display(s.head(15)), use_container_width=True, hide_index=True)
        with tab_neutral:
            n = all_flow[all_flow['_direction'] == 'NEUTRAL']
            if n.empty:
                st.info("중립 체결 옵션이 없습니다.")
            else:
                st.dataframe(format_flow_display(n.head(15)), use_container_width=True, hide_index=True)

        st.markdown("##### 📊 방향성 집계 요약")
        ds = (all_flow.groupby('_direction', sort=False)
              .agg(건수=('프리미엄($)','count'), 총프리미엄=('프리미엄($)','sum'))
              .reset_index().rename(columns={'_direction':'방향'})
              .sort_values('건수', ascending=False))
        ds['총프리미엄'] = ds['총프리미엄'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(ds, use_container_width=True, hide_index=True)

        def flow_txt(df, direction, n=5):
            sub = df[df['_direction'] == direction].head(n)
            if sub.empty:
                return "  없음"
            lines = []
            for _, r in sub.iterrows():
                tag = " [Bid=0 추정]" if r.get('스프레드') == 'BID_ZERO' else ""
                lines.append(
                    f"  {r['종류']} ${r['행사가']:.0f} | 거래량 {r['거래량']:,} "
                    f"| 프리미엄 ${r['프리미엄($)']:,} | IV {r['IV(%)']}%{tag}"
                )
            return "\n".join(lines)

        flow_buy_text  = flow_txt(all_flow, 'BUY')
        flow_sell_text = flow_txt(all_flow, 'SELL')
    else:
        if is_near:
            warn_box(
                "⚠️ <b>0DTE Smart Money 데이터 없음 — 원인:</b> yfinance는 무료 EOD 데이터이므로 "
                "장중 실시간 Bid/Ask를 제공하지 않습니다. 0DTE 옵션의 경우 "
                "Bid=0, Ask=0으로 반환되는 경우가 많아 방향성 추론이 불가합니다.<br>"
                "→ <b>대안:</b> 위 '거래량 집중 행사가' 차트를 지지/저항선 판단에 활용하세요."
            )
        else:
            st.info("방향성 추론 가능한 옵션이 없습니다. (거래량 < 100 이거나 Bid/Ask 데이터 부재)")

    # ── 프롬프트 생성 (데이터 풍부화) ─────────────────────────────────────
    if call_iv and put_iv:
        iv_line = f"콜 IV(거래량가중): {call_iv:.1f}%  /  풋 IV(거래량가중): {put_iv:.1f}%"
    else:
        iv_line = (
            f"콜 IV: {'산출불가' if not call_iv else f'{call_iv:.1f}%'}  /  "
            f"풋 IV: {'산출불가' if not put_iv else f'{put_iv:.1f}%'}"
            + ("  ← 근만기 특성상 yfinance IV 미산출 (거래량 차트 기준으로 분석할 것)" if is_near else "  ← IV 데이터 부족")
        )
    mp_line = f"${max_pain:,.0f}" if max_pain else f"미산출 ({mp_reason})"

    prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 분석하세요.

[분석 대상]
- 티커: {name} ({ticker_input}) | 만기: {selected_expiry} | 잔존: {dte}일
- 현재가: ${current_price:,.2f}
{f'- ⚠️ 근만기({dte}DTE) 옵션: OI T+1 규정으로 당일 OI 미산출. IV도 yfinance 제한으로 일부 누락.' if is_near else ''}

[핵심 수급 지표]
- 콜 거래량: {int(call_vol):,}  /  풋 거래량: {int(put_vol):,}
- PCR(거래량): {pcr_vol:.2f} → {sig_text}
- PCR(OI, 전일기준 ※참고용): {pcr_oi:.2f}
- {iv_line}
- Max Pain: {mp_line}

[거래량 집중 행사가 — 지지/저항선 도출의 핵심 근거]
▶ 콜 거래량 상위 5개 행사가 (저항선 후보):
{strikes_to_text(top_calls)}

▶ 풋 거래량 상위 5개 행사가 (지지선 후보):
{strikes_to_text(top_puts)}

[Smart Money 방향성 (Bid/Ask 추론, EOD 기반 참고용)]
▶ 공격적 BUY 상위 5건:
{flow_buy_text}

▶ 공격적 SELL 상위 5건:
{flow_sell_text}

[분석 지시사항]
1. PCR(거래량)과 콜/풋 거래량 집중 행사가를 교차하여 단기 주가 방향을 예측하세요.
2. 거래량이 집중된 콜 행사가를 저항선, 풋 행사가를 지지선으로 구체적인 가격($)을 제시하세요.
3. Max Pain이 산출된 경우 현재가({f'${current_price:,.2f}'})와의 괴리 방향을 해석하세요.
4. Smart Money 데이터가 있으면 PCR과 교차 검증하고, 없으면 거래량 데이터 위주로 분석하세요.
5. 잔존 {dte}일을 고려한 포지션 전략(감마/세타 위험)을 한 줄 언급하세요.
6. EOD 데이터 한계를 감안한 신중한 톤으로, 한글 마크다운으로 간결하게 정리하세요.
"""


# =============================================================================
# ⑥ 모드 2: 전체 기간 통합 분석
# =============================================================================
elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:

    st.info("💡 **단기(30일 이내), 중기(30~90일), 장기(90일 이상)** 만기일을 통합 분석합니다.")
    warn_box(
        "⚠️ <b>OI는 전일 장 마감 기준</b>입니다. "
        "장중에는 PCR(거래량) 위주로 참고하세요."
    )
    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner("전체 만기일 데이터 수집 중... (10~30초 소요)"):
        today = datetime.today()
        term_data = {
            "Short (단기/30일내)":  {"call_vol":0,"put_vol":0,"call_oi":0,"put_oi":0},
            "Mid (중기/30~90일)":   {"call_vol":0,"put_vol":0,"call_oi":0,"put_oi":0},
            "Long (장기/90일이상)": {"call_vol":0,"put_vol":0,"call_oi":0,"put_oi":0},
        }

        def safe_col_sum(df_opt, col):
            if df_opt is None or col not in df_opt.columns:
                return 0.0
            return float(pd.to_numeric(df_opt[col], errors='coerce').fillna(0).sum())

        prog    = st.progress(0)
        holder  = st.empty()
        total   = len(expirations)
        err_cnt = 0

        for i, exp_date in enumerate(expirations):
            try:
                d = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                if d <= 0:
                    continue
                cat = ("Short (단기/30일내)" if d <= 30 else
                       "Mid (중기/30~90일)"  if d <= 90 else
                       "Long (장기/90일이상)")
                holder.text(f"수집 중: {exp_date}  ({i+1}/{total})")
                opt = ticker.option_chain(exp_date)
                term_data[cat]["call_vol"] += safe_col_sum(opt.calls, 'volume')
                term_data[cat]["put_vol"]  += safe_col_sum(opt.puts,  'volume')
                term_data[cat]["call_oi"]  += safe_col_sum(opt.calls, 'openInterest')
                term_data[cat]["put_oi"]   += safe_col_sum(opt.puts,  'openInterest')
            except Exception:
                err_cnt += 1
            finally:
                prog.progress((i + 1) / total)

        prog.empty()
        holder.empty()
        if err_cnt > 0:
            warn_box(f"⚠️ {err_cnt}개 만기일 수집 실패. 나머지로 분석합니다.")

    df_terms = pd.DataFrame(term_data).T
    df_terms['PCR (Volume)'] = df_terms.apply(lambda r: safe_pcr(r['put_vol'], r['call_vol']), axis=1)
    df_terms['PCR (OI)']     = df_terms.apply(lambda r: safe_pcr(r['put_oi'],  r['call_oi']),  axis=1)
    valid = df_terms[(df_terms['call_vol'] + df_terms['put_vol']) > 0]

    if valid.empty:
        st.error("수집된 유효 데이터가 없습니다.")
        st.stop()

    st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=valid.index, y=valid['call_vol'],
                          name='CALL 거래량', marker_color='#00e5a0'))
    fig2.add_trace(go.Bar(x=valid.index, y=valid['put_vol'],
                          name='PUT 거래량',  marker_color='#ff4d6d'))
    fig2.update_layout(barmode='group', template='plotly_dark', height=400, hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### 📑 기간별 데이터 요약")
    st.caption("⚠️ OI 컬럼은 전일 기준. PCR(거래량) 위주 해석 권장.")
    disp = valid[['call_vol','put_vol','call_oi','put_oi','PCR (Volume)','PCR (OI)']].copy()
    disp.columns = ['Call 거래량','Put 거래량','Call OI(전일⚠️)','Put OI(전일⚠️)','PCR(거래량)','PCR(OI⚠️)']
    for col in ['Call 거래량','Put 거래량','Call OI(전일⚠️)','Put OI(전일⚠️)']:
        disp[col] = disp[col].apply(lambda x: f"{int(x):,}")
    for col in ['PCR(거래량)','PCR(OI⚠️)']:
        disp[col] = disp[col].apply(lambda x: f"{x:.2f}")
    st.dataframe(disp, use_container_width=True)

    rows_text = []
    for tn in valid.index:
        r = valid.loc[tn]
        rows_text.append(
            f"\n{tn}:\n"
            f"  콜 거래량: {int(r['call_vol']):,}  /  풋 거래량: {int(r['put_vol']):,}\n"
            f"  PCR(거래량): {r['PCR (Volume)']:.2f}  |  PCR(OI/전일기준): {r['PCR (OI)']:.2f}"
        )

    prompt = f"""
당신은 월스트리트 시니어 파생상품 애널리스트입니다.

[분석 대상]
- 티커: {ticker_input} ({name}) | 현재가: ${current_price:,.2f}

[기간별 옵션 Term Structure]
{''.join(rows_text)}

※ OI는 전일 기준 → PCR(거래량) 위주로 분석하세요.

[분석 지시사항]
1. 단기/중기/장기 PCR(거래량) 변화로 시장 심리의 Term Structure를 분석하세요.
2. 기간 간 다이버전스(단기 Bearish + 장기 Bullish 등)의 함의를 해석하세요.
3. 향후 1~3개월 주가 방향성 시나리오를 도출하세요.
4. 한글 마크다운으로 초보자도 이해할 수 있게 작성하세요.
"""


# =============================================================================
# ⑦ 공통 AI 분석 섹션
# =============================================================================
can_run = (
    ticker_input and expirations and prompt and (
        (analysis_mode == "단일 만기일 분석" and selected_expiry) or
        (analysis_mode != "단일 만기일 분석")
    )
)

if can_run:
    st.divider()
    st.subheader("🤖 Gemini AI 옵션 시장 브리핑")

    col1, col2 = st.columns(2)
    with col1:
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

    with col2:
        st.markdown("#### 옵션 2. 무료 한도 초과 시 대안")
        safe_prompt = json.dumps(prompt)
        html_code = f"""
        <button onclick="copyAndOpen()"
          style="background:#f5a623;color:#000;padding:12px 20px;border:none;
                 border-radius:8px;font-weight:bold;font-size:15px;
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

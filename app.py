import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import sqlite3, time, json, os
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")
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
.delta-pos{color:#00e5a0;font-weight:700;}
.delta-neg{color:#ff4d6d;font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 v3 — Mid-Price · Dynamic Moneyness · IV Trim · ΔOI</p>', unsafe_allow_html=True)

tab_analysis, tab_help = st.tabs(["📊 분석", "📖 도움말"])

# ══════════════════════════════════════════════════════════
# 도움말 탭
# ══════════════════════════════════════════════════════════
with tab_help:
    st.markdown("## 📖 옵션 데이터 활용 가이드 v3")
    st.markdown("---")

    st.markdown("""
    <div class="hcard pcr">
      <div class="htitle">📊 1. 풋/콜 비율 (PCR) — 시장의 공포와 탐욕 온도계
        <span class="hbadge badge-pcr">역발상 지표</span></div>
      <div class="hbody">
        <strong>PCR이란?</strong> 하락에 베팅한 사람(풋옵션) ÷ 상승에 베팅한 사람(콜옵션)의 비율입니다.<br><br>
        <strong>예시로 이해하기:</strong><br>
        &nbsp;콜옵션 거래량 1,000건 / 풋옵션 거래량 1,200건이면 PCR = 1.2<br>
        &nbsp;→ 사람들이 하락에 많이 베팅하고 있다는 뜻<br><br>
        <strong>역발상으로 읽는 법 (핵심!):</strong><br>
        &nbsp;PCR이 높다 = 모두가 하락을 두려워한다 → 이미 과도한 공포 → 곧 반등 가능성<br>
        &nbsp;PCR이 낮다 = 모두가 상승을 확신한다 → 이미 과도한 낙관 → 곧 조정 가능성<br><br>
        <table style="width:100%;border-collapse:collapse;margin-top:4px;">
          <tr style="border-bottom:1px solid #334155;background:#0f172a;">
            <th style="padding:8px 12px;color:#64748b;font-size:11px;text-align:left;">종목 유형</th>
            <th style="padding:8px 12px;color:#64748b;font-size:11px;">이 이상이면 하락 공포</th>
            <th style="padding:8px 12px;color:#64748b;font-size:11px;">이 이하면 상승 과열</th>
            <th style="padding:8px 12px;color:#64748b;font-size:11px;">왜 다른가?</th>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px 12px;color:#60a5fa;">ETF (SPY, QQQ 등)</td>
            <td style="padding:8px 12px;color:#ff4d6d;text-align:center;">&gt; 1.5</td>
            <td style="padding:8px 12px;color:#00e5a0;text-align:center;">&lt; 1.0</td>
            <td style="padding:8px 12px;color:#64748b;font-size:11px;">기관이 보험용으로 풋 많이 삼</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;color:#00e5a0;">개별 주식 (AAPL 등)</td>
            <td style="padding:8px 12px;color:#ff4d6d;text-align:center;">&gt; 1.2</td>
            <td style="padding:8px 12px;color:#00e5a0;text-align:center;">&lt; 0.7</td>
            <td style="padding:8px 12px;color:#64748b;font-size:11px;">개인 투자자 비중이 높음</td>
          </tr>
        </table><br>
        <strong>PCR 다이버전스 (고급):</strong> 오늘 PCR이 누적 PCR보다 1.5배 이상 크면<br>
        &nbsp;→ 오늘 갑자기 풋을 많이 샀다는 뜻 → 단기 공포 이벤트 가능성
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard uoa">
      <div class="htitle">🔥 2. 비정상 거래량 (UOA) — 스마트 머니가 움직였나?
        <span class="hbadge badge-uoa">스마트 머니 감지</span></div>
      <div class="hbody">
        <strong>UOA란?</strong> 평소와 달리 특정 행사가에 <strong>갑자기 대량의 거래</strong>가 터지는 현상입니다.<br>
        마치 경마에서 특정 말에 갑자기 큰돈이 몰리는 것과 같습니다.<br><br>
        <strong>이 앱의 탐지 기준:</strong><br>
        &nbsp;<span class="htag">V/OI ≥ 5배</span> : 미결제약정(쌓인 계약)의 5배 이상이 하루에 거래됨<br>
        &nbsp;<span class="htag">Dollar Premium ≥ $10K</span> : 실제 투입 자금이 1만 달러 이상 (소액 잡음 제거)<br>
        &nbsp;<span class="htag">Spread 필터</span> : 호가 간격이 너무 벌어진 비유동 옵션 자동 제거<br><br>
        <strong>옵션 위치(Moneyness)로 읽는 법:</strong><br>
        &nbsp;<span class="htag">OTM 콜 대량 매수</span> → "주가 급등을 확신"하고 베팅한 신호 (강한 투기)<br>
        &nbsp;<span class="htag">OTM 풋 대량 매수</span> → "주가 급락"을 예상하거나 주식 보유자가 보험을 든 것<br>
        &nbsp;<span class="htag">ATM 옵션 대량 매수</span> → 방향보다 "변동성 이벤트"(실적 발표 등)에 베팅<br><br>
        ⚠️ 무조건 따라가면 안 됩니다. 기관이 현물 손실을 막으려고 풋을 사기도 합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard voi">
      <div class="htitle">🔁 3. 거래량 × 미결제약정 교차 분석 — 새 돈인가, 나가는 돈인가?
        <span class="hbadge badge-voi">추세 신뢰도</span></div>
      <div class="hbody">
        <strong>핵심 개념:</strong><br>
        &nbsp;거래량 = 오늘 거래된 계약 수<br>
        &nbsp;미결제약정(OI) = 아직 안 닫힌 계약 수 (어제 기준)<br><br>
        <strong>두 가지를 함께 보면:</strong><br>
        <table style="width:100%;border-collapse:collapse;margin-top:4px;">
          <tr style="border-bottom:1px solid #334155;background:#0f172a;">
            <th style="padding:8px;color:#64748b;font-size:11px;">거래량</th>
            <th style="padding:8px;color:#64748b;font-size:11px;">미결제약정</th>
            <th style="padding:8px;color:#64748b;font-size:11px;">의미</th>
            <th style="padding:8px;color:#64748b;font-size:11px;">주가 추세</th>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;color:#00e5a0;text-align:center;">↑ 증가</td>
            <td style="padding:8px;color:#00e5a0;text-align:center;">↑ 증가</td>
            <td style="padding:8px;color:#e2e8f0;">새 돈이 들어오는 중</td>
            <td style="padding:8px;color:#00e5a0;">추세 강하게 지속 ✅</td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;color:#00e5a0;text-align:center;">↑ 증가</td>
            <td style="padding:8px;color:#ff4d6d;text-align:center;">↓ 감소</td>
            <td style="padding:8px;color:#e2e8f0;">기존 투자자들이 팔고 나감</td>
            <td style="padding:8px;color:#ff4d6d;">반전 경계 ⚠️</td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:8px;color:#ff4d6d;text-align:center;">↓ 감소</td>
            <td style="padding:8px;color:#00e5a0;text-align:center;">↑ 증가</td>
            <td style="padding:8px;color:#e2e8f0;">조용히 포지션 쌓는 중</td>
            <td style="padding:8px;color:#f5a623;">대기 매수 관찰 🔍</td>
          </tr>
          <tr>
            <td style="padding:8px;color:#ff4d6d;text-align:center;">↓ 감소</td>
            <td style="padding:8px;color:#ff4d6d;text-align:center;">↓ 감소</td>
            <td style="padding:8px;color:#e2e8f0;">에너지가 빠지고 있음</td>
            <td style="padding:8px;color:#ff4d6d;">전환점 임박 🔄</td>
          </tr>
        </table><br>
        ⚠️ 한계: yfinance OI는 어제 기준이라 오늘 생긴 새 포지션은 내일 확인 가능합니다.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard mp">
      <div class="htitle">🎯 4. 맥스 페인 & OI Wall — 만기일의 자석과 가격 벽
        <span class="hbadge badge-mp">만기일 자석 + 지지/저항</span></div>
      <div class="hbody">
        <strong>맥스 페인(Max Pain)이란?</strong><br>
        옵션을 판 사람(주로 기관·증권사)이 가장 큰 이익을 보는 가격 = 옵션을 산 사람들이 가장 큰 손실을 보는 가격입니다.<br><br>
        <strong>왜 중요한가?</strong><br>
        &nbsp;만기일이 가까울수록 주가가 맥스 페인 가격으로 끌려가는 경향이 있습니다.<br>
        &nbsp;(마켓 메이커들이 델타 헤징을 통해 자연스럽게 이 방향으로 움직이기 때문)<br><br>
        <strong>읽는 법:</strong><br>
        &nbsp;<span class="htag">현재가 > Max Pain</span> → 주가가 아래로 당겨질 가능성 (현재가 대비 음수%로 표시)<br>
        &nbsp;<span class="htag">현재가 < Max Pain</span> → 주가가 위로 당겨질 가능성 (현재가 대비 양수%로 표시)<br><br>
        <strong>OI Wall이란?</strong><br>
        &nbsp;미결제약정이 특정 행사가에 대거 몰려 있으면, 그 가격이 지지선 또는 저항선 역할을 합니다.<br>
        &nbsp;<span class="htag">Call OI 최대 행사가</span> → 저항선 (주가가 오르려 해도 막힘)<br>
        &nbsp;<span class="htag">Put OI 최대 행사가</span> → 지지선 (주가가 내려가도 막힘)<br><br>
        ⚠️ DTE가 짧을수록(만기가 임박할수록) 신뢰도가 낮아집니다. 경고 배너를 확인하세요.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard db">
      <div class="htitle">💾 5. ΔOI (미결제약정 증감) — 어제 누가 들어오고 나갔나?
        <span class="hbadge badge-db">ΔOI 추적</span></div>
      <div class="hbody">
        <strong>ΔOI란?</strong> 오늘 OI에서 어제 OI를 뺀 값입니다.<br>
        &nbsp;= 어제와 비교해 계약이 늘었는지(신규 진입) 줄었는지(청산) 보여줍니다.<br><br>
        <strong>거래량과 함께 보면:</strong><br>
        &nbsp;<span class="htag">거래량 많음 + OI 늘었음</span> → 새로운 큰 베팅이 들어온 것 🔥<br>
        &nbsp;<span class="htag">거래량 많음 + OI 줄었음</span> → 기존 포지션을 정리하고 나간 것 ✂️<br>
        &nbsp;<span class="htag">거래량 적음 + OI 늘었음</span> → 조용히 포지션을 축적 중 🤫<br><br>
        <strong>이 앱의 저장 방식:</strong><br>
        &nbsp;앱을 실행할 때마다 OI를 저장 → 다음날 비교하면 ΔOI 계산 가능<br>
        &nbsp;로컬 실행 시 파일로 영구 보존 / Streamlit Cloud는 탭을 닫으면 초기화
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hcard warn">
      <div class="htitle">⚠️ 이 앱의 한계 — 반드시 읽어주세요
        <span class="hbadge badge-warn">필독</span></div>
      <div class="hbody">
        <strong>무료 데이터(yfinance) 구조적 한계:</strong><br>
        &nbsp;📅 OI 데이터: 항상 어제 장마감 기준 (오늘 생긴 포지션은 내일 확인 가능)<br>
        &nbsp;⏱️ Bid/Ask: 실시간이 아닌 지연 데이터<br>
        &nbsp;🔢 Greeks(델타·감마·세타·베가): yfinance 미제공<br>
        &nbsp;📡 Sweep/Block 탐지: 거래소별 틱 데이터 없어서 불가<br><br>
        <strong>해석할 때 항상 기억하세요:</strong><br>
        &nbsp;• <strong>풋 매수 = 무조건 하락 예상 ❌</strong> (기관은 주식 보유 중 손실 방어용으로 풋을 삼)<br>
        &nbsp;• 이 앱의 신호는 여러 지표 중 하나, 주가 차트·뉴스·실적과 함께 봐야 함<br>
        &nbsp;• 최종 투자 판단은 항상 본인 책임입니다<br><br>
        <strong>신뢰도 높은 상황:</strong> DTE 7일 이상 · OI 충분 · 만기 전날 이전<br>
        <strong>신뢰도 낮은 상황:</strong> DTE 1~2일 · OI Wall 비어있음 · IV=0 (Fallback)
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# 분석 탭 — 함수 정의
# ══════════════════════════════════════════════════════════
with tab_analysis:

    # ────────────────────────────────────────────────────
    # [개선①] Mid-Price + 차등 Spread 필터 UOA
    # ────────────────────────────────────────────────────
    def calc_mid_price(row) -> float:
        """
        bid > 0 이면 (bid+ask)/2, 아니면 lastPrice 폴백.
        ask/2는 bid=0인 옵션을 과소평가 → lastPrice가 더 정확.
        """
        bid = row.get('bid', 0) or 0
        ask = row.get('ask', 0) or 0
        if bid > 0 and ask > 0:
            return (bid + ask) / 2.0
        return row.get('lastPrice', 0) or 0

    def spread_ratio(row) -> float:
        bid = row.get('bid', 0) or 0
        ask = row.get('ask', 0) or 0
        mid = (bid + ask) / 2.0
        if mid <= 0:
            return 999.0
        return (ask - bid) / mid

    # ────────────────────────────────────────────────────
    # [개선②] IV Expected Move 기반 동적 Moneyness
    # ────────────────────────────────────────────────────
    def get_atm_iv(calls: pd.DataFrame, puts: pd.DataFrame,
                   current_price: float) -> float:
        """현재가 ±5% 이내 옵션의 OI 가중평균 IV를 ATM IV로 사용."""
        lo, hi = current_price * 0.95, current_price * 1.05
        atm_c = calls[(calls['strike'] >= lo) & (calls['strike'] <= hi)].copy()
        atm_p = puts [(puts ['strike'] >= lo) & (puts ['strike'] <= hi)].copy()
        combined = pd.concat([atm_c, atm_p])
        if combined.empty or 'impliedVolatility' not in combined.columns:
            return 0.0
        tmp = combined[['impliedVolatility','openInterest']].copy()
        tmp = tmp.replace(0, np.nan).dropna()
        tmp = tmp[(tmp['impliedVolatility'] >= 0.05) &
                  (tmp['impliedVolatility'] <= 3.0)]
        if tmp.empty or tmp['openInterest'].sum() == 0:
            return 0.0
        return (tmp['impliedVolatility'] * tmp['openInterest']).sum() / tmp['openInterest'].sum()

    def expected_move_pct(current_price: float, atm_iv: float, dte: int) -> float:
        """
        IV Expected Move % = IV × √(DTE/365)
        ATM 기준 1σ 움직임 예상 범위.
        """
        if atm_iv <= 0 or dte <= 0:
            return 3.0  # fallback: 고정 3%
        return atm_iv * np.sqrt(dte / 365.0) * 100

    def moneyness_dynamic(strike: float, current_price: float,
                          side: str, em_pct: float) -> str:
        """
        em_pct (Expected Move %) 기반 동적 Moneyness.
        ATM: |strike/price - 1| < em_pct/100
        """
        if current_price <= 0:
            return 'N/A'
        r = strike / current_price
        lo = 1 - em_pct / 100
        hi = 1 + em_pct / 100
        if lo <= r <= hi:
            return 'ATM'
        if side == 'CALL':
            return 'ITM' if r < lo else 'OTM'
        else:
            return 'ITM' if r > hi else 'OTM'

    # ────────────────────────────────────────────────────
    # [개선③] IV 가중평균 — OI/Vol 이중 + Trim
    # ────────────────────────────────────────────────────
    def iv_weighted(df: pd.DataFrame,
                    weight_col: str = 'openInterest',
                    iv_lo: float = 0.05,
                    iv_hi: float = 3.0) -> float:
        """
        Trim(iv_lo~iv_hi) 후 weight_col 가중평균 IV.
        weight_col: 'openInterest' (누적 심리) 또는 'volume' (당일 심리)
        """
        if 'impliedVolatility' not in df.columns or weight_col not in df.columns:
            return 0.0
        tmp = df[['impliedVolatility', weight_col]].copy()
        tmp = tmp.replace(0, np.nan).dropna()
        tmp = tmp[(tmp['impliedVolatility'] >= iv_lo) &
                  (tmp['impliedVolatility'] <= iv_hi)]
        total_w = tmp[weight_col].sum()
        if total_w == 0:
            return 0.0
        return (tmp['impliedVolatility'] * tmp[weight_col]).sum() / total_w

    # ────────────────────────────────────────────────────
    # [개선④] SQLite ΔOI 스냅샷
    # ────────────────────────────────────────────────────
    DB_PATH = 'options_oi.db'
    IS_LOCAL = os.path.exists('.streamlit') or not os.environ.get('STREAMLIT_SHARING_MODE')

    def _get_db_conn():
        """SQLite 연결 (로컬). Cloud 환경에서는 session_state 사용."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS oi_snap (
                    snap_date TEXT, ticker TEXT, exp_date TEXT,
                    strike REAL, side TEXT,
                    oi REAL, volume REAL, last_price REAL, mid_price REAL,
                    PRIMARY KEY (snap_date, ticker, exp_date, strike, side)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_snap ON oi_snap(ticker,exp_date,strike,side)')
            conn.commit()
            return conn
        except Exception:
            return None

    def save_oi_snapshot(ticker_str: str, exp_date: str,
                         calls: pd.DataFrame, puts: pd.DataFrame):
        """오늘 날짜 키로 OI 스냅샷 저장 (이미 저장됐으면 스킵)."""
        today = datetime.now().strftime('%Y-%m-%d')
        key   = f"{ticker_str}_{exp_date}_{today}"

        # session_state 캐시 (Cloud/로컬 공통)
        if 'oi_snaps' not in st.session_state:
            st.session_state['oi_snaps'] = {}
        if key in st.session_state['oi_snaps']:
            return  # 이미 저장됨

        rows = []
        for side, df in [('CALL', calls), ('PUT', puts)]:
            for _, r in df.iterrows():
                mid = calc_mid_price(r)
                rows.append((today, ticker_str, exp_date,
                              float(r['strike']), side,
                              float(r.get('openInterest', 0) or 0),
                              float(r.get('volume', 0) or 0),
                              float(r.get('lastPrice', 0) or 0),
                              float(mid)))

        # session_state 저장
        st.session_state['oi_snaps'][key] = rows

        # SQLite 저장 (로컬)
        conn = _get_db_conn()
        if conn:
            try:
                conn.executemany(
                    'INSERT OR IGNORE INTO oi_snap VALUES (?,?,?,?,?,?,?,?,?)', rows)
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()

    def get_delta_oi(ticker_str: str, exp_date: str,
                     calls: pd.DataFrame, puts: pd.DataFrame,
                     current_price: float) -> pd.DataFrame:
        """
        오늘 OI - 전날 OI = ΔOI.
        반환: DataFrame with columns [side, strike, oi_today, oi_prev, delta_oi, volume, signal]
        """
        today    = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # 전날 데이터 조회 (SQLite → session_state 순서)
        prev_data = {}
        conn = _get_db_conn()
        if conn:
            try:
                cur = conn.execute(
                    'SELECT side,strike,oi,volume FROM oi_snap WHERE ticker=? AND exp_date=? AND snap_date=?',
                    (ticker_str, exp_date, yesterday))
                for row in cur.fetchall():
                    prev_data[(row[0], row[1])] = {'oi': row[2], 'vol': row[3]}
            except Exception:
                pass
            finally:
                conn.close()

        # session_state 폴백
        if not prev_data:
            prev_key = f"{ticker_str}_{exp_date}_{yesterday}"
            snaps = st.session_state.get('oi_snaps', {})
            if prev_key in snaps:
                for row in snaps[prev_key]:
                    prev_data[(row[4], row[3])] = {'oi': row[5], 'vol': row[6]}

        if not prev_data:
            return pd.DataFrame()

        lo = current_price * 0.7 if current_price > 0 else 0
        hi = current_price * 1.3 if current_price > 0 else 1e9

        records = []
        for side, df in [('CALL', calls), ('PUT', puts)]:
            df_f = df[(df['strike'] >= lo) & (df['strike'] <= hi)]
            for _, r in df_f.iterrows():
                k = (side, float(r['strike']))
                if k not in prev_data:
                    continue
                oi_t = float(r.get('openInterest', 0) or 0)
                oi_p = prev_data[k]['oi']
                vol  = float(r.get('volume', 0) or 0)
                d    = oi_t - oi_p
                # 신호 판정
                if vol > oi_p * 0.5 and d > 0:
                    sig = '🔥 신규 대형 베팅'
                elif vol > oi_p * 0.5 and d < 0:
                    sig = '✂️ 대형 청산'
                elif d > oi_p * 0.1:
                    sig = '📈 OI 증가'
                elif d < -oi_p * 0.1:
                    sig = '📉 OI 감소'
                else:
                    sig = '➖ 변화 미미'
                records.append({'side': side, 'strike': r['strike'],
                                 'oi_today': oi_t, 'oi_prev': oi_p,
                                 'delta_oi': d, 'volume': vol, 'signal': sig})

        if not records:
            return pd.DataFrame()
        df_d = pd.DataFrame(records)
        df_d = df_d[df_d['delta_oi'].abs() > 0].sort_values('delta_oi', ascending=False)
        return df_d.head(20)

    # ────────────────────────────────────────────────────
    # 기존 공통 유틸
    # ────────────────────────────────────────────────────
    def detect_uoa(df: pd.DataFrame, side: str,
                   current_price: float, em_pct: float,
                   voi_th: float = 5.0,
                   min_premium: float = 10_000) -> pd.DataFrame:
        """
        개선판 UOA:
        - Mid-Price Dollar Premium
        - 차등 Spread 필터 (ATM ≤30%, OTM ≤60%)
        - IV Expected Move 기반 동적 Moneyness
        """
        needed = [c for c in ['strike','volume','openInterest',
                               'lastPrice','bid','ask','impliedVolatility'] if c in df.columns]
        d = df[needed].copy()

        # Mid-Price
        d['mid_price']      = d.apply(calc_mid_price, axis=1)
        d['spread_r']       = d.apply(spread_ratio,   axis=1)
        d['dollar_premium'] = d['mid_price'] * d.get('volume', 0) * 100
        d['V_OI']           = d['volume'] / d['openInterest'].replace(0, np.nan)

        # 동적 Moneyness
        d['moneyness'] = d['strike'].apply(
            lambda s: moneyness_dynamic(s, current_price, side, em_pct))

        # 차등 Spread 필터: ATM ≤30%, OTM/ITM ≤60%
        def spread_limit(row):
            return 0.30 if row['moneyness'] == 'ATM' else 0.60
        d['spread_limit'] = d.apply(spread_limit, axis=1)

        filtered = d[
            (d['V_OI'] >= voi_th) &
            (d['dollar_premium'] >= min_premium) &
            (d['spread_r'] <= d['spread_limit'])
        ].copy()
        filtered['side'] = side
        return filtered.sort_values('dollar_premium', ascending=False).head(5)

    def get_mp_band(dte: int) -> float:
        """DTE 기반 Max Pain 계산 범위 (짧을수록 좁게)."""
        if dte <= 2:   return 0.15   # ±15%: DTE 1~2일, Deep OTM 제외
        elif dte <= 7: return 0.20   # ±20%: 1주일 이내
        elif dte <= 14: return 0.25  # ±25%: 2주 이내
        elif dte <= 30: return 0.30  # ±30%: 1개월 이내
        else:           return 0.40  # ±40%: 장기

    def calculate_max_pain(calls, puts, current_price: float = 0, dte: int = 60):
        """
        Max Pain 계산.
        DTE 기반 동적 band로 Deep OTM 잔여 OI 왜곡 방지.
        - DTE≤2: ±15% (NVDA $189 기준 $161~$218, $115 제외)
        - DTE>30: ±40%
        """
        band = get_mp_band(dte)
        if current_price > 0:
            lo_mp = current_price * (1 - band)
            hi_mp = current_price * (1 + band)
            calls = calls[(calls['strike'] >= lo_mp) & (calls['strike'] <= hi_mp)]
            puts  = puts [(puts ['strike'] >= lo_mp) & (puts ['strike'] <= hi_mp)]
        # OI 정수 정규화 (소수점 잔재 OI 제거)
        calls = calls.copy(); puts = puts.copy()
        calls['openInterest'] = calls['openInterest'].fillna(0).round().astype(int)
        puts ['openInterest'] = puts ['openInterest'].fillna(0).round().astype(int)
        # 실질 OI가 없는 행사가 제거
        calls = calls[calls['openInterest'] > 0]
        puts  = puts [puts ['openInterest'] > 0]
        strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
        if not strikes:
            return 0.0
        pain = {}
        for s in strikes:
            cp = ((s - calls.loc[calls['strike']<s,'strike'])
                  * calls.loc[calls['strike']<s,'openInterest']).sum()
            pp = ((puts.loc[puts['strike']>s,'strike'] - s)
                  * puts.loc[puts['strike']>s,'openInterest']).sum()
            pain[s] = cp + pp
        return min(pain, key=pain.get) if pain else 0.0

    def detect_ticker_type(info):
        qt = info.get('quoteType','').upper()
        if qt == 'ETF': return 'ETF'
        if qt in ('INDEX','MUTUALFUND'): return 'INDEX'
        return 'EQUITY'

    def get_pcr_thresholds(tt):
        if tt == 'ETF':    return 1.5, 1.0
        if tt == 'INDEX':  return 1.3, 0.85
        return 1.2, 0.7

    def pcr_divergence(pv, poi):
        if poi == 0: return 'signal-neut', 'PCR(OI)=0, 계산 불가'
        r = pv / poi
        if r > 1.5:
            return 'signal-bear', (f"PCR(Vol)/PCR(OI) = <strong>{r:.2f}배</strong> → "
                                   f"오늘 풋 거래가 누적 대비 급증 · 단기 공포/헤징 이벤트")
        elif r < 0.67:
            return 'signal-bull', (f"PCR(Vol)/PCR(OI) = <strong>{r:.2f}배</strong> → "
                                   f"오늘 콜 거래가 누적 대비 급증 · 단기 강세 모멘텀")
        return 'signal-neut', (f"PCR(Vol)/PCR(OI) = {r:.2f}배 → 당일 흐름과 누적 포지션 방향 일치")

    def vol_oi_signal(cv, pv, coi, poi):
        if coi > poi and cv > pv:   return 'bull', '📈 콜 OI 우세 + 콜 거래 활발 → 상승 추세 지속 가능'
        elif poi > coi and pv > cv: return 'bear', '📉 풋 OI 우세 + 풋 거래 활발 → 하락 추세/헤징 증가'
        elif coi > poi and pv > cv: return 'neut', '🔄 콜 OI 우세 but 풋 거래 활발 → 단기 조정 후 반등'
        else:                        return 'neut', '⚖️ 수급 혼재 → 방향성 불분명, 추가 지표 병행 필요'

    def pcr_label(v, bth=1.2, blth=0.7):
        if v > bth:   return 'signal-bull', f'PCR {v:.2f} — 풋 과쏠림(공포) · 역발상 반등 가능'
        elif v < blth: return 'signal-bear', f'PCR {v:.2f} — 콜 과쏠림(탐욕) · 조정 경계'
        return 'signal-neut', f'PCR {v:.2f} — 중립 구간'

    def add_vlines(fig, lines):
        for x_val, color, dash, label, yp in lines:
            fig.add_vline(x=x_val, line_dash=dash, line_color=color, line_width=1.5)
            if label:
                fig.add_annotation(x=x_val, y=yp, xref='x', yref='paper',
                    text=label, showarrow=False,
                    font=dict(color=color, size=10, family='monospace'),
                    bgcolor='rgba(15,23,42,.85)',
                    bordercolor=color, borderwidth=1, borderpad=3,
                    xanchor='left', yanchor='top', xshift=5)

    def sig(css, label, body):
        return f'<div class="signal-box {css}"><strong>{label}</strong> &nbsp;·&nbsp; {body}</div>'

    def mc(label, value, color, sub='', sub_color='#9ca3af'):
        return (f'<div class="mcard"><div class="mcard-label">{label}</div>'
                f'<div style="display:flex;align-items:baseline;">'
                f'<span class="mcard-value" style="color:{color};">{value}</span>'
                f'<span class="mcard-sub" style="color:{sub_color};">{sub}</span>'
                f'</div></div>')

    def fmt_p(v):
        if v >= 1_000_000: return f'${v/1_000_000:.1f}M'
        if v >= 1_000:     return f'${v/1_000:.0f}K'
        return f'${v:.0f}'

    def generate_with_fallback(prompt, api_key):
        genai.configure(api_key=api_key)
        models = ['gemini-2.0-flash-lite-preview-02-05','gemini-1.5-pro',
                  'gemini-1.5-flash','gemini-1.5-flash-8b']
        errs = []
        for m in models:
            try:
                r = genai.GenerativeModel(m).generate_content(prompt)
                return r.text, m
            except Exception as e:
                errs.append(f'[{m}: {str(e)[:60]}]'); time.sleep(0.5)
        raise Exception('모든 모델 실패: ' + ' / '.join(errs))

    # ── API 키 ──
    api_key     = st.secrets.get('GEMINI_API_KEY')
    has_api_key = api_key is not None
    if not has_api_key:
        st.sidebar.error('⚠️ Streamlit Secrets에 GEMINI_API_KEY 없음')

    # ── 사이드바 ──
    with st.sidebar:
        st.header('🔍 검색 설정')
        ticker_input  = st.text_input('티커 심볼 (예: AAPL, NVDA, SPY)', value='AAPL').upper()
        analysis_mode = st.radio('분석 모드', ['단일 만기일 분석', '전체 기간 통합 분석 (단/중/장기)'])
        ticker        = yf.Ticker(ticker_input)
        expirations   = []
        try:
            expirations = ticker.options
            if not expirations: st.error('옵션 데이터 없음')
        except: st.error('서버 연결 오류')

        selected_expiry = None
        if expirations and analysis_mode == '단일 만기일 분석':
            selected_expiry = st.selectbox('만기일 선택', expirations)

        st.markdown('---')
        st.markdown('**💾 ΔOI 데이터베이스**')
        if os.path.exists(DB_PATH):
            try:
                conn = _get_db_conn()
                cnt  = conn.execute('SELECT COUNT(DISTINCT snap_date||ticker) FROM oi_snap').fetchone()[0]
                conn.close()
                st.success(f'로컬 DB 활성 · {cnt}개 스냅샷')
            except: st.info('DB 초기화 중')
        else:
            st.info('첫 실행 시 자동 생성')
        snaps_in_mem = len(st.session_state.get('oi_snaps', {}))
        if snaps_in_mem:
            st.caption(f'메모리 캐시: {snaps_in_mem}개')

    # ── 현재가 / 종목 정보 ──
    current_price = 0; name = ticker_input; ticker_type = 'EQUITY'
    if ticker_input and expirations:
        try:
            info          = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            if not current_price:
                current_price = ticker.history(period='1d')['Close'].iloc[-1]
            name        = info.get('longName', ticker_input)
            ticker_type = detect_ticker_type(info)
        except: pass

        bear_th, bull_th = get_pcr_thresholds(ticker_type)
        type_label = {'ETF':'ETF','INDEX':'INDEX','EQUITY':'개별주'}.get(ticker_type,'개별주')
        type_cls   = {'ETF':'tb-etf','INDEX':'tb-idx','EQUITY':'tb-eq'}.get(ticker_type,'tb-eq')
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:8px;">'
            f'<span style="font-size:1.25rem;font-weight:700;">📊 {name} ({ticker_input}) | ${current_price:,.2f}</span>'
            f'<span class="{type_cls}">{type_label} · PCR >{bear_th}/{bull_th}</span>'
            f'</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # 모드 1: 단일 만기일 분석
    # ══════════════════════════════════════════════════════
    if analysis_mode == '단일 만기일 분석' and selected_expiry:
        with st.spinner(f"'{selected_expiry}' 옵션 체인 분석 중..."):
            opt   = ticker.option_chain(selected_expiry)
            calls, puts = opt.calls.copy(), opt.puts.copy()

            # DTE 계산 (실제값 보존, 표시/계산용은 min 1)
            dte_real = (datetime.strptime(selected_expiry,'%Y-%m-%d') - datetime.today()).days
            dte      = max(dte_real, 1)

            # 단기 만기 경고 배너
            if dte_real <= 0:
                st.error('⚠️ **만기 당일(DTE=0):** OI·IV 데이터 거의 소진. 모든 지표 신뢰도 매우 낮음.')
            elif dte_real <= 2:
                st.warning(f'⚠️ **초단기 만기(DTE={dte_real}일):** 대부분 OI 청산. Max Pain·OI Wall·IV 신뢰도 낮음.')
            elif dte_real <= 5:
                st.info(f'ℹ️ **단기 만기(DTE={dte_real}일):** IV 데이터 불안정 가능. EM 수치는 참고용으로만 활용.')

            # [개선②] ATM IV → Expected Move
            atm_iv    = get_atm_iv(calls, puts, current_price)
            em_pct    = expected_move_pct(current_price, atm_iv, dte)
            em_source = 'ATM IV 기반' if atm_iv > 0 else '⚠️ Fallback(ATM IV=0, 고정 3%)'

            # [개선④] OI 스냅샷 저장
            save_oi_snapshot(ticker_input, selected_expiry, calls, puts)

            # 필터 범위: EM×2 기반, 최소 ±15% 보장 (DTE 짧을 때 범위 축소 방지)
            em_band = max(em_pct * 2, 15.0)
            lo = current_price * (1 - em_band / 100) if current_price > 0 else 0
            hi = current_price * (1 + em_band / 100) if current_price > 0 else 1e9
            lo = max(lo, current_price * 0.6)
            hi = min(hi, current_price * 1.4)
            cc = calls[(calls['strike']>=lo)&(calls['strike']<=hi)].copy()
            pc = puts [(puts ['strike']>=lo)&(puts ['strike']<=hi)].copy()

            cv  = calls['volume'].sum();                pv  = puts['volume'].sum()
            coi = calls['openInterest'].fillna(0).sum(); poi = puts['openInterest'].fillna(0).sum()
            pcr    = pv/cv    if cv>0   else 0
            pcr_oi = poi/coi  if coi>0  else 0

            # [버그수정①] Max Pain: 현재가 ±40% 필터 적용
            # 전체 체인 사용 시 Deep OTM 잔여 OI가 결과 왜곡 → $175 같은 엉뚱한 값 방지
            mp     = calculate_max_pain(calls, puts, current_price, dte=dte_real)
            mp_gap = (mp - current_price) / current_price * 100 if current_price > 0 else 0

            # OI Wall 신뢰도 체크 (DTE 짧으면 OI 거의 없음)
            max_call_oi = cc['openInterest'].fillna(0).max() if not cc.empty else 0
            max_put_oi  = pc['openInterest'].fillna(0).max() if not pc.empty else 0
            oi_wall_reliable = (max_call_oi >= 100 or max_put_oi >= 100)

            # [개선③] IV OI가중+Trim / Volume가중+Trim
            iv_oi_c  = iv_weighted(cc, 'openInterest') * 100
            iv_vol_c = iv_weighted(cc, 'volume')       * 100
            iv_oi_p  = iv_weighted(pc, 'openInterest') * 100
            iv_vol_p = iv_weighted(pc, 'volume')       * 100

            pcr_color    = '#ff4d6d' if pcr>bear_th else ('#00e5a0' if pcr<bull_th else '#f5a623')
            pcr_sub      = 'Bearish ▼' if pcr>bear_th else ('Bullish ▲' if pcr<bull_th else 'Neutral')
            mp_gap_color = '#ff4d6d' if mp_gap<-2 else ('#00e5a0' if mp_gap>2 else '#9ca3af')

            # ── 메트릭 카드 ──
            row1 = st.columns(4)
            with row1[0]: st.markdown(mc('CALL 거래량', f'{int(cv):,}', '#00e5a0'), unsafe_allow_html=True)
            with row1[1]: st.markdown(mc('PUT 거래량',  f'{int(pv):,}', '#ff4d6d'), unsafe_allow_html=True)
            with row1[2]: st.markdown(mc('PCR (Volume)', f'{pcr:.2f}', '#f3f4f6', pcr_sub, pcr_color), unsafe_allow_html=True)
            mp_lbl = 'Max Pain ⚠️' if dte_real <= 2 else 'Max Pain'
            with row1[3]: st.markdown(mc(mp_lbl, f'${mp:,.0f}' if mp > 0 else 'N/A', '#fb923c', f'({mp_gap:+.1f}%)', mp_gap_color), unsafe_allow_html=True)

            st.markdown('<br>', unsafe_allow_html=True)
            row2 = st.columns(4)
            with row2[0]: st.markdown(mc('IV Call (OI가중)', f'{iv_oi_c:.1f}%',  '#00e5a0', f'Vol가중:{iv_vol_c:.1f}%', '#6ee7b7'), unsafe_allow_html=True)
            with row2[1]: st.markdown(mc('IV Put (OI가중)',  f'{iv_oi_p:.1f}%',  '#ff4d6d', f'Vol가중:{iv_vol_p:.1f}%', '#fca5a5'), unsafe_allow_html=True)
            with row2[2]: st.markdown(mc('IV Skew (Put-Call)', f'{iv_oi_p-iv_oi_c:+.1f}%p', '#a78bfa'), unsafe_allow_html=True)
            em_color = '#9ca3af' if atm_iv > 0 else '#fbbf24'
            with row2[3]: st.markdown(mc('Expected Move', f'±{em_pct:.1f}%', '#fb923c', em_source, em_color), unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)

            # ── OI 소수점 정규화 (수평선 버그 수정) ──
            cc['openInterest'] = cc['openInterest'].fillna(0).round().astype(int)
            pc['openInterest'] = pc['openInterest'].fillna(0).round().astype(int)
            cc_oi = cc[cc['openInterest'] > 0]   # 실질 OI 있는 행만
            pc_oi = pc[pc['openInterest'] > 0]

            # x축 공통 범위 (쏠림 방지)
            all_strikes = pd.concat([cc['strike'], pc['strike']])
            if not all_strikes.empty:
                x_lo = max(all_strikes.min() - 2.5, lo - 2.5)
                x_hi = min(all_strikes.max() + 2.5, hi + 2.5)
            else:
                x_lo, x_hi = lo, hi
            xaxis_cfg = dict(range=[x_lo, x_hi])

            # ── 차트 1: 거래량 (Call↑ / Put↓, 텍스트 레이블 포함) ──
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=cc['strike'], y=cc['volume'], name='Call Vol', marker_color='#00e5a0',
                text=cc['volume'].apply(lambda v: f'{int(v/1000)}K' if v>=1000 else str(int(v)) if v>0 else ''),
                textposition='outside', textfont=dict(size=9,color='#00e5a0')
            ))
            fig.add_trace(go.Bar(
                x=pc['strike'], y=-pc['volume'], name='Put Vol', marker_color='#ff4d6d',
                text=pc['volume'].apply(lambda v: f'-{int(v/1000)}K' if v>=1000 else (f'-{int(v)}' if v>0 else '')),
                textposition='outside', textfont=dict(size=9,color='#ff4d6d')
            ))
            vl = []
            if current_price>0: vl.append((current_price,'white','dash',f'현재가 ${current_price:,.2f}',0.97))
            if mp>0:             vl.append((mp,'#fb923c','dot',f'Max Pain ${mp:,.0f} (DTE band ±{get_mp_band(dte_real)*100:.0f}%)',0.82))
            add_vlines(fig, vl)
            fig.update_layout(
                title=f'① 행사가별 거래량 · 만기:{selected_expiry} · DTE:{dte_real}일 · EM:±{em_pct:.1f}%',
                barmode='relative', template='plotly_dark', height=420, hovermode='x unified',
                xaxis=xaxis_cfg, yaxis_title='계약수 (Call↑ / Put↓)',
                legend=dict(orientation='h', y=1.02))
            st.plotly_chart(fig, use_container_width=True)

            # ── 차트 2: OI Wall (실질 OI만 표시) ──
            if not oi_wall_reliable:
                st.warning(f'⚠️ **OI Wall 신뢰도 낮음** (최대 OI={max(max_call_oi,max_put_oi):.0f}): '
                           f'DTE={dte_real}일 만기 직전 OI 소진. 참고용으로만 활용.')
            fig_oi = go.Figure()
            if not cc_oi.empty:
                fig_oi.add_trace(go.Bar(
                    x=cc_oi['strike'], y=cc_oi['openInterest'], name='Call OI',
                    marker_color='rgba(0,229,160,.7)',
                    text=cc_oi['openInterest'].apply(lambda v: f'{int(v/1000)}K' if v>=1000 else str(int(v))),
                    textposition='outside', textfont=dict(size=9,color='#6ee7b7')
                ))
            if not pc_oi.empty:
                fig_oi.add_trace(go.Bar(
                    x=pc_oi['strike'], y=-pc_oi['openInterest'], name='Put OI',
                    marker_color='rgba(255,77,109,.7)',
                    text=pc_oi['openInterest'].apply(lambda v: f'-{int(v/1000)}K' if v>=1000 else f'-{int(v)}'),
                    textposition='outside', textfont=dict(size=9,color='#fca5a5')
                ))
            vlo = []
            if current_price>0: vlo.append((current_price,'white','dash',f'현재가 ${current_price:,.2f}',0.97))
            if mp>0:             vlo.append((mp,'#fb923c','dot',f'Max Pain ${mp:,.0f}',0.82))
            if not cc_oi.empty and not pc_oi.empty and oi_wall_reliable:
                cow  = cc_oi.loc[cc_oi['openInterest'].idxmax(),'strike']
                pow_ = pc_oi.loc[pc_oi['openInterest'].idxmax(),'strike']
                vlo.append((cow,'#00e5a0','dot',f'Call OI Wall(저항) ${cow:,.0f}',0.67))
                vlo.append((pow_,'#ff4d6d','dot',f'Put OI Wall(지지) ${pow_:,.0f}{'⚠️동일' if pow_==cow else ''}',0.52))
            add_vlines(fig_oi, vlo)
            oi_sfx = ' ⚠️ 신뢰도 낮음(DTE 단기)' if not oi_wall_reliable else ''
            fig_oi.update_layout(
                title=f'② 행사가별 미결제약정 — OI Wall{oi_sfx}',
                barmode='relative', template='plotly_dark', height=420, hovermode='x unified',
                xaxis=xaxis_cfg, yaxis_title='OI (Call↑ / Put↓)',
                legend=dict(orientation='h', y=1.02))
            st.plotly_chart(fig_oi, use_container_width=True)

            # ── 차트 3: IV Smile (행사가별 내재변동성) ──
            iv_c_smile = cc[cc['impliedVolatility'].between(0.05,3.0)][['strike','impliedVolatility']].copy() if 'impliedVolatility' in cc.columns else pd.DataFrame()
            iv_p_smile = pc[pc['impliedVolatility'].between(0.05,3.0)][['strike','impliedVolatility']].copy() if 'impliedVolatility' in pc.columns else pd.DataFrame()
            if not iv_c_smile.empty or not iv_p_smile.empty:
                fig_iv = go.Figure()
                if not iv_c_smile.empty:
                    fig_iv.add_trace(go.Scatter(
                        x=iv_c_smile['strike'], y=iv_c_smile['impliedVolatility']*100,
                        mode='lines+markers', name='Call IV(%)',
                        line=dict(color='#00e5a0',width=2), marker=dict(size=5)))
                if not iv_p_smile.empty:
                    fig_iv.add_trace(go.Scatter(
                        x=iv_p_smile['strike'], y=iv_p_smile['impliedVolatility']*100,
                        mode='lines+markers', name='Put IV(%)',
                        line=dict(color='#ff4d6d',width=2,dash='dot'), marker=dict(size=5)))
                if current_price>0:
                    fig_iv.add_vline(x=current_price,line_dash='dash',line_color='white',
                        annotation_text=f'ATM ${current_price:,.0f}',annotation_position='top right')
                fig_iv.update_layout(
                    title='③ IV Smile — 행사가별 내재변동성 (낮을수록 ATM, 높을수록 OTM 공포 프리미엄)',
                    template='plotly_dark', height=360, hovermode='x unified',
                    xaxis=xaxis_cfg, yaxis_title='내재변동성 IV (%)',
                    legend=dict(orientation='h',y=1.02))
                st.plotly_chart(fig_iv, use_container_width=True)

            # ── ΔOI 차트 ──
            df_doi = get_delta_oi(ticker_input, selected_expiry, calls, puts, current_price)
            if not df_doi.empty:
                st.markdown('#### 📊 ΔOI — 전일 대비 미결제약정 증감')
                fig_d = go.Figure()
                call_d = df_doi[df_doi['side']=='CALL']
                put_d  = df_doi[df_doi['side']=='PUT']
                if not call_d.empty:
                    fig_d.add_trace(go.Bar(x=call_d['strike'], y=call_d['delta_oi'],
                        name='Call ΔOI', marker_color='rgba(0,229,160,.8)'))
                if not put_d.empty:
                    fig_d.add_trace(go.Bar(x=put_d['strike'], y=-put_d['delta_oi'],
                        name='Put ΔOI',  marker_color='rgba(255,77,109,.8)'))
                if current_price>0:
                    fig_d.add_vline(x=current_price, line_dash='dash', line_color='white')
                fig_d.add_hline(y=0, line_color='#475569', line_width=1)
                fig_d.update_layout(title='ΔOI (양수=신규진입, 음수=청산/롤오버)',
                    barmode='relative', template='plotly_dark', height=360, hovermode='x unified')
                st.plotly_chart(fig_d, use_container_width=True)

                # ΔOI 테이블
                doi_disp = df_doi.copy()
                doi_disp.columns = ['구분','행사가','OI(오늘)','OI(전일)','ΔOI','거래량','신호']
                st.dataframe(doi_disp, use_container_width=True)
            else:
                st.info('💾 ΔOI: 데이터 수집 중 — 내일 재방문 시 전일 대비 OI 증감 표시')

            # ── 이론 신호 ──
            st.markdown('### 🧠 옵션 이론 신호 분석')

            s1,m1_ = pcr_label(pcr, bear_th, bull_th)
            st.markdown(sig(s1,f'① PCR(Volume) [{type_label}기준 >{bear_th}/{bull_th}]',m1_), unsafe_allow_html=True)
            s2,m2_ = pcr_label(pcr_oi, bear_th, bull_th)
            st.markdown(sig(s2,'② PCR(OI) 누적 포지션',m2_), unsafe_allow_html=True)
            dc3,dm3 = pcr_divergence(pcr, pcr_oi)
            st.markdown(sig(dc3,'③ PCR 내부 다이버전스 (비율 기반)',dm3), unsafe_allow_html=True)

            if mp>0:
                mc4 = 'signal-bear' if mp_gap<-2 else ('signal-bull' if mp_gap>2 else 'signal-neut')
                dte_warn = f' <span style="color:#fbbf24;font-size:11px;">(⚠️ DTE={dte_real}일 — 신뢰도 낮음)</span>' if dte_real <= 2 else ''
                mb4 = (f'Max Pain ${mp:,.0f} — 현재가 대비 <strong>{mp_gap:.1f}%</strong> 아래 → 하락 수렴 압력{dte_warn}' if mp_gap<-2 else
                       (f'Max Pain ${mp:,.0f} — 현재가 대비 <strong>{mp_gap:+.1f}%</strong> 위 → 상승 수렴 압력{dte_warn}' if mp_gap>2 else
                        f'현재가 ≈ Max Pain ${mp:,.0f} → 횡보 압력{dte_warn}'))
                st.markdown(sig(mc4,'④ Max Pain 수렴 신호',mb4), unsafe_allow_html=True)

            vc5,vm5 = vol_oi_signal(cv,pv,coi,poi)
            st.markdown(sig(f'signal-{vc5}','⑤ Volume × OI 교차 신호',vm5), unsafe_allow_html=True)

            if not cc.empty and not pc.empty:
                cow  = cc.loc[cc['openInterest'].fillna(0).idxmax(),'strike']
                pow_ = pc.loc[pc['openInterest'].fillna(0).idxmax(),'strike']
                if not oi_wall_reliable:
                    # OI 신뢰도 낮음 → 경고만
                    st.markdown(sig('signal-neut','⑥ OI Wall 지지/저항',
                        f'⚠️ <strong>OI 데이터 불충분</strong> (최대 Call OI={max_call_oi:.0f}, Put OI={max_put_oi:.0f}) — '
                        f'DTE={dte_real}일 만기 직전 OI 소진. Wall 신호 신뢰 불가.'),
                        unsafe_allow_html=True)
                elif cow == pow_:
                    # Call OI Wall = Put OI Wall 동일 → 데이터 sparse
                    st.markdown(sig('signal-neut','⑥ OI Wall 지지/저항',
                        f'⚠️ <strong>Call OI Wall = Put OI Wall = ${cow:,.0f} (동일값)</strong> — '
                        f'OI가 특정 행사가에만 집중되거나 데이터 부족. 지지·저항 구분 불가.'),
                        unsafe_allow_html=True)
                else:
                    wc6 = 'signal-bear' if current_price>cow else ('signal-bull' if current_price<pow_ else 'signal-neut')
                    wb6 = (f'Call OI Wall(저항):<strong>${cow:,.0f}</strong> · Put OI Wall(지지):<strong>${pow_:,.0f}</strong>'
                           +(' · 현재가가 Call OI Wall 돌파' if current_price>cow
                             else (' · 현재가가 Put OI Wall 하회 → 추가 하락 리스크' if current_price<pow_
                                  else f' · 현재가 두 Wall 사이 → 범위 내 등락')))
                    st.markdown(sig(wc6,'⑥ OI Wall 지지/저항',wb6), unsafe_allow_html=True)

            # IV Skew
            iv_skew = iv_oi_p - iv_oi_c
            ics = 'signal-bear' if iv_skew>5 else ('signal-bull' if iv_skew<-3 else 'signal-neut')
            ims = (f'IV Skew = <strong>{iv_skew:+.1f}%p</strong> (OI가중) / {iv_vol_p-iv_vol_c:+.1f}%p (Vol가중) → 풋 공포 프리미엄 과다' if iv_skew>5 else
                   (f'IV Skew = <strong>{iv_skew:+.1f}%p</strong> → 콜 탐욕 프리미엄' if iv_skew<-3 else
                    f'IV Skew = {iv_skew:+.1f}%p → 콜·풋 IV 균형'))
            st.markdown(sig(ics,'⑦ IV Skew (OI가중+Trim / Vol가중+Trim)',ims), unsafe_allow_html=True)

            # UOA (개선판)
            uoa_c = detect_uoa(cc,'CALL',current_price,em_pct)
            uoa_p = detect_uoa(pc,'PUT', current_price,em_pct)
            uoa_all = pd.concat([uoa_c,uoa_p]).sort_values('dollar_premium',ascending=False)
            if not uoa_all.empty:
                otm_c = len(uoa_all[(uoa_all['side']=='CALL')&(uoa_all['moneyness']=='OTM')])
                otm_p = len(uoa_all[(uoa_all['side']=='PUT') &(uoa_all['moneyness']=='OTM')])
                u8c = 'signal-bull' if otm_c>otm_p else ('signal-bear' if otm_p>otm_c else 'signal-neut')
                st.markdown(sig(u8c,'⑧ UOA (Mid-Price·동적 Moneyness·차등Spread 필터)',
                    f'V/OI≥5 & $10K+ & 스프레드 필터 통과 <strong>{len(uoa_all)}건</strong> · OTM콜{otm_c}/OTM풋{otm_p}'),
                    unsafe_allow_html=True)
                ud = uoa_all[['side','moneyness','strike','mid_price','dollar_premium','V_OI','spread_r']].copy()
                ud.columns = ['구분','Moneyness','행사가','Mid가격','Dollar Premium','V/OI','Spread%']
                ud['Dollar Premium'] = ud['Dollar Premium'].apply(fmt_p)
                ud['V/OI']           = ud['V/OI'].apply(lambda x: f'{x:.1f}x')
                ud['Spread%']        = ud['Spread%'].apply(lambda x: f'{x*100:.0f}%')
                st.dataframe(ud, use_container_width=True)
            else:
                st.markdown(sig('signal-neut','⑧ UOA','조건 통과 행사가 없음'), unsafe_allow_html=True)

            # ── AI 프롬프트 ──
            cow_v  = cc.loc[cc['openInterest'].fillna(0).idxmax(),'strike'] if not cc.empty else 0
            pow_v_ = pc.loc[pc['openInterest'].fillna(0).idxmax(),'strike'] if not pc.empty else 0
            uoa_str = uoa_all[['side','moneyness','strike','dollar_premium','V_OI']].to_string(index=False) if not uoa_all.empty else '없음'
            doi_str = df_doi[['side','strike','oi_today','oi_prev','delta_oi','signal']].to_string(index=False) if not df_doi.empty else '전일 데이터 없음 (수집 중)'

            # 신뢰도 경고 문구 (프롬프트용)
            data_quality_note = ''
            if dte_real <= 2:
                data_quality_note = f'\n⚠️ 데이터 신뢰도 주의: DTE={dte_real}일로 OI 대부분 소진. Max Pain/OI Wall/IV 신뢰도 낮음.'
            elif atm_iv == 0:
                data_quality_note = f'\n⚠️ EM Fallback: ATM IV=0으로 Expected Move는 고정 3% 사용. DTE 짧거나 IV 데이터 없음.'
            oi_wall_note = f'Call OI Wall:{cow_v:,.0f} / Put OI Wall:{pow_v_:,.0f}' if oi_wall_reliable else '⚠️ OI Wall 신뢰 불가(OI 소진)'

            # 상위 OI 집중 행사가 추출
            top_call_oi = cc_oi.nlargest(3,'openInterest')[['strike','openInterest']].to_string(index=False) if not cc_oi.empty else '없음'
            top_put_oi  = pc_oi.nlargest(3,'openInterest')[['strike','openInterest']].to_string(index=False) if not pc_oi.empty else '없음'
            # IV Smile 극값
            iv_c_min = iv_c_smile.loc[iv_c_smile['impliedVolatility'].idxmin()].to_dict() if not iv_c_smile.empty else {}
            iv_p_skew_note = f"Put IV 가장 높은 행사가: ${iv_p_smile.loc[iv_p_smile['impliedVolatility'].idxmax(),'strike']:,.0f} ({iv_p_smile['impliedVolatility'].max()*100:.0f}%)" if not iv_p_smile.empty else ''

            prompt = f"""당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 종합하여 시장 심리를 심층 분석하세요.

═══════════════════════════════════════
[분석 대상]
═══════════════════════════════════════
종목: {ticker_input} ({name}) | 유형: {type_label}
만기일: {selected_expiry} | DTE: {dte_real}일 | 현재가: ${current_price:,.2f}
PCR 판단 기준: Bearish>{bear_th} / Bullish<{bull_th}{data_quality_note}
Max Pain 계산 band: ±{get_mp_band(dte_real)*100:.0f}% (DTE 기반 동적 적용)

═══════════════════════════════════════
[수급 — Volume & Open Interest]
═══════════════════════════════════════
콜 거래량: {cv:,.0f} | 풋 거래량: {pv:,.0f}
콜 OI: {coi:,.0f} | 풋 OI: {poi:,.0f}
PCR(거래량기준): {pcr:.2f}
PCR(OI기준): {pcr_oi:.2f}
PCR 내부 다이버전스 비율: {pcr/pcr_oi if pcr_oi>0 else 0:.2f}배 (1.5↑=오늘풋급증/0.67↓=오늘콜급증)
전체 콜/풋 OI 비율: {coi/(poi if poi>0 else 1):.2f} (1이상=콜 포지션 우세)

═══════════════════════════════════════
[내재변동성 IV — OI가중+Vol가중+Trim(5%~300%)]
═══════════════════════════════════════
Call IV: OI가중 {iv_oi_c:.1f}% / Vol가중 {iv_vol_c:.1f}% (차이:{iv_oi_c-iv_vol_c:+.1f}%p)
Put IV:  OI가중 {iv_oi_p:.1f}% / Vol가중 {iv_vol_p:.1f}% (차이:{iv_oi_p-iv_vol_p:+.1f}%p)
IV Skew (Put-Call, OI기준): {iv_skew:+.1f}%p → {'풋 공포 프리미엄 과다' if iv_skew>5 else ('콜 탐욕 프리미엄' if iv_skew<-3 else '균형')}
Expected Move (±1σ, DTE={dte_real}일): ±{em_pct:.1f}% = ±${current_price*em_pct/100:.1f} [{em_source}]
{iv_p_skew_note}

═══════════════════════════════════════
[Max Pain & OI Wall]
═══════════════════════════════════════
Max Pain: ${mp:,.0f} (현재가 대비 {mp_gap:+.1f}% — {'하락 수렴 압력' if mp_gap<-2 else ('상승 수렴 압력' if mp_gap>2 else '횡보 압력')})
{oi_wall_note}
Call OI 상위 3 행사가:
{top_call_oi}
Put OI 상위 3 행사가:
{top_put_oi}

═══════════════════════════════════════
[UOA — 스마트 머니 탐지 (Mid-Price + 차등Spread 필터)]
═══════════════════════════════════════
{uoa_str}

═══════════════════════════════════════
[ΔOI — 전일 대비 미결제약정 증감]
═══════════════════════════════════════
{doi_str}

═══════════════════════════════════════
[심층 분석 지시사항]
═══════════════════════════════════════
1. 수급 종합: {type_label} 구조적 특성 반영, PCR(Vol) vs PCR(OI) 다이버전스 해석
2. IV 분석: OI가중 vs Vol가중 차이, IV Skew의 공포/탐욕 의미, Expected Move 활용
3. Max Pain 시나리오: DTE={dte_real}일 기준 만기일까지 주가 수렴 경로 예측
4. OI Wall 지지/저항: 상위 3개 행사가별 Call/Put OI 집중도가 갖는 의미
5. ΔOI 스마트 머니: Vol↑+ΔOI↑(신규진입) vs Vol↑+ΔOI↓(청산) 구분 분석
6. UOA 분석: OTM/ATM/ITM 비율, Dollar Premium 규모, 방향성 추론
7. 리스크 시나리오: Bull/Bear/Neutral 3가지 시나리오와 핵심 가격 레벨
8. 데이터 신뢰도 감안: DTE={dte_real}일이므로 신뢰도 제한 사항 명시
초보 투자자도 이해할 수 있도록 친절한 한글 마크다운으로 핵심만 명확히 정리하세요."""

    # ══════════════════════════════════════════════════════
    # 모드 2: 전체 기간 통합 분석
    # ══════════════════════════════════════════════════════
    elif analysis_mode == '전체 기간 통합 분석 (단/중/장기)' and expirations:
        st.info(f'💡 {type_label} | PCR 기준 >{bear_th}/{bull_th} | Mid-Price·동적Moneyness·IV Trim·ΔOI 전체 적용')

        with st.spinner('전체 만기일 데이터 수집 중... (10~30초 소요)'):
            today = datetime.today()
            TERMS = ['Short (단기/30일내)', 'Mid (중기/30~90일)', 'Long (장기/90일이상)']

            term_data = {t: dict(call_vol=0,put_vol=0,call_oi=0,put_oi=0,
                                 iv_wsum_oi_c=0.,iv_woi_c=0.,iv_wsum_vol_c=0.,iv_wvol_c=0.,
                                 iv_wsum_oi_p=0.,iv_woi_p=0.,iv_wsum_vol_p=0.,iv_wvol_p=0.,
                                 nearest_days=9999,nearest_exp=None,exp_count=0)
                         for t in TERMS}

            strike_oi   = {}
            uoa_records = []
            expiry_pcr  = []

            progress_bar = st.progress(0)
            for i, exp_date in enumerate(expirations):
                try:
                    days = (datetime.strptime(exp_date,'%Y-%m-%d') - today).days
                    cat  = TERMS[0] if days<=30 else TERMS[1] if days<=90 else TERMS[2]
                    td   = term_data[cat]; td['exp_count'] += 1

                    opt  = ticker.option_chain(exp_date)
                    c, p = opt.calls.copy(), opt.puts.copy()

                    # [개선④] 스냅샷 저장 (근접 만기만)
                    if days <= 60:
                        save_oi_snapshot(ticker_input, exp_date, c, p)

                    cv_ = c['volume'].sum()                 if 'volume'       in c else 0
                    pv_ = p['volume'].sum()                  if 'volume'       in p else 0
                    coi_= c['openInterest'].fillna(0).sum()  if 'openInterest' in c else 0
                    poi_= p['openInterest'].fillna(0).sum()  if 'openInterest' in p else 0
                    td['call_vol']+=cv_; td['put_vol']+=pv_
                    td['call_oi'] +=coi_; td['put_oi']+=poi_

                    # [개선③] OI가중+Vol가중 IV Trim 누적
                    for col_side, df_s, wsum_oi, woi, wsum_vol, wvol in [
                        ('call','impliedVolatility' if 'impliedVolatility' in c.columns else None,
                         'iv_wsum_oi_c','iv_woi_c','iv_wsum_vol_c','iv_wvol_c'),
                        ('put', 'impliedVolatility' if 'impliedVolatility' in p.columns else None,
                         'iv_wsum_oi_p','iv_woi_p','iv_wsum_vol_p','iv_wvol_p'),
                    ]:
                        df_use = c if col_side=='call' else p
                        if 'impliedVolatility' not in df_use.columns: continue
                        if 'openInterest' not in df_use.columns: continue
                        tmp = df_use[['impliedVolatility','openInterest','volume']].copy()
                        tmp = tmp.replace(0,np.nan).dropna()
                        tmp = tmp[(tmp['impliedVolatility']>=0.05)&(tmp['impliedVolatility']<=3.0)]
                        if tmp.empty: continue
                        td[wsum_oi]  += (tmp['impliedVolatility']*tmp['openInterest']).sum()
                        td[woi]      += tmp['openInterest'].sum()
                        if 'volume' in tmp.columns:
                            td[wsum_vol] += (tmp['impliedVolatility']*tmp['volume']).sum()
                            td[wvol]     += tmp['volume'].sum()

                    if days>=0 and days<td['nearest_days']:
                        td['nearest_days']=days; td['nearest_exp']=exp_date

                    lo2 = max(current_price*0.7, 0); hi2 = current_price*1.3 if current_price>0 else 1e9
                    c_w = c[(c['strike']>=lo2)&(c['strike']<=hi2)].copy() if current_price>0 else c.copy()
                    p_w = p[(p['strike']>=lo2)&(p['strike']<=hi2)].copy() if current_price>0 else p.copy()

                    # OI Wall 집계
                    for _, row in c_w.iterrows():
                        s=row['strike']; strike_oi.setdefault(s,[0,0])
                        strike_oi[s][0] += row.get('openInterest',0) or 0
                    for _, row in p_w.iterrows():
                        s=row['strike']; strike_oi.setdefault(s,[0,0])
                        strike_oi[s][1] += row.get('openInterest',0) or 0

                    # [개선②] 동적 Moneyness UOA
                    atm_iv_exp = get_atm_iv(c, p, current_price)
                    em_exp     = expected_move_pct(current_price, atm_iv_exp, max(days,1))
                    for side2, df_s in [('CALL',c_w),('PUT',p_w)]:
                        uoa_tmp = detect_uoa(df_s, side2, current_price, em_exp)
                        for _, row in uoa_tmp.iterrows():
                            uoa_records.append({
                                'exp_date':exp_date,'term':cat.split(' ')[0],
                                'side':side2,'moneyness':row['moneyness'],
                                'strike':row['strike'],'volume':row.get('volume',0),
                                'openInterest':row.get('openInterest',0),
                                'V_OI':row['V_OI'],'dollar_premium':row['dollar_premium'],
                                'mid_price':row['mid_price'],'days':days
                            })

                    expiry_pcr.append({'exp_date':exp_date,'days':days,'term':cat.split(' ')[0],
                        'pcr_vol':pv_/cv_ if cv_>0 else np.nan,
                        'pcr_oi': poi_/coi_ if coi_>0 else np.nan,
                        'call_vol':cv_,'put_vol':pv_})
                except: pass
                progress_bar.progress((i+1)/len(expirations))
            progress_bar.empty()

            # ── 후처리 ──
            df_terms = pd.DataFrame(term_data).T
            df_terms['PCR (Volume)'] = df_terms['put_vol']/df_terms['call_vol']
            df_terms['PCR (OI)']     = df_terms['put_oi'] /df_terms['call_oi']
            df_terms['IV_OI_C%']     = (df_terms['iv_wsum_oi_c'] /df_terms['iv_woi_c'].replace(0,np.nan)*100).fillna(0)
            df_terms['IV_Vol_C%']    = (df_terms['iv_wsum_vol_c']/df_terms['iv_wvol_c'].replace(0,np.nan)*100).fillna(0)
            df_terms['IV_OI_P%']     = (df_terms['iv_wsum_oi_p'] /df_terms['iv_woi_p'].replace(0,np.nan)*100).fillna(0)
            df_terms['IV_Vol_P%']    = (df_terms['iv_wsum_vol_p']/df_terms['iv_wvol_p'].replace(0,np.nan)*100).fillna(0)
            df_terms['IV_Skew_OI']   = df_terms['IV_OI_P%']  - df_terms['IV_OI_C%']
            df_terms['IV_Skew_Vol']  = df_terms['IV_Vol_P%'] - df_terms['IV_Vol_C%']
            df_terms.fillna(0, inplace=True)

            mp_per_term = {}
            for t in TERMS:
                ne=term_data[t]['nearest_exp']
                if ne:
                    try:
                        o2=ticker.option_chain(ne); mp_per_term[t]=calculate_max_pain(o2.calls,o2.puts,current_price,dte=term_data[t]["nearest_days"])
                    except: mp_per_term[t]=0
                else: mp_per_term[t]=0

            df_wall = pd.DataFrame([(s,v[0],v[1]) for s,v in sorted(strike_oi.items())],
                                   columns=['strike','call_oi','put_oi'])
            cow_all = df_wall.loc[df_wall['call_oi'].idxmax(),'strike'] if not df_wall.empty else 0
            pow_all = df_wall.loc[df_wall['put_oi'].idxmax(), 'strike'] if not df_wall.empty else 0

            df_uoa = (pd.DataFrame(uoa_records).sort_values('dollar_premium',ascending=False)
                      .drop_duplicates(subset=['side','strike']).head(15)
                      if uoa_records else pd.DataFrame())

            df_pcr_sc = pd.DataFrame(expiry_pcr).dropna(subset=['pcr_vol'])

            total_cv  = df_terms['call_vol'].sum(); total_pv = df_terms['put_vol'].sum()
            total_coi = df_terms['call_oi'].sum();  total_poi= df_terms['put_oi'].sum()
            tot_pcr    = total_pv/total_cv    if total_cv>0    else 0
            tot_pcr_oi = total_poi/total_coi  if total_coi>0   else 0
            pc_color   = '#ff4d6d' if tot_pcr>bear_th else ('#00e5a0' if tot_pcr<bull_th else '#f5a623')
            pc_sub     = 'Bearish ▼' if tot_pcr>bear_th else ('Bullish ▲' if tot_pcr<bull_th else 'Neutral')

            # ── 메트릭 ──
            m1,m2,m3,m4,m5 = st.columns(5)
            with m1: st.markdown(mc('전체 CALL 거래량',  f'{int(total_cv):,}', '#00e5a0'), unsafe_allow_html=True)
            with m2: st.markdown(mc('전체 PUT 거래량',   f'{int(total_pv):,}', '#ff4d6d'), unsafe_allow_html=True)
            with m3: st.markdown(mc('전체 PCR(Volume)',  f'{tot_pcr:.2f}',     '#f3f4f6', pc_sub, pc_color), unsafe_allow_html=True)
            with m4: st.markdown(mc('전체 PCR(OI)',      f'{tot_pcr_oi:.2f}',  '#a78bfa'), unsafe_allow_html=True)
            with m5: st.markdown(mc('Call OI Wall',      f'${cow_all:,.0f}',   '#fb923c', f'Put OI Wall ${pow_all:,.0f}','#ff4d6d'), unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)

            # ── 차트 1: 기간별 수급 ──
            st.markdown('#### 📊 기간별 수급 비교')
            f1=go.Figure()
            f1.add_trace(go.Bar(x=df_terms.index,y=df_terms['call_vol'],name='CALL 거래량',marker_color='#00e5a0'))
            f1.add_trace(go.Bar(x=df_terms.index,y=df_terms['put_vol'], name='PUT 거래량', marker_color='#ff4d6d'))
            f1.update_layout(barmode='group',template='plotly_dark',height=340,hovermode='x unified')
            st.plotly_chart(f1, use_container_width=True)

            # ── 차트 2: PCR ──
            f2=go.Figure()
            f2.add_trace(go.Scatter(x=df_terms.index,y=df_terms['PCR (Volume)'],
                mode='lines+markers+text',name='PCR(Volume)',
                text=[f'{v:.2f}' for v in df_terms['PCR (Volume)']],textposition='top center',
                line=dict(color='#f5a623',width=3),marker=dict(size=10)))
            f2.add_trace(go.Scatter(x=df_terms.index,y=df_terms['PCR (OI)'],
                mode='lines+markers+text',name='PCR(OI)',
                text=[f'{v:.2f}' for v in df_terms['PCR (OI)']],textposition='bottom center',
                line=dict(color='#a78bfa',width=3,dash='dot'),marker=dict(size=10)))
            f2.add_hline(y=bear_th,line_dash='dash',line_color='#ff4d6d',
                         annotation_text=f'Bearish({bear_th})[{type_label}]')
            f2.add_hline(y=bull_th,line_dash='dash',line_color='#00e5a0',
                         annotation_text=f'Bullish({bull_th})[{type_label}]')
            f2.update_layout(title=f'기간별 PCR — {type_label} 기준 동적 임계값',
                template='plotly_dark',height=360)
            st.plotly_chart(f2, use_container_width=True)

            # ── 차트 3: OI Wall ──
            if not df_wall.empty:
                st.markdown('#### 🏰 OI Wall — 전 만기 집중도')
                f3=go.Figure()
                f3.add_trace(go.Bar(x=df_wall['strike'],y=df_wall['call_oi'],name='Call OI',marker_color='rgba(0,229,160,.7)'))
                f3.add_trace(go.Bar(x=df_wall['strike'],y=-df_wall['put_oi'],name='Put OI', marker_color='rgba(255,77,109,.7)'))
                vw=[]
                if current_price>0: vw.append((current_price,'white','dash',f'현재가 ${current_price:,.2f}',0.97))
                vw.append((cow_all,'#00e5a0','dot',f'Call OI Wall(저항) ${cow_all:,.0f}',0.82))
                vw.append((pow_all,'#ff4d6d','dot',f'Put OI Wall(지지) ${pow_all:,.0f}',0.67))
                add_vlines(f3, vw)
                f3.update_layout(barmode='relative',template='plotly_dark',height=400,hovermode='x unified')
                st.plotly_chart(f3, use_container_width=True)

            # ── 차트 4: IV (OI가중/Vol가중 이중 표시) ──
            iv_oi_c_t  = [df_terms.loc[t,'IV_OI_C%']  for t in TERMS]
            iv_vol_c_t = [df_terms.loc[t,'IV_Vol_C%'] for t in TERMS]
            iv_skew_oi = [df_terms.loc[t,'IV_Skew_OI'] for t in TERMS]
            if any(v>0 for v in iv_oi_c_t):
                st.markdown('#### 📉 IV Term Structure — OI가중(실선) / Vol가중(점선) / Skew')
                f4=go.Figure()
                f4.add_trace(go.Scatter(x=TERMS,y=iv_oi_c_t,mode='lines+markers',name='Call IV (OI가중)',
                    line=dict(color='#00e5a0',width=3),marker=dict(size=9)))
                f4.add_trace(go.Scatter(x=TERMS,y=iv_vol_c_t,mode='lines+markers',name='Call IV (Vol가중)',
                    line=dict(color='#00e5a0',width=2,dash='dot'),marker=dict(size=7)))
                iv_oi_p_t  = [df_terms.loc[t,'IV_OI_P%']  for t in TERMS]
                iv_vol_p_t = [df_terms.loc[t,'IV_Vol_P%'] for t in TERMS]
                f4.add_trace(go.Scatter(x=TERMS,y=iv_oi_p_t,mode='lines+markers',name='Put IV (OI가중)',
                    line=dict(color='#ff4d6d',width=3),marker=dict(size=9)))
                f4.add_trace(go.Scatter(x=TERMS,y=iv_vol_p_t,mode='lines+markers',name='Put IV (Vol가중)',
                    line=dict(color='#ff4d6d',width=2,dash='dot'),marker=dict(size=7)))
                f4.add_trace(go.Scatter(x=TERMS,y=iv_skew_oi,mode='lines+markers+text',name='IV Skew (OI가중)',
                    text=[f'{v:+.1f}' for v in iv_skew_oi],textposition='top center',
                    line=dict(color='#f5a623',width=2,dash='dash'),marker=dict(size=8)))
                f4.add_hline(y=0,line_color='#475569',line_width=1)
                f4.update_layout(title='IV Trim(5%~300%) 적용 — OI가중 vs Vol가중 비교 (두 값 차이 크면 당일 수급 특이)',
                    template='plotly_dark',height=380)
                st.plotly_chart(f4, use_container_width=True)

            # ── 차트 5: PCR 산점도 ──
            if not df_pcr_sc.empty:
                st.markdown('#### 🔵 만기별 PCR 분포')
                cmap={'Short':'#fb923c','Mid':'#a78bfa','Long':'#60a5fa'}
                f5=go.Figure()
                for tk2,clr in cmap.items():
                    sub=df_pcr_sc[df_pcr_sc['term']==tk2]
                    if sub.empty: continue
                    f5.add_trace(go.Scatter(x=sub['days'],y=sub['pcr_vol'],mode='markers',name=tk2,
                        marker=dict(color=clr,size=8,opacity=0.8),text=sub['exp_date'],
                        hovertemplate='만기:%{text}<br>잔존:%{x}일<br>PCR:%{y:.2f}<extra></extra>'))
                f5.add_hline(y=bear_th,line_dash='dash',line_color='#ff4d6d',annotation_text=f'Bearish({bear_th})')
                f5.add_hline(y=bull_th,line_dash='dash',line_color='#00e5a0',annotation_text=f'Bullish({bull_th})')
                f5.update_layout(xaxis_title='잔존일',yaxis_title='PCR(Volume)',
                    template='plotly_dark',height=340)
                st.plotly_chart(f5, use_container_width=True)

            # ── Max Pain 기간별 ──
            st.markdown('#### 🎯 기간별 Max Pain')
            mp_cols=st.columns(3)
            for idx2,t2 in enumerate(TERMS):
                mpv=mp_per_term[t2]; gap2=(mpv-current_price)/current_price*100 if current_price>0 else 0
                gc2='#ff4d6d' if gap2<-2 else ('#00e5a0' if gap2>2 else '#f5a623')
                with mp_cols[idx2]:
                    st.markdown(mc(f"Max Pain [{t2.split(' ')[0]}]",
                        f'${mpv:,.0f}' if mpv>0 else 'N/A',gc2,
                        f'({gap2:+.1f}%)' if mpv>0 else '',gc2), unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)

            # ── 기간별 요약 테이블 ──
            st.markdown('#### 📑 기간별 데이터 요약 (IV = OI가중+Trim / Vol가중+Trim)')
            disp = df_terms[['call_vol','put_vol','call_oi','put_oi','PCR (Volume)','PCR (OI)',
                              'IV_OI_C%','IV_Vol_C%','IV_OI_P%','IV_Vol_P%','IV_Skew_OI','IV_Skew_Vol']].copy()
            disp.columns=['Call거래량','Put거래량','Call OI','Put OI','PCR(Vol)','PCR(OI)',
                          'IV_C(OI%)','IV_C(Vol%)','IV_P(OI%)','IV_P(Vol%)','Skew(OI)','Skew(Vol)']
            for c2 in ['Call거래량','Put거래량','Call OI','Put OI']:
                disp[c2]=disp[c2].apply(lambda x: f'{int(x):,}')
            for c2 in ['PCR(Vol)','PCR(OI)']:
                disp[c2]=disp[c2].apply(lambda x: f'{x:.2f}')
            for c2 in ['IV_C(OI%)','IV_C(Vol%)','IV_P(OI%)','IV_P(Vol%)']:
                disp[c2]=disp[c2].apply(lambda x: f'{x:.1f}%')
            for c2 in ['Skew(OI)','Skew(Vol)']:
                disp[c2]=disp[c2].apply(lambda x: f'{x:+.1f}%p')
            st.dataframe(disp, use_container_width=True)

            # ── UOA ──
            st.markdown('#### 🔥 UOA — 전 만기 (Mid-Price + 동적Moneyness + 차등Spread필터)')
            if not df_uoa.empty:
                ud2=df_uoa[['term','side','moneyness','strike','days','dollar_premium','V_OI','mid_price']].copy()
                ud2.columns=['기간','구분','Moneyness','행사가','잔존일','Dollar Premium','V/OI','Mid가격']
                ud2['Dollar Premium']=ud2['Dollar Premium'].apply(fmt_p)
                ud2['V/OI']=ud2['V/OI'].apply(lambda x: f'{x:.1f}x')
                st.dataframe(ud2, use_container_width=True)
            else:
                st.info('조건 통과 UOA 없음')

            # ── 이론 신호 ──
            st.markdown('### 🧠 Term Structure 이론 신호')
            short=df_terms.loc[TERMS[0]]; mid=df_terms.loc[TERMS[1]]; long_=df_terms.loc[TERMS[2]]
            pcr_s=short['PCR (Volume)']; pcr_m=mid['PCR (Volume)']; pcr_l=long_['PCR (Volume)']
            poi_s=short['PCR (OI)'];    poi_l=long_['PCR (OI)']

            s0,m0=pcr_label(tot_pcr,bear_th,bull_th)
            st.markdown(sig(s0,f'① 전체 PCR [{type_label}기준]',m0), unsafe_allow_html=True)
            for lbl2,pv_ in [('단기',pcr_s),('중기',pcr_m),('장기',pcr_l)]:
                s_,m_=pcr_label(pv_,bear_th,bull_th)
                st.markdown(sig(s_,f'② PCR [{lbl2}]',m_), unsafe_allow_html=True)

            div_sl=pcr_l-pcr_s
            if abs(div_sl)>0.3:
                dc3='signal-bull' if div_sl<0 else 'signal-bear'
                dm3=(f'단기PCR({pcr_s:.2f}) > 장기PCR({pcr_l:.2f}) → 단기 공포/장기 낙관 · 단기 조정 후 반등' if div_sl<0 else
                     f'단기PCR({pcr_s:.2f}) < 장기PCR({pcr_l:.2f}) → 단기 탐욕/장기 경계 · 단기 상승 후 리스크')
            else:
                dc3='signal-neut'; dm3=f'단기·장기 PCR 차이 {abs(div_sl):.2f} → 기간별 심리 유사'
            st.markdown(sig(dc3,'③ PCR 기간별 다이버전스',dm3), unsafe_allow_html=True)

            for lbl3,pv_,poi_ in [('단기',pcr_s,poi_s),('장기',pcr_l,poi_l)]:
                dc4,dm4=pcr_divergence(pv_,poi_)
                st.markdown(sig(dc4,f'④ PCR 내부 다이버전스 (비율)[{lbl3}]',dm4), unsafe_allow_html=True)

            for lbl5,row5 in [('단기',short),('중기',mid),('장기',long_)]:
                vc5,vm5=vol_oi_signal(row5['call_vol'],row5['put_vol'],row5['call_oi'],row5['put_oi'])
                st.markdown(sig(f'signal-{vc5}',f'⑤ Volume × OI [{lbl5}]',vm5), unsafe_allow_html=True)

            for t6 in TERMS:
                mpv6=mp_per_term[t6]
                if mpv6>0 and current_price>0:
                    gap6=(mpv6-current_price)/current_price*100
                    mc6='signal-bear' if gap6<-2 else ('signal-bull' if gap6>2 else 'signal-neut')
                    mb6=(f'Max Pain ${mpv6:,.0f} — 현재가 대비 <strong>{gap6:.1f}%</strong> 아래 · 하락 수렴' if gap6<-2 else
                         (f'Max Pain ${mpv6:,.0f} — 현재가 대비 <strong>{gap6:+.1f}%</strong> 위 · 상승 수렴' if gap6>2 else
                          f'Max Pain ${mpv6:,.0f} ≈ 현재가 · 횡보 압력'))
                    st.markdown(sig(mc6,f"⑥ Max Pain [{t6.split(' ')[0]}]",mb6), unsafe_allow_html=True)

            if cow_all>0:
                wc7='signal-bear' if current_price>cow_all else ('signal-bull' if current_price<pow_all else 'signal-neut')
                wb7=(f'Call OI Wall(저항)<strong>${cow_all:,.0f}</strong> · Put OI Wall(지지)<strong>${pow_all:,.0f}</strong>'
                     +(' · 현재가 Call OI Wall 위 → 저항 돌파 신호' if current_price>cow_all
                       else (' · 현재가 Put OI Wall 아래 → 추가 하락 리스크' if current_price<pow_all
                             else ' · 현재가 두 Wall 사이 → 범위 내 등락')))
                st.markdown(sig(wc7,'⑦ OI Wall 지지/저항 (전 만기)',wb7), unsafe_allow_html=True)

            for lbl8,t8 in [('단기',TERMS[0]),('중기',TERMS[1]),('장기',TERMS[2])]:
                oi_sk=df_terms.loc[t8,'IV_Skew_OI']; vol_sk=df_terms.loc[t8,'IV_Skew_Vol']
                oi_c =df_terms.loc[t8,'IV_OI_C%']
                if oi_c>0:
                    i8c='signal-bear' if oi_sk>5 else ('signal-bull' if oi_sk<-3 else 'signal-neut')
                    i8m=(f'Skew(OI):<strong>{oi_sk:+.1f}%p</strong> / Skew(Vol):{vol_sk:+.1f}%p → 풋 공포 프리미엄 과다' if oi_sk>5 else
                         (f'Skew(OI):<strong>{oi_sk:+.1f}%p</strong> / Skew(Vol):{vol_sk:+.1f}%p → 콜 탐욕 프리미엄' if oi_sk<-3 else
                          f'Skew(OI):{oi_sk:+.1f}%p / Skew(Vol):{vol_sk:+.1f}%p → 균형'))
                    st.markdown(sig(i8c,f'⑧ IV Skew [{lbl8}]',i8m), unsafe_allow_html=True)

            if not df_uoa.empty:
                uc=len(df_uoa[df_uoa['side']=='CALL']); up=len(df_uoa[df_uoa['side']=='PUT'])
                otm_c=len(df_uoa[(df_uoa['side']=='CALL')&(df_uoa['moneyness']=='OTM')])
                otm_p=len(df_uoa[(df_uoa['side']=='PUT') &(df_uoa['moneyness']=='OTM')])
                top_p=df_uoa.iloc[0]['dollar_premium']
                u9='signal-bull' if uc>up else ('signal-bear' if up>uc else 'signal-neut')
                st.markdown(sig(u9,'⑨ UOA 스마트 머니 (Mid-Price+동적Moneyness+차등Spread)',
                    f'CALL {uc}건(OTM {otm_c}) / PUT {up}건(OTM {otm_p}) · 최대단건 {fmt_p(top_p)} · '
                    +('OTM콜 우세 → 상승 확신 베팅' if otm_c>otm_p else
                      ('OTM풋 우세 → 하락/헤징' if otm_p>otm_c else '균형 → 변동성 이벤트'))),
                    unsafe_allow_html=True)

            # ── AI 프롬프트 ──
            uoa_top = df_uoa[['term','side','moneyness','strike','dollar_premium','V_OI','days']].head(10).to_string(index=False) if not df_uoa.empty else '없음'
            iv_str  = '\n'.join([f"  {t.split(' ')[0]}: Call IV(OI가중) {df_terms.loc[t,'IV_OI_C%']:.1f}% / (Vol가중) {df_terms.loc[t,'IV_Vol_C%']:.1f}% | Skew {df_terms.loc[t,'IV_Skew_OI']:+.1f}%p" for t in TERMS])
            mp_str  = '\n'.join([f"  {t.split(' ')[0]}: ${mp_per_term[t]:,.0f} ({(mp_per_term[t]-current_price)/current_price*100 if current_price>0 else 0:+.1f}%)" for t in TERMS])

            prompt = f"""당신은 월스트리트 시니어 파생상품 애널리스트입니다.
'{name}({ticker_input})'의 전 만기 옵션 데이터를 분석하세요.

[분석 대상] 종목유형:{type_label} | 현재가:${current_price:,.2f}
PCR 기준: Bearish>{bear_th} / Bullish<{bull_th}

[기간별 수급]
단기(≤30일): PCR(Vol):{pcr_s:.2f}/PCR(OI):{poi_s:.2f}/다이버전스비율:{pcr_s/poi_s:.2f}배
중기(30~90일): PCR(Vol):{pcr_m:.2f}/PCR(OI):{mid['PCR (OI)']:.2f}
장기(≥90일): PCR(Vol):{pcr_l:.2f}/PCR(OI):{poi_l:.2f}/다이버전스비율:{pcr_l/poi_l:.2f}배

[IV Term Structure (OI가중+Vol가중 Trim 5%~300%)]
{iv_str}

[Max Pain (음수=하락압력)]
{mp_str}

[OI Wall] Call OI Wall(저항):${cow_all:,.0f} / Put OI Wall(지지):${pow_all:,.0f}

[UOA — Mid-Price + 동적Moneyness]
{uoa_top}

[분석 지시사항]
1. {type_label} PCR 구조적 특성 반영해 기간별 PCR 해석
2. PCR 다이버전스 비율로 당일 수급 편향 분석
3. IV Skew(OI가중 vs Vol가중 괴리) 해석
4. Max Pain 기간별 수렴 압력과 시나리오
5. OI Wall 지지/저항 활용 시나리오
6. UOA OTM 비율로 스마트 머니 의도 추론
7. 향후 1개월/3개월 Bull/Bear/Neutral 시나리오 + 핵심 가격 레벨
친절한 한글 마크다운으로 정리하세요."""

    # ══════════════════════════════════════════════════════
    # 공통 AI 분석 섹션
    # ══════════════════════════════════════════════════════
    if ticker_input and expirations and (
        (analysis_mode == '단일 만기일 분석' and selected_expiry) or
        analysis_mode != '단일 만기일 분석'
    ):
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

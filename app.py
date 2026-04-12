import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import time

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .big-font { font-size:40px !important; font-weight: bold; color: #00e5a0; text-shadow: 0 0 20px rgba(0,229,160,0.2); }
    .subtitle { font-size:16px; color: #a0a0a0; margin-bottom: 25px; font-family: 'monospace'; }
    .stMetric { background-color: #111827; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 데이터 분석 시스템 (Python + Gemini AI)</p>', unsafe_allow_html=True)

# --- 2. Gemini API 설정 (안정적인 Fallback 로직) ---
def generate_with_fallback(prompt, api_key):
    """
    지원 중단된 모델(1.0-pro 등)을 제외하고 최신 모델들로 순차적 호출을 시도합니다.
    """
    genai.configure(api_key=api_key)
    
    # 현재 작동이 확인된 최신 모델 리스트 (우선순위 순)
    fallback_chain = [
        "gemini-1.5-pro",          # 가장 지능이 높음
        "gemini-2.0-flash",        # 가장 빠름 (현재 Preview/Exp 버전 확인 필요)
        "gemini-1.5-flash",        # 안정적인 범용 모델
        "gemini-1.5-flash-8b"      # 경량화 모델
    ]
    
    last_error_log = []
    
    for model_name in fallback_chain:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name 
        except Exception as e:
            error_msg = f"{model_name}: {str(e)}"
            last_error_log.append(error_msg)
            time.sleep(0.5)
            continue
            
    raise Exception(f"모든 AI 모델 호출 실패: {' | '.join(last_error_log)}")

# Secrets에서 API 키 가져오기
api_key = st.secrets.get("GEMINI_API_KEY")
has_api_key = api_key is not None

if not has_api_key:
    st.sidebar.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다.")

# --- 3. 사이드바 검색 설정 ---
with st.sidebar:
    st.header("🔍 검색 설정")
    ticker_symbol = st.text_input("티커 심볼 입력 (예: AAPL, TSLA, NVDA)", value="AAPL").upper()
    
    ticker = yf.Ticker(ticker_symbol)
    try:
        expirations = ticker.options
        if expirations:
            selected_expiry = st.selectbox("만기일 선택", expirations)
        else:
            st.error(f"'{ticker_symbol}'의 옵션 데이터를 찾을 수 없습니다.")
            selected_expiry = None
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        selected_expiry = None

# --- 4. 데이터 수집 및 대시보드 출력 ---
if ticker_symbol and selected_expiry:
    # 실시간 가격 및 정보
    try:
        # 현재가 가져오기 (Fast Info 우선)
        ticker_info = ticker.info
        spot_price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice')
        
        # 가격 정보가 없는 경우 history로 보완
        if not spot_price:
            spot_price = ticker.history(period="1d")['Close'].iloc[-1]
            
        company_name = ticker_info.get('longName', ticker_symbol)
    except:
        spot_price = 0
        company_name = ticker_symbol

    st.subheader(f"📊 {company_name} ({ticker_symbol}) | 현재가: ${spot_price:,.2f}")
    st.info(f"선택된 만기일: {selected_expiry}")

    with st.spinner("옵션 체인 데이터 수집 중..."):
        # 옵션 데이터 추출
        opt = ticker.option_chain(selected_expiry)
        calls = opt.calls
        puts = opt.puts
        
        # 현재가 기준 ±30% 범위 필터링 (가독성 향상)
        if spot_price > 0:
            min_strike, max_strike = spot_price * 0.7, spot_price * 1.3
            calls_filtered = calls[(calls['strike'] >= min_strike) & (calls['strike'] <= max_strike)]
            puts_filtered = puts[(puts['strike'] >= min_strike) & (puts['strike'] <= max_strike)]
        else:
            calls_filtered, puts_filtered = calls, puts

        # 주요 지표 계산
        total_call_vol = calls['volume'].sum()
        total_put_vol = puts['volume'].sum()
        pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0

        # 지표 가시화
        m1, m2, m3 = st.columns(3)
        m1.metric("CALL 총 거래량", f"{int(total_call_vol):,}")
        m2.metric("PUT 총 거래량", f"{int(total_put_vol):,}")
        
        sentiment = "중립"
        if pcr > 1.2: sentiment = "하락 우세 (Bearish)"
        elif pcr < 0.7: sentiment = "상승 우세 (Bullish)"
        m3.metric("Put/Call Ratio", f"{pcr:.2f}", sentiment)

        # --- 차트 시각화 ---
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=calls_filtered['strike'], y=calls_filtered['volume'],
            name='CALL Volume', marker_color='#00e5a0', opacity=0.8
        ))
        fig.add_trace(go.Bar(
            x=puts_filtered['strike'], y=-puts_filtered['volume'], # 풋은 반대 방향으로 표시
            name='PUT Volume', marker_color='#ff4d6d', opacity=0.8
        ))

        fig.update_layout(
            title=f"행사가(Strike)별 거래량 분포 (만기: {selected_expiry})",
            barmode='relative',
            template="plotly_dark",
            height=450,
            xaxis_title="Strike Price",
            yaxis_title="Volume",
            hovermode="x unified"
        )
        # 현재가 라인 추가
        if spot_price > 0:
            fig.add_vline(x=spot_price, line_dash="dash", line_color="white", annotation_text="Spot Price")

        st.plotly_chart(fig, use_container_width=True)

        # --- 상세 데이터 테이블 ---
        t1, t2 = st.tabs(["▲ CALL 옵션 리스트", "▼ PUT 옵션 리스트"])
        with t1:
            st.dataframe(calls[['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']], use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(puts[['strike', 'lastPrice', 'volume', 'openInterest', 'impliedVolatility']], use_container_width=True, hide_index=True)

    # --- 5. Gemini AI 분석 리포트 ---
    if has_api_key:
        st.divider()
        st.subheader("🤖 Gemini AI 옵션 시장 정밀 브리핑")
        
        if st.button("분석 리포트 생성", type="primary"):
            with st.spinner("Gemini가 방대한 옵션 체인 데이터를 분석 중입니다..."):
                # AI에게 전달할 데이터 요약
                analysis_prompt = f"""
                당신은 파생상품 분석 전문가입니다. 아래 주식의 옵션 데이터를 바탕으로 향후 주가 방향을 분석해 주세요.
                
                [종목 정보]
                티커: {ticker_symbol} / 종목명: {company_name} / 현재가: ${spot_price}
                분석 만기일: {selected_expiry}
                
                [수급 데이터]
                - 콜옵션 총 거래량: {total_call_vol}
                - 풋옵션 총 거래량: {total_put_vol}
                - Put/Call Ratio: {pcr:.2f}
                
                [기술적 특징]
                - 거래량이 가장 많이 집중된 행사가(Strike): (데이터 기반으로 분석 요청)
                
                [요청사항]
                1. 현재 시장 참여자들이 상승(Bull)과 하락(Bear) 중 어느 쪽에 더 강하게 배팅하고 있는지 결론을 내주세요.
                2. Put/Call Ratio가 역사적 평균 대비 어떤 상태인지, 그리고 이것이 심리적으로 '공포'인지 '탐욕'인지 설명해 주세요.
                3. 트레이더가 주목해야 할 핵심 저항선(Call 매물대)과 지지선(Put 매물대)을 가격대로 제시해 주세요.
                4. 초보자도 이해할 수 있도록 친절하고 전문적인 한글 톤으로 요약해 주세요.
                """
                
                try:
                    report, used_model = generate_with_fallback(analysis_prompt, api_key)
                    st.success(f"분석 완료 (사용 모델: {used_model})")
                    st.markdown(f"""
                    <div style="background-color: #1e293b; padding: 25px; border-radius: 12px; border-left: 5px solid #00e5a0; color: #f3f4f6; line-height: 1.6;">
                        {report}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"AI 분석 중 오류가 발생했습니다: {e}")

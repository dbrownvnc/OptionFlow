import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .big-font { font-size:40px !important; font-weight: bold; color: #00e5a0; }
    .subtitle { font-size:16px; color: #a0a0a0; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 거래량 분석기 (Python + Gemini AI)</p>', unsafe_allow_html=True)

# --- 2. Gemini API 설정 (st.secrets 활용) ---
has_api_key = False
try:
    # Streamlit Cloud의 Secrets 또는 로컬 .streamlit/secrets.toml에서 키를 가져옴
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)
    has_api_key = True
except KeyError:
    st.warning("⚠️ Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다. AI 분석 기능이 비활성화됩니다.")

# --- 3. 사이드바 (종목 및 만기일 선택) ---
with st.sidebar:
    st.header("검색 설정")
    ticker_symbol = st.text_input("티커 심볼 (예: AAPL, TSLA, SPY)", value="AAPL").upper()
    
    if ticker_symbol:
        ticker = yf.Ticker(ticker_symbol)
        try:
            expirations = ticker.options
        except Exception:
            expirations = []
            
        if expirations:
            selected_expiry = st.selectbox("만기일 선택", expirations)
        else:
            st.error("해당 종목의 옵션 데이터를 찾을 수 없습니다.")
            selected_expiry = None

# --- 4. 메인 로직 (데이터 수집 및 시각화) ---
if ticker_symbol and 'selected_expiry' in locals() and selected_expiry:
    # 현재가 가져오기
    try:
        spot_price = ticker.info.get('regularMarketPrice')
        if not spot_price:
            spot_price = ticker.history(period="1d")['Close'].iloc[-1]
    except:
        spot_price = 0

    st.subheader(f"📊 {ticker_symbol} | 현재가: ${spot_price:,.2f} | 만기일: {selected_expiry}")

    with st.spinner("옵션 데이터 불러오는 중..."):
        # 옵션 체인 데이터 가져오기
        opt = ticker.option_chain(selected_expiry)
        
        # 현재가 기준 ±30% 범위로 데이터 필터링
        if spot_price > 0:
            min_strike, max_strike = spot_price * 0.7, spot_price * 1.3
            calls = opt.calls[(opt.calls['strike'] >= min_strike) & (opt.calls['strike'] <= max_strike)]
            puts = opt.puts[(opt.puts['strike'] >= min_strike) & (opt.puts['strike'] <= max_strike)]
        else:
            calls, puts = opt.calls, opt.puts

        # 요약 통계 계산
        call_vol = calls['volume'].sum() if 'volume' in calls else 0
        put_vol = puts['volume'].sum() if 'volume' in puts else 0
        pcr = put_vol / call_vol if call_vol > 0 else 0

        # 지표 출력
        col1, col2, col3 = st.columns(3)
        col1.metric("CALL 거래량 (상승 베팅)", f"{int(call_vol):,}")
        col2.metric("PUT 거래량 (하락 베팅)", f"{int(put_vol):,}")
        
        # PCR에 따른 심리 분석
        sentiment = "중립"
        if pcr > 1.2: sentiment = "하락 신호 (Bearish)"
        elif pcr < 0.8: sentiment = "상승 신호 (Bullish)"
        col3.metric("P/C Ratio (Put/Call 비율)", f"{pcr:.2f}", sentiment, delta_color="off")

        # --- 차트 시각화 (Plotly) ---
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=calls['strike'], y=calls['volume'], 
            name='CALL 거래량', marker_color='rgba(0, 229, 160, 0.7)'
        ))
        fig.add_trace(go.Bar(
            x=puts['strike'], y=-puts['volume'], # 풋은 아래로 표시
            name='PUT 거래량', marker_color='rgba(255, 77, 109, 0.7)'
        ))
        
        fig.update_layout(
            title="행사가별 거래량 분포 (현재가 ±30%)",
            barmode='relative',
            xaxis_title="행사가 (Strike Price)",
            yaxis_title="거래량 (Volume)",
            template="plotly_dark",
            hovermode="x unified"
        )
        if spot_price > 0:
            fig.add_vline(x=spot_price, line_dash="dash", line_color="white", annotation_text="현재가")

        st.plotly_chart(fig, use_container_width=True)

        # --- 데이터 테이블 ---
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("#### ▲ CALLS (콜옵션)")
            st.dataframe(calls[['strike', 'volume', 'openInterest', 'impliedVolatility', 'lastPrice']], use_container_width=True, hide_index=True)
        with t_col2:
            st.markdown("#### ▼ PUTS (풋옵션)")
            st.dataframe(puts[['strike', 'volume', 'openInterest', 'impliedVolatility', 'lastPrice']], use_container_width=True, hide_index=True)

# --- 5. Gemini AI 분석 세션 ---
if has_api_key and ticker_symbol and 'selected_expiry' in locals() and selected_expiry:
    st.divider()
    st.subheader("🤖 Gemini AI 옵션 시장 분석")
    
    if st.button("AI 브리핑 생성하기"):
        with st.spinner("Gemini가 데이터를 분석 중입니다..."):
            model = genai.GenerativeModel('gemini-2.5-pro')
            prompt = f"""
            당신은 월스트리트의 전문 파생상품 애널리스트입니다. 아래 데이터를 바탕으로 시장 심리를 분석해주세요.
            
            [데이터]
            종목: {ticker_symbol}
            현재가: {spot_price}
            만기일: {selected_expiry}
            콜옵션 총 거래량: {call_vol}
            풋옵션 총 거래량: {put_vol}
            Put/Call Ratio (PCR): {pcr:.2f}
            
            [지시사항]
            1. 현재 옵션 트레이더들이 이 종목에 대해 단기적으로 상승을 예상하는지, 하락을 예상하는지 명확히 결론을 내주세요.
            2. PCR 수치가 의미하는 바를 1~2문장으로 쉽게 설명해주세요.
            3. 전문적이지만 초보자도 이해할 수 있는 톤으로 요약해서 작성해주세요.
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("분석 완료!")
                st.write(response.text)
            except Exception as e:
                st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
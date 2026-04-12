import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import time
import json

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="OPTIONS FLOW", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .big-font { font-size:40px !important; font-weight: bold; color: #00e5a0; text-shadow: 0 0 20px rgba(0,229,160,0.2); }
    .subtitle { font-size:16px; color: #a0a0a0; margin-bottom: 25px; font-family: 'monospace'; }
    .stMetric { background-color: #111827; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .report-box { background-color: #1e293b; padding: 25px; border-radius: 12px; border-left: 5px solid #00e5a0; color: #f3f4f6; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">OPTIONS FLOW</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">실시간 옵션 분석 시스템 (Gemini Smart Fallback)</p>', unsafe_allow_html=True)

# --- 2. Gemini API 설정 (안정성 강화) ---
def generate_with_fallback(prompt, api_key):
    genai.configure(api_key=api_key)
    
    # 429 에러를 피하기 위해 한도가 넉넉한 프리뷰 모델부터 시도
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
    
    ticker = yf.Ticker(ticker_input)
    try:
        expirations = ticker.options
        if expirations:
            selected_expiry = st.selectbox("만기일 선택", expirations)
        else:
            st.error("옵션 데이터를 찾을 수 없는 티커입니다.")
            selected_expiry = None
    except:
        st.error("데이터 서버 연결에 문제가 발생했습니다.")
        selected_expiry = None

# --- 4. 데이터 포맷팅 함수 (최대한 많은 지표 노출) ---
def format_option_df(df):
    if df is None or df.empty:
        return df
    
    # yfinance에서 제공하는 유용한 컬럼들을 최대한 가져옴
    useful_cols = [
        'contractSymbol', 'strike', 'lastPrice', 'bid', 'ask', 
        'change', 'percentChange', 'volume', 'openInterest', 
        'impliedVolatility', 'inTheMoney', 'lastTradeDate'
    ]
    
    # 데이터프레임에 존재하는 컬럼만 필터링
    available_cols = [c for c in useful_cols if c in df.columns]
    f_df = df[available_cols].copy()
    
    # 보기 좋게 포맷팅 적용
    if 'impliedVolatility' in f_df.columns:
        f_df['impliedVolatility'] = (f_df['impliedVolatility'] * 100).map("{:.2f}%".format)
    if 'percentChange' in f_df.columns:
        f_df['percentChange'] = f_df['percentChange'].map("{:+.2f}%".format)
    if 'change' in f_df.columns:
        f_df['change'] = f_df['change'].map("{:+.2f}".format)
    if 'lastTradeDate' in f_df.columns:
        # 시간대 변환 및 포맷 변경
        f_df['lastTradeDate'] = pd.to_datetime(f_df['lastTradeDate']).dt.strftime('%Y-%m-%d %H:%M')
    if 'inTheMoney' in f_df.columns:
        f_df['inTheMoney'] = f_df['inTheMoney'].map({True: "✅ ITM", False: "❌ OTM"})

    # 한글 헤더로 이름 변경
    rename_dict = {
        'contractSymbol': '계약 심볼',
        'strike': '행사가',
        'lastPrice': '현재가',
        'bid': '매수호가(Bid)',
        'ask': '매도호가(Ask)',
        'change': '변동액',
        'percentChange': '변동률',
        'volume': '거래량',
        'openInterest': '미결제약정(OI)',
        'impliedVolatility': '내재변동성(IV)',
        'inTheMoney': 'ITM 여부',
        'lastTradeDate': '최근 거래일시'
    }
    
    f_df = f_df.rename(columns=rename_dict)
    return f_df

# --- 5. 데이터 수집 및 대시보드 시각화 ---
if ticker_input and selected_expiry:
    try:
        info = ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not current_price:
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
        name = info.get('longName', ticker_input)
    except:
        current_price = 0
        name = ticker_input

    st.subheader(f"📊 {name} ({ticker_input}) | 현재가: ${current_price:,.2f}")
    
    with st.spinner("옵션 체인 분석 중..."):
        opt_chain = ticker.option_chain(selected_expiry)
        calls, puts = opt_chain.calls, opt_chain.puts
        
        # 차트를 위해 현재가 근처 ±30% 필터링 (테이블에는 필터링 안 된 전체 표출)
        if current_price > 0:
            min_strike = current_price * 0.7
            max_strike = current_price * 1.3
            calls_chart = calls[(calls['strike'] >= min_strike) & (calls['strike'] <= max_strike)]
            puts_chart = puts[(puts['strike'] >= min_strike) & (puts['strike'] <= max_strike)]
        else:
            calls_chart, puts_chart = calls, puts

        # 주요 지표 계산
        call_vol = calls['volume'].sum()
        put_vol = puts['volume'].sum()
        pcr = put_vol / call_vol if call_vol > 0 else 0

        # 지표 표시
        c1, c2, c3 = st.columns(3)
        c1.metric("CALL 거래량", f"{int(call_vol):,}")
        c2.metric("PUT 거래량", f"{int(put_vol):,}")
        
        status = "중립"
        if pcr > 1.2: status = "하락 신호 (Bearish)"
        elif pcr < 0.7: status = "상승 신호 (Bullish)"
        c3.metric("Put/Call Ratio", f"{pcr:.2f}", status)

        # Plotly 차트
        fig = go.Figure()
        fig.add_trace(go.Bar(x=calls_chart['strike'], y=calls_chart['volume'], name='Calls', marker_color='#00e5a0'))
        fig.add_trace(go.Bar(x=puts_chart['strike'], y=-puts_chart['volume'], name='Puts', marker_color='#ff4d6d'))
        
        fig.update_layout(
            title=f"행사가별 거래량 분포 (만기: {selected_expiry}) - 현재가 ±30% 구간",
            barmode='relative', template="plotly_dark", height=400,
            hovermode="x unified"
        )
        if current_price > 0:
            fig.add_vline(x=current_price, line_dash="dash", line_color="white", annotation_text="현재가")
        
        st.plotly_chart(fig, use_container_width=True)

        # 💡 상위 데이터 테이블 - 가능한 한 많은 데이터를 포맷팅하여 보여줌
        st.markdown("#### 📑 전체 옵션 체인 상세 데이터")
        tab1, tab2 = st.tabs(["▲ CALL 옵션 상세", "▼ PUT 옵션 상세"])
        with tab1:
            st.dataframe(format_option_df(calls), use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(format_option_df(puts), use_container_width=True, hide_index=True)

    # --- 6. AI 분석 섹션 ---
    st.divider()
    st.subheader("🤖 Gemini AI 옵션 시장 브리핑")
    
    # AI에게 보낼 프롬프트 텍스트 미리 생성
    prompt = f"""
    당신은 월스트리트 파생상품 전문가입니다. 아래 데이터를 바탕으로 시장 심리를 분석하세요.
    
    [정보]
    티커: {ticker_input} / 현재가: ${current_price} / 만기일: {selected_expiry}
    콜옵션 총 거래량: {call_vol:,} / 풋옵션 총 거래량: {put_vol:,}
    Put/Call Ratio: {pcr:.2f}
    
    [지시사항]
    1. 현재 시장 참여자들이 단기 주가 방향을 어떻게 보고 있는지 명확한 결론을 내려주세요.
    2. PCR 수치가 역사적 평균(약 0.7~1.0) 대비 어떤 수준이며 심리적 상태가 어떠한지 설명하세요.
    3. 가장 큰 거래량이 몰린 행사가를 찾아 지지선/저항선 관점에서 해석해 주세요.
    4. 초보자도 이해할 수 있게 친절한 한글로 작성해 주세요.
    """

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        st.markdown("#### 옵션 1. 스트림릿에서 바로 분석")
        if st.button("✨ API 자동 분석 (약 10초 소요)", type="primary", use_container_width=True):
            if has_api_key:
                with st.spinner("AI가 데이터를 분석하고 있습니다..."):
                    try:
                        result, used_model = generate_with_fallback(prompt, api_key)
                        st.success(f"분석 완료! (사용한 모델: {used_model})")
                        st.markdown(f'<div class="report-box">{result}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"분석 중 오류 발생 (무료 한도 초과 등): {e}")
            else:
                st.error("API 키가 설정되지 않았습니다.")

    with col_btn2:
        st.markdown("#### 옵션 2. 무료 한도 초과 시 대안")
        # Javascript를 이용해 프롬프트를 클립보드에 복사하고 새 창을 띄우는 커스텀 컴포넌트
        safe_prompt = json.dumps(prompt)
        html_code = f"""
        <button onclick="copyAndOpen()" style="background-color: #f5a623; color: #000; padding: 12px 20px; border: none; border-radius: 8px; font-weight: bold; font-size: 15px; cursor: pointer; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: 0.2s;">
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

    # 생성된 프롬프트 내용 확인 가능하도록 표시
    with st.expander("생성된 분석 프롬프트 내용 확인하기", expanded=False):
        st.code(prompt, language="text")

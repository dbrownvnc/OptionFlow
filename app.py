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

# --- 4. 데이터 포맷팅 함수 ---
def format_option_df(df):
    if df is None or df.empty:
        return df
    
    useful_cols = [
        'contractSymbol', 'strike', 'lastPrice', 'bid', 'ask', 
        'change', 'percentChange', 'volume', 'openInterest', 
        'impliedVolatility', 'inTheMoney', 'lastTradeDate'
    ]
    
    available_cols = [c for c in useful_cols if c in df.columns]
    f_df = df[available_cols].copy()
    
    if 'impliedVolatility' in f_df.columns:
        f_df['impliedVolatility'] = (f_df['impliedVolatility'] * 100).map("{:.2f}%".format)
    if 'percentChange' in f_df.columns:
        f_df['percentChange'] = f_df['percentChange'].map("{:+.2f}%".format)
    if 'change' in f_df.columns:
        f_df['change'] = f_df['change'].map("{:+.2f}".format)
    if 'lastTradeDate' in f_df.columns:
        f_df['lastTradeDate'] = pd.to_datetime(f_df['lastTradeDate']).dt.strftime('%Y-%m-%d %H:%M')
    if 'inTheMoney' in f_df.columns:
        f_df['inTheMoney'] = f_df['inTheMoney'].map({True: "✅ ITM", False: "❌ OTM"})

    rename_dict = {
        'contractSymbol': '계약 심볼', 'strike': '행사가', 'lastPrice': '현재가',
        'bid': '매수호가(Bid)', 'ask': '매도호가(Ask)', 'change': '변동액',
        'percentChange': '변동률', 'volume': '거래량', 'openInterest': '미결제약정(OI)',
        'impliedVolatility': '내재변동성(IV)', 'inTheMoney': 'ITM 여부', 'lastTradeDate': '최근 거래일시'
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
        
        if current_price > 0:
            min_strike = current_price * 0.7
            max_strike = current_price * 1.3
            calls_chart = calls[(calls['strike'] >= min_strike) & (calls['strike'] <= max_strike)]
            puts_chart = puts[(puts['strike'] >= min_strike) & (puts['strike'] <= max_strike)]
        else:
            calls_chart, puts_chart = calls, puts

        call_vol = calls['volume'].sum()
        put_vol = puts['volume'].sum()
        pcr = put_vol / call_vol if call_vol > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("CALL 거래량", f"{int(call_vol):,}")
        c2.metric("PUT 거래량", f"{int(put_vol):,}")
        status = "하락 신호 (Bearish)" if pcr > 1.2 else ("상승 신호 (Bullish)" if pcr < 0.7 else "중립")
        c3.metric("Put/Call Ratio", f"{pcr:.2f}", status)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=calls_chart['strike'], y=calls_chart['volume'], name='Calls', marker_color='#00e5a0'))
        fig.add_trace(go.Bar(x=puts_chart['strike'], y=-puts_chart['volume'], name='Puts', marker_color='#ff4d6d'))
        
        fig.update_layout(
            title=f"행사가별 거래량 분포 (만기: {selected_expiry}) - 현재가 ±30% 구간",
            barmode='relative', template="plotly_dark", height=400, hovermode="x unified"
        )
        if current_price > 0:
            fig.add_vline(x=current_price, line_dash="dash", line_color="white", annotation_text="현재가")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📑 전체 옵션 체인 상세 데이터")
        tab1, tab2 = st.tabs(["▲ CALL 옵션 상세", "▼ PUT 옵션 상세"])
        with tab1: st.dataframe(format_option_df(calls), use_container_width=True, hide_index=True)
        with tab2: st.dataframe(format_option_df(puts), use_container_width=True, hide_index=True)

    # --- 6. AI 분석용 심층 데이터 추출 및 프롬프트 생성 ---
    st.divider()
    st.subheader("🤖 Gemini AI 옵션 시장 브리핑")
    
    # 💡 [핵심 강화] 프롬프트용 상세 데이터 연산
    call_oi = calls['openInterest'].sum()
    put_oi = puts['openInterest'].sum()
    pcr_oi = put_oi / call_oi if call_oi > 0 else 0
    
    call_itm_vol = calls[calls['inTheMoney']]['volume'].sum() if 'inTheMoney' in calls.columns else 0
    call_otm_vol = call_vol - call_itm_vol
    put_itm_vol = puts[puts['inTheMoney']]['volume'].sum() if 'inTheMoney' in puts.columns else 0
    put_otm_vol = put_vol - put_itm_vol
    
    avg_call_iv = calls['impliedVolatility'].mean() * 100 if 'impliedVolatility' in calls.columns else 0
    avg_put_iv = puts['impliedVolatility'].mean() * 100 if 'impliedVolatility' in puts.columns else 0
    
    def format_top_strikes(df, sort_col):
        if df is None or df.empty or sort_col not in df.columns: return "데이터 없음"
        top_df = df.nlargest(3, sort_col)
        res = []
        for _, r in top_df.iterrows():
            strike = r.get('strike', 0)
            vol = r.get('volume', 0)
            oi = r.get('openInterest', 0)
            iv = r.get('impliedVolatility', 0) * 100
            res.append(f"${strike:,.2f} (Vol:{vol:,.0f} / OI:{oi:,.0f} / IV:{iv:.1f}%)")
        return " | ".join(res)
        
    top_c_vol_str = format_top_strikes(calls, 'volume')
    top_p_vol_str = format_top_strikes(puts, 'volume')
    top_c_oi_str = format_top(calls, 'openInterest')
    top_p_oi_str = format_top(puts, 'openInterest')

    # 초정밀 심층 프롬프트
    prompt = f"""
당신은 월스트리트의 수석 파생상품 애널리스트입니다. 
아래에 제공된 상세한 옵션 체인(Option Chain) 데이터를 바탕으로 현재 시장 참여자들의 심리와 주가 방향성을 심층 분석하세요.

[기본 정보]
- 티커(종목명): {ticker_input} ({name})
- 기초자산 현재가: ${current_price:,.2f}
- 옵션 만기일: {selected_expiry}

[종합 수급 요약]
- 총 거래량(Volume): 콜 {call_vol:,.0f} vs 풋 {put_vol:,.0f} (거래량 P/C Ratio: {pcr:.2f})
- 총 미결제약정(OI): 콜 {call_oi:,.0f} vs 풋 {put_oi:,.0f} (OI P/C Ratio: {pcr_oi:.2f})
- 내가격(ITM) 거래량: 콜 {call_itm_vol:,.0f} / 풋 {put_itm_vol:,.0f}
- 외가격(OTM) 거래량: 콜 {call_otm_vol:,.0f} / 풋 {put_otm_vol:,.0f}
- 평균 내재변동성(IV): 콜 {avg_call_iv:.2f}% / 풋 {avg_put_iv:.2f}%

[거래량 집중 구간 (스마트 머니 단기 동향 예측)]
- 콜옵션 거래량 상위 3개 행사가: {top_c_vol_str}
- 풋옵션 거래량 상위 3개 행사가: {top_p_vol_str}

[미결제약정(OI) 집중 구간 (강력한 지지/저항선 예측)]
- 콜옵션 미결제약정 상위 3개 행사가 (저항대): {top_c_oi_str}
- 풋옵션 미결제약정 상위 3개 행사가 (지지대): {top_p_oi_str}

[분석 지시사항 - 반드시 아래 목차를 지켜 작성하세요]
1. **옵션 수급 및 심리 분석**: 
   - P/C Ratio(거래량과 미결제약정 차이 비교)와 ITM/OTM 거래량 비율을 종합하여, 현재 시장이 상방(콜 매집)을 기대하는지 하방(풋 헷지/매집)을 대비하는지 분석하세요.
2. **변동성(IV) 분석**: 
   - 콜과 풋의 평균 내재변동성 차이를 통해 시장이 예상하는 리스크 프리미엄과 향후 주가 변동폭을 해석하세요.
3. **핵심 매물대 (지지 및 저항선) 설정**: 
   - 거래량과 미결제약정이 가장 많이 누적된 행사가를 바탕으로 단기적인 주가 하단(지지선)과 상단(저항선)을 구체적인 가격으로 제시하고 그 이유를 설명하세요.
4. **실전 트레이딩 전략**: 
   - 이 옵션 데이터를 바탕으로 주식 투자자나 단기 트레이더가 취할 수 있는 구체적인 매매 전략(방향성 베팅, 위험 헷지 등)을 제안하세요.
5. 분석은 초보자도 이해할 수 있으면서도 전문가의 깊이가 느껴지는 '한글(Korean)' 마크다운 형식으로 가독성 있게 작성해 주세요.
"""

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        st.markdown("#### 옵션 1. 스트림릿에서 바로 분석")
        if st.button("✨ API 자동 분석 (약 10초 소요)", type="primary", use_container_width=True):
            if has_api_key:
                with st.spinner("AI가 방대한 데이터를 바탕으로 심층 분석을 진행 중입니다..."):
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
        safe_prompt = json.dumps(prompt)
        html_code = f"""
        <button onclick="copyAndOpen()" style="background-color: #f5a623; color: #000; padding: 12px 20px; border: none; border-radius: 8px; font-weight: bold; font-size: 15px; cursor: pointer; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: 0.2s;">
            📋 초정밀 프롬프트 복사 & Gemini 웹 열기
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

    with st.expander("🔍 AI에게 전송되는 심층 데이터 원본 확인하기", expanded=False):
        st.code(prompt, language="text")

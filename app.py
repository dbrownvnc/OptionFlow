import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
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

# --- 4. 공통 데이터 수집 (현재가 등) ---
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

# =====================================================================
# 모드 1: 단일 만기일 분석 (기존 로직 유지)
# =====================================================================
if analysis_mode == "단일 만기일 분석" and selected_expiry:
    with st.spinner(f"'{selected_expiry}' 만기 옵션 체인 분석 중..."):
        opt_chain = ticker.option_chain(selected_expiry)
        calls, puts = opt_chain.calls, opt_chain.puts
        
        if current_price > 0:
            min_strike, max_strike = current_price * 0.7, current_price * 1.3
            calls_chart = calls[(calls['strike'] >= min_strike) & (calls['strike'] <= max_strike)]
            puts_chart = puts[(puts['strike'] >= min_strike) & (puts['strike'] <= max_strike)]
        else:
            calls_chart, puts_chart = calls, puts

        call_vol = calls['volume'].sum()
        put_vol = puts['volume'].sum()
        call_oi = calls['openInterest'].sum()
        put_oi = puts['openInterest'].sum()
        pcr = put_vol / call_vol if call_vol > 0 else 0

        c1, c2, c3 = st.columns(3)
        status_color = "#f5a623"
        status_text = "중립 (Neutral)"
        if pcr > 1.2: 
            status_color, status_text = "#ff4d6d", "하락 신호 (Bearish)"
        elif pcr < 0.7: 
            status_color, status_text = "#00e5a0", "상승 신호 (Bullish)"

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
        with c1: st.markdown(get_metric_card("CALL 거래량", f"{int(call_vol):,}", "#00e5a0"), unsafe_allow_html=True)
        with c2: st.markdown(get_metric_card("PUT 거래량", f"{int(put_vol):,}", "#ff4d6d"), unsafe_allow_html=True)
        with c3: st.markdown(get_metric_card("Put/Call Ratio", f"{pcr:.2f}", "#f3f4f6", status_text, status_color), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # 차트
        fig = go.Figure()
        fig.add_trace(go.Bar(x=calls_chart['strike'], y=calls_chart['volume'], name='Calls', marker_color='#00e5a0'))
        fig.add_trace(go.Bar(x=puts_chart['strike'], y=-puts_chart['volume'], name='Puts', marker_color='#ff4d6d'))
        fig.update_layout(title=f"행사가별 거래량 (만기: {selected_expiry})", barmode='relative', template="plotly_dark", height=400, hovermode="x unified")
        if current_price > 0: fig.add_vline(x=current_price, line_dash="dash", line_color="white")
        st.plotly_chart(fig, use_container_width=True)

        prompt = f"""
당신은 월스트리트 파생상품 애널리스트입니다. 아래 데이터를 바탕으로 시장 심리를 분석하세요.
[분석 대상] {name} ({ticker_input}) / 만기일: {selected_expiry} / 현재가: ${current_price:,.2f}
[단일 만기일 수급]
- 콜옵션 거래량: {call_vol:,.0f} (OI: {call_oi:,.0f})
- 풋옵션 거래량: {put_vol:,.0f} (OI: {put_oi:,.0f})
- PCR: {pcr:.2f}
지시사항: 단기 주가 방향을 예측하고 지지/저항선을 도출하여 한글 마크다운으로 요약하세요.
"""

# =====================================================================
# 모드 2: 다중 기간 통합 분석 (새로 추가된 핵심 로직)
# =====================================================================
elif analysis_mode == "전체 기간 통합 분석 (단/중/장기)" and expirations:
    st.info("💡 **단기(30일 이내), 중기(30~90일), 장기(90일 이상)** 만기일 옵션 데이터를 모두 수집하여 입체적으로 분석합니다.")
    
    with st.spinner("전체 만기일 데이터를 수집 중입니다... (만기일이 많을 경우 10~30초 소요)"):
        today = datetime.today()
        
        # 기간별 집계 딕셔너리
        term_data = {
            "Short (단기/30일내)": {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
            "Mid (중기/30~90일)": {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0},
            "Long (장기/90일이상)": {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0}
        }
        
        # 진행바 표시
        progress_bar = st.progress(0)
        total_exps = len(expirations)
        
        # 모든 만기일을 순회하며 데이터 집계
        for i, exp_date in enumerate(expirations):
            try:
                days_to_exp = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
                
                # 기간 분류
                if days_to_exp <= 30: category = "Short (단기/30일내)"
                elif days_to_exp <= 90: category = "Mid (중기/30~90일)"
                else: category = "Long (장기/90일이상)"
                
                opt = ticker.option_chain(exp_date)
                term_data[category]["call_vol"] += opt.calls['volume'].sum() if 'volume' in opt.calls else 0
                term_data[category]["put_vol"] += opt.puts['volume'].sum() if 'volume' in opt.puts else 0
                term_data[category]["call_oi"] += opt.calls['openInterest'].sum() if 'openInterest' in opt.calls else 0
                term_data[category]["put_oi"] += opt.puts['openInterest'].sum() if 'openInterest' in opt.puts else 0
                
            except Exception as e:
                pass
            progress_bar.progress((i + 1) / total_exps)
            
        progress_bar.empty()

        # 데이터 프레임 변환
        df_terms = pd.DataFrame(term_data).T
        df_terms['PCR (Volume)'] = df_terms['put_vol'] / df_terms['call_vol']
        df_terms['PCR (OI)'] = df_terms['put_oi'] / df_terms['call_oi']
        df_terms.fillna(0, inplace=True)

        # 다중 기간 집계 차트 표시
        st.markdown("#### 📊 기간별 수급 비교 (Term Structure)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_terms.index, y=df_terms['call_vol'], name='CALL 거래량', marker_color='#00e5a0'))
        fig2.add_trace(go.Bar(x=df_terms.index, y=df_terms['put_vol'], name='PUT 거래량', marker_color='#ff4d6d'))
        fig2.update_layout(barmode='group', template='plotly_dark', height=400, hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### 📑 기간별 데이터 요약")
        display_df = df_terms.copy()
        display_df.columns = ['Call 거래량', 'Put 거래량', 'Call 미결제약정', 'Put 미결제약정', 'PCR(거래량)', 'PCR(미결제)']
        for col in ['Call 거래량', 'Put 거래량', 'Call 미결제약정', 'Put 미결제약정']:
            display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}")
        for col in ['PCR(거래량)', 'PCR(미결제)']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}")
        st.dataframe(display_df, use_container_width=True)

        # 다중 기간 전용 프롬프트 생성
        prompt = f"""
당신은 월스트리트의 시니어 파생상품 애널리스트입니다. 제공된 '{name} ({ticker_input})'의 [기간별(Term Structure) 옵션 수급 데이터]를 바탕으로 시장의 단기, 중기, 장기 시나리오를 입체적으로 분석하세요.

[분석 대상]
- 티커: {ticker_input} ({name})
- 현재가: ${current_price:,.2f}

[기간별 수급 데이터 (Volume & Open Interest)]
1. 단기 (30일 이내):
   - 콜 거래량: {df_terms.loc['Short (단기/30일내)']['call_vol']:,.0f} / 콜 OI: {df_terms.loc['Short (단기/30일내)']['call_oi']:,.0f}
   - 풋 거래량: {df_terms.loc['Short (단기/30일내)']['put_vol']:,.0f} / 풋 OI: {df_terms.loc['Short (단기/30일내)']['put_oi']:,.0f}
   - PCR (Volume): {df_terms.loc['Short (단기/30일내)']['PCR (Volume)']:.2f}

2. 중기 (30일 ~ 90일):
   - 콜 거래량: {df_terms.loc['Mid (중기/30~90일)']['call_vol']:,.0f} / 콜 OI: {df_terms.loc['Mid (중기/30~90일)']['call_oi']:,.0f}
   - 풋 거래량: {df_terms.loc['Mid (중기/30~90일)']['put_vol']:,.0f} / 풋 OI: {df_terms.loc['Mid (중기/30~90일)']['put_oi']:,.0f}
   - PCR (Volume): {df_terms.loc['Mid (중기/30~90일)']['PCR (Volume)']:.2f}

3. 장기 (90일 이상):
   - 콜 거래량: {df_terms.loc['Long (장기/90일이상)']['call_vol']:,.0f} / 콜 OI: {df_terms.loc['Long (장기/90일이상)']['call_oi']:,.0f}
   - 풋 거래량: {df_terms.loc['Long (장기/90일이상)']['put_vol']:,.0f} / 풋 OI: {df_terms.loc['Long (장기/90일이상)']['put_oi']:,.0f}
   - PCR (Volume): {df_terms.loc['Long (장기/90일이상)']['PCR (Volume)']:.2f}

[분석 지시사항]
1. **기간별 심리 변화(Term Structure):** 단기 트레이더들의 심리(투기/헤징)와 중장기 투자자들의 포지션(추세 확신)이 어떻게 다른지 입체적으로 비교 분석하세요.
2. **다이버전스 캐치:** 단기 PCR과 장기 PCR이 크게 다르다면, 시장이 단기 조정을 겪더라도 장기적으로 우상향을 보는지(혹은 그 반대인지) 통찰력 있게 설명하세요.
3. **종합 결론:** 위 3개 기간의 데이터를 종합했을 때, 향후 1~3개월간 예상되는 주가의 방향성 시나리오를 도출해 주세요.
4. 초보자도 이해할 수 있도록 친절한 한글 마크다운으로 깔끔하게 정리하세요.
"""

# =====================================================================
# 공통 AI 분석 섹션 (모드에 맞춰 생성된 프롬프트 전달)
# =====================================================================
if ticker_input and expirations and ((analysis_mode == "단일 만기일 분석" and selected_expiry) or analysis_mode != "단일 만기일 분석"):
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

    with st.expander("생성된 고도화 분석 프롬프트 내용 확인하기", expanded=False):
        st.code(prompt, language="text")

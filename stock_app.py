import streamlit as st
import pandas as pd
from stock_scanner import StockScanner
import plotly.graph_objects as go
from datetime import datetime
import time
import signal
import threading
import json
import os
import requests
from streamlit.runtime import Runtime

# --- Page Configuration ---
st.set_page_config(
    page_title="Premium Stock Selection Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def shutdown_app():
    """애플리케이션과 브라우저 창을 동시에 종료합니다."""
    # 종료 화면으로 전환 (연결 끊김 에러 방지)
    st.markdown("""
        <div style="background:#0e1117; color:white; height:100vh; width:100vw; position:fixed; top:0; left:0; z-index:9999; display:flex; align-items:center; justify-content:center; font-family:sans-serif; flex-direction:column;">
            <h1 style="color: #ff4b4b;">🏁 프로그램 종료 중...</h1>
            <p style="font-size: 1.2em; color: #8b949e;">터미널 창(CMD)이 잠시 후 자동으로 닫힙니다.</p>
            <p style="color: #58a6ff;">이 브라우저 창을 닫으셔도 좋습니다.</p>
        </div>
        <script>
            // 창 닫기 시도 (일부 브라우저 허용)
            setTimeout(function() { window.close(); }, 2000);
        </script>
    """, unsafe_allow_html=True)
    
    # 서버가 화면을 전송할 시간을 벌어준 뒤 종료
    def delayed_exit():
        time.sleep(2)
        print("\n👋 사용자가 종료 버튼을 눌렀습니다. 프로그램을 종료합니다.")
        os._exit(0)
        
    threading.Thread(target=delayed_exit).start()

def auto_shutdown_monitor():
    """브라우저 탭이 모두 닫히면 서버를 자동으로 종료합니다."""
    start_time = time.time()
    has_connected = False
    
    while True:
        time.sleep(3) 
        try:
            runtime = Runtime.instance()
            # 세션 매니저 이름이 버전에 따라 다를 수 있으므로 유연하게 대응
            session_mgr = getattr(runtime, '_session_mgr', None) or getattr(runtime, '_session_manager', None)
            
            if session_mgr:
                sessions = session_mgr.list_active_sessions()
                
                if not has_connected and len(sessions) > 0:
                    has_connected = True
                    print("🌐 브라우저 세션 연결됨. 자동 종료 감시 가동 중...")
                    
                if has_connected and len(sessions) == 0:
                    print("\n🛑 브라우저 창이 모두 닫혔습니다. 프로그램을 종료합니다.")
                    os._exit(0)
                    break
            
            if not has_connected and (time.time() - start_time) > 40:
                print("\n⚠️ 40초 동안 연결이 없어 프로그램을 자동 종료합니다.")
                os._exit(0)
                break
        except Exception as e:
            continue

# 클라우드 배포를 위해 자동 종료 기능 비활성화
# if 'shutdown_monitor_started' not in st.session_state:
#     st.session_state['shutdown_monitor_started'] = True
#     threading.Thread(target=auto_shutdown_monitor, daemon=True).start()


# --- Custom Styling ---
st.markdown("""
    <style>
    /* 기본 테마 설정 */
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1a1c24;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .stHeading {
        color: #58a6ff;
    }
    
    /* 📱 스마트폰/모바일 환경 최적화 CSS (화면 가로 768px 이하) */
    @media (max-width: 768px) {
        /* 전체 화면 좌우상하 여백을 줄여서 스마트폰 화면을 넓게 사용 */
        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        
        /* 큰 텍스트(제목) 크기를 모바일에 맞게 축소하여 줄바꿈 최소화 */
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
        
        /* 터치하기 편하도록 버튼 요소들의 세로 길이를 살짝 늘리고 크기 조정 */
        .stButton > button {
            width: 100% !important;
            min-height: 50px !important;
            margin-bottom: 5px;
        }
        
        /* 모바일에서는 표(DataFrame) 안의 글자 크기를 줄여 한눈에 많은 정보가 들어오도록 함 */
        [data-testid="stDataFrame"] {
            font-size: 0.75rem !important;
        }
        
        /* 라디오 버튼(필터링 선택 등) 레이아웃 글씨 축소 */
        .stRadio > div > label {
            font-size: 0.8rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- Configuration Management ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {"telegram_token": "", "telegram_chat_id": "", "auto_send": False, "custom_url": ""}
    return {"telegram_token": "", "telegram_chat_id": "", "auto_send": False, "custom_url": ""}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def send_telegram_message(message):
    config = load_config()
    token = config.get("telegram_token")
    chat_id = config.get("telegram_chat_id")
    
    if not token or not chat_id:
        return False, "텔레그램 설정(토큰, 채팅ID)이 필요합니다."
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # 텔레그램 메시지 길이 제한(4096자) 처리: 안전하게 4000자씩 분할
        max_length = 4000
        messages = [message[i:i+max_length] for i in range(0, len(message), max_length)]
        
        for msg in messages:
            data = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
            response = requests.post(url, data=data)
            if response.status_code != 200:
                return False, f"오류: {response.text}"
        
        return True, "성공"
    except Exception as e:
        return False, str(e)

def format_stock_message(results, market_name):
    if not results:
        return "검색된 종목이 없습니다."
    
    msg = f"🔍 *[{market_name}] 종목 분석 리포트*\n"
    msg += f"📅 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    msg += f"📊 분석된 종목: 총 {len(results)}개\n\n"
    
    df_res = pd.DataFrame(results).sort_values(by='score', ascending=False)
    
    # 1. 전략 중첩 & 급등 TOP 분석 (최대 5개)
    special_top = get_special_stocks(results)
    if special_top:
        msg += "💎 *전략 중첩 & 급등 TOP 분석*\n"
        for row in special_top[:5]:
            action_emoji = "🚀" if "🚀" in row['signals'] else "💎"
            msg += f"{action_emoji} *{row['Name']}* ({row['symbol']})\n"
            msg += f"   - 점수: {row['score']} | 신호: {row.get('total_signals', 0)}개 중첩\n"
        msg += "------------------\n\n"

    # 2. 종합 점수 상위 종목 (최대 5개 상세 요약)
    msg += "🏆 *종합 점수 상위 상세 분석*\n"
    for _, row in df_res.head(5).iterrows():
        action_emoji = "🚀" if row['action'] == "BUY" else ("⚠️" if row['action'] == "SELL" else "👀")
        msg += f"{action_emoji} *{row['Name']}* ({row['symbol']})\n"
        msg += f"   - 신호: {row['action_desc']} (점수: {row['score']}점)\n"
        msg += f"   - 요약: {row['signals'][:60]}...\n\n"
    
    # 3. 전체 분석 결과 리스트 (간결한 형식)
    msg += "📋 *전체 분석 결과 리스트*\n"
    msg += "```\n" # 가독성을 위해 코드 블록 사용 (고정 폭 폰트)
    msg += "순위 | 종목명 (코드) | 점수 | 신호\n"
    msg += "-" * 34 + "\n"
    
    # 신호 표기 한글화 맵핑
    status_map = {
        "강력 매수": "강력매수",
        "추격 매수 가능": "추격매수",
        "분할 매수 유효": "매수유효",
        "관망": "관망",
        "과매수 익절 권장": "익절권장",
        "추세 이탈 우려 (매도/손절)": "매도주의"
    }
    
    for i, (_, row) in enumerate(df_res.iterrows()):
        raw_desc = row['action_desc']
        display_status = status_map.get(raw_desc, raw_desc[:4]) # 맵핑 안되면 앞 4자만
        msg += f"{i+1:2d}. {row['Name'][:8]} ({row['symbol']}) | {row['score']}점 | {display_status}\n"
    msg += "```\n\n"
    
    msg += "🔗 대시보드에서 차트와 전문가 의견을 확인하세요."
    return msg

def format_portfolio_message(p_results, scanner):
    if not p_results:
        return "보유 중인 종목이 없거나 분석 데이터가 없습니다."
    
    msg = "💼 *[나의 포트폴리오 현황]*\n"
    msg += f"📅 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    # 데이터프레임으로 변환하여 시장별 그룹화 (속도 및 편의성)
    df_p = pd.DataFrame(p_results)
    if 'market' not in df_p.columns:
        return "분석 데이터 형식이 올바르지 않습니다."
        
    for market in df_p['market'].unique():
        msg += f"📍 *{market} 시장*\n"
        df_m = df_p[df_p['market'] == market]
        for _, row in df_m.iterrows():
            # 컬럼명 대소문자 및 존재 여부 유연하게 대응
            symbol = row.get('symbol') or row.get('Symbol') or 'Unknown'
            name = row.get('name') or row.get('Name') or scanner.get_symbol_name(symbol, market)
            action = row.get('action', 'WAIT')
            action_desc = row.get('action_desc', '-')
            price = row.get('current_price', 0)
            rsi = row.get('rsi', 0)
            
            action_emoji = "🚀" if action == "BUY" else ("⚠️" if action == "SELL" else "👀")
            msg += f"{action_emoji} *{name}* ({symbol})\n"
            msg += f"   - 신호: {action} ({action_desc})\n"
            msg += f"   - 현재가: {price:,.0f} | RSI: {rsi:.1f}\n\n"
    
    msg += "📢 매도 신호가 발생한 종목은 즉시 대응하세요."
    return msg

def get_special_stocks(results):
    """급등 전조가 있거나, 전문가 전략이 2개 이상 부합하는 종목을 필터링합니다."""
    special = []
    for r in results:
        is_surge = "🚀 급등 전조" in r['signals']
        # 전문가 전략 개수 계산
        expert_count = sum(1 for k, v in r.get('experts', {}).items() if v)
        # 퓨처온 멘토 전략 추가 계산
        fo_count = sum(1 for k in ['isle', 'shintae', 'juns'] if r.get('futureon', {}).get(k))
        # 세력 수급 개수 계산
        sm_count = sum(1 for k, v in r.get('smart_money', {}).items() if v)
        
        if is_surge or expert_count >= 2 or (expert_count + fo_count >= 1 and sm_count >= 1):
            r['total_signals'] = expert_count + fo_count + sm_count + (1 if is_surge else 0)
            special.append(r)
    
    # 신호 강도 순으로 정렬 후 TOP 10 반환
    return sorted(special, key=lambda x: (x.get('total_signals', 0), x['score']), reverse=True)[:10]

def display_detailed_chart(symbol, market):
    """선택된 종목의 상세 캔들스틱 차트를 표시합니다."""
    # 데이터 가져오기 (최근 120일)
    df = scanner.get_historical_data(symbol, market, days=120)
    if df is None or df.empty:
        st.error(f"{symbol} 데이터를 불러오지 못했습니다.")
        return

    # 기술 지표 계산 (이동평균선)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # RSI 계산 (이미 scanner에 로직이 있으나 차트용으로 재계산 또는 사용)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Plotly 차트 생성
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=(f'📈 {symbol} 캔들스틱', '📊 RSI 지표'),
                        row_heights=[0.7, 0.3])

    # 1. 캔들스틱 추가
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    
    # 2. 이동평균선 및 Future On 지표 추가
    # 기본 이평선
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='rgba(255,255,255,0.4)', width=1), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='rgba(255,165,0,0.4)', width=1), name='MA60'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='rgba(255,0,0,0.4)', width=1), name='MA120'), row=1, col=1)

    # 🏆 퓨처온 핵심 지표 (강조)
    if 'GoldLine' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['GoldLine'], line=dict(color='#f1c40f', width=2), name='🏆 골드라인 (EMA 33)'), row=1, col=1)
    
    if 'WhaleLine' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['WhaleLine'], line=dict(color='#9b59b6', width=2, dash='dash'), name='🐳 세력선 (EMA 448)'), row=1, col=1)

    # 볼린저 밴드 (NS밴드)
    if 'BB_High' in df.columns and 'BB_Low' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(173, 216, 230, 0.1)'), showlegend=False, name='BB High'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(173, 216, 230, 0.1)'), fill='tonexty', showlegend=False, name='BB Low'), row=1, col=1)

    # 3. 수평 지지/저항선 (Horizontal Levels)
    # scanner 인스턴스가 add_indicators를 내부에서 호출하면서 self.horizontal_levels를 설정하도록 되어 있음
    if hasattr(scanner, 'horizontal_levels') and scanner.horizontal_levels:
        for level in scanner.horizontal_levels:
            fig.add_hline(y=level, line_dash="dot", line_color="rgba(255,255,255,0.2)", 
                          annotation_text=f"S/R: {level:,.0f}", annotation_position="bottom right", row=1, col=1)

    # 4. RSI 추가
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=1.5), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(height=700, template="plotly_dark", showlegend=True, 
                      xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True)

# --- Portfolio Management ---
# 실행 환경에 구애받지 않도록 절대 경로 사용
PORTFOLIO_FILE = os.path.join(BASE_DIR, "portfolio.json")

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except:
            return {"KR": [], "US": [], "COIN": []}
    return {"KR": [], "US": [], "COIN": []}

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f)

# --- App Logic ---
st.title("🚀 Premium Stock Selection & Monitoring")

# @st.cache_resource # 캐싱된 이전 버전의 StockScanner 객체로 인해 find_symbol_by_name 속성 오류가 발생할 수 있습니다.
def get_scanner():
    return StockScanner()

scanner = get_scanner()

# @st.cache_data(ttl=3600)  # 코드 변경 후 데이터 호환성을 위해 일시적으로 캐싱 비활성화
def run_scan(market_choice, scan_limit):
    if market_choice == "한국 (KRX)":
        symbols_df = scanner.get_krx_symbols().head(scan_limit)
        market_code = 'KR'
        symbol_col = 'Code' if 'Code' in symbols_df.columns else 'Symbol'
    elif market_choice == "미국 (US)":
        symbols_df = scanner.get_us_symbols().head(scan_limit)
        market_code = 'US'
        symbol_col = 'Symbol'
    else: # 암호화폐 (Upbit)
        symbols_df = scanner.get_coin_symbols().head(scan_limit)
        market_code = 'COIN'
        symbol_col = 'Symbol'

    results = []
    for i, (idx, row) in enumerate(symbols_df.iterrows()):
        symbol = row[symbol_col]
        name = row['Name']
        analysis = scanner.analyze_stock(symbol, market_code)
        
        if analysis and analysis['score'] >= 50:
            analysis['Name'] = name
            results.append(analysis)
    return results

def plot_chart(df, symbol, name):
    """Plotly를 사용하여 캔들스틱 차트와 보조 지표를 그립니다."""
    fig = go.Figure()

    # 1. 캔들스틱 차트
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candle'
    ))

    # 2. 이동평균선
    if 'MA50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='orange', width=1.5), name='MA50'))
    if 'MA200' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='red', width=1.5), name='MA200'))

    # 3. 볼린저 밴드 (급등 전조 확인용)
    if 'BB_High' in df.columns and 'BB_Low' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(173, 216, 230, 0.2)'), name='BB High'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(173, 216, 230, 0.2)'), fill='tonexty', name='BB Low'))

    # 레이아웃 설정
    fig.update_layout(
        title=f"📈 {name} ({symbol}) 상세 차트",
        yaxis_title="Price",
        xaxis_title="Date",
        template="plotly_dark",
        height=600,
        xaxis_rangeslider_visible=False
    )
    return fig

# --- 공통 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정")
    market_choice = st.radio("분석 시장 선택", ["한국 (KRX)", "미국 (US)", "암호화폐 (Upbit)"])
    
    # 시장 선택 변경 시 이전 결과 초기화
    if 'selected_market' not in st.session_state:
        st.session_state['selected_market'] = market_choice
    if st.session_state['selected_market'] != market_choice:
        st.session_state['scan_results'] = []
        st.session_state['selected_market'] = market_choice
    scan_limit = st.slider("분석 종목 수 (샘플)", 10, 100, 30)
    run_button = st.button("🔥 스캔 시작")
    
    st.markdown("---")
    st.subheader("📢 알림 설정")
    config = load_config()
    tg_token = st.text_input("Telegram Bot Token", value=config.get("telegram_token", ""), type="password")
    tg_chat_id = st.text_input("Telegram Chat ID", value=config.get("telegram_chat_id", ""))
    auto_send = st.checkbox("🔥 스캔 완료 시 자동 전송", value=config.get("auto_send", False))
    st.markdown("---")
    st.subheader("🌐 외부 접속 환경 설정")
    custom_url_input = st.text_input("커스텀 URL (선택, ngrok 등)", value=config.get("custom_url", ""), help="외부망에서 접속할 때 할당받은 주소(예: https://1234.ngrok.io)를 입력하면 해당 주소로 QR코드가 생성됩니다. 비워두면 현재 PC의 내부망 IP로 자동 생성됩니다.")
    
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        if st.button("💾 설정 저장", use_container_width=True):
            config["telegram_token"] = tg_token
            config["telegram_chat_id"] = tg_chat_id
            config["auto_send"] = auto_send
            config["custom_url"] = custom_url_input
            save_config(config)
            st.success("설정이 저장되었습니다!")
    
    with col_cfg2:
        if st.button("⚡ 연결 테스트", use_container_width=True):
            if not tg_token or not tg_chat_id:
                st.warning("토큰과 채팅ID를 먼저 입력하세요.")
            else:
                test_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                test_data = {"chat_id": tg_chat_id, "text": "✅ *주식 대시보드*: 연결 테스트 성공! 🚀", "parse_mode": "Markdown"}
                try:
                    res = requests.post(test_url, data=test_data)
                    if res.status_code == 200:
                        st.success("연결 성공! 텔레그램을 확인하세요.")
                    else:
                        st.error(f"실패: {res.text}")
                except Exception as e:
                    st.error(f"오류: {e}")
    
    if st.button("🔍 내 채팅 ID 자동으로 찾기"):
        if not tg_token:
            st.warning("먼저 봇 토큰(Token)을 입력해 주세요.")
        else:
            try:
                with st.spinner("텔레그램에서 최신 메시지를 확인 중입니다..."):
                    # 봇에게 메시지를 보낸 이력을 확인하여 채팅 ID를 가져옴
                    update_url = f"https://api.telegram.org/bot{tg_token}/getUpdates"
                    res = requests.get(update_url).json()
                    
                    if res.get("ok") and res.get("result"):
                        # 최신 업데이트부터 역순으로 탐색
                        found_id = None
                        found_name = None
                        
                        for update in reversed(res["result"]):
                            # 일반 메시지 확인
                            if "message" in update:
                                found_id = update["message"]["chat"]["id"]
                                found_name = update["message"]["chat"].get("title") or update["message"]["chat"].get("first_name", "사용자")
                                break
                            # 채널 포스트 확인
                            elif "channel_post" in update:
                                found_id = update["channel_post"]["chat"]["id"]
                                found_name = update["channel_post"]["chat"].get("title", "채널")
                                break
                        
                        if found_id:
                            st.success(f"성공! '{found_name}' (ID: {found_id})를 찾았습니다.")
                            st.info("이 ID를 채팅 ID 칸에 입력하고 저장하세요. (채널의 경우 -100으로 시작하는 숫자가 맞습니다.)")
                        else:
                            st.error("최근 메시지나 포스트를 찾지 못했습니다.")
                    else:
                        st.error("봇이 받은 메시지가 없습니다. 텔레그램 채팅방(또는 채널)에서 메시지를 보내거나 포스팅한 후 다시 시도해 주세요.")
            except Exception as e:
                st.error(f"오류 발생: {e}")

    st.markdown("---")
    st.subheader("📱 모바일 접속")
    
    # 모바일용 QR 코드 및 링크 제공
    def get_local_ip():
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'
            
    local_ip = get_local_ip()
    
    # 커스텀 URL이 설정되어 있는지 확인
    saved_url = config.get("custom_url", "").strip()
    if saved_url:
        mobile_url = saved_url
        # URL 형식 보정 (http/https가 없으면 추가)
        if not mobile_url.startswith("http"):
            mobile_url = "http://" + mobile_url
        msg_desc = "입력하신 전용 네트워크 주소(ngrok 등)로 QR이 생성되었습니다. 외부 어디서든 폰으로 스캔하세요!"
    else:
        mobile_url = f"http://{local_ip}:8501"
        msg_desc = "PC와 동일한 Wi-Fi에 연결된 폰으로 아래 QR을 스캔하세요."
    
    st.info(f"💡 **스마트폰으로 편하게 보기:**\n{msg_desc}")
    
    # 레이아웃을 이쁘게 배치
    col_qr1, col_qr2 = st.columns([1, 1])
    with col_qr1:
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={mobile_url}", width=120)
    with col_qr2:
        st.write(" ") # 수직 정렬
        st.write(" ")
        st.caption("접속 주소:")
        st.code(mobile_url, language="text")

    st.markdown("---")
    st.subheader("🏁 시스템")
    if st.button("🚀 프로그램 완전히 종료", help="웹페이지와 터미널(CMD) 창을 모두 닫습니다."):
        shutdown_app()

# 메인 탭 구성
tab_scan, tab_portfolio = st.tabs(["🔍 종목 스캔", "💼 나의 포트폴리오"])

with tab_scan:
    st.markdown("### 🔍 시장 종목 스캐너")
    
    # [신규] 개별 종목 직접 검색 섹션
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_input = st.text_input("🔍 종목명 또는 코드 검색 (예: 삼성전자, AAPL, 비트코인)", key="direct_search_input").strip()
    with search_col2:
        st.write(" ") # 수직 정렬용
        if st.button("🚀 즉시 분석", use_container_width=True):
            if search_input:
                with st.spinner(f"'{search_input}' 정밀 분석 중..."):
                    # 1. 시장 코드 자동 판별 (코드 직접 입력 대응)
                    m_code = 'KR'
                    input_upper = search_input.upper()
                    if '-' in input_upper: m_code = 'COIN'
                    elif any(c.isalpha() for c in input_upper): m_code = 'US'
                    
                    # 먼저 코드로 분석 시도
                    analysis = scanner.analyze_stock(input_upper, m_code)
                    target_symbol = input_upper
                    
                    # 2. 코드로 분석 실패 시 이름으로 검색 시도
                    if not analysis:
                        found_code, found_market = scanner.find_symbol_by_name(search_input)
                        if found_code:
                            target_symbol = found_code
                            m_code = found_market
                            analysis = scanner.analyze_stock(target_symbol, m_code)
                    
                    if analysis:
                        analysis['Name'] = scanner.get_symbol_name(target_symbol, m_code)
                        analysis['market_type'] = m_code
                        st.session_state['direct_search_result'] = analysis
                        st.success(f"{analysis['Name']} ({target_symbol}) 분석 완료!")
                    else:
                        st.error("종목을 찾을 수 없거나 데이터를 가져오지 못했습니다. 이름이나 코드를 확인해 주세요.")
            else:
                st.warning("분석할 종목명 또는 코드를 입력하세요.")

    if 'direct_search_result' in st.session_state and st.session_state['direct_search_result']:
        s_data = st.session_state['direct_search_result']
        with st.expander(f"📌 {s_data['Name']} ({s_data['symbol']}) 검색 결과 (클릭하여 닫기)", expanded=True):
            st.markdown(f"#### 🛰️ {s_data['Name']} 실시간 기술적 상태")
            
            s_col1, s_col2 = st.columns([2, 1])
            with s_col1:
                display_detailed_chart(s_data['symbol'], s_data['market_type'])
            with s_col2:
                st.metric("현재가", f"{s_data['current_price']:,.0f}")
                st.metric("종합 점수", f"{s_data['score']}점")
                st.markdown("##### 📡 분석 신호")
                for sig in s_data['signals'].split(','):
                    if sig.strip(): st.caption(f"• {sig.strip()}")
                
                if s_data['action'] == 'BUY': st.success(f"**{s_data['action_desc']}**")
                else: st.info(f"**{s_data['action_desc']}**")
                
                if st.button("⭐ 검색 종목 포트폴리오 추가", key="add_search_portfolio", use_container_width=True):
                    p_data = load_portfolio()
                    m_key = s_data['market_type']
                    if s_data['symbol'] not in p_data[m_key]:
                        p_data[m_key].append(s_data['symbol'])
                        save_portfolio(p_data)
                        st.success("포트폴리오에 등록되었습니다!")
                    else: st.warning("이미 등록된 종목입니다.")
            
            if st.button("❌ 검색 결과 지우기", use_container_width=True):
                del st.session_state['direct_search_result']
                st.rerun()

    st.write("---")
    st.markdown("#### 📡 시장 전체 자동 스캐너")
    st.caption("실시간 데이터를 분석하여 급등 전조 및 세력 수급 종목을 대량 검색합니다.")

    if run_button:
        st.subheader(f"🔍 {market_choice} 상위 종목 분석 중...")
        
        with st.spinner("데이터를 분석하고 리스트를 생성하고 있습니다. 잠시만 기다려 주세요..."):
            results = run_scan(market_choice, scan_limit)
            st.session_state['scan_results'] = results
            st.session_state['current_market'] = market_choice
            
            # 자동 전송 로직
            config = load_config()
            if config.get("auto_send") and results:
                report_msg = format_stock_message(results, market_choice)
                success, msg = send_telegram_message(report_msg)
                if success:
                    st.info("📢 분석 결과가 텔레그램으로 자동 전송되었습니다.")
                else:
                    st.warning(f"⚠️ 자동 전송 실패: {msg}")

    if 'scan_results' in st.session_state and st.session_state['scan_results']:
        results = st.session_state['scan_results']
        current_market = st.session_state['current_market']
        df_res = pd.DataFrame(results).sort_values(by='score', ascending=False).reset_index(drop=True)
        
        st.markdown("---")
        
        # --- [NEW] 매매법 필터링 섹션 ---
        st.subheader("🎯 매매법별 필터링")
        
        # 각 매매법별 데이터 분류 로직
        def check_aurora(row):
            return row.get('aurora', {}).get('signal', False)
            
        def check_futureon(row):
            fo = row.get('futureon', {})
            return fo.get('isle') or fo.get('shintae') or fo.get('juns')

        strategies = {
            "전체": df_res,
            "🚀 급등 임박": df_res[df_res['signals'].str.contains("🚀 급등 전조")] if not df_res.empty else df_res,
            "🥣 주식단테": df_res[df_res['signals'].str.contains("밥그릇|256")] if not df_res.empty else df_res,
            "📦 고쨱짹": df_res[df_res['signals'].str.contains("고쨱짹")] if not df_res.empty else df_res,
            "🐜 홍인기": df_res[df_res['signals'].str.contains("홍인기|끼")] if not df_res.empty else df_res,
            "🚀 AP-김용재": df_res[df_res['signals'].str.contains("AP-김용재")] if not df_res.empty else df_res,
            "✨ 오로라": df_res[df_res.apply(check_aurora, axis=1)] if not df_res.empty else df_res,
            "🏆 퓨처온": df_res[df_res.apply(check_futureon, axis=1)] if not df_res.empty else df_res
        }
        
        # 매매법 선택 옵션 생성 (개수 포함)
        strategy_options = [f"{k} ({len(v)})" for k, v in strategies.items()]
        
        # 기본값 설정 (스캔 직후에는 '전체'가 선택되도록 함)
        default_index = 0
        
        selected_strategy_label = st.radio(
            "필터링할 매매법 선택", 
            strategy_options, 
            index=default_index,
            horizontal=True, 
            key=f"strategy_filter_{current_market}_{len(results)}" # 결과 개수가 바뀌면 초기화되도록 키 설정
        )
        selected_strategy_name = selected_strategy_label.split(" (")[0]
        df_filtered = strategies[selected_strategy_name].reset_index(drop=True)

        # --- [신규] 정밀 필터링 섹션 ---
        st.markdown("---")
        st.subheader("🔍 주가 및 등락률 필터링")
        
        # 시장별 적절한 주가 범위 설정
        if "한국" in current_market:
            p_max_limit = 1500000
            p_step = 1000
        elif "미국" in current_market:
            p_max_limit = 5000
            p_step = 10
        else: # 코인
            p_max_limit = 100000000
            p_step = 10000

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            price_range = st.slider(
                "주가 범위 선택", 
                0, p_max_limit, (0, p_max_limit), 
                step=p_step,
                key=f"price_filter_{current_market}"
            )
        with col_f2:
            change_range = st.slider(
                "당일 등락률 범위 (%)", 
                -30.0, 30.0, (-30.0, 30.0), 
                step=0.5,
                key=f"change_filter_{current_market}"
            )
            
        # 기존 필터링된 데이터에 추가 범위 필터 적용
        if not df_filtered.empty:
            if 'change_rate' not in df_filtered.columns:
                df_filtered['change_rate'] = 0.0
            if 'current_price' not in df_filtered.columns:
                df_filtered['current_price'] = 0.0
                
            df_filtered = df_filtered[
                (df_filtered['current_price'] >= price_range[0]) & 
                (df_filtered['current_price'] <= price_range[1]) &
                (df_filtered['change_rate'] >= change_range[0]) &
                (df_filtered['change_rate'] <= change_range[1])
            ].reset_index(drop=True)

        # --- [1] 급등 임박 (Surge Alarm) 카드 섹션 ---
        # 팁: 급등 임박 종목은 항상 보여주거나, 특정 필터에서만 보여줄 수 있음. 여기서는 '전체' 또는 '급등 임박' 선택 시 표시
        surge_stocks = [r for r in results if "🚀 급등 전조" in r['signals']]
        if surge_stocks and selected_strategy_name in ["전체", "🚀 급등 임박"]:
            st.subheader("🚀 급등 임박 (Surge Alarm)")
            st.info("거래량 폭증 및 변동성 수축으로 에너지 분출이 임박한 종목들입니다.")
            surge_cols = st.columns(min(len(surge_stocks), 4))
            for i, row in enumerate(surge_stocks[:4]):
                with surge_cols[i]:
                    # 전문가 뱃지 HTML 생성
                    expert_badges = ""
                    if row.get("experts", {}).get("dante"):
                        if "밥그릇" in row['signals']: expert_badges += '<span style="background-color: #9b59b6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">🥣 단테-밥그릇</span>'
                        if "256" in row['signals']: expert_badges += '<span style="background-color: #34495e; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">🎯 단테-256</span>'
                    if row.get("experts", {}).get("gozack"): expert_badges += '<span style="background-color: #e67e22; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">📦 쨱짹-박스권</span>'
                    if row.get("experts", {}).get("hongingi"): expert_badges += '<span style="background-color: #c0392b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">|🐜 홍인기-대장주</span>'
                    if row.get("experts", {}).get("ap_inv"): expert_badges += '<span style="background-color: #2980b9; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">🚀 AP-김용재</span>'
                    if row.get("aurora", {}).get("signal"): expert_badges += '<span style="background-color: #f1c40f; color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">✨ 오로라</span>'
                    if row.get("futureon", {}).get("isle"): expert_badges += '<span style="background-color: #27ae60; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">🏆 이슬-골드라인</span>'
                    if row.get("futureon", {}).get("shintae"): expert_badges += '<span style="background-color: #8e44ad; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">🏆 신태-수급밴드</span>'
                    if row.get("futureon", {}).get("juns"): expert_badges += '<span style="background-color: #e67e22; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; margin-right: 5px;">🏆 준S-3파동</span>'
                    
                    st.markdown(f"""
<div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 2px solid #ff4b4b; box-shadow: 0 0 10px rgba(255, 75, 75, 0.3);">
<h3 style="margin:0; color: #ff4b4b;">🚀 {row['Name']}</h3>
<p style="margin:0; font-size: 0.85em; color: #8b949e;">{row['symbol']}</p>
<h2 style="margin:10px 0; color: white;">{row['current_price']:,.0f}</h2>
<div style="background-color: #ff4b4b; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 0.8em; margin-bottom: 5px; display: inline-block;">
SCORE: {row['score']}
</div>
<div style="display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 5px;">
{expert_badges}
</div>
<p style="margin:5px 0; font-size: 0.8em; color: #d1d5da; line-height: 1.2;">📢 {row['signals'].split('🚀')[1] if '🚀' in row['signals'] else row['signals']}</p>
</div>
""", unsafe_allow_html=True)
            st.write("")

        # --- [2] 실시간 분석 결과 리스트 (Table) ---
        st.subheader(f"📋 {selected_strategy_name} 분석 결과 리스트")
        
        # UI 보관용 컨테이너 사용 (DOM 안정성 확보)
        table_container = st.container()
        
        with table_container:
            if df_filtered.empty:
                st.warning(f"'{selected_strategy_name}' 매매법에 해당하는 종목이 없습니다.")
                selection_event = None
            else:
                st.info(f"💡 **팁**: 아래 테이블에서 종목을 클릭하면 하단에 상세 차트와 전문가 매매법 분석 결과가 나타납니다. (총 {len(df_filtered)}개)")
                
                df_display = df_filtered[['action', 'action_desc', 'symbol', 'Name', 'score', 'current_price', 'change_rate', 'rsi', 'signals']]
                df_display.columns = ['액션', '상태', '코드', '종목명', '점수', '현재가', '등락률', 'RSI', '상세신호']
                
                # 스타일링이 on_select와 충돌하여 React DOM 에러(removeChild)를 유발할 수 있으므로, 스타일 대신 순수 df를 넘기고 고유 키를 할당합니다.
                selection_event = st.dataframe(
                    df_display,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    hide_index=True,
                    key=f"table_{current_market}_{selected_strategy_name}_{len(df_display)}"
                )

        # --- [3] 행 선택 시 상세 분석 섹션 (Expert Analysis 포함) ---
        if selection_event and hasattr(selection_event, 'selection') and selection_event.selection.rows:
            selected_idx = selection_event.selection.rows[0]
            if selected_idx < len(df_filtered):
                # df_filtered는 한글 컬럼명으로 되어 있을 수 있으므로 원본 키에 접근하도록 주의
                # 또는 df_filtered 생성 시 원본을 유지하고 display용만 따로 만들거나 함.
                # 현재 df_filtered는 원본 컬럼을 가지고 있으므로 iloc로 접근 가능
                selected_data = df_filtered.iloc[selected_idx]
                selected_symbol = selected_data['symbol']
                
                st.markdown(f"### 📈 {selected_data['Name']} ({selected_symbol}) 정밀 분석")
                
                # 전문가 기법 해당 여부 확인 섹션 (강조)
                st.markdown("#### 🧐 전문가 기법 및 수급 확인")
                exp_cols1 = st.columns(2)
                with exp_cols1[0]:
                    st.write("**🥣 주식단테 (밥그릇/2/5/6)**")
                    if "밥그릇" in selected_data['signals']: st.success("✅ **밥그릇 3번 자리 감지!** (하락 횡보 후 돌파)")
                    elif "256" in selected_data['signals']: st.info("✅ **256 스윙 타점!** (추세 안착)")
                    else: st.write("⚪ 조건 미달")
                
                with exp_cols1[1]:
                    st.write("**📦 고쨱짹 (박스돌파/거봉)**")
                    if "고쨱짹" in selected_data['signals']: st.success("✅ **박스권 돌파 + 수급 대폭발!**")
                    else: st.write("⚪ 조건 미달")
                
                exp_cols2 = st.columns(2)
                with exp_cols2[0]:
                    st.write("**🐜 대왕개미 홍인기 (대장주/끼/D+0)**")
                    if "홍인기" in selected_data['signals']: st.success("✅ **주도주/대장주 탄생의 신호!**")
                    elif "끼" in selected_data['signals']: st.info("✅ **강력한 '끼' 보유 종목!**")
                    else: st.write("⚪ 조건 미달")
                
                with exp_cols2[1]:
                    st.write("**🚀 AP투자연구소 김용재**")
                    if "AP-김용재" in selected_data['signals']: st.success("✅ **맥점 돌파 및 수급 집중!**")
                    else: st.write("⚪ 조건 미달")
            
                exp_cols3 = st.columns(2)
                with exp_cols3[0]:
                    st.write("**✨ 오로라 검색기 (낙폭과대)**")
                    if selected_data.get('aurora', {}).get('signal'): 
                        st.success("✅ **오로라 반등 시그널 포착!**")
                        for r in selected_data['aurora']['reasons']:
                            st.caption(f"• {r}")
                    else: st.write("⚪ 조건 미달")
                
                with exp_cols3[1]:
                    st.write("**🏆 퓨처온 멘토 군단 분석**")
                    if selected_data.get('futureon', {}).get('reasons'):
                        st.success("✅ **퓨처온 멘토 신호 포착!**")
                        for r in selected_data['futureon']['reasons']:
                            st.caption(f"• {r}")
                    else: st.write("⚪ 조건 미달")

                col_chart, col_side = st.columns([2, 1])
                with col_chart:
                    display_detailed_chart(selected_symbol, current_market)
                
                with col_side:
                    st.metric("현재가", f"{selected_data['current_price']:,.0f}")
                    st.metric("종합 점수", f"{selected_data['score']}점")
                    st.markdown("##### 📡 실시간 감지 신호")
                    for s in selected_data['signals'].split(','):
                        if s.strip(): st.write(f"- {s.strip()}")
                    
                    st.markdown("##### 💡 전문가 의견")
                    if selected_data['action'] == 'BUY': st.success(f"**{selected_data['action_desc']}**")
                    else: st.info(f"**{selected_data['action_desc']}**")
                    
                    if st.button("⭐ 포트폴리오에 추가", use_container_width=True):
                        p_data = load_portfolio()
                        m_key = 'KR' if "한국" in current_market else ('US' if "미국" in current_market else 'COIN')
                        if selected_symbol not in p_data[m_key]:
                            p_data[m_key].append(selected_symbol)
                            save_portfolio(p_data)
                            st.success("추가되었습니다!")
                            st.rerun()
                        else: st.warning("이미 등록된 종목입니다.")

        # --- 공유 및 하단 섹션 ---
        st.markdown("---")
        st.markdown(f"### 📤 필터링 결과 공유 ({len(df_filtered)}개 종목)")
        c1, c2, c3 = st.columns(3)
        
        # 필터링된 결과를 리스트로 변환
        filtered_results = df_filtered.to_dict('records')
        
        with c1:
            if st.button("⭐ 필터결과 포트폴리오 추가", use_container_width=True, help="현재 필터링된 모든 종목을 포트폴리오에 등록합니다."):
                if not filtered_results:
                    st.warning("추가할 종목이 없습니다.")
                else:
                    p_data = load_portfolio()
                    m_key = 'KR' if "한국" in current_market else ('US' if "미국" in current_market else 'COIN')
                    added_count = 0
                    for r in filtered_results:
                        s_code = r['symbol']
                        if s_code not in p_data[m_key]:
                            p_data[m_key].append(s_code)
                            added_count += 1
                    
                    if added_count > 0:
                        save_portfolio(p_data)
                        st.success(f"✅ 필터링된 종목 {added_count}개가 추가되었습니다!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("이미 모두 등록되어 있습니다.")

        with c2:
            if st.button("📱 필터결과 Telegram 전송", use_container_width=True):
                if not filtered_results:
                    st.warning("전송할 종목이 없습니다.")
                else:
                    report_msg = format_stock_message(filtered_results, f"{current_market} 필터링")
                    success, msg = send_telegram_message(report_msg)
                    if success: st.success("전송되었습니다!")
                    else: st.error(f"실패: {msg}")
        with c3:
            if filtered_results:
                report_text = format_stock_message(filtered_results, f"{current_market} 필터링").replace("*", "")
                st.code(report_text, language="text")
                st.caption("필터링된 리포트 텍스트입니다.")
            else:
                st.write("필터링된 결과가 없습니다.")

    else:
        if not run_button and ('scan_results' not in st.session_state):
            st.info("사이드바에서 시장을 선택하고 '스캔 시작' 버튼을 눌러주세요.")

with tab_portfolio:
    st.markdown("### 💼 나의 포트폴리오 관리")
    st.write("보유 중인 종목을 시장별로 관리하고 매도 타이밍을 실시간 모니터링합니다.")
    
    portfolio = load_portfolio()
    
    # 1. 모든 보유 종목 데이터 일괄 분석 (최상단 매도 알림용)
    all_owned = []
    for m, symbols in portfolio.items():
        for s in symbols:
            all_owned.append({'market': m, 'symbol': s})
            
    p_results = []
    if all_owned:
        with st.spinner("모든 보유 종목의 상태를 실시간 분석 중..."):
            for item in all_owned:
                res = scanner.analyze_stock(item['symbol'], item['market'])
                if res:
                    res['market'] = item['market']
                    p_results.append(res)
    
    # --- [A] 공통: 통합 매도 신호 요약 섹션 ---
    if p_results:
        df_all = pd.DataFrame(p_results)
        sell_stocks = df_all[df_all['action'] == "SELL"]
        
        st.markdown("### 📤 포트폴리오 공유 및 알림")
        cp1, cp2 = st.columns(2)
        
        with cp1:
            if st.button("📱 포트폴리오 현황 Telegram 전송", use_container_width=True):
                p_msg = format_portfolio_message(p_results, scanner)
                success, msg = send_telegram_message(p_msg)
                if success:
                    st.success("포트폴리오 현황이 전송되었습니다!")
                else:
                    st.error(f"전송 실패: {msg}")

        if not sell_stocks.empty:
            st.error(f"🚨 **긴급 매도 필요**: 총 {len(sell_stocks)}개의 종목에서 매도 신호가 감지되었습니다!")
            
            with cp2:
                if st.button("⚠️ 매도 신호만 텔레그램 전송", use_container_width=True):
                    sell_msg = "🚨 *[포트폴리오 매도 알림]*\n\n"
                    for _, s_row in sell_stocks.iterrows():
                        sell_msg += f"⚠️ *{s_row['symbol']}*\n   - {s_row['action_desc']}\n   - {s_row['signals']}\n\n"
                    
                    success, msg = send_telegram_message(sell_msg)
                    if success:
                        st.success("매도 신호가 전송되었습니다!")
                    else:
                        st.error(f"전송 실패: {msg}")

            s_cols = st.columns(min(len(sell_stocks), 3))
            for i, (_, row) in enumerate(sell_stocks.head(3).iterrows()):
                with s_cols[i]:
                    st.markdown(f"""
<div style="background-color: #721c24; padding: 10px; border-radius: 8px; border: 1px solid #f5c6cb; color: white;">
    <strong>⚠️ {row['symbol']} ({row['market']})</strong><br>
    {row['action_desc']}<br>
    <small style="font-size: 0.8em;">{row['signals']}</small>
</div>
""", unsafe_allow_html=True)
            st.write("")

    # --- [B] 시장별 서브 탭 구성 ---
    sub_tabs = st.tabs(["🇰🇷 한국 주식", "🇺🇸 미국 주식", "🪙 암호화폐"])
    market_keys = ["KR", "US", "COIN"]
    
    for i, tab in enumerate(sub_tabs):
        m_key = market_keys[i]
        with tab:
            st.write(f"#### {m_key} 포트폴리오")
            
            # 종목 추가 영역
            with st.expander("➕ 새 종목 수동 등록"):
                c1, c2 = st.columns([3, 1])
                new_s = c1.text_input(f"{m_key} 코드 입력", key=f"add_{m_key}").strip().upper()
                if c2.button("등록", key=f"btn_{m_key}"):
                    if new_s and new_s not in portfolio[m_key]:
                        portfolio[m_key].append(new_s)
                        save_portfolio(portfolio)
                        st.success(f"{new_s} 등록 완료!")
                        st.rerun()
            
            # 해당 시장 종목 표시 (분석 결과가 없더라도 리스트는 보여줌)
            owned_symbols = portfolio[m_key]
            if owned_symbols:
                # 분석 결과 맵핑
                m_results = [r for r in p_results if r['market'] == m_key]
                
                # 분석되지 않은 종목들도 리스트에 포함
                display_data = []
                for s in owned_symbols:
                    # 종목 이름 가져오기
                    s_name = scanner.get_symbol_name(s, m_key)
                    
                    # 분석 결과가 있는지 확인
                    res = next((r for r in m_results if r['symbol'] == s), None)
                    if res:
                        res['name'] = s_name # 이름 추가
                        display_data.append(res)
                    else:
                        # 분석 결과가 아직 없는 경우 기본 데이터 생성
                        display_data.append({
                            'action': 'WAIT',
                            'action_desc': '분석 대기 중...',
                            'symbol': s,
                            'name': s_name,
                            'score': 0,
                            'current_price': 0,
                            'rsi': 0,
                            'signals': '데이터를 불러오고 있습니다.',
                            'market': m_key
                        })
                
                df_m = pd.DataFrame(display_data)
                
                # 데이터 그리드 (다중 선택 활성화)
                st.write("**현재 현황** (아래 표에서 종목을 선택하여 복수 삭제가 가능합니다.)")
                display_cols = ['action', 'action_desc', 'name', 'symbol', 'score', 'current_price', 'rsi', 'signals']
                
                def color_action_v2(val):
                    if val == 'BUY': return 'background-color: #28a745; color: white'
                    if val == 'SELL': return 'background-color: #dc3545; color: white'
                    if val == 'WAIT': return 'background-color: #30363d; color: #8b949e'
                    return ''

                selection = st.dataframe(
                    df_m[display_cols].style.applymap(color_action_v2, subset=['action']),
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    hide_index=True,
                    key=f"ptr_table_{m_key}"
                )
                
                # [개선] 삭제 UI를 더 명확하게 표시
                st.markdown("---")
                st.markdown("##### 🗑️ 종목 삭제 관리")
                
                selected_indices = selection.selection.rows
                if not selected_indices:
                    st.info("💡 위 표에서 삭제할 종목의 **왼쪽 체크박스**를 선택하면 삭제 버튼이 활성화됩니다.")
                    # 비활성 버튼 표시 (사용자가 버튼의 존재를 알 수 있도록)
                    st.button("선택된 종목이 없습니다", disabled=True, use_container_width=True, key=f"disabled_del_{m_key}")
                else:
                    selected_symbols = [df_m.iloc[idx]['symbol'] for idx in selected_indices]
                    if st.button(f"🔥 선택한 {len(selected_symbols)}개 종목 포트폴리오에서 즉시 삭제", 
                                 key=f"del_multi_{m_key}", 
                                 type="primary", 
                                 use_container_width=True):
                        for sym in selected_symbols:
                            if sym in portfolio[m_key]:
                                portfolio[m_key].remove(sym)
                        save_portfolio(portfolio)
                        st.success(f"성공적으로 {len(selected_symbols)}개 종목을 삭제했습니다!")
                        time.sleep(1)
                        st.rerun()

                # --- [C] 행 선택 시 상세 분석 섹션 (Expert Analysis 포함) ---
                if selected_indices:
                    selected_idx = selected_indices[0]
                    if selected_idx < len(df_m):
                        selected_data = df_m.iloc[selected_idx]
                        selected_symbol = selected_data['symbol']
                        
                        st.markdown("---")
                        st.markdown(f"### 📈 {selected_data['name']} ({selected_symbol}) 정밀 분석")
                        
                        # 전문가 기법 해당 여부 확인 섹션 (강조)
                        st.markdown("#### 🧐 전문가 기법 및 수급 확인")
                        exp_cols1 = st.columns(2)
                        with exp_cols1[0]:
                            st.write("**🥣 주식단테 (밥그릇/2/5/6)**")
                            if "밥그릇" in str(selected_data['signals']): st.success("✅ **밥그릇 3번 자리 감지!** (하락 횡보 후 돌파)")
                            elif "256" in str(selected_data['signals']): st.info("✅ **256 스윙 타점!** (추세 안착)")
                            else: st.write("⚪ 조건 미달")
                        
                        with exp_cols1[1]:
                            st.write("**📦 고쨱짹 (박스돌파/거봉)**")
                            if "고쨱짹" in str(selected_data['signals']): st.success("✅ **박스권 돌파 + 수급 대폭발!**")
                            else: st.write("⚪ 조건 미달")
                        
                        exp_cols2 = st.columns(2)
                        with exp_cols2[0]:
                            st.write("**🐜 대왕개미 홍인기 (대장주/끼/D+0)**")
                            if "홍인기" in str(selected_data['signals']): st.success("✅ **주도주/대장주 탄생의 신호!**")
                            elif "끼" in str(selected_data['signals']): st.info("✅ **강력한 '끼' 보유 종목!**")
                            else: st.write("⚪ 조건 미달")
                        
                        with exp_cols2[1]:
                            st.write("**🚀 AP투자연구소 김용재**")
                            if "AP-김용재" in str(selected_data['signals']): st.success("✅ **맥점 돌파 및 수급 집중!**")
                            else: st.write("⚪ 조건 미달")
                    
                        exp_cols3 = st.columns(2)
                        with exp_cols3[0]:
                            st.write("**✨ 오로라 검색기 (낙폭과대)**")
                            if isinstance(selected_data.get('aurora'), dict) and selected_data.get('aurora', {}).get('signal'): 
                                st.success("✅ **오로라 반등 시그널 포착!**")
                                for r in selected_data['aurora']['reasons']:
                                    st.caption(f"• {r}")
                            else: st.write("⚪ 조건 미달")
                        
                        with exp_cols3[1]:
                            st.write("**🏆 퓨처온 멘토 군단 분석**")
                            if isinstance(selected_data.get('futureon'), dict) and selected_data.get('futureon', {}).get('reasons'):
                                st.success("✅ **퓨처온 멘토 신호 포착!**")
                                for r in selected_data['futureon']['reasons']:
                                    st.caption(f"• {r}")
                            else: st.write("⚪ 조건 미달")

                        col_chart, col_side = st.columns([2, 1])
                        with col_chart:
                            display_detailed_chart(selected_symbol, m_key)
                        
                        with col_side:
                            st.metric("현재가", f"{selected_data['current_price']:,.0f}")
                            st.metric("종합 점수", f"{selected_data['score']}점")
                            st.markdown("##### 📡 실시간 감지 신호")
                            for s in str(selected_data['signals']).split(','):
                                if s.strip(): st.write(f"- {s.strip()}")
                            
                            st.markdown("##### 💡 전문가 의견")
                            if selected_data['action'] == 'BUY': st.success(f"**{selected_data['action_desc']}**")
                            else: st.info(f"**{selected_data['action_desc']}**")
                
                # [추가] 테이블 선택이 어려운 경우를 위한 드롭다운 삭제 (백업 방식)
                with st.expander("⚠️ 표 선택이 안 되시나요? (이름으로 삭제)"):
                    c_sel, c_del = st.columns([3, 1])
                    fallback_s = c_sel.selectbox("삭제할 개별 종목 선택", owned_symbols, key=f"fallback_sel_{m_key}")
                    if c_del.button("개별 삭제", key=f"fallback_del_{m_key}"):
                        portfolio[m_key].remove(fallback_s)
                        save_portfolio(portfolio)
                        st.rerun()
            else:
                st.info(f"등록된 {m_key} 보유 종목이 없습니다.")
    
# Footer
st.divider()
st.caption(f"Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: FinanceDataReader, yfinance")

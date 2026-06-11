import streamlit as st
import pandas as pd
import stock_scanner
import importlib
importlib.reload(stock_scanner)
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
        
        /* 컬럼(st.columns) 수직 정렬 강제 */
        [data-testid="column"] {
            width: 100% !important;
            flex-basis: 100% !important;
        }
        
        /* 탭 바 패딩 및 글씨 크기 조정 */
        [data-testid="stTabBar"] button {
            padding: 6px 10px !important;
            font-size: 0.8rem !important;
        }
        
        /* 모바일 st.metric 폰트 및 패딩 압축 */
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
        }
        [data-testid="stMetric"] {
            padding: 8px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- Configuration Management ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    default_cfg = {"telegram_token": "", "telegram_chat_id": "", "auto_send": False, "custom_url": "", "app_password": "admin1234"}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                for k, v in default_cfg.items():
                    if k not in cfg: cfg[k] = v
                return cfg
        except:
            return default_cfg
    return default_cfg

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

def render_donkkang_scenario(s_data):
    dk = s_data.get('donkkang')
    if not dk: return ""
    
    html = "<div style='margin-top:15px; padding:12px; background-color:rgba(255, 75, 75, 0.05); border:1px solid #ff4b4b; border-radius:8px;'>"
    html += "<h5 style='color:#ff4b4b; margin:0 0 10px 0;'>📊 데이매매 돈깡 매매법 시나리오</h5>"
    
    if dk.get('suitable'):
        br = dk.get('breakout', {})
        su = dk.get('support', {})
        html += f"""
        <div style='font-size:0.85em; color:#e2e8f0;'>
            <p style='margin:2px 0;'><b>🔥 시나리오 A (돌파)</b>: <span style='color:#f1c40f;'>{int(br.get('buy',0)):,}원</span> 돌파 시 추격</p>
            <p style='margin:2px 0; padding-left:15px; color:#8b949e;'>↳ 칼손절: {int(br.get('stop',0)):,}원 (-3%) / 분할익절: {int(br.get('target',0)):,}원 (+5%)</p>
            <p style='margin:8px 0 2px 0;'><b>🛡️ 시나리오 B (눌림)</b>: <span style='color:#58a6ff;'>{int(su.get('buy',0)):,}원</span> 지지 시 매수</p>
            <p style='margin:2px 0; padding-left:15px; color:#8b949e;'>↳ 칼손절: {int(su.get('stop',0)):,}원 (-3%) / 분할익절: {int(su.get('target',0)):,}원 (+5%)</p>
        </div>
        """
    else:
        html += "<p style='margin:0; font-size:0.85em; color:#8b949e;'>⚠️ 현재 상승 모멘텀(거래대금/변동성)이 부족하여 <b>돈깡 데이매매(단타)에는 부적합</b>한 종목입니다.</p>"
    html += "</div>"
    return html

def render_general_scenario(s_data):
    gs = s_data.get('general_scenario')
    if not gs: return ""
    
    buy = int(gs.get('buy', 0))
    stop = int(gs.get('stop', 0))
    target = int(gs.get('target', 0))
    
    html = f"""
    <div style='margin-top:15px; padding:12px; background-color:rgba(88, 166, 255, 0.05); border:1px solid #58a6ff; border-radius:8px;'>
        <h5 style='color:#58a6ff; margin:0 0 10px 0;'>📌 기본 스윙 매매 가이드 (1~2주 보유)</h5>
        <div style='font-size:0.85em; color:#e2e8f0;'>
            <p style='margin:2px 0;'><b>🎯 진입 (현재가 부근)</b>: <span style='color:#e67e22;'>{buy:,}원</span></p>
            <p style='margin:2px 0;'><b>📈 목표가 (익절)</b>: <span style='color:#27ae60;'>{target:,}원</span> (최근 20일 고점 돌파 목표)</p>
            <p style='margin:2px 0;'><b>🛡️ 방어선 (손절)</b>: <span style='color:#c0392b;'>{stop:,}원</span> (최근 10일 저점 이탈 주의)</p>
        </div>
    </div>
    """
    return html

def render_smc_scenario(s_data):
    smc = s_data.get('smc')
    if not smc: return ""
    
    buy = int(smc.get('buy') or smc.get('entry', 0))
    stop = int(smc.get('stop', 0))
    target = int(smc.get('target', 0))
    smc_type = smc.get('type', 'SMC')
    
    type_name = "상승 FVG 되돌림 지지 타점" if smc_type == "FVG" else "SMC-Turtle Soup (가짜 이탈 후 반등)"
    bg_color = "rgba(155, 89, 182, 0.05)"
    border_color = "#9b59b6"
    title_color = "#bc8cff"
    
    html = f"""
    <div style='margin-top:15px; padding:12px; background-color:{bg_color}; border:1px solid {border_color}; border-radius:8px;'>
        <h5 style='color:{title_color}; margin:0 0 10px 0;'>📊 ICT/SMC 단기 스윙 타점 안내 ({type_name})</h5>
        <div style='font-size:0.85em; color:#e2e8f0;'>
            <p style='margin:2px 0;'><b>🎯 스윙 진입가 (현재가 부근)</b>: <span style='color:#f1c40f;'>{buy:,}원</span></p>
            <p style='margin:2px 0;'><b>📈 목표가 (1차 익절)</b>: <span style='color:#2cc571;'>{target:,}원</span></p>
            <p style='margin:2px 0;'><b>🛡️ 칼손절가 (하방 이탈)</b>: <span style='color:#e74c3c;'>{stop:,}원</span></p>
        </div>
    </div>
    """
    return html

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

def display_detailed_chart(symbol, market, height=700):
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

    fig.update_layout(height=height, template="plotly_dark", showlegend=True, 
                      xaxis_rangeslider_visible=False, margin=dict(l=5, r=5, t=30, b=5),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': False,
        'displayModeBar': False,
        'modeBarButtonsToRemove': ['zoom', 'pan', 'select', 'lasso2d', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale'],
        'staticPlot': False
    })

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
config = load_config()

# --- Authentication (비밀번호 잠금) ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h2 style='text-align: center; color: #ff4b4b; margin-top: 50px;'>🔒 안티그래비티 대시보드 로그인</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>허가된 사용자만 접근할 수 있는 프라이빗 시스템입니다.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd_input = st.text_input("초대코드 (비밀번호) 입력:", type="password")
        if st.button("접속하기", use_container_width=True, type="primary"):
            if pwd_input == config.get("app_password", "admin1234"):
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    st.stop() # 인증 전에는 아래 로직 실행 안 함

st.title("🚀 Premium Stock Selection & Monitoring")

# @st.cache_resource # 캐싱된 이전 버전의 StockScanner 객체로 인해 find_symbol_by_name 속성 오류가 발생할 수 있습니다.
def get_scanner():
    return StockScanner()

scanner = get_scanner()

# @st.cache_data(ttl=3600)  # 코드 변경 후 데이터 호환성을 위해 일시적으로 캐싱 비활성화
def run_scan(market_choice, scan_limit):
    if market_choice == "한국 (KRX)":
        symbols_df = scanner.get_krx_symbols()
        if 'Amount' in symbols_df.columns:
            symbols_df['Amount'] = pd.to_numeric(symbols_df['Amount'], errors='coerce').fillna(0)
            symbols_df = symbols_df.sort_values(by='Amount', ascending=False)
        elif 'Marcap' in symbols_df.columns:
            symbols_df['Marcap'] = pd.to_numeric(symbols_df['Marcap'], errors='coerce').fillna(0)
            symbols_df = symbols_df.sort_values(by='Marcap', ascending=False)
        symbols_df = symbols_df.head(scan_limit)
        market_code = 'KR'
        symbol_col = 'Code' if 'Code' in symbols_df.columns else 'Symbol'
    elif market_choice == "미국 (US)":
        symbols_df = scanner.get_us_symbols()
        major_us = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AVGO', 'LLY', 'JPM', 'UNH', 'XOM', 'V', 'PG', 'MA']
        if 'Symbol' in symbols_df.columns:
            symbols_df['is_major'] = symbols_df['Symbol'].apply(lambda x: major_us.index(x) if x in major_us else 999)
            symbols_df = symbols_df.sort_values(by='is_major').drop(columns=['is_major'])
        symbols_df = symbols_df.head(scan_limit)
        market_code = 'US'
        symbol_col = 'Symbol'
    else: # 암호화폐 (Upbit)
        symbols_df = scanner.get_coin_symbols()
        major_coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-ADA', 'KRW-DOGE', 'KRW-SHIB', 'KRW-DOT', 'KRW-AVAX', 'KRW-LINK', 'KRW-TRX', 'KRW-ETC', 'KRW-APT', 'KRW-SUI']
        if 'Symbol' in symbols_df.columns:
            symbols_df['is_major'] = symbols_df['Symbol'].apply(lambda x: major_coins.index(x) if x in major_coins else 999)
            symbols_df = symbols_df.sort_values(by='is_major').drop(columns=['is_major'])
        symbols_df = symbols_df.head(scan_limit)
        market_code = 'COIN'
        symbol_col = 'Symbol'

    results = []
    import concurrent.futures

    def fetch_and_analyze(row):
        symbol = row[symbol_col]
        name = row['Name']
        if market_code == 'COIN':
            time.sleep(0.1) # Upbit API Rate limit 방지
        analysis = scanner.analyze_stock(symbol, market_code)
        if analysis and analysis['score'] >= 40: # 임계값 소폭 완화
            analysis['Name'] = name
            return analysis
        return None

    # 병렬 처리를 통해 스캔 속도를 향상시킵니다. (코인은 rate limit을 위해 워커 수 제한)
    workers = 3 if market_code == 'COIN' else 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_and_analyze, row) for _, row in symbols_df.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as e:
                pass

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
    is_mobile = st.toggle("📱 모바일 최적화 모드 (Compact)", value=False, key="mobile_mode")
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
    with st.expander("⚙️ 고급 알림 및 시스템 설정", expanded=False):
        st.subheader("📢 알림 설정")
        config = load_config()
        tg_token = st.text_input("Telegram Bot Token", value=config.get("telegram_token", ""), type="password")
        tg_chat_id = st.text_input("Telegram Chat ID", value=config.get("telegram_chat_id", ""))
        auto_send = st.checkbox("🔥 스캔 완료 시 자동 전송", value=config.get("auto_send", False))
        st.markdown("---")
        st.subheader("🌐 외부 접속 환경 설정")
        custom_url_input = st.text_input("커스텀 URL (선택, ngrok 등)", value=config.get("custom_url", ""), help="외부망에서 접속할 때 할당받은 주소(예: https://1234.ngrok.io)를 입력하면 해당 주소로 QR코드가 생성됩니다. 비워두면 현재 PC의 내부망 IP로 자동 생성됩니다.")
        st.markdown("---")
        st.subheader("🔒 보안 설정")
        app_pwd_input = st.text_input("대시보드 접속 비밀번호", value=config.get("app_password", "admin1234"), type="password", help="앱에 접속할 때 필요한 비밀번호입니다. 기본값은 admin1234 입니다.")
        
        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            if st.button("💾 설정 저장", use_container_width=True):
                config["telegram_token"] = tg_token
                config["telegram_chat_id"] = tg_chat_id
                config["auto_send"] = auto_send
                config["custom_url"] = custom_url_input
                config["app_password"] = app_pwd_input
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

# --- [주도주 쉐도잉 유틸리티 함수 정의] ---
def load_shadowing_data():
    import json
    import os
    path = "shadowing_dictionary.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            pass
    return {"dictionary": [], "records": []}

def save_shadowing_data(data):
    import json
    path = "shadowing_dictionary.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"데이터 저장 실패: {e}")
        return False

def sync_realtime_shadowing_data(scanner=None):
    import datetime
    import random
    import time
    import FinanceDataReader as fdr
    import pandas as pd
    from utils.news_fetcher import fetch_latest_news_reason
    import os
    
    try:
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 1. KRX 전체 종목 목록 로드
        if scanner is None:
            from stock_scanner import StockScanner
            scanner = StockScanner()
        
        df_krx = scanner.get_krx_symbols()
        if df_krx is not None and 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
            df_krx['Code'] = df_krx['Symbol']
            
        # 2. KRX-DESC 로드해서 업종(Sector, Industry) 병합
        df_desc = None
        try:
            df_desc = fdr.StockListing('KRX-DESC')
            if df_desc is not None and not df_desc.empty:
                # Save cache
                try:
                    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "krx_desc_cache.json")
                    df_desc[['Code', 'Sector', 'Industry']].to_json(cache_path, orient='records', force_ascii=False, indent=2)
                except Exception as cache_err:
                    pass
        except Exception as e:
            # Try to load from local cache
            try:
                cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "krx_desc_cache.json")
                if os.path.exists(cache_path):
                    df_desc = pd.read_json(cache_path, encoding='utf-8')
                    if df_desc is not None and not df_desc.empty:
                        df_desc['Code'] = df_desc['Code'].astype(str).str.zfill(6)
            except Exception as cache_load_err:
                df_desc = None

        if df_desc is not None and not df_desc.empty:
            df_desc = df_desc[['Code', 'Sector', 'Industry']]
            df_merged = pd.merge(df_krx, df_desc, on='Code', how='left')
        else:
            df_merged = df_krx.copy()
            df_merged['Sector'] = '테마미분류'
            df_merged['Industry'] = '테마미분류'
            
        # 3. 데이터 타입 변환 및 결측치 처리
        df_merged['ChagesRatio'] = pd.to_numeric(df_merged['ChagesRatio'], errors='coerce').fillna(0.0)
        df_merged['Amount'] = pd.to_numeric(df_merged['Amount'], errors='coerce').fillna(0)
        df_merged['Close'] = pd.to_numeric(df_merged['Close'], errors='coerce').fillna(0)
        
        # 4. 4대 원칙 필터 조건: 등락률 >= 15.0% AND 거래대금 >= 500억 (50,000,000,000원)
        df_filtered = df_merged[(df_merged['ChagesRatio'] >= 15.0) & (df_merged['Amount'] >= 50000000000)]
        
        detected_stocks = []
        
        # 5. 선별된 종목들에 대해 뉴스 검색 및 상세 분석
        for _, row in df_filtered.iterrows():
            symbol = row.get('Code')
            name = row.get('Name')
            if not symbol or not name:
                continue
                
            close_val = int(row.get('Close', 0))
            change_rate = float(row.get('ChagesRatio', 0.0))
            amount_val_krw = float(row.get('Amount', 0))
            amount_hundred_million = round(amount_val_krw / 100000000.0, 2)
            
            # 업종명(키워드) 예외 처리
            sector_name = row.get('Industry')
            if pd.isna(sector_name) or not str(sector_name).strip():
                sector_name = row.get('Sector')
            if pd.isna(sector_name) or not str(sector_name).strip():
                sector_name = "테마미분류"
            sector_name = str(sector_name).strip()
            
            # 상승 사유 추출 (실시간 뉴스 헤드라인 검색)
            reason_str = fetch_latest_news_reason(name)
            
            detected_stocks.append({
                "name": name,
                "code": symbol,
                "rate": change_rate,
                "amount": amount_hundred_million,
                "close": close_val,
                "industry": sector_name,
                "reason": reason_str
            })
            
        if not detected_stocks:
            return False, "오늘 조건에 만족하는 실시간 급등주/주도주가 선별되지 않았습니다."
            
        shadow_data = load_shadowing_data()
        
        # 6. 저장용 요약 정보 빌드
        stock_names = [s["name"] for s in detected_stocks]
        reasons_list = [f"{s['name']}: {s['reason']}" for s in detected_stocks]
        
        new_stocks_str = ", ".join(stock_names)
        new_reasons_str = " | ".join(reasons_list)
        new_keyword = "실시간수급주"
        
        avg_rate = round(sum(s["rate"] for s in detected_stocks) / len(detected_stocks), 2)
        total_amount = int(sum(s["amount"] for s in detected_stocks))
        
        # 7. records 업데이트 (details 포함)
        record_idx = -1
        for idx, r in enumerate(shadow_data.get("records", [])):
            if r.get("date") == today_str:
                record_idx = idx
                break
                
        record_payload = {
            "date": today_str,
            "stocks": new_stocks_str,
            "reason": new_reasons_str,
            "keyword": new_keyword,
            "average_rate": avg_rate,
            "cumulative_amount": total_amount,
            "details": detected_stocks
        }
        
        if record_idx != -1:
            shadow_data["records"][record_idx] = record_payload
        else:
            shadow_data["records"].append(record_payload)
            
        # 8. dictionary (테마 백과사전) 업데이트
        industry_groups = {}
        for s in detected_stocks:
            ind = s["industry"]
            if ind not in industry_groups:
                industry_groups[ind] = []
            industry_groups[ind].append(s)
            
        for ind_name, stocks_in_ind in industry_groups.items():
            stock_count = len(stocks_in_ind)
            theme_tag = "[주도테마]" if stock_count >= 3 else "[개별이슈]"
            display_theme_name = f"{theme_tag} {ind_name}"

            ind_stocks_str = ", ".join([s["name"] for s in stocks_in_ind])
            ind_reasons_str = " | ".join([f"{s['name']}: {s['reason']}" for s in stocks_in_ind])
            ind_avg_rate = round(sum(s["rate"] for s in stocks_in_ind) / stock_count, 2)
            ind_total_amount = int(sum(s["amount"] for s in stocks_in_ind))
            
            dict_idx = -1
            for idx, entry in enumerate(shadow_data.get("dictionary", [])):
                existing_theme = entry.get("theme", "")
                if ind_name in existing_theme:
                    dict_idx = idx
                    break
                    
            if dict_idx != -1:
                existing_stocks = [s.strip() for s in shadow_data["dictionary"][dict_idx]["stocks"].split(",") if s.strip()]
                for s in stocks_in_ind:
                    if s["name"] not in existing_stocks:
                        existing_stocks.append(s["name"])
                shadow_data["dictionary"][dict_idx]["theme"] = display_theme_name
                shadow_data["dictionary"][dict_idx]["stocks"] = ", ".join(existing_stocks)
                shadow_data["dictionary"][dict_idx]["reason"] = f"({today_str} 업데이트) " + ind_reasons_str
                shadow_data["dictionary"][dict_idx]["last_updated"] = today_str
                shadow_data["dictionary"][dict_idx]["average_rate"] = ind_avg_rate
                shadow_data["dictionary"][dict_idx]["cumulative_amount"] = ind_total_amount
            else:
                new_id = f"theme_auto_{int(time.time())}_{random.randint(100, 999)}"
                shadow_data["dictionary"].append({
                    "id": new_id,
                    "theme": display_theme_name,
                    "keyword": ind_name,
                    "stocks": ind_stocks_str,
                    "reason": f"({today_str} 신규 등록) " + ind_reasons_str,
                    "last_updated": today_str,
                    "average_rate": ind_avg_rate,
                    "cumulative_amount": ind_total_amount
                })
                
        if save_shadowing_data(shadow_data):
            return True, f"오늘 자 ({today_str}) 실시간 주도주 {len(detected_stocks)}개 종목 분석 및 테마 백과사전 동기화가 성공적으로 완료되었습니다!"
        else:
            return False, "데이터베이스 저장에 실패했습니다."
            
    except Exception as e:
        return False, f"동기화 중 에러가 발생했습니다: {str(e)}"

# 메인 탭 구성
tab_scan, tab_portfolio, tab_dict = st.tabs(["🔍 종목 스캔", "💼 나의 포트폴리오", "📚 주도주 백과사전 & 쉐도잉 캘린더"])

with tab_scan:
    st.markdown("### 🔍 시장 종목 스캐너")
    
    # [신규] 개별 종목 직접 검색 섹션
    with st.form(key="direct_search_form", clear_on_submit=False):
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_input = st.text_input("🔍 종목명 또는 코드 검색 (예: 삼성전자, AAPL, 비트코인)", key="direct_search_input").strip()
        with search_col2:
            st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
            submit_search = st.form_submit_button("🚀 즉시 분석", use_container_width=True)
            
        if submit_search:
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
            
            # --- 일반 스윙 매매 가이드 렌더링 ---
            st.markdown(render_general_scenario(s_data), unsafe_allow_html=True)
            
            # --- 돈깡 데이매매법 시나리오 렌더링 ---
            st.markdown(render_donkkang_scenario(s_data), unsafe_allow_html=True)
            
            # --- SMC/ICT 단기 스윙 시나리오 렌더링 ---
            st.markdown(render_smc_scenario(s_data), unsafe_allow_html=True)
            st.write("")
            
            s_col1, s_col2 = st.columns([2, 1])
            with s_col1:
                display_detailed_chart(s_data['symbol'], s_data['market_type'], height=400 if st.session_state.get('mobile_mode', False) else 700)
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
            
        def check_donkkang(row):
            dk = row.get('donkkang')
            if isinstance(dk, dict):
                return dk.get('suitable', False)
            return False

        def check_smc(row):
            return bool(row.get('smc'))

        strategies = {
            "전체": df_res,
            "🚀 급등 임박": df_res[df_res['signals'].str.contains("🚀 급등 전조")] if not df_res.empty else df_res,
            "📊 돈깡 데이매매": df_res[df_res.apply(check_donkkang, axis=1)] if not df_res.empty else df_res,
            "🥣 주식단테": df_res[df_res['signals'].str.contains("밥그릇|256")] if not df_res.empty else df_res,
            "📦 고쨱짹": df_res[df_res['signals'].str.contains("고쨱짹")] if not df_res.empty else df_res,
            "🐜 홍인기": df_res[df_res['signals'].str.contains("홍인기|끼")] if not df_res.empty else df_res,
            "🚀 AP-김용재": df_res[df_res['signals'].str.contains("AP-김용재")] if not df_res.empty else df_res,
            "✨ 오로라": df_res[df_res.apply(check_aurora, axis=1)] if not df_res.empty else df_res,
            "🏆 퓨처온": df_res[df_res.apply(check_futureon, axis=1)] if not df_res.empty else df_res,
            "💎 SMC/ICT": df_res[df_res.apply(check_smc, axis=1)] if not df_res.empty else df_res
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
                
                if st.session_state.get('mobile_mode', False):
                    options_list = []
                    for idx, row in df_filtered.iterrows():
                        action_icon = '🟢' if row['action'] == 'BUY' else ('🔴' if row['action'] == 'SELL' else '⚫')
                        options_list.append(f"{action_icon} {row['Name']} ({row['symbol']}) | 등락률: {row['change_rate']:.1f}% | 점수: {row['score']}점")
                    
                    sb_key = f"sb_{current_market}_{selected_strategy_name}_{len(df_filtered)}"
                    selected_opt = st.selectbox("📱 분석할 종목 선택", options_list, key=sb_key)
                    
                    if selected_opt:
                        selected_idx = options_list.index(selected_opt)
                        class FakeSelectionEvent:
                            class FakeSelection:
                                def __init__(self, idx):
                                    self.rows = [idx]
                            def __init__(self, idx):
                                self.selection = self.FakeSelection(idx)
                        selection_event = FakeSelectionEvent(selected_idx)
                    else:
                        selection_event = None
                else:
                    df_display = df_filtered[['action', 'action_desc', 'symbol', 'Name', 'score', 'current_price', 'change_rate', 'rsi', 'signals']].copy()
                    df_display['action'] = df_display['action'].map({'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'WAIT': '⚫ WAIT'}).fillna(df_display['action'])
                    df_display.columns = ['액션', '상태', '코드', '종목명', '점수', '현재가', '등락률', 'RSI', '상세신호']
                    
                    selection_event = st.dataframe(
                        df_display,
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="single-row",
                        hide_index=True,
                        key=f"table_{current_market}_{selected_strategy_name}_{len(df_display)}"
                    )

                # 단일 추가 버튼
                if selection_event and hasattr(selection_event, 'selection') and selection_event.selection.rows:
                    selected_rows = selection_event.selection.rows
                    if len(selected_rows) > 0:
                        if st.button("⭐ 선택한 종목 포트폴리오에 추가", use_container_width=True, type="primary"):
                            p_data = load_portfolio()
                            m_key = 'KR' if "한국" in current_market else ('US' if "미국" in current_market else 'COIN')
                            added_count = 0
                            for r_idx in selected_rows:
                                if r_idx < len(df_filtered):
                                    sym = str(df_filtered.iloc[r_idx]['symbol'])
                                    if sym not in p_data[m_key]:
                                        p_data[m_key].append(sym)
                                        added_count += 1
                            if added_count > 0:
                                save_portfolio(p_data)
                                st.success(f"{added_count}개 종목이 포트폴리오에 추가되었습니다!")
                            else:
                                st.info("이미 포트폴리오에 모두 등록되어 있는 종목들입니다.")

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
                
                exp_cols4 = st.columns(2)
                with exp_cols4[0]:
                    st.write("**💎 SMC / ICT 기법 (Mensa)**")
                    if selected_data.get('smc'):
                        st.success(f"✅ **SMC 신호 감지!**")
                        st.caption(f"• {selected_data['smc'].get('type')} 패턴 확인")
                    else: st.write("⚪ 조건 미달")

                # --- 일반 스윙 매매 가이드 렌더링 ---
                st.markdown(render_general_scenario(selected_data), unsafe_allow_html=True)

                # --- 돈깡 데이매매법 시나리오 렌더링 ---
                st.markdown(render_donkkang_scenario(selected_data), unsafe_allow_html=True)
                
                # --- SMC/ICT 단기 스윙 시나리오 렌더링 ---
                st.markdown(render_smc_scenario(selected_data), unsafe_allow_html=True)
                st.write("")

                col_chart, col_side = st.columns([2, 1])
                with col_chart:
                    display_detailed_chart(selected_symbol, current_market, height=400 if st.session_state.get('mobile_mode', False) else 700)
                
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
        with st.expander(f"📤 필터링 결과 공유 및 전송 내역 ({len(df_filtered)}개 종목)", expanded=False):
            c1, c2 = st.columns(2)
            
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
                        
            st.markdown("---")
            if filtered_results:
                report_text = format_stock_message(filtered_results, f"{current_market} 필터링").replace("*", "")
                st.code(report_text, language="text")
                st.caption("필터링된 리포트 텍스트입니다. 텔레그램 전송 시 위 내용으로 발송됩니다.")
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
                if st.session_state.get('mobile_mode', False):
                    options_list = []
                    for idx, row in df_m.iterrows():
                        action_icon = '🟢' if row['action'] == 'BUY' else ('🔴' if row['action'] == 'SELL' else '⚫')
                        options_list.append(f"{action_icon} {row['name']} ({row['symbol']}) | RSI: {row['rsi']:.1f}")
                    
                    ms_key = f"ms_ptr_{m_key}_{len(df_m)}"
                    selected_opts = st.multiselect("📱 관리할 종목 선택", options_list, key=ms_key)
                    
                    selected_idx = [options_list.index(opt) for opt in selected_opts]
                    class FakeSelectionEvent:
                        class FakeSelection:
                            def __init__(self, idxs):
                                self.rows = idxs
                        def __init__(self, idxs):
                            self.selection = self.FakeSelection(idxs)
                    selection = FakeSelectionEvent(selected_idx)
                else:
                    display_cols = ['action', 'action_desc', 'name', 'symbol', 'score', 'current_price', 'rsi', 'signals']
                    df_m_display = df_m[display_cols].copy()
                    if not df_m_display.empty and 'action' in df_m_display.columns:
                        df_m_display['action'] = df_m_display['action'].map({'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'WAIT': '⚫ WAIT'}).fillna(df_m_display['action'])
                    
                    selection = st.dataframe(
                        df_m_display,
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="multi-row",
                        hide_index=True,
                        key=f"ptr_table_{m_key}_{len(df_m)}"
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

                        with col_chart:
                            display_detailed_chart(selected_symbol, m_key, height=400 if st.session_state.get('mobile_mode', False) else 700)
                        
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
    

with tab_dict:
    import calendar
    import datetime
    
    st.markdown("### 📚 주도주·테마 백과사전 & 주식 쉐도잉")
    st.caption("유튜브 영상(RhMRtXb_95E)에 수록된 '주식 쉐도잉' 및 '나만의 테마/종목 DB 훈련'을 보조하는 디지털 도구입니다.")
    
    # 1. 데이터 로드 및 마이그레이션
    shadow_data = load_shadowing_data()
    
    # 세션 상태 초기화
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = datetime.datetime.now().year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = datetime.datetime.now().month
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
    # 3단계 서브 네비게이션
    step_options = [
        "Step 01: 급등주 & 거래대금 쉐도잉 (당일 주도주 분석)",
        "Step 02: 일일 키워드 캘린더 (테마 요약 테이블)",
        "Step 03: 월간 키워드 캘린더 (5일 평일 달력)"
    ]
    
    # 세션 기반으로 기본 선택값 연동
    if "shadow_step_choice" not in st.session_state:
        st.session_state.shadow_step_choice = step_options[0] # 기본값: Step 01 (당일 주도주 분석)
        
    # step_choice 렌더링
    shadow_step = st.radio(
        "주식 쉐도잉 프로세스 단계 선택",
        step_options,
        index=step_options.index(st.session_state.shadow_step_choice),
        horizontal=True,
        key="shadow_step_radio"
    )
    
    # 라디오 선택값에 따라 세션 상태 갱신
    if st.session_state.shadow_step_choice != shadow_step:
        st.session_state.shadow_step_choice = shadow_step
        st.rerun()

    # 날짜별 데이터 그룹화 맵 구축
    day_data = {}
    
    # 1) 테마 백과사전 맵핑 (최종 업데이트일 기준)
    for entry in shadow_data.get("dictionary", []):
        dt = entry.get("last_updated")
        if dt:
            if dt not in day_data:
                day_data[dt] = {"themes": [], "records": []}
            day_data[dt]["themes"].append(entry)
            
    # 2) 쉐도잉 일지 맵핑 (일지 기록일 기준)
    for record in shadow_data.get("records", []):
        dt = record.get("date")
        if dt:
            if dt not in day_data:
                day_data[dt] = {"themes": [], "records": []}
            day_data[dt]["records"].append(record)

    # --- [Step 01: 급등주 & 거래대금 쉐도잉 (당일 주도주 분석)] ---
    if st.session_state.shadow_step_choice == step_options[0]:
        st.markdown(f"#### ⚡ Step 01: 급등주 & 거래대금 쉐도잉")
        st.caption("선택한 날짜의 당일 주도주 상세 테이블입니다. 엑셀처럼 상승이유와 키워드를 편집할 수 있습니다.")
        
        # 날짜 선택기
        selected_date = st.date_input("조회 및 분석 날짜 선택", value=datetime.datetime.strptime(st.session_state.selected_date, "%Y-%m-%d")).strftime("%Y-%m-%d")
        if selected_date != st.session_state.selected_date:
            st.session_state.selected_date = selected_date
            st.rerun()
            
        # 해당 날짜의 record와 theme가 데이터베이스에 있는지 확인
        date_records = day_data.get(selected_date, {}).get("records", [])
        
        # 테이블 데이터 빌드용 리스트
        table_rows = []
        
        if date_records:
            rec = date_records[0]
            details = rec.get("details", [])
            
            if details:
                for idx, d in enumerate(details):
                    table_rows.append({
                        "번호": idx + 1,
                        "업종": d.get("industry", "주도업종"),
                        "종목코드": d.get("code", ""),
                        "종목명": d.get("name", ""),
                        "등락률": d.get("rate", 0.0),
                        "거래대금(억)": d.get("amount", 0),
                        "종가": d.get("close", 0),
                        "상승이유": d.get("reason", ""),
                        "키워드": d.get("keyword", rec.get("keyword", ""))
                    })
            else:
                stocks = [s.strip() for s in rec.get("stocks", "").split(",") if s.strip()]
                reasons = rec.get("reason", "")
                keyword = rec.get("keyword", "")
                
                reason_map = {}
                if "|" in reasons:
                    parts = reasons.split("|")
                    for p in parts:
                        if ":" in p:
                            s_parts = p.split(":", 1)
                            if len(s_parts) == 2:
                                reason_map[s_parts[0].strip()] = s_parts[1].strip()
                else:
                    for s in stocks:
                        reason_map[s] = reasons
                
                for idx, s in enumerate(stocks):
                    s_code = ""
                    found_code, found_market = scanner.find_symbol_by_name(s)
                    if found_code:
                        s_code = found_code
                    
                    import random
                    random.seed(sum(ord(c) for c in s) + int(selected_date.replace("-", "")))
                    s_rate = round(random.uniform(10.5, 29.9), 2)
                    s_amt = int(random.uniform(100, 1500))
                    s_close = int(random.uniform(2000, 150000))
                    
                    table_rows.append({
                        "번호": idx + 1,
                        "업종": "주도업종",
                        "종목코드": s_code,
                        "종목명": s,
                        "등락률": s_rate,
                        "거래대금(억)": s_amt,
                        "종가": s_close,
                        "상승이유": reason_map.get(s, reasons),
                        "키워드": keyword
                    })
        else:
            st.info(f"📅 {selected_date}에 기록된 쉐도잉 데이터가 없습니다. 아래 '실시간 데이터 반영' 버튼으로 수집하거나 행을 추가하여 직접 작성해 주세요.")
            
        # 세션 상태 초기화 (날짜별로 유니크하게 관리)
        sel_key = f"sel_shadow_stock_{selected_date}"
        if sel_key not in st.session_state:
            st.session_state[sel_key] = None
            
        # 데이터프레임 빌드
        if not table_rows:
            df_display = pd.DataFrame(columns=["선택", "번호", "업종", "종목코드", "종목명", "등락률", "거래대금(억)", "종가", "상승이유", "키워드"])
        else:
            df_display = pd.DataFrame(table_rows)
            df_display.insert(0, "선택", False)
            curr_sel = st.session_state[sel_key]
            if curr_sel is not None and 0 <= curr_sel < len(df_display):
                df_display.loc[curr_sel, "선택"] = True
            
        # 데이터 에디터 렌더링
        st.markdown("##### 📝 급등주 & 거래대금 쉐도잉 편집 테이블")
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "선택": st.column_config.CheckboxColumn(width="small"),
                "번호": st.column_config.NumberColumn(disabled=True),
                "업종": st.column_config.TextColumn(width="medium"),
                "종목코드": st.column_config.TextColumn(width="medium"),
                "종목명": st.column_config.TextColumn(width="medium"),
                "등락률": st.column_config.NumberColumn(format="%.2f%%"),
                "거래대금(억)": st.column_config.NumberColumn(format="%d억"),
                "종가": st.column_config.NumberColumn(format="%d원"),
                "상승이유": st.column_config.TextColumn(width="large"),
                "키워드": st.column_config.TextColumn(width="medium")
            },
            key=f"shadow_editor_{selected_date}"
        )
        
        # [신규] 쉐도잉 편집 테이블 선택 체크박스 감지 및 단일 선택(라디오 단추화) 로직
        if edited_df is not None and not edited_df.empty and "선택" in edited_df.columns:
            currently_true_indices = edited_df[edited_df["선택"] == True].index.tolist()
            previous_sel = st.session_state[sel_key]
            
            new_sel = None
            if len(currently_true_indices) > 0:
                if previous_sel in currently_true_indices:
                    if len(currently_true_indices) > 1:
                        # 이미 선택된게 있는 상태에서 새것이 선택된 경우
                        new_candidates = [idx for idx in currently_true_indices if idx != previous_sel]
                        new_sel = new_candidates[0]
                    else:
                        new_sel = previous_sel
                else:
                    # 새로운 것이 하나만 체크된 경우
                    new_sel = currently_true_indices[0]
            else:
                new_sel = None
                
            if new_sel != previous_sel:
                st.session_state[sel_key] = new_sel
                st.rerun()
                
        # [신규] 선택 종목 분석 연동
        selected_stock_data = None
        curr_sel = st.session_state[sel_key]
        if curr_sel is not None and curr_sel < len(df_display):
            row = df_display.iloc[curr_sel]
            symbol = row.get("종목코드", "")
            name = row.get("종목명", "")
            
            if name:
                # 종목 코드가 없는 경우 역추적
                if not symbol or pd.isna(symbol):
                    found_code, found_market = scanner.find_symbol_by_name(name)
                    if found_code:
                        symbol = found_code
                        market = found_market
                    else:
                        symbol = None
                        market = 'KR'
                else:
                    symbol = str(symbol).strip().upper()
                    # 시장 자동 판별
                    market = 'KR'
                    if '-' in symbol: market = 'COIN'
                    elif any(c.isalpha() for c in symbol): market = 'US'
                    
                if symbol:
                    with st.spinner(f"'{name}' ({symbol}) 상세 분석 및 차트를 불러오는 중..."):
                        analysis = scanner.analyze_stock(symbol, market)
                        if analysis:
                            analysis['Name'] = name
                            analysis['market_type'] = market
                            selected_stock_data = analysis
                        else:
                            st.error(f"'{name}' ({symbol}) 시세 데이터를 불러오지 못했습니다. 데이터가 없거나 코드 형식을 확인해주세요.")
                else:
                    st.warning(f"'{name}' 종목의 종목코드를 찾을 수 없습니다. 종목코드 열에 올바른 코드를 직접 입력해주세요.")
                        
        if selected_stock_data:
            st.markdown("---")
            st.markdown(f"### 📈 {selected_stock_data['Name']} ({selected_stock_data['symbol']}) 상세 분석 (쉐도잉 연동)")
            
            # 전문가 기법 해당 여부 확인 섹션 (강조)
            st.markdown("#### 🧐 전문가 기법 및 수급 확인")
            exp_cols1 = st.columns(2)
            with exp_cols1[0]:
                st.write("**🥣 주식단테 (밥그릇/2/5/6)**")
                if "밥그릇" in str(selected_stock_data['signals']): st.success("✅ **밥그릇 3번 자리 감지!**")
                elif "256" in str(selected_stock_data['signals']): st.info("✅ **256 타점 진입!**")
                else: st.write("⚪ 조건 미달")
            with exp_cols1[1]:
                st.write("**📦 고쨱짹 (박스돌파)**")
                if "고쨱짹" in str(selected_stock_data['signals']): st.success("✅ **박스권 돌파 + 수급 대폭발!**")
                else: st.write("⚪ 조건 미달")
                
            exp_cols2 = st.columns(2)
            with exp_cols2[0]:
                st.write("**🐜 대왕개미 홍인기 (대장주/끼)**")
                if "홍인기" in str(selected_stock_data['signals']): st.success("✅ **주도주 장대양봉 발생!**")
                elif "끼" in str(selected_stock_data['signals']): st.info("✅ **과거 급등 '끼' 보유!**")
                else: st.write("⚪ 조건 미달")
            with exp_cols2[1]:
                st.write("**🚀 AP투자연구소 김용재**")
                if "AP-김용재" in str(selected_stock_data['signals']): st.success("✅ **시가/고가 돌파 및 수급 집중!**")
                else: st.write("⚪ 조건 미달")
                
            exp_cols3 = st.columns(2)
            with exp_cols3[0]:
                st.write("**💎 SMC / ICT 기법 (Mensa)**")
                if selected_stock_data.get('smc'):
                    st.success(f"✅ **SMC 신호 감지!**")
                    st.caption(f"• {selected_stock_data['smc'].get('type')} 패턴 확인")
                else: st.write("⚪ 조건 미달")
                
            # 일반 및 돈깡 시나리오 가이드
            st.markdown(render_general_scenario(selected_stock_data), unsafe_allow_html=True)
            st.markdown(render_donkkang_scenario(selected_stock_data), unsafe_allow_html=True)
            st.markdown(render_smc_scenario(selected_stock_data), unsafe_allow_html=True)
            
            # 차트 및 감지 신호 메트릭
            col_chart, col_side = st.columns([2, 1])
            with col_chart:
                display_detailed_chart(selected_stock_data['symbol'], selected_stock_data['market_type'], height=400 if st.session_state.get('mobile_mode', False) else 700)
            with col_side:
                st.metric("현재가", f"{selected_stock_data['current_price']:,.0f}")
                st.metric("종합 점수", f"{selected_stock_data['score']}점")
                st.markdown("##### 📡 실시간 감지 신호")
                for s in str(selected_stock_data['signals']).split(','):
                    if s.strip(): st.write(f"- {s.strip()}")
                
                st.markdown("##### 💡 전문가 의견")
                if selected_stock_data['action'] == 'BUY': st.success(f"**{selected_stock_data['action_desc']}**")
                else: st.info(f"**{selected_stock_data['action_desc']}**")
                
                if st.button("⭐ 포트폴리오에 추가", key="add_portfolio_shadow_btn"):
                    p_data = load_portfolio()
                    m_key = selected_stock_data['market_type']
                    if selected_stock_data['symbol'] not in p_data[m_key]:
                        p_data[m_key].append(selected_stock_data['symbol'])
                        save_portfolio(p_data)
                        st.success("추가되었습니다!")
                        st.rerun()
                    else: st.warning("이미 등록된 종목입니다.")
            st.markdown("---")
        
        col_db1, col_db2 = st.columns(2)
        with col_db1:
            if st.button("💾 테이블 편집 내용 저장 및 테마 DB 동기화", type="primary", use_container_width=True):
                if edited_df is not None and not edited_df.empty:
                    # 일지(records) 갱신
                    new_stocks = ",".join(edited_df["종목명"].dropna().tolist())
                    
                    # 상승이유 문자열 결합 (종목명: 상승이유 | 종목명: 상승이유)
                    new_reasons = []
                    new_details = []
                    for _, row in edited_df.iterrows():
                        new_reasons.append(f"{row['종목명']}: {row['상승이유']}")
                        new_details.append({
                            "name": row["종목명"],
                            "code": row["종목코드"] if row.get("종목코드") else "",
                            "rate": float(row["등락률"]) if row.get("등락률") else 0.0,
                            "amount": int(row["거래대금(억)"]) if row.get("거래대금(억)") else 0,
                            "close": int(row["종가"]) if row.get("종가") else 0,
                            "industry": row["업종"] if row.get("업종") else "주도업종",
                            "reason": row["상승이유"] if row.get("상승이유") else ""
                        })
                    reasons_str = " | ".join(new_reasons)
                    
                    new_keywords = ",".join(list(set(edited_df["키워드"].dropna().tolist())))
                    
                    # 쉐도잉 일지용 데이터 빌드
                    record_idx = -1
                    for idx, r in enumerate(shadow_data.get("records", [])):
                        if r.get("date") == selected_date:
                            record_idx = idx
                            break
                            
                    avg_rate = round(edited_df["등락률"].mean() if "등락률" in edited_df.columns else 15.0, 2)
                    total_amt = int(edited_df["거래대금(억)"].sum() if "거래대금(억)" in edited_df.columns else 500)
                    
                    record_payload = {
                        "date": selected_date,
                        "stocks": new_stocks,
                        "reason": reasons_str,
                        "keyword": new_keywords,
                        "average_rate": avg_rate,
                        "cumulative_amount": total_amt,
                        "details": new_details
                    }
                    
                    if record_idx != -1:
                        shadow_data["records"][record_idx] = record_payload
                    else:
                        shadow_data["records"].append(record_payload)
                        
                    # 테마 백과사전(dictionary) 갱신
                    for _, row in edited_df.iterrows():
                        kw = row["키워드"]
                        if not kw:
                            continue
                        kw_stocks = [row["종목명"]]
                        kw_reason = row["상승이유"]
                        
                        dict_idx = -1
                        for idx, entry in enumerate(shadow_data.get("dictionary", [])):
                            if entry.get("theme") == kw:
                                dict_idx = idx
                                break
                                
                        if dict_idx != -1:
                            existing_stocks = [s.strip() for s in shadow_data["dictionary"][dict_idx]["stocks"].split(",") if s.strip()]
                            for ks in kw_stocks:
                                if ks not in existing_stocks:
                                    existing_stocks.append(ks)
                            shadow_data["dictionary"][dict_idx]["stocks"] = ", ".join(existing_stocks)
                            shadow_data["dictionary"][dict_idx]["last_updated"] = selected_date
                            shadow_data["dictionary"][dict_idx]["reason"] = f"({selected_date} 업데이트) " + kw_reason
                            shadow_data["dictionary"][dict_idx]["average_rate"] = avg_rate
                            shadow_data["dictionary"][dict_idx]["cumulative_amount"] = total_amt
                        else:
                            import time
                            new_id = f"theme_auto_{int(time.time())}_{hash(kw)%1000}"
                            shadow_data["dictionary"].append({
                                "id": new_id,
                                "theme": kw,
                                "stocks": ", ".join(kw_stocks),
                                "reason": f"({selected_date} 신규 등록) 오늘 거래대금 급증 및 강한 세력 수급 신호가 발생한 당일 시장 주도주/테마군입니다. " + kw_reason,
                                "last_updated": selected_date,
                                "average_rate": avg_rate,
                                "cumulative_amount": total_amt
                            })
                            
                    if save_shadowing_data(shadow_data):
                        st.success(f"✅ {selected_date}자 급등주 쉐도잉 테이블 및 백과사전이 완벽하게 저장되었습니다!")
                        st.rerun()
                else:
                    st.warning("저장할 데이터가 테이블에 존재하지 않습니다.")
                    
        with col_db2:
            if st.button("🔄 실시간 데이터 오늘 자 자동 수집 및 반영", type="secondary", use_container_width=True):
                with st.spinner("실시간 한국 시장(KRX) 주도주 분석 및 백과사전 동기화 중..."):
                    success, msg = sync_realtime_shadowing_data(scanner)
                    if success:
                        st.success(msg)
                        st.session_state.selected_date = datetime.datetime.now().strftime("%Y-%m-%d")
                        st.rerun()
                    else:
                        st.error(msg)

    # --- [Step 02: 일일 키워드 캘린더 (테마 요약 테이블)] ---
    elif st.session_state.shadow_step_choice == step_options[1]:
        st.markdown(f"#### 📅 Step 02: 일일 키워드 캘린더")
        st.caption("선택한 월의 일자별 핵심 키워드(테마) 1~6 목록 테이블입니다.")
        
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        with col_nav1:
            if st.button("◀ 이전 달", key="step2_prev_month", use_container_width=True):
                st.session_state.cal_month -= 1
                if st.session_state.cal_month == 0:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                st.rerun()
        with col_nav2:
            st.markdown(f"<h4 style='text-align: center; color: #ffffff;'>📅 {st.session_state.cal_year}년 {st.session_state.cal_month}월</h4>", unsafe_allow_html=True)
        with col_nav3:
            if st.button("다음 달 ▶", key="step2_next_month", use_container_width=True):
                st.session_state.cal_month += 1
                if st.session_state.cal_month == 13:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                st.rerun()
                
        target_prefix = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}"
        month_records = [r for r in shadow_data.get("records", []) if r.get("date", "").startswith(target_prefix)]
        month_records = sorted(month_records, key=lambda x: x.get("date", ""), reverse=True)
        
        if not month_records:
            st.info(f"📅 {st.session_state.cal_year}년 {st.session_state.cal_month}월에 기록된 주식 쉐도잉 일지가 없습니다.")
        else:
            html_table = """
            <style>
                .shadow-table {
                    width: 100%;
                    border-collapse: collapse;
                    background-color: #0d1117;
                    color: #c9d1d9;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                    font-size: 13px;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    overflow: hidden;
                    margin-bottom: 20px;
                }
                .shadow-table th {
                    background-color: #161b22;
                    color: #8b949e;
                    font-weight: 600;
                    padding: 10px 8px;
                    text-align: center;
                    border: 1px solid #30363d;
                    font-size: 13px;
                }
                .shadow-table td {
                    padding: 8px 6px;
                    border: 1px solid #30363d;
                    vertical-align: top;
                }
                .shadow-table tr:hover {
                    background-color: rgba(255, 255, 255, 0.02);
                }
                .kw-cell-box {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 6px;
                    padding: 6px;
                    min-height: 80px;
                    box-sizing: border-box;
                }
                .kw-title-badge {
                    display: inline-block;
                    background-color: rgba(56, 139, 253, 0.15);
                    color: #58a6ff;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 11px;
                    margin-bottom: 6px;
                    max-width: 100%;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }
                .kw-stock-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 11px;
                    line-height: 1.3;
                }
                .kw-stock-table td {
                    padding: 2px 0 !important;
                    border: none !important;
                }
                .kw-stock-name {
                    color: #ffffff;
                    font-weight: 500;
                    max-width: 65px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    cursor: help;
                    text-decoration: underline dotted rgba(255,255,255,0.3);
                }
                .kw-stock-rate {
                    color: #ff7b72;
                    text-align: right;
                    font-weight: bold;
                }
                .kw-stock-amt {
                    color: #8b949e;
                    text-align: right;
                }
            </style>
            <table class="shadow-table">
                <thead>
                    <tr>
                        <th style="width: 10%;">일자</th>
                        <th style="width: 15%;">키워드 1</th>
                        <th style="width: 15%;">키워드 2</th>
                        <th style="width: 15%;">키워드 3</th>
                        <th style="width: 15%;">키워드 4</th>
                        <th style="width: 15%;">키워드 5</th>
                        <th style="width: 15%;">키워드 6</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for rec in month_records:
                r_date = rec.get("date", "")
                r_dt = datetime.datetime.strptime(r_date, "%Y-%m-%d")
                weekday_str = ["월", "화", "수", "목", "금", "토", "일"][r_dt.weekday()]
                date_display = f"<b>{r_dt.month}월 {r_dt.day}일</b><br/><span style='color: #8b949e; font-size: 11px;'>({weekday_str})</span>"
                
                details = rec.get("details", [])
                
                keywords_data = {}
                if details:
                    for d in details:
                        ind = d.get("industry", "주도업종")
                        if ind not in keywords_data:
                            keywords_data[ind] = []
                        keywords_data[ind].append(d)
                else:
                    raw_keyword = rec.get("keyword", "실시간수급주")
                    raw_stocks = rec.get("stocks", "")
                    raw_reasons = rec.get("reason", "")
                    
                    keywords_list = [k.strip() for k in raw_keyword.split(",") if k.strip()]
                    stocks_list = [s.strip() for s in raw_stocks.split(",") if s.strip()]
                    
                    reason_map = {}
                    if "|" in raw_reasons:
                        parts = raw_reasons.split("|")
                        for p in parts:
                            if ":" in p:
                                s_parts = p.split(":", 1)
                                if len(s_parts) == 2:
                                    reason_map[s_parts[0].strip()] = s_parts[1].strip()
                    else:
                        for s in stocks_list:
                            reason_map[s] = raw_reasons
                    
                    if keywords_list:
                        for idx, kw in enumerate(keywords_list[:6]):
                            keywords_data[kw] = []
                            chunk_size = max(1, len(stocks_list) // len(keywords_list))
                            chunk_stocks = stocks_list[idx * chunk_size : (idx + 1) * chunk_size]
                            if idx == len(keywords_list) - 1:
                                chunk_stocks = stocks_list[idx * chunk_size :]
                                
                            for s in chunk_stocks:
                                import random
                                random.seed(sum(ord(c) for c in s) + int(r_date.replace("-", "")))
                                s_rate = round(random.uniform(10.5, 29.9), 2)
                                s_amt = int(random.uniform(100, 1500))
                                s_close = int(random.uniform(2000, 150000))
                                keywords_data[kw].append({
                                    "name": s,
                                    "rate": s_rate,
                                    "amount": s_amt,
                                    "close": s_close,
                                    "reason": reason_map.get(s, raw_reasons)
                                })
                    else:
                        keywords_data["실시간수급주"] = []
                        for s in stocks_list:
                            import random
                            random.seed(sum(ord(c) for c in s) + int(r_date.replace("-", "")))
                            s_rate = round(random.uniform(10.5, 29.9), 2)
                            s_amt = int(random.uniform(100, 1500))
                            s_close = int(random.uniform(2000, 150000))
                            keywords_data["실시간수급주"].append({
                                "name": s,
                                "rate": s_rate,
                                "amount": s_amt,
                                "close": s_close,
                                "reason": reason_map.get(s, raw_reasons)
                            })
                
                sorted_kws = []
                for kw, stocks_in_kw in keywords_data.items():
                    total_amt = sum(s.get("amount", 0) for s in stocks_in_kw)
                    sorted_kws.append((kw, stocks_in_kw, total_amt))
                sorted_kws = sorted(sorted_kws, key=lambda x: x[2], reverse=True)
                
                html_table += f"""
                <tr>
                    <td style="text-align: center; font-weight: bold; background-color: #161b22; border-right: 2px solid #30363d;">
                        {date_display}
                    </td>
                """
                
                for i in range(6):
                    if i < len(sorted_kws):
                        kw_name, kw_stocks, _ = sorted_kws[i]
                        
                        cell_content = f"""
                        <div class="kw-cell-box">
                            <span class="kw-title-badge" title="{kw_name}">{kw_name}</span>
                            <table class="kw-stock-table">
                        """
                        
                        for s in kw_stocks[:5]:
                            rate_str = f"+{s['rate']}%" if s['rate'] > 0 else f"{s['rate']}%"
                            reason_clean = str(s.get('reason', '확인 불가')).replace('"', "'")
                            cell_content += f"""
                                <tr>
                                    <td class="kw-stock-name" title="[{s['name']}] 급등사유: {reason_clean}">{s['name']}</td>
                                    <td class="kw-stock-rate">{rate_str}</td>
                                    <td class="kw-stock-amt">{int(s['amount'])}억</td>
                                </tr>
                            """
                            
                        if len(kw_stocks) > 5:
                            cell_content += f"""
                                <tr>
                                    <td colspan="3" style="text-align: center; color: #8b949e; font-size: 10px; padding-top: 4px !important;">
                                        외 {len(kw_stocks) - 5}개 더보기...
                                    </td>
                                </tr>
                            """
                            
                        cell_content += """
                            </table>
                        </div>
                        """
                        
                        html_table += f"<td>{cell_content}</td>"
                    else:
                        html_table += "<td><div style='color: rgba(255,255,255,0.1); text-align: center; padding: 20px 0;'>-</div></td>"
                        
                html_table += "</tr>"
                
            html_table += """
                </tbody>
            </table>
            """
            
            st.markdown("##### 📊 일일 키워드 캘린더 요약표")
            st.markdown(html_table.replace("\n", " "), unsafe_allow_html=True)

    # --- [Step 03: 월간 키워드 캘린더 (5일 평일 달력)] ---
    elif st.session_state.shadow_step_choice == step_options[2]:
        st.markdown(f"#### 📅 Step 03: 월간 키워드 캘린더")
        st.caption("주말(토, 일)을 제외한 평일(월~금) 기준의 월간 주도 테마 캘린더입니다. 분석 버튼 클릭 시 Step 01로 바로 연동됩니다.")
        
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        with col_nav1:
            if st.button("◀ 이전 달", key="step3_prev_month", use_container_width=True):
                st.session_state.cal_month -= 1
                if st.session_state.cal_month == 0:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                st.rerun()
        with col_nav2:
            st.markdown(f"<h4 style='text-align: center; color: #ffffff;'>📅 {st.session_state.cal_year}년 {st.session_state.cal_month}월</h4>", unsafe_allow_html=True)
        with col_nav3:
            if st.button("다음 달 ▶", key="step3_next_month", use_container_width=True):
                st.session_state.cal_month += 1
                if st.session_state.cal_month == 13:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                st.rerun()
                
        # 모바일 최적화 모드(Compact)가 켜져 있는 경우
        if st.session_state.get("mobile_mode", False):
            st.info("📱 모바일 모드: 화면 폭에 최적화된 세로형 아코디언 리스트로 캘린더가 표시됩니다.")
            
            cal = calendar.Calendar(firstweekday=6)
            weeks = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
            
            def get_pastel_style(theme_name):
                colors = [
                    ("rgba(56, 139, 253, 0.25)", "#58a6ff"),
                    ("rgba(46, 160, 67, 0.25)", "#57ab5a"),
                    ("rgba(248, 81, 73, 0.25)", "#ff7b72"),
                    ("rgba(210, 153, 34, 0.25)", "#d29922"),
                    ("rgba(187, 128, 250, 0.25)", "#bc8cff")
                ]
                import hashlib
                idx = int(hashlib.md5(theme_name.encode('utf-8')).hexdigest(), 16) % len(colors)
                return colors[idx]
            
            # 주차별로 그룹화하여 표시
            for w_idx, week in enumerate(weeks):
                valid_days = [d for d in week[1:6] if d > 0] # 월~금
                if not valid_days:
                    continue
                    
                start_day = valid_days[0]
                end_day = valid_days[-1]
                week_title = f"📅 {w_idx+1}주차 ({st.session_state.cal_month:02d}월 {start_day:02d}일 ~ {end_day:02d}일)"
                
                # 해당 주차에 데이터가 1개라도 있는 날짜가 있는지 체크
                has_any_data = False
                for d in valid_days:
                    d_str = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{d:02d}"
                    if d_str in day_data:
                        has_any_data = True
                        break
                        
                is_expanded = has_any_data
                
                with st.expander(week_title, expanded=is_expanded):
                    for d in valid_days:
                        date_str = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{d:02d}"
                        has_data = date_str in day_data
                        day_of_week = ["월", "화", "수", "목", "금"][week.index(d) - 1]
                        
                        col_date, col_btn = st.columns([3, 1])
                        
                        with col_date:
                            selected_marker = " 🎯" if st.session_state.selected_date == date_str else ""
                            st.markdown(f"**{d}일 ({day_of_week})**" + (" 🟢" if has_data else "") + selected_marker)
                            if has_data:
                                day_records = day_data[date_str].get("records", [])
                                disp_items = []
                                if day_records and "details" in day_records[0] and day_records[0]["details"]:
                                    rec = day_records[0]
                                    details = rec["details"]
                                    
                                    industry_groups = {}
                                    for d_item in details:
                                        ind = d_item.get("industry", "주도업종")
                                        if ind not in industry_groups:
                                            industry_groups[ind] = []
                                        industry_groups[ind].append(d_item)
                                        
                                    for ind_name, stocks_in_ind in industry_groups.items():
                                        avg_rate = round(sum(s.get("rate", 0) for s in stocks_in_ind) / len(stocks_in_ind), 2)
                                        total_amt = int(sum(s.get("amount", 0) for s in stocks_in_ind))
                                        disp_items.append((ind_name, avg_rate, total_amt))
                                        
                                    disp_items = sorted(disp_items, key=lambda x: x[2], reverse=True)
                                else:
                                    day_themes = day_data[date_str].get("themes", [])
                                    for t in day_themes:
                                        disp_items.append((t.get("theme"), t.get("average_rate", 10.0), t.get("cumulative_amount", 500)))
                                        
                                # 칩 형태로 테마 노출
                                badges_html = ""
                                for item_theme, rate, amt in disp_items[:3]:
                                    bg_color, text_color = get_pastel_style(item_theme)
                                    badges_html += f"""
                                    <span style="
                                        background-color: {bg_color};
                                        color: {text_color};
                                        padding: 2px 6px;
                                        border-radius: 4px;
                                        font-weight: bold;
                                        font-size: 0.78em;
                                        display: inline-block;
                                        margin-right: 4px;
                                        margin-bottom: 4px;
                                    ">{item_theme} (+{rate}%)</span>
                                    """
                                if badges_html:
                                    st.markdown(badges_html, unsafe_allow_html=True)
                            else:
                                st.caption("기록 없음")
                        
                        with col_btn:
                            if has_data:
                                btn_type = "primary" if st.session_state.selected_date == date_str else "secondary"
                                if st.button("🔎 분석", key=f"cal_btn_m_{date_str}_{w_idx}", use_container_width=True, type=btn_type):
                                    st.session_state.selected_date = date_str
                                    st.session_state.shadow_step_choice = step_options[0]
                                    st.rerun()
                            else:
                                st.write("")
                                
                        st.markdown("<div style='margin: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05);'></div>", unsafe_allow_html=True)
        else:
            cols_day = st.columns(5)
            weekdays_5 = ["월", "화", "수", "목", "금"]
            for idx, w_name in enumerate(weekdays_5):
                cols_day[idx].markdown(f"<div class='weekday-header' style='color: #ffffff; text-shadow: none;'>{w_name}</div>", unsafe_allow_html=True)
                
            cal = calendar.Calendar(firstweekday=6)
            weeks = cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
            
            def get_pastel_style(theme_name):
                colors = [
                    ("rgba(56, 139, 253, 0.25)", "#58a6ff"),
                    ("rgba(46, 160, 67, 0.25)", "#57ab5a"),
                    ("rgba(248, 81, 73, 0.25)", "#ff7b72"),
                    ("rgba(210, 153, 34, 0.25)", "#d29922"),
                    ("rgba(187, 128, 250, 0.25)", "#bc8cff")
                ]
                import hashlib
                idx = int(hashlib.md5(theme_name.encode('utf-8')).hexdigest(), 16) % len(colors)
                return colors[idx]

            for w_idx, week in enumerate(weeks):
                mon_val = week[1]
                tue_val = week[2]
                wed_val = week[3]
                thu_val = week[4]
                fri_val = week[5]
                
                day_vals = [mon_val, tue_val, wed_val, thu_val, fri_val]
                cols = st.columns(5)
                
                for idx, day in enumerate(day_vals):
                    if day == 0:
                        cols[idx].write("")
                    else:
                        date_str = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                        has_data = date_str in day_data
                        
                        table_rows_html = ""
                        if has_data:
                            day_records = day_data[date_str].get("records", [])
                            
                            disp_items = []
                            if day_records and "details" in day_records[0] and day_records[0]["details"]:
                                rec = day_records[0]
                                details = rec["details"]
                                
                                industry_groups = {}
                                for d in details:
                                    ind = d.get("industry", "주도업종")
                                    if ind not in industry_groups:
                                        industry_groups[ind] = []
                                    industry_groups[ind].append(d)
                                    
                                for ind_name, stocks_in_ind in industry_groups.items():
                                    avg_rate = round(sum(s.get("rate", 0) for s in stocks_in_ind) / len(stocks_in_ind), 2)
                                    total_amt = int(sum(s.get("amount", 0) for s in stocks_in_ind))
                                    disp_items.append((ind_name, avg_rate, total_amt))
                                    
                                disp_items = sorted(disp_items, key=lambda x: x[2], reverse=True)
                            else:
                                day_themes = day_data[date_str].get("themes", [])
                                for t in day_themes:
                                    disp_items.append((t.get("theme"), t.get("average_rate", 10.0), t.get("cumulative_amount", 500)))
                                for r in day_records:
                                    keywords = [k.strip() for k in r.get("keyword", "").split(",") if k.strip()]
                                    for k in keywords:
                                        if k not in [item[0] for item in disp_items]:
                                            disp_items.append((k, r.get("average_rate", 10.0), r.get("cumulative_amount", 500)))
                                            
                            for item_theme, rate, amt in disp_items[:3]:
                                bg_color, text_color = get_pastel_style(item_theme)
                                row_html = f"""
                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <td style="padding: 2px 0;">
                                        <span style="
                                            background-color: {bg_color};
                                            color: {text_color};
                                            padding: 1px 4px;
                                            border-radius: 4px;
                                            font-weight: bold;
                                            font-size: 0.82em;
                                            display: inline-block;
                                            max-width: 70px;
                                            overflow: hidden;
                                            text-overflow: ellipsis;
                                            white-space: nowrap;
                                        " title="{item_theme}">{item_theme}</span>
                                    </td>
                                    <td style="text-align: right; color: #ff7b72; font-weight: bold; font-size: 0.85em; padding: 2px 0;">{rate}%</td>
                                    <td style="text-align: right; color: #58a6ff; font-size: 0.8em; padding: 2px 2px 2px 0;">{amt}억</td>
                                </tr>
                                """
                                table_rows_html += row_html.replace("\n", " ")
                                
                        is_selected = st.session_state.selected_date == date_str
                        card_border = "2px solid #58a6ff" if is_selected else ("1px solid #38edf9" if has_data else "1px solid rgba(255,255,255,0.15)")
                        card_bg = "rgba(88, 166, 255, 0.08)" if is_selected else ("rgba(255,255,255,0.04)" if has_data else "transparent")
                        
                        card_html = f"""
                        <div style="
                            background-color: {card_bg};
                            border: {card_border};
                            border-radius: 8px;
                            padding: 8px 6px;
                            height: 140px;
                            display: flex;
                            flex-direction: column;
                            justify-content: flex-start;
                            box-sizing: border-box;
                            margin-bottom: 4px;
                            position: relative;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 2px; margin-bottom: 4px;">
                                <span style="font-weight: bold; font-size: 1.05em; color: {'#58a6ff' if is_selected else '#ffffff'};">{day}</span>
                                {"<span style='color: #57ab5a; font-size: 0.8em; font-weight: bold;'>●</span>" if has_data else ""}
                            </div>
                            <div style="flex-grow: 1; overflow: hidden; width: 100%;">
                        """
                        
                        if has_data and table_rows_html:
                            card_html += f"""
                                <table style="width: 100%; font-size: 0.75em; border-collapse: collapse; line-height: 1.2;">
                                    <tbody>
                                        {table_rows_html}
                                    </tbody>
                                </table>
                            """
                        else:
                            card_html += """
                                <div style="display: flex; justify-content: center; align-items: center; height: 100%; color: rgba(255,255,255,0.3); font-size: 0.8em;">
                                    기록 없음
                                </div>
                            """
                        card_html += """
                            </div>
                        </div>
                        """
                        
                        flat_card_html = card_html.replace("\n", " ").strip()
                        cols[idx].markdown(flat_card_html, unsafe_allow_html=True)
                        
                        btn_label = f"🔎 {day}일 분석"
                        btn_type = "primary" if is_selected else "secondary"
                        if cols[idx].button(btn_label, key=f"cal_btn_{date_str}_{w_idx}_{idx}", use_container_width=True, type=btn_type):
                            st.session_state.selected_date = date_str
                            st.session_state.shadow_step_choice = step_options[0]
                            st.rerun()

        if st.session_state.selected_date:
            sel_date = st.session_state.selected_date
            st.markdown(f"##### 📋 {sel_date} 주도주 & 쉐도잉 간략 요약")
            
            day_themes = day_data.get(sel_date, {}).get("themes", [])
            day_records = day_data.get(sel_date, {}).get("records", [])
            
            if not day_themes and not day_records:
                st.info(f"📅 {sel_date}에 자동으로 등록되거나 기록된 상세 데이터가 없습니다.")
            else:
                det_col1, det_col2 = st.columns(2)
                with det_col1:
                    st.markdown("##### 📖 당일 동기화 테마 백과사전")
                    if not day_themes:
                        st.write("⚪ 해당일 등록된 테마가 없습니다.")
                    for entry in day_themes:
                        rate_info = f"<span style='color: #ff7b72; font-weight: bold;'>▲ {entry.get('average_rate', 0)}%</span>" if entry.get('average_rate') else ""
                        amt_info = f"<span style='color: #58a6ff; font-weight: bold;'> | {entry.get('cumulative_amount', 0)}억</span>" if entry.get('cumulative_amount') else ""
                        
                        st.markdown(f"""
                        <div class="detail-card theme-card" style="margin-bottom: 12px; padding: 12px; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; background-color: rgba(255,255,255,0.02);">
                            <div class="detail-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px; margin-bottom: 6px;">
                                <span class="detail-title" style="color:#ffffff !important; font-weight: bold; font-size: 1.05em;">🏷️ {entry.get('theme')}</span>
                                <span style="font-size: 0.85em;">{rate_info}{amt_info}</span>
                            </div>
                            <div class="detail-body">
                                <p style="color:#e2e8f0 !important; margin: 4px 0;"><strong>📈 주도 종목:</strong> <span class="highlight" style="color:#58a6ff !important; font-weight: bold;">{entry.get('stocks')}</span></p>
                                <p style="color:#adbac7 !important; margin: 4px 0; font-size: 0.9em; line-height: 1.4;"><strong>💡 상세 원인:</strong> {entry.get('reason')}</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                with det_col2:
                    st.markdown("##### 📝 당일 핵심 쉐도잉 일지")
                    if not day_records:
                        st.write("⚪ 해당일 작성된 쉐도잉 일지가 없습니다.")
                    else:
                        rec = day_records[0]
                        details = rec.get("details", [])
                        
                        if details:
                            st.write("**🔥 주요 급등주 시세 및 상승이유**")
                            
                            sub_rows = []
                            for idx, d in enumerate(details):
                                rate_val = d.get('rate', 0.0)
                                rate_str = f"+{rate_val}%" if rate_val > 0 else f"{rate_val}%"
                                sub_rows.append(f"""
                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <td style="color: #ffffff; font-weight: bold; padding: 4px 2px;">{d.get('name')}</td>
                                    <td style="color: #8b949e; font-size: 0.85em; padding: 4px 2px;">{d.get('industry', '')}</td>
                                    <td style="color: #ff7b72; font-weight: bold; text-align: right; padding: 4px 2px;">{rate_str}</td>
                                    <td style="color: #58a6ff; text-align: right; padding: 4px 2px;">{int(d.get('amount', 0))}억</td>
                                    <td style="color: #adbac7; font-size: 0.88em; padding: 4px 2px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{d.get('reason', '')}">{d.get('reason', '')}</td>
                                </tr>
                                """.replace("\n", ""))
                                
                            table_html = f"""
                            <table style="width: 100%; border-collapse: collapse; font-size: 11px; line-height: 1.3;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; color: #8b949e;">
                                        <th style="padding-bottom: 4px;">종목</th>
                                        <th style="padding-bottom: 4px;">업종</th>
                                        <th style="padding-bottom: 4px; text-align: right;">등락률</th>
                                        <th style="padding-bottom: 4px; text-align: right;">거래대금</th>
                                        <th style="padding-bottom: 4px; padding-left: 6px;">상승이유</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {"".join(sub_rows)}
                                </tbody>
                            </table>
                            """
                            st.markdown(table_html.replace("\n", " "), unsafe_allow_html=True)
                            st.caption("※ 표를 마우스로 올리시면 말줄임 처리된 전체 상승이유를 볼 수 있습니다.")
                            
                            st.write("")
                            st.markdown(f"**💡 장중 흐름 요약:**\n{rec.get('reason')}")
                        else:
                            for record in day_records:
                                st.markdown(f"""
                                <div class="detail-card shadow-card" style="margin-bottom: 12px; padding: 12px; border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; background-color: rgba(255,255,255,0.02);">
                                    <div class="detail-header" style="border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px; margin-bottom: 6px;">
                                        <span class="detail-title" style="color:#ffffff !important; font-weight: bold; font-size: 1.05em;">📅 키워드: {record.get('keyword')}</span>
                                    </div>
                                    <div class="detail-body">
                                        <p style="color:#e2e8f0 !important; margin: 4px 0;"><strong>🔥 주요 급등주:</strong> <span class="highlight" style="color:#58a6ff !important; font-weight: bold;">{record.get('stocks')}</span></p>
                                        <p style="color:#adbac7 !important; margin: 4px 0; font-size: 0.9em; line-height: 1.4;"><strong>📝 상세 흐름 & 뉴스:</strong> {record.get('reason')}</p>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

    # 6. 관리 및 데이터 아카이브
    st.write("---")
    st.markdown("#### 📦 쉐도잉 데이터 아카이브 관리")
    
    with st.expander("✍️ 신규 주도주 쉐도잉 일지 수동 작성/추가 Form", expanded=False):
        with st.form("shadow_form_new", clear_on_submit=True):
            s_date = st.date_input("날짜").strftime('%Y-%m-%d')
            s_keyword = st.text_input("핵심 키워드 (예: 반도체, 초전도체)", placeholder="핵심 테마나 재료 입력")
            s_stocks = st.text_input("주도 종목 (예: 한미반도체, 제주반도체)", placeholder="콤마(,)로 구분하여 입력")
            s_reason = st.text_area("주도 이유 및 장중 흐름", placeholder="상승 이유, 뉴스, 특징 거래대금 흐름 등 기록")
            
            col_inp1, col_inp2 = st.columns(2)
            with col_inp1:
                s_rate = st.number_input("평균 상승률 (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, help="주도주 평균 등락률 (입력 안하면 자동 난수 보정)")
            with col_inp2:
                s_amount = st.number_input("누적 거래대금 (억 원)", min_value=0, max_value=50000, value=0, step=10, help="당일 주도 테마 총 거래대금 (입력 안하면 자동 난수 보정)")
            
            if st.form_submit_button("💾 일지 기록 저장"):
                if s_keyword and s_stocks:
                    import random
                    rate_val = s_rate if s_rate > 0 else round(random.uniform(5.0, 29.0), 2)
                    amount_val = s_amount if s_amount > 0 else int(random.uniform(200, 2000))
                    
                    stocks_list = [s.strip() for s in s_stocks.split(",") if s.strip()]
                    new_details = []
                    for s in stocks_list:
                        s_code = ""
                        found_code, found_market = scanner.find_symbol_by_name(s)
                        if found_code:
                            s_code = found_code
                            
                        import random as r_seed
                        r_seed.seed(sum(ord(c) for c in s) + int(s_date.replace("-", "")))
                        if len(stocks_list) == 1:
                            s_rate_val = rate_val
                            s_amt_val = amount_val
                        else:
                            s_rate_val = round(r_seed.uniform(rate_val * 0.8, rate_val * 1.2), 2)
                            s_rate_val = min(30.0, max(-30.0, s_rate_val))
                            s_amt_val = int(amount_val / len(stocks_list))
                            
                        s_close_val = int(r_seed.uniform(2000, 150000))
                        
                        new_details.append({
                            "name": s,
                            "code": s_code,
                            "rate": s_rate_val,
                            "amount": s_amt_val,
                            "close": s_close_val,
                            "industry": s_keyword.split(",")[0].strip() if s_keyword else "주도업종",
                            "reason": s_reason
                        })
                    
                    # 중복 날짜 체크 및 추가
                    record_idx = -1
                    for idx, r in enumerate(shadow_data.get("records", [])):
                        if r.get("date") == s_date:
                            record_idx = idx
                            break
                            
                    record_payload = {
                        "date": s_date,
                        "stocks": s_stocks,
                        "reason": s_reason,
                        "keyword": s_keyword,
                        "average_rate": rate_val,
                        "cumulative_amount": amount_val,
                        "details": new_details
                    }
                    
                    if record_idx != -1:
                        shadow_data["records"][record_idx] = record_payload
                    else:
                        shadow_data["records"].append(record_payload)
                    
                    # 테마 백과사전 자동 업데이트
                    keywords = [k.strip() for k in s_keyword.split(",") if k.strip()]
                    for kw in keywords:
                        dict_idx = -1
                        for idx, entry in enumerate(shadow_data.get("dictionary", [])):
                            if entry.get("theme") == kw:
                                dict_idx = idx
                                break
                        if dict_idx != -1:
                            existing_stocks = [s.strip() for s in shadow_data["dictionary"][dict_idx]["stocks"].split(",") if s.strip()]
                            for ks in [s.strip() for s in s_stocks.split(",")]:
                                if ks not in existing_stocks:
                                    existing_stocks.append(ks)
                            shadow_data["dictionary"][dict_idx]["stocks"] = ", ".join(existing_stocks)
                            shadow_data["dictionary"][dict_idx]["last_updated"] = s_date
                            shadow_data["dictionary"][dict_idx]["reason"] = f"({s_date} 업데이트) " + s_reason
                            shadow_data["dictionary"][dict_idx]["average_rate"] = rate_val
                            shadow_data["dictionary"][dict_idx]["cumulative_amount"] = amount_val
                        else:
                            import time
                            new_id = f"theme_auto_{int(time.time())}_{hash(kw)%1000}"
                            shadow_data["dictionary"].append({
                                "id": new_id,
                                "theme": kw,
                                "stocks": s_stocks,
                                "reason": f"({s_date} 신규 등록) " + s_reason,
                                "last_updated": s_date,
                                "average_rate": rate_val,
                                "cumulative_amount": amount_val
                            })
                    if save_shadowing_data(shadow_data):
                        st.success("✅ 주도주 쉐도잉 일지 및 테마 백과사전이 성공적으로 반영되었습니다!")
                        st.rerun()
                else:
                    st.error("키워드와 주도 종목은 필수 입력 값입니다.")

    if "archive_theme_page" not in st.session_state:
        st.session_state.archive_theme_page = 1
        
    with st.expander("📖 전체 테마 백과사전 아카이브 목록 (최신순)", expanded=True):
        st.write("주도주 조건이 만족되어 백과사전에 자동으로 등록 및 업데이트된 전체 테마 목록입니다.")
        theme_search = st.text_input("🔍 테마명 또는 종목명 검색", key="theme_search_input").strip().lower()
        
        all_themes = sorted(shadow_data.get("dictionary", []), key=lambda x: x.get('last_updated', ''), reverse=True)
        
        if theme_search:
            filtered_themes = [t for t in all_themes if theme_search in t.get('theme', '').lower() or theme_search in t.get('stocks', '').lower()]
        else:
            filtered_themes = all_themes
            
        ITEMS_PER_PAGE = 10
        total_theme_pages = max(1, (len(filtered_themes) - 1) // ITEMS_PER_PAGE + 1)
        
        if st.session_state.archive_theme_page > total_theme_pages:
            st.session_state.archive_theme_page = total_theme_pages
            
        start_idx = (st.session_state.archive_theme_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_themes = filtered_themes[start_idx:end_idx]
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ 이전 페이지", key="theme_prev", disabled=(st.session_state.archive_theme_page <= 1), use_container_width=True):
                st.session_state.archive_theme_page -= 1
                st.rerun()
        with col2:
            st.markdown(f"<div style='text-align:center; padding-top:8px; color:#8b949e;'>페이지 {st.session_state.archive_theme_page} / {total_theme_pages} <span style='font-size:0.9em;'>(총 {len(filtered_themes)}건)</span></div>", unsafe_allow_html=True)
        with col3:
            if st.button("다음 페이지 ▶", key="theme_next", disabled=(st.session_state.archive_theme_page >= total_theme_pages), use_container_width=True):
                st.session_state.archive_theme_page += 1
                st.rerun()
                
        st.divider()
        
        if not page_themes:
            st.info("검색 결과가 없습니다.")
            
        for entry in page_themes:
            reason_formatted = entry.get('reason', '').replace(' | ', '<br/>&nbsp;&nbsp;• ')
            stocks_count = len([s for s in entry.get('stocks', '').split(',') if s.strip()])
            badge_html = f"<span style='background-color:rgba(88,166,255,0.15); color:#58a6ff; padding:2px 8px; border-radius:12px; font-size:0.8em; margin-left:8px;'>편입종목: {stocks_count}개</span>"
            
            st.markdown(f"""
            <div style="
                background-color: rgba(255,255,255,0.02) !important;
                border: 1px solid rgba(255,255,255,0.05) !important;
                border-radius: 8px !important;
                padding: 12px !important;
                margin-bottom: 12px !important;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div>
                        <span style="font-weight:bold; font-size:1.05em; color:#f1c40f;">🏷️ {entry.get('theme')}</span>
                        {badge_html}
                    </div>
                    <span style="font-size:0.78em; color:#8b949e;">최종 업데이트: {entry.get('last_updated')}</span>
                </div>
                <p style="margin:5px 0 10px 0; font-size:0.88em; color:#adbac7;">📈 <b>주도 종목:</b> <span style="color:#58a6ff; font-weight:bold;">{entry.get('stocks')}</span></p>
                <details>
                    <summary style="cursor:pointer; color:#8b949e; font-size:0.85em; user-select:none; outline:none;"><b>💡 상세 원인 펼쳐보기 (클릭)</b></summary>
                    <div style="margin-top:8px; padding-left:10px; border-left:2px solid #30363d; font-size:0.82em; color:#c9d1d9; line-height:1.6;">
                        &nbsp;&nbsp;• {reason_formatted}
                    </div>
                </details>
            </div>
            """, unsafe_allow_html=True)
            
    if "archive_record_page" not in st.session_state:
        st.session_state.archive_record_page = 1
        
    with st.expander("📝 전체 주식 쉐도잉 일지 아카이브 기록 (최신순)", expanded=True):
        st.write("매일 수동 또는 자동 동기화로 기록된 쉐도잉 일지 전체 기록입니다.")
        record_search = st.text_input("🔍 키워드 또는 종목명 검색", key="record_search_input").strip().lower()
        
        all_records = sorted(shadow_data.get("records", []), key=lambda x: x.get('date', ''), reverse=True)
        
        if record_search:
            filtered_records = [r for r in all_records if record_search in r.get('keyword', '').lower() or record_search in r.get('stocks', '').lower()]
        else:
            filtered_records = all_records
            
        ITEMS_PER_PAGE_REC = 10
        total_record_pages = max(1, (len(filtered_records) - 1) // ITEMS_PER_PAGE_REC + 1)
        
        if st.session_state.archive_record_page > total_record_pages:
            st.session_state.archive_record_page = total_record_pages
            
        r_start_idx = (st.session_state.archive_record_page - 1) * ITEMS_PER_PAGE_REC
        r_end_idx = r_start_idx + ITEMS_PER_PAGE_REC
        page_records = filtered_records[r_start_idx:r_end_idx]
        
        r_col1, r_col2, r_col3 = st.columns([1, 2, 1])
        with r_col1:
            if st.button("◀ 이전 페이지", key="record_prev", disabled=(st.session_state.archive_record_page <= 1), use_container_width=True):
                st.session_state.archive_record_page -= 1
                st.rerun()
        with r_col2:
            st.markdown(f"<div style='text-align:center; padding-top:8px; color:#8b949e;'>페이지 {st.session_state.archive_record_page} / {total_record_pages} <span style='font-size:0.9em;'>(총 {len(filtered_records)}건)</span></div>", unsafe_allow_html=True)
        with r_col3:
            if st.button("다음 페이지 ▶", key="record_next", disabled=(st.session_state.archive_record_page >= total_record_pages), use_container_width=True):
                st.session_state.archive_record_page += 1
                st.rerun()
                
        st.divider()
        
        if not page_records:
            st.info("검색 결과가 없습니다.")
            
        for record in page_records:
            reason_formatted = record.get('reason', '').replace(' | ', '<br/>&nbsp;&nbsp;• ')
            st.markdown(f"""
            <div style="
                background-color: rgba(30, 34, 42, 0.4) !important;
                border-left: 4px solid #58a6ff !important;
                border: 1px solid rgba(255,255,255,0.05) !important;
                border-radius: 0 8px 8px 0 !important;
                padding: 15px !important;
                margin-bottom: 15px !important;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:bold; font-size:1em; color:#58a6ff;">📅 {record.get('date')} | 핵심 키워드: {record.get('keyword')}</span>
                </div>
                <p style="margin:5px 0 10px 0; font-size:0.88em; color:#adbac7;">🔥 <b>주요 급등주:</b> {record.get('stocks')}</p>
                <details>
                    <summary style="cursor:pointer; color:#8b949e; font-size:0.85em; user-select:none; outline:none;"><b>📝 상세 흐름 & 뉴스 펼쳐보기 (클릭)</b></summary>
                    <div style="margin-top:8px; padding-left:10px; border-left:2px solid #58a6ff; font-size:0.82em; color:#c9d1d9; line-height:1.6;">
                        &nbsp;&nbsp;• {reason_formatted}
                    </div>
                </details>
            </div>
            """, unsafe_allow_html=True)


# Footer
st.divider()
st.caption(f"Last sync: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: FinanceDataReader, yfinance")

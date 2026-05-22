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
import yfinance as yf

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
    /* 기본 테마 설정 - 전체 앱 배경 다크 모드로 강력 강제 고정 */
    .stApp {
        background-color: #0b0e14 !important;
        color: #c9d1d9 !important;
    }
    
    /* 사이드바 다크 톤앤매너로 일치 */
    section[data-testid="stSidebar"] {
        background-color: #0f121d !important;
        border-right: 1px solid #1f2438 !important;
    }
    
    /* 텍스트 요소들 강제 흰색 계열로 고정 */
    h1, h2, h3, h4, h5, h6, p, li, span, label {
        color: #f0f6fc !important;
    }
    
    /* Streamlit 내장 캡션 색상도 밝게 상향 조정 */
    .stCaption, .stMarkdown caption {
        color: #8b949e !important;
    }
    
    /* Streamlit Metric 컴포넌트 커스터마이징 */
    .stMetric {
        background-color: #161b22 !important;
        padding: 15px !important;
        border-radius: 10px !important;
        border: 1px solid #30363d !important;
    }
    
    /* 제목 헤딩 */
    .stHeading {
        color: #58a6ff !important;
    }

    /* 탭 메뉴 디자인 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: #0f121d !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        border: 1px solid #1f2438 !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px !important;
        white-space: pre !important;
        background-color: transparent !important;
        border-radius: 6px !important;
        color: #8b949e !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #f0f6fc !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #58a6ff1a !important;
        color: #58a6ff !important;
        border: 1px solid #58a6ff33 !important;
    }

    /* 아코디언/익스팬더 스타일 초프리미엄화 */
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px 8px 0 0 !important;
        color: #f0f6fc !important;
        font-weight: bold !important;
    }
    .streamlit-expanderContent {
        background-color: #0e1117 !important;
        border-left: 1px solid #30363d !important;
        border-right: 1px solid #30363d !important;
        border-bottom: 1px solid #30363d !important;
        border-radius: 0 0 8px 8px !important;
        padding: 16px !important;
    }

    /* 입력창 및 셀렉트 박스 초프리미엄 다크화 */
    .stSelectbox div[data-baseweb="select"] {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    .stTextInput input {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    
    /* 버튼 스타일 초프리미엄 다크화 */
    .stButton > button {
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #30363d !important;
        color: #f0f6fc !important;
        border-color: #8b949e !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* 📱 스마트폰/모바일 환경 최적화 CSS (화면 가로 768px 이하) */
    @media (max-width: 768px) {
        /* 전체 화면 좌우상하 여백을 줄여서 스마트폰 화면을 넓게 사용 */
        .block-container {
            padding-top: 1.0rem !important;
            padding-left: 0.3rem !important;
            padding-right: 0.3rem !important;
            padding-bottom: 1.0rem !important;
        }
        
        /* 큰 텍스트(제목) 크기를 모바일에 맞게 축소하여 줄바꿈 최소화 */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1.0rem !important; }
        
        /* 터치하기 편하도록 버튼 요소들의 세로 길이를 살짝 늘리고 크기 조정 */
        .stButton > button {
            width: 100% !important;
            min-height: 44px !important;
            margin-bottom: 5px;
            font-size: 0.85rem !important;
            padding: 8px 12px !important;
        }
        
        /* 모바일에서는 표(DataFrame) 안의 글자 크기를 줄여 한눈에 많은 정보가 들어오도록 함 */
        [data-testid="stDataFrame"] {
            font-size: 0.70rem !important;
        }
        
        /* 라디오 버튼(필터링 선택 등) 레이아웃 글씨 축소 및 가로 배치 최적화 */
        .stRadio > div {
            gap: 6px !important;
        }
        .stRadio > div > label {
            font-size: 0.75rem !important;
            padding: 4px 8px !important;
        }

        /* 탭 메뉴 디자인 모바일용 초컴팩트화 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px !important;
            padding: 3px 6px !important;
        }
        .stTabs [data-baseweb="tab"] {
            height: 32px !important;
            font-size: 0.75rem !important;
            padding: 0 8px !important;
        }

        /* 모바일에서 거시경제 지표 카드 컴팩트화 */
        div[style*="backdrop-filter: blur(10px)"] {
            padding: 6px 8px !important;
            margin-bottom: 8px !important;
        }
        div[style*="backdrop-filter: blur(10px)"] > div {
            font-size: 0.7rem !important;
        }

        /* 모바일에서 메트릭 카드 글씨 크기 줄이기 */
        div[style*="backdrop-filter: blur(16px)"] {
            padding: 10px 14px !important;
            margin-bottom: 10px !important;
        }
        div[style*="backdrop-filter: blur(16px)"] > div > span {
            font-size: 0.75em !important;
        }
        div[style*="backdrop-filter: blur(16px)"] > div[style*="font-size: 2.1em"] {
            font-size: 1.5em !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def get_local_ip():
    """PC의 내부 IP 주소를 가져옵니다."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

# --- Configuration Management ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    """설정 정보를 불러옵니다. (클라우드 Secrets 우선, 로컬 파일 후순위)"""
    # 1. Streamlit Cloud Secrets 확인 (배포 환경 보안)
    if hasattr(st, "secrets"):
        try:
            token = st.secrets.get("telegram_token")
            chat_id = st.secrets.get("telegram_chat_id")
            if token and chat_id:  # Secrets에 토큰과 채팅 ID가 정상 등록된 경우에만 사용
                return {
                    "telegram_token": token,
                    "telegram_chat_id": chat_id,
                    "auto_send": st.secrets.get("auto_send", False),
                    "custom_url": st.secrets.get("custom_url", "")
                }
        except:
            pass

    # 2. 로컬 파일 확인
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
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

def convert_to_tradingview_symbol(symbol, market):
    """일반 심볼을 트레이딩뷰 전용 심볼 포맷으로 변환합니다."""
    symbol = symbol.upper().strip()
    if market == 'COIN' or market == '암호화폐 (Upbit)':
        if '-' in symbol:
            parts = symbol.split('-')
            if len(parts) == 2:
                quote, base = parts[0], parts[1]
                if quote == 'KRW':
                    return f"UPBIT:{base}KRW"
                elif quote == 'BTC':
                    return f"UPBIT:{base}BTC"
                else:
                    return f"UPBIT:{base}{quote}"
        return f"UPBIT:{symbol}KRW"
    elif market == 'KR' or market == '한국 (KRX)':
        if symbol.isdigit():
            return f"KRX:{symbol}"
        return f"KRX:{symbol}"
    elif market == 'US' or market == '미국 (US)':
        return f"NASDAQ:{symbol}"
    return symbol

def clean_html(html_str):
    """HTML 문자열 내부의 모든 줄바꿈과 연속된 공백을 한 줄로 정돈하여 Streamlit 마크다운 파서 오작동을 원천 봉쇄합니다."""
    import re
    cleaned = html_str.replace('\n', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def render_premium_metric(label, value, suffix="", color=None):
    """다크 테마 고정 환경에서 극도로 눈에 띄고 입체적인 Glassmorphism 네온 메트릭 카드를 렌더링합니다."""
    # 네온 테마 색상 지정
    accent_color = color if color else "#58a6ff"
    
    # 종합 점수일 때 고휘도 네온 색상으로 매핑하여 가시성 극대화
    if suffix == "점" or label == "종합 점수":
        try:
            score_val = int(''.join(filter(str.isdigit, str(value))))
        except:
            score_val = 50
            
        if score_val >= 70:
            accent_color = "#26a69a"  # 초고휘도 에메랄드 네온 그린
        elif score_val >= 40:
            accent_color = "#f1c40f"  # 초고휘도 네온 옐로우
        else:
            accent_color = "#ef5350"  # 초고휘도 네온 레드
            
    border_style = f"border: 2px solid {accent_color}cc !important;"  # 보더 두께 2px로 확장 및 선명도 증대
    shadow_style = f"box-shadow: 0 0 20px {accent_color}44, 0 12px 30px rgba(0, 0, 0, 0.6), inset 0 1px 0 0 rgba(255, 255, 255, 0.2) !important;"  # 네온 글로우 및 입체 쉐도우 대폭 강화
    bg_style = "background: linear-gradient(135deg, rgba(28, 33, 46, 0.95) 0%, rgba(16, 20, 28, 0.99) 100%) !important;"  # 더 깊고 매혹적인 어두운 배경 그라데이션
    
    emoji = "💵" if label == "현재가" else "🏆"
    
    return clean_html(f"""
    <div style="
        {bg_style}
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        {border_style}
        border-radius: 14px !important;
        padding: 18px 22px !important;
        margin-bottom: 16px !important;
        {shadow_style}
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    ">
        <!-- 네온 광원 효과 데코레이션 극대화 -->
        <div style="
            position: absolute !important;
            top: -30px !important;
            right: -30px !important;
            width: 100px !important;
            height: 100px !important;
            background: {accent_color} !important;
            opacity: 0.22 !important;
            filter: blur(25px) !important;
            border-radius: 50% !important;
            pointer-events: none !important;
        "></div>
        
        <div style="
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            margin-bottom: 8px !important;
        ">
            <span style="font-size: 0.88em !important; color: #8b949e !important; font-weight: 700 !important; letter-spacing: 1px !important; text-transform: uppercase !important;">{label}</span>
            <span style="font-size: 1.3em !important; filter: drop-shadow(0 0 5px {accent_color}55) !important;">{emoji}</span>
        </div>
        
        <div style="
            font-size: 2.1em !important; 
            font-weight: 900 !important; 
            color: {accent_color} !important; 
            display: flex !important; 
            align-items: baseline !important; 
            gap: 3px !important; 
            line-height: 1.15 !important; 
            letter-spacing: -0.5px !important;
            text-shadow: 0 0 15px {accent_color}77 !important; /* 글자 광원 극대화 */
        ">
            <span style="color: {accent_color} !important;">{value}</span>
            <span style="font-size: 0.52em !important; font-weight: 700 !important; color: #8b949e !important; margin-left: 3px !important; text-shadow: none !important;">{suffix}</span>
        </div>
    </div>
    """)

def render_premium_signals(signals_str):
    """실시간 기술적 감지 신호를 두 번째 이미지의 Antigravity 대시보드 스타일의 정갈하고 뚜렷한 리스트로 변환합니다."""
    signals = [s.strip() for s in str(signals_str).split(',') if s.strip()]
    if not signals:
        return clean_html(f"""
        <div style="padding: 15px !important; color: #8b949e !important; font-size: 0.9em !important; text-align: center !important; background: rgba(22, 27, 34, 0.95) !important; border-radius: 8px !important;">
            감지된 신호가 없습니다.
        </div>
        """)
        
    items_html = ""
    for sig in signals:
        icon = "📈"
        if any(k in sig for k in ["세력", "매집", "OBV"]):
            icon = "📡"
        elif any(k in sig for k in ["256", "정배열", "이평선"]):
            icon = "⚡"
        elif any(k in sig for k in ["골드", "이슬", "준S", "멘토"]):
            icon = "🏆"
        elif any(k in sig for k in ["돌파", "상승", "급등"]):
            icon = "🚀"
        elif any(k in sig for k in ["과매도", "낙폭", "변곡"]):
            icon = "✨"
        
        items_html += f"""
        <div style="
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            padding: 10px 14px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
            font-size: 0.9em !important;
            color: #ecf0f1 !important;
            text-align: left !important;
        ">
            <span style="font-size: 1.25em !important; line-height: 1 !important;">{icon}</span>
            <span style="font-weight: 500 !important; color: #f0f6fc !important; line-height: 1.4 !important;">{sig}</span>
        </div>
        """
        
    return clean_html(f"""
    <div style="
        background: rgba(22, 27, 34, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        margin-bottom: 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    ">
        {items_html}
    </div>
    """)

def render_premium_expert_opinion(action, action_desc):
    """전문가 의견을 세련된 그라데이션 및 Glassmorphism 액션 배지로 렌더링합니다."""
    is_buy = action == 'BUY'
    bg_color = "rgba(38, 166, 154, 0.15)" if is_buy else "rgba(52, 152, 219, 0.15)"
    text_color = "#26a69a" if is_buy else "#3498db"
    border_color = "rgba(38, 166, 154, 0.3)" if is_buy else "rgba(52, 152, 219, 0.3)"
    badge_label = "🔥 적극 분할 매수 유효" if is_buy else "💡 관망 및 분할 접근"
    
    return clean_html(f"""
    <div style="
        background: {bg_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
        padding: 14px 16px !important;
        margin-top: 5px !important;
        margin-bottom: 15px !important;
        text-align: center !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
    ">
        <div style="font-size: 0.75em !important; color: #8b949e !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 1px !important; margin-bottom: 4px !important;">AI Recommendation</div>
        <div style="font-size: 1.15em !important; font-weight: 700 !important; color: {text_color} !important; letter-spacing: -0.2px !important;">{badge_label}</div>
        <div style="font-size: 0.85em !important; color: #f0f6fc !important; margin-top: 5px !important; font-weight: 500 !important; line-height: 1.4 !important; text-align: center !important;">{action_desc}</div>
    </div>
    """)

def render_premium_strategy_grid(selected_data):
    """6대 전문가 전략 매칭 상태를 모던하고 깔끔한 Glassmorphism 그리드로 렌더링합니다."""
    signals_str = str(selected_data.get('signals', ''))
    
    # 1. 주식단테 판정
    dante_status = "미달"
    dante_color = "#4d5666"
    dante_bg = "rgba(77, 86, 102, 0.15)"
    if "밥그릇" in signals_str:
        dante_status = "밥그릇 3번"
        dante_color = "#26a69a"
        dante_bg = "rgba(38, 166, 154, 0.15)"
    elif "256" in signals_str:
        dante_status = "256 스윙"
        dante_color = "#3498db"
        dante_bg = "rgba(52, 152, 219, 0.15)"
        
    # 2. 고쨱짹 판정
    go_status = "미달"
    go_color = "#4d5666"
    go_bg = "rgba(77, 86, 102, 0.15)"
    if "고쨱짹" in signals_str:
        go_status = "박스돌파"
        go_color = "#26a69a"
        go_bg = "rgba(38, 166, 154, 0.15)"
        
    # 3. 홍인기 판정
    hong_status = "미달"
    hong_color = "#4d5666"
    hong_bg = "rgba(77, 86, 102, 0.15)"
    if "홍인기" in signals_str:
        hong_status = "주도대장주"
        hong_color = "#26a69a"
        hong_bg = "rgba(38, 166, 154, 0.15)"
    elif "끼" in signals_str:
        hong_status = "끼 보유주"
        hong_color = "#f1c40f"
        hong_bg = "rgba(241, 196, 15, 0.15)"
        
    # 4. AP투자연구소 판정
    ap_status = "미달"
    ap_color = "#4d5666"
    ap_bg = "rgba(77, 86, 102, 0.15)"
    if "AP-김용재" in signals_str:
        ap_status = "맥점돌파"
        ap_color = "#26a69a"
        ap_bg = "rgba(38, 166, 154, 0.15)"
        
    # 5. 오로라 판정
    aurora_val = selected_data.get('aurora', {})
    aurora_sig = aurora_val.get('signal', False) if isinstance(aurora_val, dict) else False
    aurora_status = "미달"
    aurora_color = "#4d5666"
    aurora_bg = "rgba(77, 86, 102, 0.15)"
    if aurora_sig:
        aurora_status = "과매도반등"
        aurora_color = "#26a69a"
        aurora_bg = "rgba(38, 166, 154, 0.15)"
        
    # 6. 퓨처온 판정
    fo_val = selected_data.get('futureon', {})
    fo_sig = False
    if isinstance(fo_val, dict):
        fo_sig = fo_val.get('isle') or fo_val.get('shintae') or fo_val.get('juns')
    fo_status = "미달"
    fo_color = "#4d5666"
    fo_bg = "rgba(77, 86, 102, 0.15)"
    if fo_sig:
        fo_status = "멘토 신호"
        fo_color = "#26a69a"
        fo_bg = "rgba(38, 166, 154, 0.15)"

    return clean_html(f"""
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 20px;">
        <!-- 주식단테 -->
        <div style="background: rgba(30, 34, 42, 0.35); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div>
                <div style="font-size: 0.85em; font-weight: 600; color: inherit;">🥣 주식단테</div>
                <div style="font-size: 0.70em; color: inherit; opacity: 0.55; margin-top: 1px;">밥그릇 & 256 기법</div>
            </div>
            <span style="color: {dante_color}; background: {dante_bg}; font-size: 0.70em; padding: 3px 8px; border-radius: 5px; font-weight: bold; border: 1px solid {dante_color}33;">
                {dante_status}
            </span>
        </div>
        
        <!-- 고쨱짹 -->
        <div style="background: rgba(30, 34, 42, 0.35); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div>
                <div style="font-size: 0.85em; font-weight: 600; color: inherit;">📦 고쨱짹</div>
                <div style="font-size: 0.70em; color: inherit; opacity: 0.55; margin-top: 1px;">박스돌파 & 거봉</div>
            </div>
            <span style="color: {go_color}; background: {go_bg}; font-size: 0.70em; padding: 3px 8px; border-radius: 5px; font-weight: bold; border: 1px solid {go_color}33;">
                {go_status}
            </span>
        </div>
        
        <!-- 대왕개미 홍인기 -->
        <div style="background: rgba(30, 34, 42, 0.35); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div>
                <div style="font-size: 0.85em; font-weight: 600; color: inherit;">🐜 홍인기</div>
                <div style="font-size: 0.70em; color: inherit; opacity: 0.55; margin-top: 1px;">대장주 & 끼분석</div>
            </div>
            <span style="color: {hong_color}; background: {hong_bg}; font-size: 0.70em; padding: 3px 8px; border-radius: 5px; font-weight: bold; border: 1px solid {hong_color}33;">
                {hong_status}
            </span>
        </div>
        
        <!-- AP투자연구소 -->
        <div style="background: rgba(30, 34, 42, 0.35); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div>
                <div style="font-size: 0.85em; font-weight: 600; color: inherit;">🚀 AP-김용재</div>
                <div style="font-size: 0.70em; color: inherit; opacity: 0.55; margin-top: 1px;">돌파 맥점판정</div>
            </div>
            <span style="color: {ap_color}; background: {ap_bg}; font-size: 0.70em; padding: 3px 8px; border-radius: 5px; font-weight: bold; border: 1px solid {ap_color}33;">
                {ap_status}
            </span>
        </div>
        
        <!-- 오로라 검색기 -->
        <div style="background: rgba(30, 34, 42, 0.35); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div>
                <div style="font-size: 0.85em; font-weight: 600; color: inherit;">✨ 오로라</div>
                <div style="font-size: 0.70em; color: inherit; opacity: 0.55; margin-top: 1px;">낙폭과대 반등</div>
            </div>
            <span style="color: {aurora_color}; background: {aurora_bg}; font-size: 0.70em; padding: 3px 8px; border-radius: 5px; font-weight: bold; border: 1px solid {aurora_color}33;">
                {aurora_status}
            </span>
        </div>
        
        <!-- 퓨처온 멘토군단 -->
        <div style="background: rgba(30, 34, 42, 0.35); border: 1px solid #30363d; border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div>
                <div style="font-size: 0.85em; font-weight: 600; color: inherit;">🏆 퓨처온</div>
                <div style="font-size: 0.70em; color: inherit; opacity: 0.55; margin-top: 1px;">멘토 핵심수식</div>
            </div>
            <span style="color: {fo_color}; background: {fo_bg}; font-size: 0.70em; padding: 3px 8px; border-radius: 5px; font-weight: bold; border: 1px solid {fo_color}33;">
                {fo_status}
            </span>
        </div>
    </div>
    """)

def display_detailed_chart(symbol, market):
    """선택된 종목의 상세 차트를 표시합니다. (가상화폐는 트레이딩뷰 실시간, 주식은 초프리미엄 3단 Plotly)"""
    
    # 1. 가상화폐 (COIN) 일 때는 트레이딩뷰 실시간 차트 위젯 렌더링
    if market == 'COIN' or market == '암호화폐 (Upbit)':
        tv_symbol = convert_to_tradingview_symbol(symbol, market)
        widget_html = f"""
        <div class="tradingview-widget-container" style="height: 520px; width: 100%; border-radius: 10px; overflow: hidden; border: 1px solid #30363d; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
          <div id="tradingview_chart" style="height: 520px; width: 100%;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
            {{
              "width": "100%",
              "height": 520,
              "symbol": "{tv_symbol}",
              "interval": "D",
              "timezone": "Asia/Seoul",
              "theme": "dark",
              "style": "1",
              "locale": "ko",
              "toolbar_bg": "#131722",
              "enable_publishing": false,
              "hide_side_toolbar": false,
              "allow_symbol_change": true,
              "save_image": false,
              "container_id": "tradingview_chart"
            }}
          );
          </script>
        </div>
        """
        import streamlit.components.v1 as components
        components.html(widget_html, height=530)
        return

    # 2. 주식 (KRX/US) 일 때는 초프리미엄 3단 Plotly 렌더링
    df = scanner.get_historical_data(symbol, market, days=120)
    if df is None or df.empty:
        st.error(f"{symbol} 데이터를 불러오지 못했습니다.")
        return

    # 기술 지표 계산
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
    # RSI 계산
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # 3단 서브플롯 구성 (1단: 캔들스틱/맥점, 2단: 거래량, 3단: RSI)
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04, 
        subplot_titles=(f'📈 {symbol} 캔들스틱 & 전문가 수식', '📊 거래량 (Volume)', '⚡ RSI 보조지표'),
        row_heights=[0.55, 0.20, 0.25]
    )

    # --- 1단: 캔들스틱 및 전문가 핵심 수식 ---
    fig.add_trace(go.Candlestick(
        x=df.index, 
        open=df['Open'], 
        high=df['High'], 
        low=df['Low'], 
        close=df['Close'], 
        name='주가',
        increasing_line_color='#26a69a',  # 트레이딩뷰 에메랄드 그린
        decreasing_line_color='#ef5350',  # 트레이딩뷰 네온 로즈 레드
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350'
    ), row=1, col=1)
    
    # 기본 이평선 (은은하게 처리)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='rgba(255,255,255,0.25)', width=1), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='rgba(255,165,0,0.25)', width=1), name='MA60'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='rgba(255,0,0,0.25)', width=1), name='MA120'), row=1, col=1)

    # 🏆 퓨처온 핵심 지표
    if 'GoldLine' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['GoldLine'], line=dict(color='#ffd700', width=2.5), name='🏆 골드라인 (EMA 33)'), row=1, col=1)
    
    if 'WhaleLine' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['WhaleLine'], line=dict(color='#a855f7', width=2.5, dash='dash'), name='🐳 세력선 (EMA 448)'), row=1, col=1)

    # 볼린저 밴드
    if 'BB_High' in df.columns and 'BB_Low' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(173, 216, 230, 0.08)'), showlegend=False, name='BB High'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(173, 216, 230, 0.08)'), fill='tonexty', showlegend=False, name='BB Low'), row=1, col=1)

    # 수평 지지/저항선
    if hasattr(scanner, 'horizontal_levels') and scanner.horizontal_levels:
        for level in scanner.horizontal_levels:
            fig.add_hline(y=level, line_dash="dot", line_color="rgba(255,255,255,0.15)", 
                          annotation_text=f"S/R: {level:,.0f}", annotation_position="bottom right", row=1, col=1)

    # --- 2단: 거래량 막대 그래프 ---
    volume_colors = []
    for idx, r in df.iterrows():
        if r['Close'] >= r['Open']:
            volume_colors.append('rgba(38, 166, 154, 0.55)')  # 상승 반투명 그린
        else:
            volume_colors.append('rgba(239, 83, 80, 0.55)')  # 하락 반투명 로즈 레드
            
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        name='거래량',
        marker_color=volume_colors,
        showlegend=False
    ), row=2, col=1)

    # --- 3단: RSI 보조지표 ---
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#00e5ff', width=2), name='RSI'), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 83, 80, 0.4)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(38, 166, 154, 0.4)", row=3, col=1)

    # 차트 전체 스타일링 (트레이딩뷰 프리미엄 다크)
    fig.update_layout(
        height=800,
        template="plotly_dark",
        plot_bgcolor='#131722',  # 트레이딩뷰 특유의 딥 다크 블루
        paper_bgcolor='#0e1117',
        showlegend=True, 
        xaxis_rangeslider_visible=False, 
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1,
            font=dict(size=10)
        )
    )

    # 초정밀 투명 격자선 설정
    fig.update_xaxes(
        gridcolor='rgba(255, 255, 255, 0.04)', 
        linecolor='rgba(255, 255, 255, 0.1)',
        zeroline=False
    )
    fig.update_yaxes(
        gridcolor='rgba(255, 255, 255, 0.04)', 
        linecolor='rgba(255, 255, 255, 0.1)',
        zeroline=False
    )
    
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

@st.cache_data(ttl=300)
def get_macro_indicators():
    """글로벌 거시경제 지표 데이터를 수집하고 당일 등락 정보를 계산합니다."""
    tickers = {
        "KOSPI": "^KS11",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "환율 (USD/KRW)": "KRW=X",
        "미 국채 10년": "^TNX",
        "달러 인덱스": "DX-Y.NYB"
    }
    
    data = {}
    for name, ticker in tickers.items():
        try:
            # 5일치 일봉 데이터를 조회하여 최근 2영업일 가격 비교
            tk = yf.Ticker(ticker)
            df = tk.history(period="5d")
            if df is not None and len(df) >= 2:
                prev_close = df['Close'].iloc[-2]
                curr_price = df['Close'].iloc[-1]
                delta = curr_price - prev_close
                delta_pct = (delta / prev_close) * 100
                
                # 데이터 정제 (Nan 방지)
                if pd.isna(curr_price) or pd.isna(prev_close):
                    df_clean = df.dropna(subset=['Close'])
                    if len(df_clean) >= 2:
                        prev_close = df_clean['Close'].iloc[-2]
                        curr_price = df_clean['Close'].iloc[-1]
                        delta = curr_price - prev_close
                        delta_pct = (delta / prev_close) * 100
                    else:
                        raise ValueError("Cleaned data insufficient")
                
                data[name] = {
                    "price": float(curr_price),
                    "delta": float(delta),
                    "delta_pct": float(delta_pct),
                    "success": True
                }
            elif df is not None and len(df) == 1:
                curr_price = df['Close'].iloc[-1]
                data[name] = {
                    "price": float(curr_price),
                    "delta": 0.0,
                    "delta_pct": 0.0,
                    "success": True
                }
            else:
                data[name] = {"success": False, "reason": "No data returned"}
        except Exception as e:
            data[name] = {"success": False, "reason": str(e)}
            
    return data

def render_macro_dashboard():
    """거시경제 지표를 전광판 형태로 대시보드 상단에 렌더링합니다."""
    macro_data = get_macro_indicators()
    
    cols = st.columns(6)
    
    for i, (name, info) in enumerate(macro_data.items()):
        with cols[i]:
            if info.get("success", False):
                price = info["price"]
                delta = info["delta"]
                delta_pct = info["delta_pct"]
                
                # 포맷 설정
                if "KOSPI" in name or "S&P" in name or "NASDAQ" in name:
                    price_str = f"{price:,.2f}"
                    delta_str = f"{delta:+,.2f}"
                elif "환율" in name:
                    price_str = f"{price:,.2f}원"
                    delta_str = f"{delta:+,.2f}원"
                elif "국채" in name:
                    price_str = f"{price:.3f}%"
                    delta_str = f"{delta:+.3f}%"
                else: # 달러 인덱스 등
                    price_str = f"{price:,.2f}"
                    delta_str = f"{delta:+,.2f}"
                
                # 등락에 따른 색상 및 기호 결정 (상승: 녹색, 하락: 적색, 보합: 회색)
                if delta > 0:
                    color = "#00e676"  # Premium Emerald Green
                    bg_effect = "rgba(0, 230, 118, 0.03)"
                    border_color = "rgba(0, 230, 118, 0.2)"
                    shadow_color = "rgba(0, 230, 118, 0.1)"
                    icon = "▲"
                elif delta < 0:
                    color = "#ff1744"  # Premium Neon Rose Red
                    bg_effect = "rgba(255, 23, 68, 0.03)"
                    border_color = "rgba(255, 23, 68, 0.2)"
                    shadow_color = "rgba(255, 23, 68, 0.1)"
                    icon = "▼"
                else:
                    color = "#8b949e"  # Soft Gray
                    bg_effect = "rgba(139, 148, 158, 0.03)"
                    border_color = "rgba(139, 148, 158, 0.15)"
                    shadow_color = "transparent"
                    icon = "■"
                
                st.markdown(f"""
                <div style="
                    background: {bg_effect};
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 1px solid {border_color};
                    border-radius: 8px;
                    padding: 8px 12px;
                    text-align: center;
                    box-shadow: 0 4px 12px {shadow_color};
                    transition: all 0.3s ease;
                    margin-bottom: 15px;
                ">
                    <div style="font-size: 0.78em; color: inherit; opacity: 0.65; font-weight: 500; letter-spacing: 0.5px; margin-bottom: 2px;">{name}</div>
                    <div style="font-size: 1.15em; font-weight: 700; color: inherit; margin: 2px 0;">{price_str}</div>
                    <div style="font-size: 0.75em; font-weight: 600; color: {color}; display: flex; align-items: center; justify-content: center; gap: 2px;">
                        <span>{icon}</span> {delta_str} ({delta_pct:+.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                reason = info.get("reason", "데이터 부재")
                st.markdown(f"""
                <div style="
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px dashed rgba(241, 196, 15, 0.3);
                    border-radius: 8px;
                    padding: 8px 12px;
                    text-align: center;
                    margin-bottom: 15px;
                ">
                    <div style="font-size: 0.75em; color: inherit; opacity: 0.65; margin-bottom: 2px;">{name}</div>
                    <div style="font-size: 0.9em; font-weight: 600; color: #f1c40f; margin: 4px 0;">조회 대기</div>
                    <div style="font-size: 0.65em; color: inherit; opacity: 0.5;">{reason[:20]}</div>
                </div>
                """, unsafe_allow_html=True)

# --- App Logic ---
st.title("🚀 Premium Stock Selection & Monitoring")
render_macro_dashboard()

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
        name='주가',
        increasing_line_color='#26a69a',  # 트레이딩뷰 에메랄드 그린
        decreasing_line_color='#ef5350',  # 트레이딩뷰 네온 로즈 레드
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350'
    ))

    # 2. 이동평균선
    if 'MA50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='rgba(255,165,0,0.4)', width=1.2), name='MA50'))
    if 'MA200' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='rgba(255,23,68,0.4)', width=1.2), name='MA200'))

    # 3. 볼린저 밴드 (급등 전조 확인용)
    if 'BB_High' in df.columns and 'BB_Low' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(173, 216, 230, 0.08)'), showlegend=False, name='BB High'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(173, 216, 230, 0.08)'), fill='tonexty', showlegend=False, name='BB Low'))

    # 레이아웃 설정
    fig.update_layout(
        title=f"📈 {name} ({symbol}) 상세 차트",
        yaxis_title="Price",
        xaxis_title="Date",
        template="plotly_dark",
        plot_bgcolor='#131722',  # 트레이딩뷰 특유의 딥 다크 블루
        paper_bgcolor='#0e1117',
        height=600,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        )
    )

    # 초정밀 투명 격자선 설정
    fig.update_xaxes(
        gridcolor='rgba(255, 255, 255, 0.04)',
        linecolor='rgba(255, 255, 255, 0.1)',
        zeroline=False
    )
    fig.update_yaxes(
        gridcolor='rgba(255, 255, 255, 0.04)',
        linecolor='rgba(255, 255, 255, 0.1)',
        zeroline=False
    )
    
    return fig

# --- 공통 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    # [모바일 최적화] 모바일 간소화 뷰 토글 스위치 (기본값 True)
    mobile_view = st.toggle("📱 모바일 간소화 모드", value=True, help="활성화하면 모바일 화면에서 스크롤을 길게 만드는 대형 차트와 세부 분석을 자동으로 접어 스크롤 압박을 줄입니다.")
    
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
    st.markdown("---")
    st.subheader("🌐 외부 접속 환경 설정")
    custom_url_input = st.text_input("커스텀 URL (선택, ngrok 등)", value=config.get("custom_url", ""), help="외부망에서 접속할 때 할당받은 주소(예: https://1234.ngrok.io)를 입력하면 해당 주소로 QR코드가 생성됩니다. 비워두면 현재 PC의 내부망 IP로 자동 생성됩니다.")
    
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        if st.button("💾 설정 저장", use_container_width=True):
            config["telegram_token"] = tg_token
            config["telegram_chat_id"] = tg_chat_id
            config["auto_send"] = False
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
    # 클라우드 환경이 아닐 때만 종료 및 모바일 설정 표시
    is_cloud = "STREAMLIT_RUNTIME" in os.environ or ".streamlit" in BASE_DIR
    
    if not is_cloud:
        st.markdown("---")
        st.subheader("📱 모바일 접속")
        
        # 모바일용 QR 코드 및 링크 제공
        local_ip = get_local_ip()
        saved_url = config.get("custom_url", "").strip()
        if saved_url:
            mobile_url = saved_url
            if not mobile_url.startswith("http"): mobile_url = "http://" + mobile_url
            msg_desc = "입력하신 전용 네트워크 주소(ngrok 등)로 QR이 생성되었습니다."
        else:
            mobile_url = f"http://{local_ip}:8501"
            msg_desc = "PC와 동일한 Wi-Fi에 연결된 폰으로 스캔하세요."
        
        st.info(f"💡 **스마트폰 접속:**\n{msg_desc}")
        col_qr1, col_qr2 = st.columns([1, 1])
        with col_qr1:
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={mobile_url}", width=120)
        with col_qr2:
            st.caption("주소:")
            st.code(mobile_url, language="text")

        st.markdown("---")
        st.subheader("🏁 시스템")
        if st.button("🚀 프로그램 완전히 종료"):
            shutdown_app()
    else:
        st.markdown("---")
        st.caption("☁️ 클라우드 배포 모드로 동작 중입니다.")

# 메인 탭 구성
tab_scan, tab_whale, tab_portfolio, tab_guide = st.tabs(["🔍 종목 스캔", "🐳 세력분석 & 매매타점", "💼 나의 포트폴리오", "💡 사용법 & 알고리즘"])

with tab_scan:
    st.markdown("### 🔍 시장 종목 스캐너")
    
    # [신규] 개별 종목 직접 검색 섹션
    st.markdown("#### 🔍 종목 정밀 검색")
    search_input = st.text_input("🔍 종목명, 코드, 또는 자음 검색 (예: 삼성전자, AAPL, ㅅㅅ, ㅂㅌ)", key="direct_search_input").strip()
    
    if search_input:
        matches = scanner.search_symbols(search_input)
        if matches:
            st.write(f"💡 '{search_input}' 검색 결과 ({len(matches)}개):")
            
            # 검색 결과 선택
            cols = st.columns([3, 1])
            with cols[0]:
                selected_match = st.selectbox(
                    "분석할 종목을 선택하세요", 
                    options=matches, 
                    format_func=lambda x: x['Display'],
                    key="selected_search_match"
                )
            with cols[1]:
                st.write(" ") # 수직 정렬
                if st.button("🚀 즉시 분석", use_container_width=True, key="start_direct_analysis"):
                    with st.spinner(f"'{selected_match['Name']}' 정밀 분석 중..."):
                        target_symbol = selected_match['Symbol']
                        m_code = selected_match['Market']
                        analysis = scanner.analyze_stock(target_symbol, m_code)
                        
                        if analysis:
                            analysis['Name'] = selected_match['Name']
                            analysis['market_type'] = m_code
                            st.session_state['direct_search_result'] = analysis
                            st.success(f"{analysis['Name']} ({target_symbol}) 분석 완료!")
                        else:
                            st.error("데이터를 가져오는 중 오류가 발생했습니다.")
        else:
            st.error("일치하는 종목이 없습니다. 검색어를 확인해 주세요.")

    if 'direct_search_result' in st.session_state and st.session_state['direct_search_result']:
        s_data = st.session_state['direct_search_result']
        with st.expander(f"📌 {s_data['Name']} ({s_data['symbol']}) 검색 결과 (클릭하여 닫기)", expanded=True):
            st.markdown(f"#### 🛰️ {s_data['Name']} 실시간 기술적 상태")
            
            # 모바일 뷰 분기
            if mobile_view:
                # 차트를 expander로 감싸서 숨겨둠으로써 스크롤 감소
                with st.expander("📈 실시간 정밀 차트 보기", expanded=False):
                    display_detailed_chart(s_data['symbol'], s_data['market_type'])
                
                score_val = s_data['score']
                score_color = '#26a69a' if score_val >= 70 else ('#ef5350' if score_val < 40 else '#f1c40f')
                price_suffix = "원" if s_data['market_type'] != 'US' else "달러"
                
                st.markdown(render_premium_metric("현재가", f"{s_data['current_price']:,.0f}", price_suffix), unsafe_allow_html=True)
                st.markdown(render_premium_metric("종합 점수", f"{score_val}", "점", score_color), unsafe_allow_html=True)
                
                st.markdown("##### 📡 실시간 감지 신호")
                st.markdown(render_premium_signals(s_data['signals']), unsafe_allow_html=True)
                
                st.markdown("##### 💡 전문가 의견")
                st.markdown(render_premium_expert_opinion(s_data['action'], s_data['action_desc']), unsafe_allow_html=True)
                
                if st.button("⭐ 검색 종목 포트폴리오 추가", key="add_search_portfolio", use_container_width=True):
                    p_data = load_portfolio()
                    m_key = s_data['market_type']
                    if s_data['symbol'] not in p_data[m_key]:
                        p_data[m_key].append(s_data['symbol'])
                        save_portfolio(p_data)
                        st.success("포트폴리오에 등록되었습니다!")
                    else: st.warning("이미 등록된 종목입니다.")
            else:
                s_col1, s_col2 = st.columns([2, 1])
                with s_col1:
                    display_detailed_chart(s_data['symbol'], s_data['market_type'])
                with s_col2:
                    score_val = s_data['score']
                    score_color = '#26a69a' if score_val >= 70 else ('#ef5350' if score_val < 40 else '#f1c40f')
                    price_suffix = "원" if s_data['market_type'] != 'US' else "달러"
                    
                    st.markdown(render_premium_metric("현재가", f"{s_data['current_price']:,.0f}", price_suffix), unsafe_allow_html=True)
                    st.markdown(render_premium_metric("종합 점수", f"{score_val}", "점", score_color), unsafe_allow_html=True)
                    st.markdown("##### 📡 실시간 감지 신호")
                    st.markdown(render_premium_signals(s_data['signals']), unsafe_allow_html=True)
                    
                    st.markdown("##### 💡 전문가 의견")
                    st.markdown(render_premium_expert_opinion(s_data['action'], s_data['action_desc']), unsafe_allow_html=True)
                    
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
            # 이전 검색 내역 및 상세 테이블 잔재 클리어
            if 'direct_search_result' in st.session_state:
                del st.session_state['direct_search_result']
            st.session_state['scan_count'] = st.session_state.get('scan_count', 0) + 1
            
            results = run_scan(market_choice, scan_limit)
            st.session_state['scan_results'] = results
            st.session_state['current_market'] = market_choice

    if 'scan_results' in st.session_state and st.session_state['scan_results']:
        results = st.session_state['scan_results']
        current_market = st.session_state['current_market']
        df_res = pd.DataFrame(results).sort_values(by='score', ascending=False).reset_index(drop=True)
        
        st.markdown("---")
        
        # 수동 텔레그램 전송 연동
        col_send_all_1, col_send_all_2 = st.columns([3, 1])
        with col_send_all_1:
            st.success(f"✅ {current_market} 스캔 완료! 총 {len(results)}개 우수 종목 분석 완료 (종합 점수 50점 이상)")
        with col_send_all_2:
            if st.button("📱 전체 스캔결과 Telegram 전송", use_container_width=True, key="btn_send_all_tg"):
                with st.spinner("텔레그램 전송 중..."):
                    report_msg = format_stock_message(results, current_market)
                    success, msg = send_telegram_message(report_msg)
                    if success:
                        st.success("전송 완료! 🚀")
                    else:
                        st.error(f"전송 실패: {msg}")
        
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
            "🏆 캐치(KATCH)": df_res[df_res['signals'].str.contains("캐치")] if not df_res.empty else df_res,
            "🥣 주식단테": df_res[df_res['signals'].str.contains("밥그릇|256")] if not df_res.empty else df_res,
            "📦 고쨱짹": df_res[df_res['signals'].str.contains("고쨱짹")] if not df_res.empty else df_res,
            "🐜 홍인기": df_res[df_res['signals'].str.contains("홍인기|끼")] if not df_res.empty else df_res,
            "🚀 AP-김용재": df_res[df_res['signals'].str.contains("AP-김용재")] if not df_res.empty else df_res,
            "🌞 데이매매": df_res[df_res['signals'].str.contains("🌞 데이매매")] if not df_res.empty else df_res,
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
        # 팁: 급등 임박 종목은 항상 보여주어 사용자가 필터를 바꾸더라도 언제든지 눈에 띄게 확인 가능하도록 고도화
        surge_stocks = [r for r in results if "🚀 급등 전조" in r['signals']]
        if surge_stocks:
            st.subheader("🚀 급등 임박 (Surge Alarm)")
            st.info("거래량 폭증 및 변동성 수축으로 에너지 분출이 임박한 종목들입니다.")
            surge_cols = st.columns(min(len(surge_stocks), 4))
            for i, row in enumerate(surge_stocks[:4]):
                with surge_cols[i]:
                    # 전문가 뱃지 HTML 생성
                    expert_badges = ""
                    if row.get("experts", {}).get("dante"):
                        if "밥그릇" in row['signals']: expert_badges += '<span style="background-color: #9b59b6 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🥣 단테-밥그릇</span>'
                        if "256" in row['signals']: expert_badges += '<span style="background-color: #34495e !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🎯 단테-256</span>'
                    if row.get("experts", {}).get("gozack"): expert_badges += '<span style="background-color: #e67e22 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">📦 쨱짹-박스권</span>'
                    if row.get("experts", {}).get("hongingi"): expert_badges += '<span style="background-color: #c0392b !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🐜 홍인기-대장</span>'
                    if row.get("experts", {}).get("ap_inv"): expert_badges += '<span style="background-color: #2980b9 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🚀 AP-김용재</span>'
                    if row.get("aurora", {}).get("signal"): expert_badges += '<span style="background-color: #f1c40f !important; color: black !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(0,0,0,0.15) !important;">✨ 오로라</span>'
                    if row.get("futureon", {}).get("isle"): expert_badges += '<span style="background-color: #27ae60 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🏆 이슬-골드</span>'
                    if row.get("futureon", {}).get("shintae"): expert_badges += '<span style="background-color: #8e44ad !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🏆 신태-수급</span>'
                    if row.get("futureon", {}).get("juns"): expert_badges += '<span style="background-color: #d35400 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🏆 준S-3파동</span>'
                    if "🌞 데이매매" in row['signals']: expert_badges += '<span style="background-color: #f39c12 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🌞 데이매매</span>'
                    if "🏆 캐치" in row['signals']: expert_badges += '<span style="background-color: #16a085 !important; color: white !important; padding: 3px 7px !important; border-radius: 4px !important; font-size: 0.7em !important; font-weight: 800 !important; margin-right: 5px !important; display: inline-block !important; border: 1px solid rgba(255,255,255,0.15) !important;">🏆 캐치</span>'
                    
                    price_suffix = "원" if current_market != '미국 (US)' else "달러"
                    
                    st.markdown(clean_html(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(255, 75, 75, 0.16) 0%, rgba(20, 24, 33, 0.99) 100%) !important;
                        backdrop-filter: blur(16px) !important;
                        -webkit-backdrop-filter: blur(16px) !important;
                        padding: 20px !important;
                        border-radius: 14px !important;
                        border: 2px solid #ff4b4b !important;
                        box-shadow: 0 0 25px rgba(255, 75, 75, 0.4), 0 10px 30px rgba(0, 0, 0, 0.6), inset 0 1px 0 0 rgba(255, 255, 255, 0.2) !important;
                        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
                        position: relative !important;
                        overflow: hidden !important;
                        margin-bottom: 15px !important;
                    ">
                        <!-- 백그라운드 발광 데코레이션 -->
                        <div style="
                            position: absolute !important;
                            top: -20px !important;
                            right: -20px !important;
                            width: 80px !important;
                            height: 80px !important;
                            background: #ff4b4b !important;
                            opacity: 0.25 !important;
                            filter: blur(20px) !important;
                            border-radius: 50% !important;
                            pointer-events: none !important;
                        "></div>
                        
                        <div style="display: flex !important; justify-content: space-between !important; align-items: flex-start !important; margin-bottom: 8px !important;">
                            <div>
                                <h3 style="margin: 0 !important; color: #ff4b4b !important; font-size: 1.35em !important; font-weight: 800 !important; text-shadow: 0 0 10px rgba(255, 75, 75, 0.5) !important; line-height: 1.2 !important;">🚀 {row['Name']}</h3>
                                <span style="font-size: 0.8em !important; color: #8b949e !important; font-weight: 600 !important; letter-spacing: 0.5px !important;">{row['symbol']}</span>
                            </div>
                            <div style="background-color: #ff4b4b !important; color: white !important; padding: 3px 8px !important; border-radius: 6px !important; font-weight: 900 !important; font-size: 0.75em !important; box-shadow: 0 0 8px rgba(255, 75, 75, 0.6) !important; border: 1px solid rgba(255,255,255,0.2) !important;">
                                SCORE {row['score']}
                            </div>
                        </div>
                        
                        <div style="font-size: 2.0em !important; font-weight: 900 !important; color: #ffffff !important; margin: 12px 0 10px 0 !important; line-height: 1.1 !important; display: flex !important; align-items: baseline !important; gap: 2px !important; text-shadow: 0 2px 10px rgba(0,0,0,0.5) !important;">
                            {row['current_price']:,.0f}
                            <span style="font-size: 0.5em !important; font-weight: 700 !important; color: #8b949e !important; margin-left: 2px !important;">{price_suffix}</span>
                        </div>
                        
                        <div style="display: flex !important; gap: 4px !important; flex-wrap: wrap !important; margin-bottom: 10px !important;">
                            {expert_badges}
                        </div>
                        
                        <p style="margin: 8px 0 0 0 !important; font-size: 0.82em !important; color: #e1e7ed !important; line-height: 1.4 !important; font-weight: 500 !important; border-top: 1px solid rgba(255,255,255,0.08) !important; padding-top: 8px !important;">
                            📢 {row['signals'].split('🚀')[1] if '🚀' in row['signals'] else row['signals']}
                        </p>
                    </div>
                    """), unsafe_allow_html=True)
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
                
                if mobile_view:
                    # 모바일 최적화: 가로 폭이 좁은 모바일을 위해 핵심 4개 컬럼만 제공
                    df_display = df_filtered[['action', 'Name', 'score', 'change_rate']].copy()
                    df_display['action'] = df_display['action'].map({'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'WAIT': '⚫ WAIT'}).fillna(df_display['action'])
                    df_display.columns = ['액션', '종목명', '점수', '등락률']
                else:
                    # PC 환경: 전체 9개 컬럼 상세 정보 제공
                    df_display = df_filtered[['action', 'action_desc', 'symbol', 'Name', 'score', 'current_price', 'change_rate', 'rsi', 'signals']].copy()
                    df_display['action'] = df_display['action'].map({'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'WAIT': '⚫ WAIT'}).fillna(df_display['action'])
                    df_display.columns = ['액션', '상태', '코드', '종목명', '점수', '현재가', '등락률', 'RSI', '상세신호']
                
                # 스타일링이 on_select와 충돌하여 React DOM 에러(removeChild)를 유발할 수 있으므로, 스타일 대신 순수 df를 넘기고 고유 키를 할당합니다.
                selection_event = st.dataframe(
                    df_display,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    hide_index=True,
                    key=f"table_{current_market}_{selected_strategy_name}_{st.session_state.get('scan_count', 0)}_{len(df_display)}"
                )

                # 일괄 추가 버튼
                if selection_event and hasattr(selection_event, 'selection') and selection_event.selection.rows:
                    selected_rows = selection_event.selection.rows
                    if len(selected_rows) > 0:
                        if st.button(f"⭐ 선택한 {len(selected_rows)}개 종목 포트폴리오에 일괄 추가", use_container_width=True, type="primary"):
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
                
                if mobile_view:
                    # 모바일 최적화: 스크롤 단축을 위해 전문가 기법과 차트를 접은 상태로 제공
                    with st.expander("🧐 전문가 기법 및 수급 확인 (클릭하여 펼치기)", expanded=False):
                        st.markdown(render_premium_strategy_grid(selected_data), unsafe_allow_html=True)
                        expert_reasons = []
                        if isinstance(selected_data.get('aurora'), dict) and selected_data.get('aurora', {}).get('signal'):
                            for r in selected_data['aurora']['reasons']:
                                expert_reasons.append(f"✨ **오로라**: {r}")
                        if isinstance(selected_data.get('futureon'), dict) and selected_data.get('futureon', {}).get('reasons'):
                            for r in selected_data['futureon']['reasons']:
                                expert_reasons.append(f"🏆 **퓨처온**: {r}")
                        if expert_reasons:
                            for reason in expert_reasons:
                                st.caption(reason)
                    
                    with st.expander("📈 실시간 정밀 차트 보기", expanded=False):
                        display_detailed_chart(selected_symbol, current_market)
                    
                    score_val = selected_data['score']
                    score_color = '#26a69a' if score_val >= 70 else ('#ef5350' if score_val < 40 else '#f1c40f')
                    price_suffix = "원" if current_market != '미국 (US)' else "달러"
                    
                    st.markdown(render_premium_metric("현재가", f"{selected_data['current_price']:,.0f}", price_suffix), unsafe_allow_html=True)
                    st.markdown(render_premium_metric("종합 점수", f"{score_val}", "점", score_color), unsafe_allow_html=True)
                    
                    st.markdown("##### 📡 실시간 감지 신호")
                    st.markdown(render_premium_signals(selected_data['signals']), unsafe_allow_html=True)
                    
                    st.markdown("##### 💡 전문가 의견")
                    st.markdown(render_premium_expert_opinion(selected_data['action'], selected_data['action_desc']), unsafe_allow_html=True)
                    
                    if st.button("⭐ 포트폴리오에 추가", use_container_width=True, key="add_to_portfolio_mobile"):
                        p_data = load_portfolio()
                        m_key = 'KR' if "한국" in current_market else ('US' if "미국" in current_market else 'COIN')
                        if selected_symbol not in p_data[m_key]:
                            p_data[m_key].append(selected_symbol)
                            save_portfolio(p_data)
                            st.success("추가되었습니다!")
                            st.rerun()
                        else: st.warning("이미 등록된 종목입니다.")
                else:
                    # PC 환경: 전체 정보 즉시 노출
                    st.markdown("#### 🧐 전문가 기법 및 수급 확인")
                    st.markdown(render_premium_strategy_grid(selected_data), unsafe_allow_html=True)
                    
                    expert_reasons = []
                    if isinstance(selected_data.get('aurora'), dict) and selected_data.get('aurora', {}).get('signal'):
                        for r in selected_data['aurora']['reasons']:
                            expert_reasons.append(f"✨ **오로라**: {r}")
                    if isinstance(selected_data.get('futureon'), dict) and selected_data.get('futureon', {}).get('reasons'):
                        for r in selected_data['futureon']['reasons']:
                            expert_reasons.append(f"🏆 **퓨처온**: {r}")
                    
                    if expert_reasons:
                        with st.expander("📝 기술적 분석 상세 근거 확인", expanded=True):
                            for reason in expert_reasons:
                                st.caption(reason)

                    col_chart, col_side = st.columns([2, 1])
                    with col_chart:
                        display_detailed_chart(selected_symbol, current_market)
                    
                    with col_side:
                        score_val = selected_data['score']
                        score_color = '#26a69a' if score_val >= 70 else ('#ef5350' if score_val < 40 else '#f1c40f')
                        price_suffix = "원" if current_market != '미국 (US)' else "달러"
                        
                        st.markdown(render_premium_metric("현재가", f"{selected_data['current_price']:,.0f}", price_suffix), unsafe_allow_html=True)
                        st.markdown(render_premium_metric("종합 점수", f"{score_val}", "점", score_color), unsafe_allow_html=True)
                        st.markdown("##### 📡 실시간 감지 신호")
                        st.markdown(render_premium_signals(selected_data['signals']), unsafe_allow_html=True)
                        
                        st.markdown("##### 💡 전문가 의견")
                        st.markdown(render_premium_expert_opinion(selected_data['action'], selected_data['action_desc']), unsafe_allow_html=True)
                        
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
        
        # 필터링된 결과를 리스트로 변환
        filtered_results = df_filtered.to_dict('records')
        
        # 수직 나열 배치
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

        if st.button("📱 필터결과 Telegram 전송", use_container_width=True):
            if not filtered_results:
                st.warning("전송할 종목이 없습니다.")
            else:
                with st.spinner("텔레그램 전송 중..."):
                    report_msg = format_stock_message(filtered_results, f"{current_market} 필터링")
                    success, msg = send_telegram_message(report_msg)
                    if success: st.success("전송되었습니다! 🚀")
                    else: st.error(f"실패: {msg}")

        # 리포트 텍스트 접기/펼치기 구조
        with st.expander("📋 필터링된 리포트 텍스트 확인 (클릭하여 펼치기)", expanded=False):
            if filtered_results:
                report_text = format_stock_message(filtered_results, f"{current_market} 필터링").replace("*", "")
                st.code(report_text, language="text")
                st.caption("필터링된 리포트 텍스트입니다. 복사해서 다른 곳에 활용하실 수 있습니다.")
            else:
                st.write("필터링된 결과가 없습니다.")

    else:
        if not run_button and ('scan_results' not in st.session_state):
            st.info("사이드바에서 시장을 선택하고 '스캔 시작' 버튼을 눌러주세요.")

with tab_whale:
    st.markdown("### 🐳 세력 평단가 & 매매 타점 정밀 분석")
    st.caption("수급(거래량) 폭증일의 거래량 가중평균 가격(VWAP)을 추정하여 세력 평단가 및 핵심 지지/저항 매매 타점을 안내합니다.")
    
    st.markdown("#### 🔍 종목 정밀 세력 분석")
    
    # 1. 종목 검색창
    whale_search_input = st.text_input("🔍 분석할 종목명, 코드, 또는 자음 검색 (예: 삼성전자, AAPL, ㅅㅅ)", key="whale_search_input").strip()
    
    if whale_search_input:
        whale_matches = scanner.search_symbols(whale_search_input)
        if whale_matches:
            st.write(f"💡 '{whale_search_input}' 검색 결과 ({len(whale_matches)}개):")
            
            # 검색 결과 선택
            whale_cols = st.columns([3, 1])
            with whale_cols[0]:
                selected_whale_match = st.selectbox(
                    "세력 분석 대상 종목을 선택하세요", 
                    options=whale_matches, 
                    format_func=lambda x: x['Display'],
                    key="selected_whale_match"
                )
            with whale_cols[1]:
                st.write(" ") # 수직 정렬
                start_whale_analysis = st.button("🐳 세력분석 시작", use_container_width=True, key="start_whale_analysis")
                
            if start_whale_analysis:
                with st.spinner(f"'{selected_whale_match['Name']}' 세력 평단가 및 타점 분석 중..."):
                    whale_res = scanner.calculate_whale_analysis(selected_whale_match['Symbol'], selected_whale_match['Market'])
                    if whale_res:
                        whale_res['Name'] = selected_whale_match['Name']
                        whale_res['market_type'] = selected_whale_match['Market']
                        st.session_state['active_whale_analysis'] = whale_res
                        st.success(f"{whale_res['Name']} ({selected_whale_match['Symbol']}) 세력 분석 완료!")
                    else:
                        st.error("충분한 거래 데이터가 없거나 데이터를 가져오는 중 오류가 발생했습니다. (최소 20영업일 이상 필요)")
        else:
            st.error("일치하는 종목이 없습니다. 검색어를 확인해 주세요.")

    # 2. 분석 결과 표시
    if 'active_whale_analysis' in st.session_state and st.session_state['active_whale_analysis']:
        w_data = st.session_state['active_whale_analysis']
        
        st.markdown("---")
        st.markdown(f"### 🛰️ {w_data['Name']} ({w_data['symbol']}) 세력 분석 리포트")
        
        # 3. 목표가/손절가 조정 슬라이더 (사용자 피드백 반영 - 고급 옵션)
        with st.expander("⚙️ 분석 목표가 / 손절가 비율 개별 조정"):
            col_adj1, col_adj2, col_adj3 = st.columns(3)
            # 기본값 설정
            target_1_pct = col_adj1.slider("1차 목표가 (%)", 5.0, 50.0, 15.0, step=1.0) / 100.0
            target_2_pct = col_adj2.slider("2차 목표가 (%)", 10.0, 100.0, 30.0, step=1.0) / 100.0
            stop_loss_pct = col_adj3.slider("손절가 비율 (%)", 3.0, 30.0, 7.0, step=1.0) / 100.0
            
            # 조정값 적용
            w_data['target_price_1'] = w_data['mid_term_basis'] * (1.0 + target_1_pct)
            w_data['target_price_2'] = w_data['mid_term_basis'] * (1.0 + target_2_pct)
            w_data['stop_loss'] = w_data['long_term_basis'] * (1.0 - stop_loss_pct)
            
            # 손익비 재계산
            risk = max(1, w_data['current_price'] - w_data['stop_loss'])
            reward = max(1, w_data['target_price_1'] - w_data['current_price'])
            w_data['rr_ratio'] = reward / risk
            
        # 메트릭 카드 3분할
        m_col1, m_col2, m_col3 = st.columns(3)
        
        with m_col1:
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; text-align: center;">
                <p style="margin:0; font-size:0.9em; color:#8b949e;">🔴 단기 세력평단가 (20일)</p>
                <h3 style="margin:5px 0; color:#ff4b4b;">{w_data['short_term_basis']:,.0f} 원</h3>
                <small style="color:#58a6ff;">단기 매집 추정 평단</small>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col2:
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 2px solid #f1c40f; text-align: center; box-shadow: 0 0 10px rgba(241, 196, 15, 0.2);">
                <p style="margin:0; font-size:0.9em; color:#8b949e;">🏆 중기 세력평단가 (60일)</p>
                <h3 style="margin:5px 0; color:#f1c40f;">{w_data['mid_term_basis']:,.0f} 원</h3>
                <small style="color:#2ecc71;">주도 세력 핵심 기준 단가</small>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col3:
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; text-align: center;">
                <p style="margin:0; font-size:0.9em; color:#8b949e;">🐳 장기 세력평단가 (120일)</p>
                <h3 style="margin:5px 0; color:#9b59b6;">{w_data['long_term_basis']:,.0f} 원</h3>
                <small style="color:#e67e22;">장기 매집 및 최종 보루</small>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("")
        
        # 실시간 매매 상태 지침 및 손익비 카드
        guide_col1, guide_col2 = st.columns([2, 1])
        
        curr_price = w_data['current_price']
        b_lower, b_upper = w_data['buy_zone']
        
        # 실시간 매매 상태 판별
        if curr_price < w_data['stop_loss']:
            status_color = "#e74c3c"
            status_text = "🚨 최종 손절가 이탈! 리스크 관리 시급"
            action_desc_txt = "추세 이탈 우려 구간이므로 신규 진입을 금지하고, 기존 보유 물량은 비중 축소 및 손절 처리를 적극 권장합니다."
        elif b_lower <= curr_price <= b_upper:
            status_color = "#2ecc71"
            status_text = "🟢 최적의 눌림목 분할 매수 영역!"
            action_desc_txt = "현재 주가가 중기 세력평단가 밴드 내에 위치하고 있습니다. 세력의 매집 단가와 밀접하여 손절 리스크가 낮고 반등 확률이 높은 최적의 진입 시점입니다."
        elif curr_price < b_lower:
            status_color = "#f39c12"
            status_text = "🟡 바닥 지지 확인 및 저가 매수 구간"
            action_desc_txt = "주가가 세력 평단가 하단선 아래로 내려왔으나 최종 손절선(장기평단가) 위에 위치하여 지지를 확인하고 있습니다. 분할 매수 접근은 유효하나, 반등 거래량이 실릴 때 비중을 싣는 것이 유리합니다."
        elif curr_price > w_data['target_price_1']:
            status_color = "#9b59b6"
            status_text = "🔵 1차 목표가 도달! 분할 익절 권장"
            action_desc_txt = "세력 평단가 대비 15% 이상 급등하여 1차 목표가 또는 강한 저항선 위에 위치하고 있습니다. 추격 매수를 자제하고 리스크 관리를 위해 보유 물량의 30~50%는 수익 실현(익절)하는 것을 권장합니다."
        else: # b_upper < curr_price <= target_price_1
            # 괴리율 계산
            gap_pct = ((curr_price - w_data['mid_term_basis']) / w_data['mid_term_basis']) * 100
            status_color = "#3498db"
            status_text = f"👀 상승 추세 유지 (평단가 대비 +{gap_pct:.1f}%)"
            action_desc_txt = f"세력 평단가를 상회하며 안정적 상승 추세를 이어가고 있습니다. 신규 매수 시에는 약간의 눌림 조정(목표 매수가: {b_upper:,.0f}원 이하)을 기다리거나, {w_data['breakout_point']:,.0f}원 돌파 시 돌파 매수로 접근하십시오."

        with guide_col1:
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 20px; border-radius: 10px; border: 1px solid #30363d; min-height: 220px;">
                <h4 style="margin-top:0; color:{status_color};">{status_text}</h4>
                <p style="color:#adbac7; font-size:0.95em; line-height:1.6;">{action_desc_txt}</p>
                <div style="display:flex; gap:10px; margin-top:15px; flex-wrap:wrap;">
                    <span style="background-color:rgba(46, 204, 113, 0.1); color:#2ecc71; padding:3px 8px; border-radius:4px; font-size:0.85em; font-weight:bold;">👉 매수 밴드: {b_lower:,.0f} ~ {b_upper:,.0f} 원</span>
                    <span style="background-color:rgba(52, 152, 219, 0.1); color:#3498db; padding:3px 8px; border-radius:4px; font-size:0.85em; font-weight:bold;">🚀 돌파 기준가: {w_data['breakout_point']:,.0f} 원</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with guide_col2:
            # 손익비 신호 및 보고서
            rr = w_data['rr_ratio']
            if rr >= 2.0:
                rr_badge = '<span style="background-color:#2ecc71; color:white; padding:2px 6px; border-radius:4px; font-weight:bold;">매우 우수</span>'
            elif rr >= 1.2:
                rr_badge = '<span style="background-color:#3498db; color:white; padding:2px 6px; border-radius:4px; font-weight:bold;">보통</span>'
            else:
                rr_badge = '<span style="background-color:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-weight:bold;">불리</span>'
                
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 20px; border-radius: 10px; border: 1px solid #30363d; min-height: 220px;">
                <h5 style="margin-top:0; color:#58a6ff;">📊 매매 시나리오 요약</h5>
                <table style="width:100%; font-size:0.85em; border-collapse:collapse; color:#adbac7;">
                    <tr style="border-bottom:1px solid #22272e;"><td style="padding:6px 0;">현재가</td><td style="text-align:right; font-weight:bold; color:white;">{curr_price:,.0f} 원</td></tr>
                    <tr style="border-bottom:1px solid #22272e;"><td style="padding:6px 0;">1차 목표가</td><td style="text-align:right; font-weight:bold; color:#2ecc71;">{w_data['target_price_1']:,.0f} 원</td></tr>
                    <tr style="border-bottom:1px solid #22272e;"><td style="padding:6px 0;">2차 목표가</td><td style="text-align:right; font-weight:bold; color:#3498db;">{w_data['target_price_2']:,.0f} 원</td></tr>
                    <tr style="border-bottom:1px solid #22272e;"><td style="padding:6px 0;">최종 손절가</td><td style="text-align:right; font-weight:bold; color:#e74c3c;">{w_data['stop_loss']:,.0f} 원</td></tr>
                    <tr><td style="padding:6px 0;">추정 손익비</td><td style="text-align:right; font-weight:bold; color:white;">{rr:.2f}배 ({rr_badge})</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("")
        
        # 4. 세력 분석 맞춤형 Plotly 차트
        st.subheader("🐳 세력 매매 타점 시각화 차트")
        
        # 차트용 데이터
        c_df = w_data['df']
        c_df = c_df.iloc[-120:].copy() # 최근 120일
        
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # 2단 서브플롯 구성 (캔들스틱 + 거래량)
        c_fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.08, 
            subplot_titles=(f'📈 {w_data["Name"]} 캔들스틱 및 세력 타점', '📊 거래량 및 세력 수급'),
            row_heights=[0.75, 0.25]
        )
        
        # 4.1 캔들스틱 추가
        c_fig.add_trace(go.Candlestick(
            x=c_df.index, 
            open=c_df['Open'], 
            high=c_df['High'], 
            low=c_df['Low'], 
            close=c_df['Close'], 
            name='주가'
        ), row=1, col=1)
        
        # 4.2 세력 평단가 라인 추가 (중기 평단가를 굵게, 단기/장기를 얇게)
        c_fig.add_trace(go.Scatter(
            x=c_df.index, 
            y=[w_data['short_term_basis']]*len(c_df), 
            line=dict(color='rgba(255, 75, 75, 0.6)', width=1, dash='dash'), 
            name='단기 세력평단 (20일)'
        ), row=1, col=1)
        
        c_fig.add_trace(go.Scatter(
            x=c_df.index, 
            y=[w_data['mid_term_basis']]*len(c_df), 
            line=dict(color='#f1c40f', width=2.5), 
            name='🏆 중기 세력평단 (60일)'
        ), row=1, col=1)
        
        c_fig.add_trace(go.Scatter(
            x=c_df.index, 
            y=[w_data['long_term_basis']]*len(c_df), 
            line=dict(color='#9b59b6', width=1, dash='dash'), 
            name='장기 세력평단 (120일)'
        ), row=1, col=1)
        
        # 4.3 목표가 및 손절가 추가 (점선 및 실선)
        c_fig.add_trace(go.Scatter(
            x=c_df.index, 
            y=[w_data['target_price_1']]*len(c_df), 
            line=dict(color='#2ecc71', width=1.5, dash='dot'), 
            name='1차 목표가'
        ), row=1, col=1)
        
        c_fig.add_trace(go.Scatter(
            x=c_df.index, 
            y=[w_data['target_price_2']]*len(c_df), 
            line=dict(color='#3498db', width=1.5, dash='dot'), 
            name='2차 목표가'
        ), row=1, col=1)
        
        c_fig.add_trace(go.Scatter(
            x=c_df.index, 
            y=[w_data['stop_loss']]*len(c_df), 
            line=dict(color='#e74c3c', width=2), 
            name='🚨 최종 손절선'
        ), row=1, col=1)
        
        # 4.4 매수 밴드 음영 영역 채우기
        c_fig.add_shape(
            type="rect",
            x0=c_df.index[0], y0=b_lower,
            x1=c_df.index[-1], y1=b_upper,
            fillcolor="rgba(46, 204, 113, 0.08)",
            line=dict(width=0),
            layer="below",
            row=1, col=1
        )
        
        # 4.5 거래량 차트 추가
        c_df['MA20_Vol'] = c_df['Volume'].rolling(window=20).mean().fillna(method='bfill')
        vol_colors = []
        for idx, row in c_df.iterrows():
            if row['Volume'] > row['MA20_Vol'] * 1.8:
                vol_colors.append('#f1c40f') # 수급 급증일: 골드
            else:
                vol_colors.append('rgba(88, 166, 255, 0.3)') # 일반 거래일: 반투명 블루
                
        c_fig.add_trace(go.Bar(
            x=c_df.index, 
            y=c_df['Volume'], 
            marker_color=vol_colors, 
            name='거래량'
        ), row=2, col=1)
        
        c_fig.update_layout(
            height=450 if mobile_view else 700, # 모바일일 경우 차트 높이를 적절히 조절
            template="plotly_dark", 
            showlegend=True, 
            xaxis_rangeslider_visible=False, 
            margin=dict(l=5, r=5, t=30, b=5),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        if mobile_view:
            with st.expander("📈 세력 매매 타점 차트 펼치기 (터치)", expanded=False):
                st.plotly_chart(c_fig, use_container_width=True)
        else:
            st.plotly_chart(c_fig, use_container_width=True)
        
        # 5. 세력 지표 요약 진단표
        st.markdown("#### 🕵️ 세력 매집 시그널 종합 판정표")
        s_col_t1, s_col_t2 = st.columns(2)
        
        whale_days_count = w_data['whale_activity_count']
        
        with s_col_t1:
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; min-height: 180px;">
                <h5 style="margin-top:0; color:#58a6ff;">🔥 수급 강도 및 활동 빈도</h5>
                <ul style="color:#adbac7; font-size:0.9em; line-height:1.6; padding-left:20px;">
                    <li>최근 120일 내 <b>세력 대량 거래 개입일</b>: <b>{whale_days_count}회</b> 포착</li>
                    <li>현재가 대비 중기 평단가 이격도: <b>{((curr_price - w_data['mid_term_basis'])/w_data['mid_term_basis'])*100:.2f}%</b></li>
                    <li>현재 MFI (자금유입지수): <b>{c_df['MFI'].iloc[-1]:.1f}</b></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        with s_col_t2:
            st.markdown(f"""
            <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; min-height: 180px;">
                <h5 style="margin-top:0; color:#58a6ff;">⚖️ 리스크 대비 기대 수익 요약</h5>
                <ul style="color:#adbac7; font-size:0.9em; line-height:1.6; padding-left:20px;">
                    <li>1차 목표가 기대수익률: <b style="color:#2ecc71;">+{((w_data['target_price_1'] - curr_price)/curr_price)*100:.1f}%</b></li>
                    <li>2차 목표가 기대수익률: <b style="color:#3498db;">+{((w_data['target_price_2'] - curr_price)/curr_price)*100:.1f}%</b></li>
                    <li>최종 손절선 예상손실률: <b style="color:#e74c3c;">-{((curr_price - w_data['stop_loss'])/curr_price)*100:.1f}%</b></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        # 포트폴리오 즉시 추가 연계 버튼
        if st.button("⭐ 현재 분석한 종목을 포트폴리오에 등록", use_container_width=True, key="add_whale_to_portfolio"):
            p_data = load_portfolio()
            m_key = w_data['market_type']
            if w_data['symbol'] not in p_data[m_key]:
                p_data[m_key].append(w_data['symbol'])
                save_portfolio(p_data)
                st.success("보유 포트폴리오에 성공적으로 등록되었습니다!")
            else:
                st.warning("이미 등록된 종목입니다.")
                
        # 검색 결과 지우기
        if st.button("❌ 세력 분석 결과 지우기", use_container_width=True, key="clear_active_whale"):
            del st.session_state['active_whale_analysis']
            st.rerun()
    else:
        st.info("💡 위의 검색창에서 종목명을 입력하고 '세력분석 시작' 버튼을 누르면 평단가와 지지선, 목표가/손절가 정보가 상세하게 출력됩니다.")

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
                
                if mobile_view:
                    # 모바일용 컴팩트 컬럼
                    display_cols = ['action', 'name', 'score', 'current_price']
                    df_m_display = df_m[display_cols].copy()
                    if not df_m_display.empty and 'action' in df_m_display.columns:
                        df_m_display['action'] = df_m_display['action'].map({'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'WAIT': '⚫ WAIT'}).fillna(df_m_display['action'])
                    df_m_display.columns = ['액션', '종목명', '점수', '현재가']
                else:
                    # PC용 전체 컬럼
                    display_cols = ['action', 'action_desc', 'name', 'symbol', 'score', 'current_price', 'rsi', 'signals']
                    df_m_display = df_m[display_cols].copy()
                    if not df_m_display.empty and 'action' in df_m_display.columns:
                        df_m_display['action'] = df_m_display['action'].map({'BUY': '🟢 BUY', 'SELL': '🔴 SELL', 'WAIT': '⚫ WAIT'}).fillna(df_m_display['action'])
                    df_m_display.columns = ['액션', '상태', '종목명', '코드', '점수', '현재가', 'RSI', '상세신호']

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
                        
                        if mobile_view:
                            # 모바일 최적화: 전문가 매매법과 차트를 expander 내부로 수납하여 접어둠
                            with st.expander("🧐 전문가 기법 및 수급 확인 (클릭하여 펼치기)", expanded=False):
                                st.markdown(render_premium_strategy_grid(selected_data), unsafe_allow_html=True)
                                expert_reasons = []
                                if isinstance(selected_data.get('aurora'), dict) and selected_data.get('aurora', {}).get('signal'):
                                    for r in selected_data['aurora']['reasons']:
                                        expert_reasons.append(f"✨ **오로라**: {r}")
                                if isinstance(selected_data.get('futureon'), dict) and selected_data.get('futureon', {}).get('reasons'):
                                    for r in selected_data['futureon']['reasons']:
                                        expert_reasons.append(f"🏆 **퓨처온**: {r}")
                                if expert_reasons:
                                    for reason in expert_reasons:
                                        st.caption(reason)
                            
                            with st.expander("📈 실시간 정밀 차트 보기", expanded=False):
                                display_detailed_chart(selected_symbol, m_key)
                                
                            score_val = selected_data['score']
                            score_color = '#26a69a' if score_val >= 70 else ('#ef5350' if score_val < 40 else '#f1c40f')
                            price_suffix = "원" if m_key != 'US' else "달러"
                            
                            st.markdown(render_premium_metric("현재가", f"{selected_data['current_price']:,.0f}", price_suffix), unsafe_allow_html=True)
                            st.markdown(render_premium_metric("종합 점수", f"{score_val}", "점", score_color), unsafe_allow_html=True)
                            
                            st.markdown("##### 📡 실시간 감지 신호")
                            st.markdown(render_premium_signals(selected_data['signals']), unsafe_allow_html=True)
                            
                            st.markdown("##### 💡 전문가 의견")
                            st.markdown(render_premium_expert_opinion(selected_data['action'], selected_data['action_desc']), unsafe_allow_html=True)
                        else:
                            # PC 환경: 모든 정보 즉시 상세 노출
                            st.markdown("#### 🧐 전문가 기법 및 수급 확인")
                            st.markdown(render_premium_strategy_grid(selected_data), unsafe_allow_html=True)
                            
                            expert_reasons = []
                            if isinstance(selected_data.get('aurora'), dict) and selected_data.get('aurora', {}).get('signal'):
                                for r in selected_data['aurora']['reasons']:
                                    expert_reasons.append(f"✨ **오로라**: {r}")
                            if isinstance(selected_data.get('futureon'), dict) and selected_data.get('futureon', {}).get('reasons'):
                                for r in selected_data['futureon']['reasons']:
                                    expert_reasons.append(f"🏆 **퓨처온**: {r}")
                            
                            if expert_reasons:
                                with st.expander("📝 기술적 분석 상세 근거 확인", expanded=True):
                                    for reason in expert_reasons:
                                        st.caption(reason)

                            col_chart, col_side = st.columns([2, 1])
                            with col_chart:
                                display_detailed_chart(selected_symbol, m_key)
                            
                            with col_side:
                                score_val = selected_data['score']
                                score_color = '#26a69a' if score_val >= 70 else ('#ef5350' if score_val < 40 else '#f1c40f')
                                price_suffix = "원" if m_key != 'US' else "달러"
                                
                                st.markdown(render_premium_metric("현재가", f"{selected_data['current_price']:,.0f}", price_suffix), unsafe_allow_html=True)
                                st.markdown(render_premium_metric("종합 점수", f"{score_val}", "점", score_color), unsafe_allow_html=True)
                                st.markdown("##### 📡 실시간 감지 신호")
                                st.markdown(render_premium_signals(selected_data['signals']), unsafe_allow_html=True)
                                
                                st.markdown("##### 💡 전문가 의견")
                                st.markdown(render_premium_expert_opinion(selected_data['action'], selected_data['action_desc']), unsafe_allow_html=True)
                
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

with tab_guide:
    st.markdown("### 💡 종목분석기 사용법 및 알고리즘 완벽 가이드")
    st.caption("이 대시보드는 기본 기술적 보조지표와 국내 최정상 전문가들의 매매 기법을 결합한 다차원 스코어링 알고리즘으로 작동합니다.")
    
    st.markdown("---")
    
    # 1. 종합 스코어링 시스템 배점표
    st.markdown("#### 📊 1. 종합 스코어링 시스템 (100점 만점)")
    st.info("각 종목을 스캔할 때 분석 항목별로 가산점을 부여하며, 최종 점수는 최대 100점으로 제한됩니다.")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("""
        <div style="background-color: #1a1c24; padding: 18px; border-radius: 10px; border: 1px solid #30363d; min-height: 290px;">
            <h5 style="color: #58a6ff; margin-top: 0; font-size: 1.1em;">📈 기본 추세 및 모멘텀 분석</h5>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.95em; color: #adbac7;">
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;"><b>정배열 상승 추세 (가격 > 50 > 200)</b></td><td style="text-align: right; color: #2ecc71; font-weight: bold;">+40점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;">단기 이평선 상단 위치 (가격 > 50)</td><td style="text-align: right; color: #2ecc71; font-weight: bold;">+20점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;"><b>안정적 상승 모멘텀 (RSI 45 ~ 65)</b></td><td style="text-align: right; color: #2ecc71; font-weight: bold;">+30점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;">RSI 저점 매수 유효 구간 (RSI < 45)</td><td style="text-align: right; color: #2ecc71; font-weight: bold;">+10점</td></tr>
                <tr><td style="padding: 8px 0;"><b>거래량 폭발 (5일 avg vs 20일 avg 1.5배)</b></td><td style="text-align: right; color: #2ecc71; font-weight: bold;">+30점</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        
    with col_s2:
        st.markdown("""
        <div style="background-color: #1a1c24; padding: 18px; border-radius: 10px; border: 1px solid #30363d; min-height: 290px;">
            <h5 style="color: #ff4b4b; margin-top: 0; font-size: 1.1em;">🚀 급등 전조 및 세력 수급 분석</h5>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.95em; color: #adbac7;">
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;">거래량 에너지 분출 (20일 avg 2.5배 폭증)</td><td style="text-align: right; color: #ff4b4b; font-weight: bold;">+20점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;">변동성 응축 (볼린저 밴드 수축)</td><td style="text-align: right; color: #ff4b4b; font-weight: bold;">+10점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;">3일 연속 상승 캔들 (양봉)</td><td style="text-align: right; color: #ff4b4b; font-weight: bold;">+15점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;"><b>추세 내 눌림목(Pullback) 포착</b></td><td style="text-align: right; color: #ff4b4b; font-weight: bold;">+20점</td></tr>
                <tr style="border-bottom: 1px solid #30363d;"><td style="padding: 8px 0;">세력 매집 흔적 포착 (OBV 우상향)</td><td style="text-align: right; color: #ff4b4b; font-weight: bold;">+15점</td></tr>
                <tr><td style="padding: 8px 0;">자금 유입 강세 (MFI > 55)</td><td style="text-align: right; color: #ff4b4b; font-weight: bold;">+15점</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        st.write("")

    st.markdown("---")

    # 2. 7대 전문가 기법 및 기술적 상세 조건
    st.markdown("#### 🧐 2. 전문가 기법 및 기술적 상세 조건")
    
    with st.expander("🥣 주식단테 '밥그릇 패턴' & '256 기법' (종합점수 +25점 / +15점)"):
        st.markdown("""
        *   **밥그릇 3번 돌파 패턴 (+25점)**: 
            *   1년 최고가 대비 30% 이상 폭락한 뒤, 최근 60일간 변동성 10% 내외로 횡보하여 바닥을 다진(밥그릇 2번) 종목이 112일선(장기이평선)을 강력하게 뚫고 올라서는 **추세 전환의 초입 맥점**을 포착합니다.
        *   **256 스윙 기법 (+15점)**: 
            *   20일선이 우상향하고 5일선이 20일선 위에 위치(정배열 초입)하며, 현재가가 60일선 위에 위치하여 단기 스윙에 가장 안정적이고 탄력적인 추세를 확인합니다.
        """)
        
    with st.expander("📦 고쨱짹 '박스권 돌파 & 거봉' (종합점수 +30점)"):
        st.markdown("""
        *   **원리**: 최근 20거래일 동안의 최고점(박스 상단)을 몸통으로 돌파하면서, 당일 거래량이 20일 평균 거래량의 2.5배를 넘어서는 **'거봉(수급폭발)'**이 뜰 때 포착합니다. 
        *   **특징**: 지루한 횡보 기간을 끝내고 매물대를 한 번에 소화하며 급등 랠리를 시작하는 강한 모멘텀 돌파 기법입니다.
        """)

    with st.expander("🐜 대왕개미 홍인기 '대장주 첫 장대양봉 & 끼' (종합점수 +35점)"):
        st.markdown("""
        *   **홍인기 D+0 매매법**: 당일 주가 상승률 7% 이상 + 거래량이 20일 평균 대비 300% 이상 폭증 + 60일 최고가를 돌파하는 **"당일 테마의 첫 대장 장대양봉"**을 포착합니다.
        *   **종목의 끼 분석**: 최근 3개월(60거래일) 내 20% 이상 급등한 이력이나 상한가 도달 이력이 있는 '끼가 많은' 주도주를 골라내어 스윙 및 단타 승률을 극대화합니다.
        """)

    with st.expander("🚀 AP투자연구소 김용재 소장 '시가/고가 돌파' (종합점수 +30점)"):
        st.markdown("""
        *   **원리**: 당일 장중 시가 및 전일 고가를 모두 돌파(Breakout)하면서 거래량이 전일 대비 300% 이상 또는 20일 평균 대비 200% 이상 폭발적으로 들어올 때 감지합니다.
        *   **특징**: 단기 이평선(5선과 20선)의 이격도가 3% 이내로 수렴한 수렴 구간에서 에너지가 위로 강력 분출되는 시점을 기가 막히게 잡아내어 장 초반 단타 매수 타이밍을 선사합니다.
        """)

    with st.expander("✨ 오로라 검색기 '낙폭과대 변곡점' (종합점수 +40점)"):
        st.markdown("""
        *   **원리**: 단기 급락으로 주가가 엔벨로프 하한선(20일 이동평균선 대비 -20%선) 이하 또는 인근 3% 이내까지 내려앉은 과매도 영역에서 **당일 첫 양봉**과 함께 거래량이 증가하거나 RSI 과매도권(35 이하)을 탈출하는 반등의 변곡점을 잡아냅니다.
        *   **특징**: 악재나 투매로 과하게 밀린 우량주 및 주도 테마주가 기술적으로 강력한 반등을 줄 때, 바닥의 꼬리를 낚아채는 매수 급소 전략입니다.
        """)

    with st.expander("🏆 퓨처온 멘토 군단 (이슬/신태/준S) 매매법 (각 +25점)"):
        st.markdown("""
        *   **이슬 멘토 (골드라인 매매법)**: 황금 지수평균선인 EMA 33선 위에 캔들이 안착하고 골드라인이 우상향할 때 지지 매수 관점을 갖습니다.
        *   **신태 멘토 (NS밴드 지지)**: 볼린저 밴드 하단 부근에 캔들 꼬리가 접촉하고, 당일 양봉을 그리며 20일 평균 거래량의 1.2배를 초과하는 수급이 들어올 때의 매수 맥점입니다.
        *   **준S 멘토 (3파동 저점 상승)**: 20일 기준선 위에서 주가가 놀고 있으면서, 최근 60거래일 동안 3개의 유의미한 단기 저점들이 점점 높아지는 우상향 엘리어트 파동의 초입을 포착합니다.
        """)

    st.markdown("---")

    # 4. 실시간 매매 판정 (Action) 가이드
    st.markdown("#### 🎯 3. 실시간 매매 판정 (Action) 가이드")
    st.markdown("""
    <div style="background-color: #1a1c24; padding: 18px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.95em; color: #adbac7; text-align: left;">
            <thead>
                <tr style="border-bottom: 2px solid #30363d; color: #58a6ff;">
                    <th style="padding: 10px 5px; width: 22%;">판정 (Action)</th>
                    <th style="padding: 10px 5px; width: 33%;">세부 설명 (Action Desc)</th>
                    <th style="padding: 10px 5px; width: 45%;">기술적 판정 조건</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #22272e;">
                    <td style="padding: 12px 5px;"><span style="background-color: rgba(46, 204, 113, 0.2); color: #2ecc71; padding: 3px 8px; border-radius: 5px; font-weight: bold;">🟢 강력 매수</span></td>
                    <td style="padding: 12px 5px; font-weight: bold; color: #fff;">눌림목 포착 및 적극 매수 권장</td>
                    <td style="padding: 12px 5px; color: #8b949e;">종합 점수 <b>70점 이상</b>이면서 <br>우상향 내 <b>눌림목(Pullback)</b> 조건에 부합할 때</td>
                </tr>
                <tr style="border-bottom: 1px solid #22272e;">
                    <td style="padding: 12px 5px;"><span style="background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; padding: 3px 8px; border-radius: 5px; font-weight: bold;">🟢 추격 매수 가능</span></td>
                    <td style="padding: 12px 5px; font-weight: bold; color: #fff;">돌파 상승세 진입</td>
                    <td style="padding: 12px 5px; color: #8b949e;">종합 점수 <b>70점 이상</b>일 때 (추격 매물 돌파 상승)</td>
                </tr>
                <tr style="border-bottom: 1px solid #22272e;">
                    <td style="padding: 12px 5px;"><span style="background-color: rgba(46, 204, 113, 0.1); color: #82e0aa; padding: 3px 8px; border-radius: 5px; font-weight: bold;">🟢 분할 매수 유효</span></td>
                    <td style="padding: 12px 5px; font-weight: bold; color: #fff;">점진적 진입 가능</td>
                    <td style="padding: 12px 5px; color: #8b949e;">종합 점수 <b>50점 이상 70점 미만</b>일 때</td>
                </tr>
                <tr style="border-bottom: 1px solid #22272e;">
                    <td style="padding: 12px 5px;"><span style="background-color: rgba(231, 76, 60, 0.2); color: #e74c3c; padding: 3px 8px; border-radius: 5px; font-weight: bold;">🔴 과매수 익절 권장</span></td>
                    <td style="padding: 12px 5px; font-weight: bold; color: #fff;">분할 매도 및 수익 실현</td>
                    <td style="padding: 12px 5px; color: #8b949e;">과열 신호인 <b>RSI 지표가 75 이상</b>으로 치솟았을 때</td>
                </tr>
                <tr style="border-bottom: 1px solid #22272e;">
                    <td style="padding: 12px 5px;"><span style="background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; padding: 3px 8px; border-radius: 5px; font-weight: bold;">🔴 추세 이탈 우려</span></td>
                    <td style="padding: 12px 5px; font-weight: bold; color: #fff;">손절 및 비중 축소 권장</td>
                    <td style="padding: 12px 5px; color: #8b949e;">종합 점수가 <b>40점 미만</b>이면서 <br>주가가 <b>20일 이평선(MA20) 아래</b>로 내려앉았을 때</td>
                </tr>
                <tr>
                    <td style="padding: 12px 5px;"><span style="background-color: rgba(149, 165, 166, 0.2); color: #95a5a6; padding: 3px 8px; border-radius: 5px; font-weight: bold;">⚫ 관망</span></td>
                    <td style="padding: 12px 5px; font-weight: bold; color: #fff;">대기 및 관망</td>
                    <td style="padding: 12px 5px; color: #8b949e;">위의 강력한 매수/매도 조건 중 그 어느 것에도 해당하지 않을 때</td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 4. 장중 데이매매(단타) 실전 활용 가이드
    st.markdown("#### 🚀 4. 장중 데이매매(단타) 실전 활용 가이드")
    
    st.success("💡 데이매매(데이트레이딩)는 당일 매집된 거래대금(돈)이 쏠리는 '대장주'에서 짧게 방망이를 쥐고 대응해야 성공합니다.")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("""
        <div style="background-color: #1a1c24; padding: 18px; border-radius: 10px; border: 1px solid #30363d; min-height: 250px;">
            <h5 style="color: #f1c40f; margin-top: 0; font-size: 1.1em;">⏰ 장중 시간대별 매매 시나리오</h5>
            <ul style="color: #adbac7; padding-left: 20px; font-size: 0.95em; line-height: 1.6;">
                <li><b>[09:00 ~ 09:30] 시가 돌파 타점</b>
                    <br><small style="color: #8b949e;">- <b>'AP-김용재 소장 매매법'</b> 신호가 발생하고 거래량이 폭증하는 종목 공략 (목표가 2~4% 내외 청산)</small>
                </li>
                <li style="margin-top: 10px;"><b>[09:30 ~ 11:30] 시장 주도주 공략</b>
                    <br><small style="color: #8b949e;">- <b>'홍인기 D+0'</b> 및 <b>'고쨱짹 박스돌파'</b> 신호가 뜬 대장주가 눌렸다가 지지받는 눌림목에서 분할 매수</small>
                </li>
                <li style="margin-top: 10px;"><b>[13:00 ~ 15:00] 낙폭과대 변곡점 공략</b>
                    <br><small style="color: #8b949e;">- <b>'오로라 검색기'</b> 신호가 뜬 종목 중 지지받고 5분봉 첫 양봉을 그리는 종목 분할 매수</small>
                </li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with col_d2:
        st.markdown("""
        <div style="background-color: #1a1c24; padding: 18px; border-radius: 10px; border: 1px solid #30363d; min-height: 250px;">
            <h5 style="color: #e74c3c; margin-top: 0; font-size: 1.1em;">🚨 단타 매매 3대 필수 원칙</h5>
            <ol style="color: #adbac7; padding-left: 20px; font-size: 0.95em; line-height: 1.7;">
                <li><b>종합 스코어 70점 이상만 선택</b>
                    <br><small style="color: #8b949e;">- 거래대금과 힘이 증명되지 않은 종목은 절대 단타로 진입하지 않습니다.</small>
                </li>
                <li style="margin-top: 10px;"><b>분봉 차트 및 호가창 병행</b>
                    <br><small style="color: #8b949e;">- 본 분석기로 주도 종목을 먼저 발굴한 뒤, 진입/청산 타점은 1분봉/3분봉 차트와 매수-매도 잔량 호가창을 함께 보며 잡습니다.</small>
                </li>
                <li style="margin-top: 10px;"><b>기계적인 손절 대응</b>
                    <br><small style="color: #8b949e;">- 예측이 틀려 분봉상의 당일 시가나 최근 지지선을 이탈하면 <b>-1.5% ~ -2% 내외</b>에서 즉시 손절을 집행합니다.</small>
                </li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        st.write("")

# Footer
st.divider()
st.caption(f"Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: FinanceDataReader, yfinance")

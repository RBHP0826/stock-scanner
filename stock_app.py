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

# 쉐도잉 & 백과사전 파일 경로 설정
SHADOWING_FILE = os.path.join(BASE_DIR, "shadowing_dictionary.json")

def initialize_default_shadowing_data():
    """기본 주도 테마 백과사전 및 쉐도잉 일지 예시 데이터를 반환합니다."""
    import datetime
    t_day = datetime.datetime.now().strftime('%Y-%m-%d')
    return {
        "dictionary": [
            {
                "id": "theme_001",
                "theme": "반도체 HBM / CXL",
                "stocks": "한미반도체, 네오셈, 삼성전자, SK하이닉스",
                "reason": "엔비디아향 HBM3E/HBM4 공급 경쟁 본격화 및 AI 고성능 컴퓨팅을 위한 차세대 CXL 2.0 규격 메모리 모듈 부각",
                "last_updated": t_day
            },
            {
                "id": "theme_002",
                "theme": "인공지능 (AI) 온디바이스",
                "stocks": "제주반도체, 오픈엣지테크놀로지, 리노공업, 칩스앤미디어",
                "reason": "클라우드를 거치지 않고 단말기 자체에서 AI를 수행하는 온디바이스 기기 개화로 저전력 메모리 반도체 및 NPU IP 설계 가치 폭등",
                "last_updated": t_day
            },
            {
                "id": "theme_003",
                "theme": "초전도체 (LK-99 / PCPOSOS)",
                "stocks": "신성델타테크, 파워로직스, 서남, 덕성",
                "reason": "상온 초전도체 개발 주장 및 국내외 연구진의 학회 발표, 교차 검증 소식이 전해질 때마다 테마 전체가 극도의 변동성을 보이며 급등락",
                "last_updated": t_day
            },
            {
                "id": "theme_004",
                "theme": "2차전지 (양극재 / 리튬)",
                "stocks": "에코프로, 에코프로비엠, 포스코퓨처엠, 금양, 엘앤에프",
                "reason": "글로벌 친환경 탄소 제로 정책 수혜 및 북미 시장 중심의 대규모 배터리 핵심 양극소재 장기 공급 계약 수주에 따른 고성장성 부각",
                "last_updated": t_day
            }
        ],
        "records": [
            {
                "date": t_day,
                "keyword": "반도체",
                "stocks": "한미반도체, 네오셈",
                "reason": "기관/외인의 HBM 대량 순매수 유입 및 차세대 반도체 공정 가속화에 따른 강력한 상승 국면 진입"
            }
        ]
    }

def load_shadowing_data():
    """로컬 JSON에서 쉐도잉 데이터를 불러옵니다. 파일이 없을 경우 기본값을 생성합니다."""
    if os.path.exists(SHADOWING_FILE):
        try:
            with open(SHADOWING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 데이터 정합성 검증
                if "dictionary" not in data: data["dictionary"] = []
                if "records" not in data: data["records"] = []
                
                # [자동 보정] 과거 샘플 구식 날짜(2026-05-23 등)를 오늘 날짜로 자동 마이그레이션 최신화
                import datetime
                t_day = datetime.datetime.now().strftime('%Y-%m-%d')
                updated_flag = False
                for entry in data.get("dictionary", []):
                    if entry.get("last_updated") == "2026-05-23":
                        entry["last_updated"] = t_day
                        updated_flag = True
                
                if updated_flag:
                    save_shadowing_data(data)
                    
                return data
        except Exception as e:
            st.error(f"쉐도잉 데이터 로드 중 오류 발생: {e}")
            return initialize_default_shadowing_data()
    else:
        # 파일이 없으면 기본 데이터로 초기화
        data = initialize_default_shadowing_data()
        save_shadowing_data(data)
        return data

def save_shadowing_data(data):
    """쉐도잉 데이터를 로컬 JSON에 저장합니다."""
    try:
        with open(SHADOWING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"쉐도잉 데이터 저장 실패: {e}")
        return False

def sync_realtime_shadowing_data(scanner):
    """실시간 한국 시장(KRX) 데이터를 분석하여 상승률 15% 이상 & 거래대금 500억 이상 터진 주도주를 자동으로 쉐도잉 및 백과사전에 반영합니다. (미달 시 300억으로 자동 완화 적용)"""
    import datetime
    import pandas as pd
    import FinanceDataReader as fdr
    import time
    
    try:
        # 1. KRX 전체 종목 조회
        df_krx = fdr.StockListing('KRX')
        if df_krx is None or df_krx.empty:
            return False, "KRX 시장 정보를 실시간으로 가져올 수 없습니다."
            
        # 필요한 컬럼 정제 및 존재 확인
        if 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
            df_krx['Code'] = df_krx['Symbol']
        
        # 등락률 컬럼명 확인 (대소문자 구분 없이 Ratio, Rate, Chg, 등락 등이 포함된 컬럼 매칭)
        chg_col = None
        for col in df_krx.columns:
            c_low = col.lower()
            if 'ratio' in c_low or 'rate' in c_low or 'chg' in c_low or '등락' in col:
                chg_col = col
                break
                
        # 거래대금 컬럼명 확인 (대소문자 구분 없이 Amount, Value, Amt, 대금 등이 포함된 컬럼 매칭)
        amt_col = None
        for col in df_krx.columns:
            c_low = col.lower()
            if 'amount' in c_low or 'value' in c_low or 'amt' in c_low or '대금' in col:
                amt_col = col
                break
        
        df = df_krx.copy()
        
        # 등락률 및 거래대금 변환
        if chg_col:
            df[chg_col] = pd.to_numeric(df[chg_col], errors='coerce').fillna(0.0)
        else:
            return False, "주가 등락률 데이터를 찾을 수 없습니다."
            
        if amt_col:
            df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce').fillna(0.0)
        else:
            return False, "거래대금 데이터를 찾을 수 없습니다."
            
        # 2. 거래대금 스케일 감지 및 정제 (FinanceDataReader에 따라 원 단위 또는 백만 원 단위일 수 있음)
        max_amt = df[amt_col].max()
        # 한국 시장 기준 500억 = 50,000,000,000 원. 
        # 500억 임계치 설정 (거래대금 최대치 기준으로 단위를 동적 감지)
        if max_amt > 1e9: # 원 단위
            limit_500b = 50000000000
            limit_300b = 30000000000
        elif max_amt > 1e6: # 천 원 단위
            limit_500b = 50000000
            limit_300b = 30000000
        else: # 백만 원 단위
            limit_500b = 50000
            limit_300b = 30000
            
        # 등락률도 퍼센트 단위(15.0)인지 소수점 단위(0.15)인지 감지
        max_chg = df[chg_col].max()
        chg_threshold = 15.0 if max_chg > 1.0 else 0.15
        
        # 3. 1차 필터링 (상승률 15% 이상 & 거래대금 500억 이상)
        df_leaders = df[(df[chg_col] >= chg_threshold) & (df[amt_col] >= limit_500b)]
        
        # 만약 500억 이상 종목이 없으면, 300억 이상으로 완화
        if df_leaders.empty:
            df_leaders = df[(df[chg_col] >= chg_threshold) & (df[amt_col] >= limit_300b)]
            
        if df_leaders.empty:
            return False, "오늘 조건(상승률 15% 이상, 거래대금 300억 이상)을 만족하는 주도주가 없습니다."
            
        # 4. 분석 진행 및 테마 추출
        shadow_data = load_shadowing_data()
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        added_stocks = []
        themes_detected = {} # theme_name -> stocks_list
        
        for _, row in df_leaders.iterrows():
            code = row['Code']
            name = row.get('Name', code)
            
            # StockScanner 분석을 통해 신호 및 테마 융합
            analysis = scanner.analyze_stock(code, 'KR')
            if analysis:
                signals = analysis.get('signals', '')
                score = analysis.get('score', 50)
                
                # 강한 세력 수급 신호가 포착된 종목들만 등록
                if score >= 60 or "세력" in signals or "수급" in signals or "골드" in signals or "밥그릇" in signals:
                    added_stocks.append(name)
                    theme_found = "실시간 급등주"
                    themes_detected.setdefault(theme_found, []).append(name)
        
        if not added_stocks:
            return False, "조건은 만족했으나 세력 신호 기준 점수를 넘는 핵심 주도주가 없습니다."
            
        # 5. 백과사전(dictionary) 테마 자동 등재 및 병합 갱신
        # 기존 모든 테마의 last_updated 날짜를 오늘 날짜로 일괄 동적 갱신
        for entry in shadow_data.get("dictionary", []):
            entry["last_updated"] = today_str
            
        for theme_name, stocks_list in themes_detected.items():
            if theme_name == "실시간 급등주":
                theme_name = f"당일 급등 수급주 ({today_str})"
                
            theme_exists = False
            for entry in shadow_data.get("dictionary", []):
                if entry.get("theme") == theme_name:
                    theme_exists = True
                    # 기존 종목에 추가 (중복 제거)
                    existing_stocks = [s.strip() for s in entry.get("stocks", "").split(",") if s.strip()]
                    for s in stocks_list:
                        if s not in existing_stocks:
                            existing_stocks.append(s)
                    entry["stocks"] = ", ".join(existing_stocks)
                    entry["last_updated"] = today_str
                    entry["reason"] = f"({today_str} 실시간 자동 갱신) " + entry.get("reason", "")
                    break
                    
            if not theme_exists:
                new_id = f"theme_auto_{int(time.time())}_{hash(theme_name)%1000}"
                new_theme_auto = {
                    "id": new_id,
                    "theme": theme_name,
                    "stocks": ", ".join(stocks_list),
                    "reason": f"({today_str} 실시간 자동 등재) 오늘 거래대금 급증 및 강한 세력 수급 신호가 발생한 당일 시장 주도주/테마군입니다.",
                    "last_updated": today_str
                }
                shadow_data["dictionary"].append(new_theme_auto)
                
        # 쉐도잉 일지(records) 추가 (당일 키워드 통합 기록)
        record_exists = False
        for rec in shadow_data.get("records", []):
            if rec.get("date") == today_str:
                record_exists = True
                existing_stocks = [s.strip() for s in rec.get("stocks", "").split(",") if s.strip()]
                for s in added_stocks:
                    if s not in existing_stocks:
                        existing_stocks.append(s)
                rec["stocks"] = ", ".join(existing_stocks)
                rec["reason"] = f"({today_str} 실시간 수급 합산) " + rec.get("reason", "")
                break
                
        if not record_exists:
            new_record = {
                "date": today_str,
                "keyword": "실시간수급주",
                "stocks": ", ".join(added_stocks),
                "reason": f"({today_str} 자동 기록) 한국 시장 당일 거래대금 및 등락률 최상위권의 강력한 주도 세력 유입 종목군"
            }
            shadow_data["records"].insert(0, new_record) # 최신글이 맨 위로
            
        # 6. 로컬 JSON 저장
        if save_shadowing_data(shadow_data):
            return True, f"✅ 실시간 한국 시장 주도주 {len(added_stocks)}개가 백과사전 및 쉐도잉 일지에 안전하게 반영되었습니다! (분석일자: {today_str})"
        else:
            return False, "동기화된 데이터를 로컬 파일에 저장하는 데 실패했습니다."
            
    except Exception as e:
        return False, f"실시간 데이터 반영 에러: {str(e)}"

def render_trading_price_guide(symbol, market_code):
    """세력 평단을 단기, 중기, 장기로 완벽하게 세분화하여, 투자 성향별 맞춤 매매 가이드라인 표를 실시간 렌더링합니다."""
    whale = scanner.calculate_whale_analysis(symbol, market_code)
    if not whale:
        return ""
        
    curr = whale['current_price']
    price_suffix = "원" if market_code != 'US' else "달러"
    
    # [1] 단기 시나리오 계산 (단타/스윙 - 현재가 및 돌파점 기준)
    bp = whale['breakout_point']
    s_b_lower = curr * 0.98
    s_b_upper = max(curr * 1.01, bp)
    s_t1 = curr * 1.05
    s_t2 = curr * 1.10
    s_sl = curr * 0.95
    
    s_ref = s_b_upper
    s_p_t1 = ((s_t1 - s_ref) / s_ref) * 100 if s_ref > 0 else 0
    s_p_t2 = ((s_t2 - s_ref) / s_ref) * 100 if s_ref > 0 else 0
    s_p_sl = ((s_sl - s_ref) / s_ref) * 100 if s_ref > 0 else 0
    
    # [2] 중기 시나리오 계산 (추세/눌림목 - 중기 세력평단 mid_term_basis 기준)
    mid = whale['mid_term_basis']
    m_b_lower = mid * 0.97
    m_b_upper = mid * 1.03
    m_t1 = whale['target_price_1']
    m_t2 = whale['target_price_2']
    m_sl = mid * 0.92
    
    m_ref = m_b_upper
    m_p_t1 = ((m_t1 - m_ref) / m_ref) * 100 if m_ref > 0 else 0
    m_p_t2 = ((m_t2 - m_ref) / m_ref) * 100 if m_ref > 0 else 0
    m_p_sl = ((m_sl - m_ref) / m_ref) * 100 if m_ref > 0 else 0
    
    # [3] 장기 시나리오 계산 (가치/매집 - 장기 세력평단 long_term_basis 기준)
    long_b = whale['long_term_basis']
    l_b_lower = long_b * 0.95
    l_b_upper = long_b * 1.02
    l_t1 = long_b * 1.25
    l_t2 = long_b * 1.50
    l_sl = whale['stop_loss']
    
    l_ref = l_b_upper
    l_p_t1 = ((l_t1 - l_ref) / l_ref) * 100 if l_ref > 0 else 0
    l_p_t2 = ((l_t2 - l_ref) / l_ref) * 100 if l_ref > 0 else 0
    l_p_sl = ((l_sl - l_ref) / l_ref) * 100 if l_ref > 0 else 0

    # 손익비 뱃지 (중기 손익비 기준 매력도 표시)
    rr = whale['rr_ratio']
    if rr >= 2.0:
        rr_badge = '<span style="background-color:#2ecc71; color:white; padding:3px 7px; border-radius:4px; font-weight:bold; font-size:0.78em; display:inline-block; border:1px solid rgba(255,255,255,0.15);">중기 손익비 최상</span>'
    elif rr >= 1.2:
        rr_badge = '<span style="background-color:#3498db; color:white; padding:3px 7px; border-radius:4px; font-weight:bold; font-size:0.78em; display:inline-block; border:1px solid rgba(255,255,255,0.15);">중기 손익비 보통</span>'
    else:
        rr_badge = '<span style="background-color:#e74c3c; color:white; padding:3px 7px; border-radius:4px; font-weight:bold; font-size:0.78em; display:inline-block; border:1px solid rgba(255,255,255,0.15);">중기 진입 주의</span>'

    html = f"""
    <div style="
        background: linear-gradient(135deg, rgba(30, 34, 42, 0.95) 0%, rgba(20, 24, 30, 0.98) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin-top: 15px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;">
            <span style="font-size: 1.05em; font-weight: bold; color: #58a6ff;">🎯 실시간 기간별(단기/중기/장기) 매매 시나리오 타점</span>
            <div>
                {rr_badge}
            </div>
        </div>
        
        <div style="overflow-x: auto;">
            <table style="width:100%; border-collapse: collapse; font-size: 0.85em; color: #adbac7; min-width: 600px;">
                <thead>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left;">
                        <th style="padding: 8px 5px; color: #8b949e; font-weight: 500; width: 22%;">구분</th>
                        <th style="padding: 8px 5px; color: #f1c40f; font-weight: bold; text-align: right; width: 26%;">⚡ 단기 (단타/스윙)</th>
                        <th style="padding: 8px 5px; color: #3498db; font-weight: bold; text-align: right; width: 26%;">📅 중기 (눌림목/추세)</th>
                        <th style="padding: 8px 5px; color: #2ecc71; font-weight: bold; text-align: right; width: 26%;">🚀 장기 (가치/매집)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px 5px; font-weight: bold; color: #ffffff;">🟢 매수 범위<br><span style="font-size:0.85em; font-weight:normal; color:#8b949e;">(Buy Zone)</span></td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #f1c40f; vertical-align: middle;">
                            {s_b_lower:,.0f} ~ {s_b_upper:,.0f} {price_suffix}<br><span style="font-size:0.8em; font-weight:normal; color:#8b949e;">돌파/단기눌림</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #3498db; vertical-align: middle;">
                            {m_b_lower:,.0f} ~ {m_b_upper:,.0f} {price_suffix}<br><span style="font-size:0.8em; font-weight:normal; color:#8b949e;">20일선/중기지지</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #2ecc71; vertical-align: middle;">
                            {l_b_lower:,.0f} ~ {l_b_upper:,.0f} {price_suffix}<br><span style="font-size:0.8em; font-weight:normal; color:#8b949e;">장기세력선/바닥</span>
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px 5px; font-weight: bold; color: #ffffff;">🎯 1차 목표가<br><span style="font-size:0.85em; font-weight:normal; color:#8b949e;">(대비 기대치)</span></td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #ffffff; vertical-align: middle;">
                            {s_t1:,.0f} {price_suffix}<br><span style="color:#f1c40f; font-size:0.9em;">{s_p_t1:+.1f}%</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #ffffff; vertical-align: middle;">
                            {m_t1:,.0f} {price_suffix}<br><span style="color:#3498db; font-size:0.9em;">{m_p_t1:+.1f}%</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #ffffff; vertical-align: middle;">
                            {l_t1:,.0f} {price_suffix}<br><span style="color:#2ecc71; font-size:0.9em;">{l_p_t1:+.1f}%</span>
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 10px 5px; font-weight: bold; color: #ffffff;">🔥 2차 목표가<br><span style="font-size:0.85em; font-weight:normal; color:#8b949e;">(대비 기대치)</span></td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #ffffff; vertical-align: middle;">
                            {s_t2:,.0f} {price_suffix}<br><span style="color:#f1c40f; font-size:0.9em;">{s_p_t2:+.1f}%</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #ffffff; vertical-align: middle;">
                            {m_t2:,.0f} {price_suffix}<br><span style="color:#3498db; font-size:0.9em;">{m_p_t2:+.1f}%</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #ffffff; vertical-align: middle;">
                            {l_t2:,.0f} {price_suffix}<br><span style="color:#2ecc71; font-size:0.9em;">{l_p_t2:+.1f}%</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 5px; font-weight: bold; color: #ffffff;">🚨 최종 손절가<br><span style="font-size:0.85em; font-weight:normal; color:#8b949e;">(Risk Cut)</span></td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e74c3c; vertical-align: middle;">
                            {s_sl:,.0f} {price_suffix}<br><span style="font-size:0.9em;">{s_p_sl:+.1f}%</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e74c3c; vertical-align: middle;">
                            {m_sl:,.0f} {price_suffix}<br><span style="font-size:0.9em;">{m_p_sl:+.1f}%</span>
                        </td>
                        <td style="padding: 10px 5px; text-align: right; font-weight: bold; color: #e74c3c; vertical-align: middle;">
                            {l_sl:,.0f} {price_suffix}<br><span style="font-size:0.9em;">{l_p_sl:+.1f}%</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div style="margin-top: 15px; background: rgba(255,255,255,0.02); border-radius: 6px; padding: 12px; border: 1px dashed rgba(255,255,255,0.05);">
            <p style="margin: 0; font-size: 0.78em; color: #8b949e; line-height: 1.5;">
                💡 <b>투자 성향별 매매법:</b><br>
                1. <b>단기(⚡)</b>: 현재 강력한 수급에 바로 탑승하되, <b>손절선(-4~-5%)을 칼같이 지켜야</b> 고점에 물리지 않는 빠른 단타 매매 영역입니다.<br>
                2. <b>중기(📅)</b>: 20일선 및 골드라인 부근까지 주가가 <b>차분히 조정을 줄 때 눌림목 진입</b>하여 전고점 1차/2차 목표가를 스윙으로 노리는 안정적인 영역입니다.<br>
                3. <b>장기(🚀)</b>: 세력의 장기 바닥 매집선 부근에서 분할 매수하여 <b>장기적 대세 상승 랠리(목표가 +25~+50% 이상)를 모아가는</b> 가치/매집 투자 영역입니다.
            </p>
        </div>
    </div>
    """
    # 마크다운 파서가 줄바꿈/들여쓰기를 코드 블록으로 잘못 오해하여 텍스트로 노출하는 문제를 100% 원천 해결하기 위해,
    # 공백과 줄바꿈을 완벽히 압축한 단 한 줄의 단일 HTML 문자열로 변환하여 리턴합니다.
    minified_html = " ".join([line.strip() for line in html.splitlines() if line.strip()])
    return minified_html

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
tab_scan, tab_portfolio, tab_dict = st.tabs(["🔍 종목 스캔", "⭐ 포트폴리오", "📚 주도테마백과사전"])

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
                
                # [신규] 실시간 추천 거래 가이드라인 카드 연동
                st.markdown(render_trading_price_guide(s_data['symbol'], s_data['market_type']), unsafe_allow_html=True)
                
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
                    key=f"table_{current_market}_{selected_strategy_name}_{len(df_display)}"
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
                    
                    # [신규] 실시간 추천 거래 가이드라인 카드 연동
                    st.markdown(render_trading_price_guide(selected_symbol, current_market), unsafe_allow_html=True)
                    
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
        with st.expander(f"📤 필터링 결과 공유 및 리포트 내보내기 ({len(df_filtered)}개 종목)", expanded=False):
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
                
                # [개선] 셀 배경색(styling)은 Streamlit 버그(removeChild)를 유발하므로, 이모지를 활용해 직관적인 색상을 부여합니다.
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
                            
                            # [신규] 실시간 추천 거래 가이드라인 카드 연동
                            st.markdown(render_trading_price_guide(selected_symbol, m_key), unsafe_allow_html=True)
                
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
    
# --- [주도테마백과사전 & 주식 쉐도잉 탭] ---
with tab_dict:
    st.markdown("### 📚 주도주·테마 백과사전 & 주식 쉐도잉")
    st.caption("유튜브 영상(RhMRtXb_95E)에 수록된 '주식 쉐도잉' 및 '나만의 테마/종목 DB 훈련'을 보조하는 디지털 도구입니다.")
    
    # 1. 데이터 불러오기
    shadow_data = load_shadowing_data()
    
    # [신규] 실시간 시장 주도 테마 자동 반영 엔진 UI 배치
    st.markdown("##### ⚡ 실시간 주도 테마 자동 동기화 엔진")
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.08) 0%, rgba(16, 20, 28, 0.95) 100%) !important;
        border: 1px solid rgba(88, 166, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    ">
        <span style="font-size: 0.9em; font-weight: bold; color: #58a6ff !important;">📢 실시간 자동화 안내</span>
        <p style="margin: 6px 0 0 0; color: #adbac7 !important; font-size: 0.85em; line-height: 1.5;">
            <b>상승률 15% 이상 & 거래대금 500억 이상</b> 터진 한국 시장(KRX)의 당일 핵심 주도주들을 실시간으로 파싱하고 
            StockScanner 엔진으로 기술 점수와 전문가 매매 신호를 종합 분석하여 <b>백과사전 테마와 쉐도잉 일지에 자동으로 누적 병합</b>합니다. (기준 미달 시 300억으로 자동 완화 적용)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_sync = st.columns([3, 1])
    with col_sync[0]:
        st.caption("※ 장 마감 후 또는 장중에 실행하시면 오늘 실시간으로 터진 뜨거운 주도주가 즉시 캘린더와 차트에 축적됩니다.")
    with col_sync[1]:
        if st.button("🔄 실시간 데이터 자동 반영", type="primary", use_container_width=True):
            with st.spinner("실시간 한국 시장(KRX) 주도주 분석 및 백과사전 동기화 중..."):
                success, msg = sync_realtime_shadowing_data(scanner)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
    # 서브 탭 구성
    sub_dict_tab, sub_shadow_tab = st.tabs(["📖 테마 백과사전", "📝 주식 쉐도잉 일지"])
    
    # 2. 테마 백과사전 탭
    with sub_dict_tab:
        st.markdown("#### 📖 실시간 동기화 테마 리스트")
        st.write("주도주 조건이 만족되어 백과사전에 자동으로 등록 및 업데이트된 테마들입니다.")
        
        for entry in shadow_data.get("dictionary", []):
            st.markdown(f"""
            <div style="
                background-color: rgba(255,255,255,0.02) !important;
                border: 1px solid rgba(255,255,255,0.05) !important;
                border-radius: 8px !important;
                padding: 12px !important;
                margin-bottom: 12px !important;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:bold; font-size:1.05em; color:#f1c40f;">🏷️ {entry.get('theme')}</span>
                    <span style="font-size:0.78em; color:#8b949e;">최종 업데이트: {entry.get('last_updated')}</span>
                </div>
                <p style="margin:5px 0; font-size:0.88em; color:#adbac7;">📈 <b>주도 종목:</b> <span style="color:#58a6ff; font-weight:bold;">{entry.get('stocks')}</span></p>
                <p style="margin:5px 0 0 0; font-size:0.82em; color:#8b949e; line-height:1.4;">💡 <b>상세 원인:</b> {entry.get('reason')}</p>
            </div>
            """, unsafe_allow_html=True)
            
    # 3. 주식 쉐도잉 일지 탭
    with sub_shadow_tab:
        st.markdown("#### 📝 당일 핵심 주도 테마 쉐도잉 일지")
        st.write("매일 퇴근 후 장 마감 데이터 중 가장 강했던 주도 섹터와 종목의 유입 이유를 기록하고 훈련하는 일지입니다.")
        
        # 쉐도잉 일지 신규 작성 Form
        with st.expander("✍️ 오늘자 주도주 쉐도잉 일지 수동 작성", expanded=False):
            with st.form("shadow_form", clear_on_submit=True):
                s_date = st.date_input("날짜").strftime('%Y-%m-%d')
                s_keyword = st.text_input("핵심 키워드 (예: 반도체, 초전도체)", placeholder="핵심 테마나 재료 입력")
                s_stocks = st.text_input("주도 종목 (예: 한미반도체, 제주반도체)", placeholder="콤마(,)로 구분하여 입력")
                s_reason = st.text_area("주도 이유 및 장중 흐름", placeholder="상승 이유, 뉴스, 특징 거래대금 흐름 등 기록")
                
                if st.form_submit_button("💾 일지 기록 저장"):
                    if s_keyword and s_stocks:
                        shadow_data["records"].insert(0, {
                            "date": s_date,
                            "keyword": s_keyword,
                            "stocks": s_stocks,
                            "reason": s_reason
                        })
                        if save_shadowing_data(shadow_data):
                            st.success("오늘의 쉐도잉 일지가 성공적으로 기록되었습니다!")
                            st.rerun()
                    else:
                        st.warning("키워드와 주도 종목는 필수 입력 항목입니다.")
                        
        # 기록된 일지 출력
        for record in shadow_data.get("records", []):
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
                <p style="margin:5px 0; font-size:0.88em; color:#adbac7;">🔥 <b>주요 급등주:</b> {record.get('stocks')}</p>
                <p style="margin:5px 0 0 0; font-size:0.82em; color:#8b949e; line-height:1.4;">📝 <b>상세 흐름 & 뉴스:</b> {record.get('reason')}</p>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.divider()
st.caption(f"Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: FinanceDataReader, yfinance")
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator
from ta.volatility import BollingerBands

def add_indicators(df):
    """이동평균선, RSI, OBV, MFI 등 지표를 DataFrame에 추가합니다."""
    df['MA20'] = SMAIndicator(df['Close'], window=20).sma_indicator()
    df['MA50'] = SMAIndicator(df['Close'], window=50).sma_indicator()
    df['MA200'] = SMAIndicator(df['Close'], window=200).sma_indicator()
    df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()
    
    # 세력 수급 지표 추가 (ta라이브러리 사용)
    df['OBV'] = OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
    df['MFI'] = MFIIndicator(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14).money_flow_index()
    
    # 볼린저 밴드 추가 (급등 전조용)
    bb = BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    df['BB_Mid'] = bb.bollinger_mavg()
    # 밴드폭 (Bandwidth) 계산
    df['BB_Width'] = (df['BB_High'] - df['BB_Low']) / df['BB_Mid']
    
    # 주식단테 장기 이평선 추가
    df['MA112'] = SMAIndicator(df['Close'], window=112).sma_indicator()
    df['MA224'] = SMAIndicator(df['Close'], window=224).sma_indicator()
    
    # 홍인기 매매법용 이평선
    df['MA5'] = SMAIndicator(df['Close'], window=5).sma_indicator()
    df['MA10'] = SMAIndicator(df['Close'], window=10).sma_indicator()
    df['MA60'] = SMAIndicator(df['Close'], window=60).sma_indicator()
    df['MA120'] = SMAIndicator(df['Close'], window=120).sma_indicator()
    
    # 오로라 검색기용 엔벨로프 (20, 20)
    df['Env_Mid'] = df['MA20']
    df['Env_Upper'] = df['Env_Mid'] * 1.20
    df['Env_Lower'] = df['Env_Mid'] * 0.80
    
    # 퓨처온 이슬 멘토 - 골드라인 (EMA 33)
    df['GoldLine'] = df['Close'].ewm(span=33, adjust=False).mean()
    
    # 퓨처온 세력선 (Whale Line) - EMA 448 (장기 추세의 기준)
    df['WhaleLine'] = df['Close'].ewm(span=448, adjust=False).mean()
    
    # 수평 지지/저항선 자동 감지 (최근 120일 기준)
    horizontal_levels = find_horizontal_levels(df)
    
    return df, horizontal_levels

def find_horizontal_levels(df, window=120):
    """최근 데이터에서 주요 수평 지지/저항 가격대를 추출합니다."""
    if len(df) < window: return []
    
    recent_df = df.iloc[-window:]
    first_price = recent_df['Close'].iloc[0]
    if first_price > 100000: round_val = -3 # 1000원 단위
    elif first_price > 10000: round_val = -2 # 100원 단위
    elif first_price > 1000: round_val = -1 # 10원 단위
    else: round_val = 0 # 1원 단위
    
    levels = []
    for i in range(2, len(recent_df) - 2):
        if recent_df['High'].iloc[i] > recent_df['High'].iloc[i-1] and \
           recent_df['High'].iloc[i] > recent_df['High'].iloc[i-2] and \
           recent_df['High'].iloc[i] > recent_df['High'].iloc[i+1] and \
           recent_df['High'].iloc[i] > recent_df['High'].iloc[i+2]:
            levels.append(round(recent_df['High'].iloc[i], round_val))
        if recent_df['Low'].iloc[i] < recent_df['Low'].iloc[i-1] and \
           recent_df['Low'].iloc[i] < recent_df['Low'].iloc[i-2] and \
           recent_df['Low'].iloc[i] < recent_df['Low'].iloc[i+1] and \
           recent_df['Low'].iloc[i] < recent_df['Low'].iloc[i+2]:
            levels.append(round(recent_df['Low'].iloc[i], round_val))
    
    if not levels: return []
    
    from collections import Counter
    counts = Counter(levels)
    current_price = df['Close'].iloc[-1]
    valid_ranges = [l for l, c in counts.most_common(10) if 0.7 * current_price < l < 1.3 * current_price]
    
    return sorted(valid_ranges[:5])

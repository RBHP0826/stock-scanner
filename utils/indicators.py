import pandas as pd
import numpy as np

def add_indicators(df):
    """이동평균선, RSI, OBV, MFI 등 지표를 DataFrame에 추가합니다."""
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['MA200'] = df['Close'].rolling(window=200).mean()
    
    # RSI 계산 (Wilder's Smoothing 방식과 동일하도록 ewm 사용)
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down.replace(0, 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 세력 수급 지표 추가 (OBV)
    direction = np.sign(df['Close'].diff()).fillna(0)
    df['OBV'] = (direction * df['Volume']).cumsum()
    
    # MFI 계산
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    price_diff = typical_price.diff()
    
    pos_flow = money_flow.where(price_diff > 0, 0.0)
    neg_flow = money_flow.where(price_diff < 0, 0.0)
    
    pos_mf14 = pos_flow.rolling(window=14).sum()
    neg_mf14 = neg_flow.rolling(window=14).sum()
    
    mr = pos_mf14 / neg_mf14.replace(0, 1e-10)
    df['MFI'] = 100 - (100 / (1 + mr))
    
    # 볼린저 밴드 추가
    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std(ddof=0)
    df['BB_High'] = df['BB_Mid'] + 2 * std
    df['BB_Low'] = df['BB_Mid'] - 2 * std
    # 밴드폭 (Bandwidth) 계산
    df['BB_Width'] = (df['BB_High'] - df['BB_Low']) / df['BB_Mid']
    
    # 주식단테 장기 이평선 추가
    df['MA112'] = df['Close'].rolling(window=112).mean()
    df['MA224'] = df['Close'].rolling(window=224).mean()
    
    # 홍인기 매매법용 이평선
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    
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

from ta.trend import SMAIndicator

def check_accumulation_bar(df):
    """대량 거래를 동반한 매집봉(윗꼬리 캔들)을 분석합니다."""
    if len(df) < 20: return False, []
    
    last = df.iloc[-1]
    avg_vol = df['Volume'].iloc[-21:-1].mean()
    
    is_big_vol = last['Volume'] > avg_vol * 3.0
    body = abs(last['Close'] - last['Open'])
    upper_shadow = last['High'] - max(last['Close'], last['Open'])
    
    if is_big_vol and upper_shadow > body * 1.5:
        return True, ["세력 매집봉 포착 (대량거래 윗꼬리)"]
    return False, []

def check_smart_money_flow(df):
    """OBV 및 MFI를 활용한 자금 유입 흐름을 분석합니다."""
    if len(df) < 20: return False, []
    
    reasons = []
    obv_trend = df['OBV'].iloc[-1] > df['OBV'].iloc[-10]
    price_trend = df['Close'].iloc[-1] <= df['Close'].iloc[-10] * 1.02
    
    if obv_trend and price_trend:
        reasons.append("세력 매집 신호 (OBV 상승 다이버전스)")
        
    if df['MFI'].iloc[-1] > 60 and df['MFI'].iloc[-5] < 40:
        reasons.append("자금 유입 급증 (MFI 돌파)")
        
    return len(reasons) > 0, reasons

def check_dante_bowl(df):
    """주식단테의 '밥그릇 패턴'을 분석합니다."""
    if len(df) < 224: return False, []
    
    close = df['Close']
    high_1y = close.iloc[-224:-112].max() if len(df) >= 224 else close.iloc[0:-112].max()
    low_recent = close.iloc[-112:].min()
    current_price = close.iloc[-1]
    
    reasons = []
    if low_recent < high_1y * 0.7:
        avg_recent = close.iloc[-60:].mean()
        if abs(current_price - avg_recent) / avg_recent < 0.1:
            if current_price > df['MA112'].iloc[-1] and close.iloc[-5] <= df['MA112'].iloc[-5]:
                reasons.append("밥그릇 3번 자리 (112선 돌파)")
                return True, reasons
            elif current_price > df['MA112'].iloc[-1]:
                reasons.append("밥그릇 바닥 다지기 후 상단 안착")
                return True, reasons
    return False, []

def check_dante_256(df):
    """주식단테의 '256 기법'을 분석합니다."""
    ma5 = SMAIndicator(df['Close'], window=5).sma_indicator()
    ma20 = df['MA20']
    ma60 = SMAIndicator(df['Close'], window=60).sma_indicator()
    
    current_price = df['Close'].iloc[-1]
    
    cond2 = (ma20.iloc[-1] > ma20.iloc[-5])
    cond5 = (ma5.iloc[-1] > ma20.iloc[-1])
    cond6 = (current_price > ma60.iloc[-1])
    
    if cond2 and cond5 and cond6:
        return True, ["256 기법 (5/20/60 추세 정배열 초입)"]
    return False, []

def check_gozack_box(df):
    """고쨱짹의 '박스권 돌파 & 거봉' 분석"""
    close = df['Close']
    vol = df['Volume']
    
    box_top = close.iloc[-21:-1].max()
    current_price = close.iloc[-1]
    
    avg_vol = vol.iloc[-20:-1].mean()
    is_big_vol = vol.iloc[-1] > avg_vol * 2.5
    
    if current_price > box_top and is_big_vol:
        return True, ["고쨱짹 박스권 돌파 + 거봉(수급폭발)"]
    return False, []

def check_hongingi(df):
    """대왕개미 홍인기의 '대장주 첫 장대양봉 & 끼' 분석"""
    if len(df) < 120: return False, []
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    vol = df['Volume']
    close = df['Close']
    
    reasons = []
    change_rate = (last['Close'] - prev['Close']) / prev['Close'] * 100
    avg_vol_20 = vol.iloc[-21:-1].mean()
    is_vol_surge = last['Volume'] > avg_vol_20 * 3.0
    high_60 = close.iloc[-61:-1].max()
    is_new_high = last['Close'] > high_60
    
    if change_rate >= 7.0 and is_vol_surge and is_new_high:
        reasons.append("홍인기 D+0: 첫 장대양봉 + 거래량 폭발 + 60일 신고가 돌파")
        
    has_talent = False
    for i in range(-60, -1):
        if i < -len(df): continue
        day_change = (df['High'].iloc[i] - df['Low'].iloc[i]) / df['Low'].iloc[i] * 100
        if day_change > 20.0 or (df['Close'].iloc[i] / df['Close'].iloc[i-1] > 1.25):
            has_talent = True
            break
    
    if has_talent:
        reasons.append("종목의 '끼' 확인 (과거 급등 이력 보유)")
        
    ma5 = df['MA5'].iloc[-1]
    ma20 = df['MA20'].iloc[-1]
    ma60 = df['MA60'].iloc[-1]
    
    if ma5 > ma20 > ma60:
        reasons.append("정배열 추세 (5 > 20 > 60)")

    if (change_rate >= 7.0 and is_vol_surge) or (has_talent and ma5 > ma20):
        return True, reasons
        
    return False, []

def check_ap_investment(df):
    """AP투자연구소 김용재 소장의 '시가/고가 돌파 & 수급' 분석"""
    if len(df) < 20: return False, []
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    vol = df['Volume']
    
    reasons = []
    is_break_open = last['Close'] > last['Open']
    is_break_prev_high = last['Close'] > prev['High']
    high_5pd = df['High'].iloc[-6:-1].max()
    is_break_5pd = last['Close'] > high_5pd
    
    avg_vol_20 = vol.iloc[-21:-1].mean()
    is_vol_surge = (last['Volume'] > prev['Volume'] * 3.0) or (last['Volume'] > avg_vol_20 * 2.0)
    
    ma5 = df['MA5'].iloc[-1]
    ma20 = df['MA20'].iloc[-1]
    
    is_ma_ok = ma5 >= ma20
    is_ma_dense = abs(ma5 - ma20) / ma20 < 0.03
    
    if (is_break_open and is_break_prev_high and is_vol_surge):
        if is_break_5pd:
            reasons.append("AP-김용재: 최근 5일 고점 돌파 (강력한 추세 전환)")
        else:
            reasons.append("AP-김용재: 당일 시가 및 전일 고점 돌파")
        
        reasons.append(f"수급 확인: 거래량 전일비 300%+ 또는 평균비 200%+ 폭증")
        
        if is_ma_ok:
            reasons.append("이평선 조건 충족 (MA5 >= MA20)")
        if is_ma_dense:
            reasons.append("이평선 밀집 구간 돌파 (에너지 응축 후 분출)")
            
        return True, reasons
        
    return False, []

def check_aurora_signal(df):
    """오로라 검색기: 엔벨로프 하단 낙폭과대 후 변곡점(반등) 포착"""
    if len(df) < 20: return False, []
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi = last['RSI']
    
    reasons = []
    is_aurora = False
    
    is_near_lower = last['Close'] <= last['Env_Lower'] * 1.03
    is_below_lower = last['Close'] <= last['Env_Lower']
    
    is_reversal = last['Close'] > last['Open']
    is_rsi_oversold = rsi < 35
    is_vol_bump = last['Volume'] > prev['Volume'] * 1.2
    
    if is_near_lower and is_reversal:
        is_aurora = True
        if is_below_lower:
            reasons.append("✨ 오로라: 엔벨로프 하단 과매도 구간 돌파 (강력 반등 시그널)")
        else:
            reasons.append("✨ 오로라: 엔벨로프 하단 지지 및 반등 변곡점 포착")
        
        if is_rsi_oversold:
            reasons.append("RSI 과매도권 탈출 모멘텀 확인")
        if is_vol_bump:
            reasons.append("반등 수급 유입 확인 (거래량 증가)")
            
    return is_aurora, reasons

def check_futureon_isle(df):
    """퓨처온 이슬 멘토: 골드라인(EMA 33) 매매법"""
    if len(df) < 33: return False, []
    
    last = df.iloc[-1]
    prev = df.iloc[-5]
    
    is_above = last['Close'] > last['GoldLine']
    is_sloping_up = last['GoldLine'] > prev['GoldLine']
    
    if is_above and is_sloping_up:
        return True, ["🏆 이슬 멘토: 골드라인(EMA 33) 지지 및 추세 안착"]
    return False, []

def check_futureon_shintae(df):
    """퓨처온 신태 멘토: NS밴드(볼린저 하단) 지지 및 수급 분석"""
    if len(df) < 20: return False, []
    
    last = df.iloc[-1]
    avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
    
    is_supported = last['Low'] <= last['BB_Low'] * 1.02
    is_rebound = last['Close'] > last['Open']
    is_vol_ok = last['Volume'] > avg_vol * 1.2
    
    if is_supported and is_rebound and is_vol_ok:
        return True, ["🏆 신태 멘토: NS밴드 하단 지지 및 수급 유입 확인"]
    return False, []

def check_futureon_juns(df):
    """퓨처온 준S 멘토: 20일 기준선 지지 및 3파동(저점 상승) 확인"""
    if len(df) < 60: return False, []
    
    lows = []
    for i in range(3):
        idx = - (i * 20) - 1
        if idx < -len(df): break
        lows.append(df['Low'].iloc[max(-len(df), idx-10) : idx].min())
    
    is_wave_up = len(lows) >= 2 and lows[0] > lows[1]
    
    last = df.iloc[-1]
    is_above_base = last['Close'] > last['MA20']
    
    if is_above_base and is_wave_up:
        return True, ["🏆 준S 멘토: 20일 기준선 상단 및 우상향 파동 확인"]
    return False, []

def check_day_trading_signal(df):
    """실시간 데이매매(Day Trading)에 최적화된 종목을 필터링합니다."""
    if len(df) < 20: return False, []
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    vol = df['Volume']
    
    reasons = []
    transaction_amount = last['Close'] * last['Volume']
    is_high_liquidity = transaction_amount >= 5000000000
    
    is_bullish = last['Close'] > last['Open']
    open_gap = (last['Open'] - prev['Close']) / prev['Close'] * 100
    
    is_break_prev_high = last['Close'] > prev['High']
    
    avg_vol_20 = vol.iloc[-21:-1].mean()
    is_vol_surge = (last['Volume'] > prev['Volume'] * 2.5) or (last['Volume'] > avg_vol_20 * 2.0)
    
    if is_high_liquidity and is_bullish and is_vol_surge:
        if is_break_prev_high:
            reasons.append("🌞 데이매매: 전일 고가 돌파 및 당일 주도주 포착")
        else:
            reasons.append("🌞 데이매매: 수급 유입 및 시가 대비 강세 유지")
            
        if open_gap > 0:
            reasons.append(f"갭 상승({open_gap:.1f}%) 후 추가 상승 모멘텀")
        
        reasons.append(f"추정 거래대금 {transaction_amount/100000000:.1f}억 돌파")
        
        return True, reasons
        
    return False, []

def check_katch_signal(df):
    """키움증권 캐치(KATCH) 자동매매 조건검색식 로직을 분석합니다."""
    if len(df) < 60: return False, []
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    reasons = []
    
    ma5 = df['MA5'].iloc[-1]
    ma20 = df['MA20'].iloc[-1]
    ma60 = df['MA60'].iloc[-1]
    is_aligned = ma5 > ma20 > ma60
    
    is_vol_surge = last['Volume'] > prev['Volume'] * 2.0
    
    high_close_20 = df['Close'].iloc[-21:-1].max()
    is_new_high = last['Close'] > high_close_20
    
    transaction_amount = last['Close'] * last['Volume']
    is_liquid = transaction_amount >= 5000000000
    
    is_up_from_open = last['Close'] > last['Open']
    
    if is_aligned and is_vol_surge and is_new_high and is_liquid and is_up_from_open:
        reasons.append("🏆 캐치(KATCH): 이평선 정배열 + 수급 폭발 + 20일 신고가 돌파")
        reasons.append(f"당일 거래대금 약 {transaction_amount/100000000:.1f}억 (주도주급 수급)")
        return True, reasons
        
    return False, []

def check_fvg_mitigation(df):
    """
    최근 발생한 Fair Value Gap(FVG) 갭 구간으로 주가가 되돌아와 지지(Mitigation)받는 상태를 포착합니다.
    """
    if len(df) < 5: return False, [], None
    
    # 최근 10일 이내에 FVG가 생성되었는지 역탐색
    for i in range(-10, -2):
        if i < -len(df) + 2: continue
        c1 = df.iloc[i-2]
        c2 = df.iloc[i-1]
        c3 = df.iloc[i]
        
        # 상승 FVG 조건 (Imbalance Gap)
        if c1['High'] < c3['Low']:
            fvg_low = float(c1['High'])
            fvg_high = float(c3['Low'])
            
            # 현재 종가(최근 일봉)가 이 FVG 구간 안에 터치하거나 걸쳐 있는지 확인
            last_close = float(df['Close'].iloc[-1])
            last_low = float(df['Low'].iloc[-1])
            
            # 갭이 아직 완전히 깨지지(Invalidated) 않았고, 현재 갭 지지 테스트 중인 경우
            if last_low <= fvg_high and last_close >= fvg_low * 0.99:
                # 갭 하단을 완전히 깨지 않은 지지 흐름
                entry = fvg_high
                stop = fvg_low * 0.97
                target = fvg_high * 1.10 # 10% 단기 스윙 목표
                
                # FVG 형성 이후의 최근 최고가를 가져올 수 있다면 타겟으로 설정
                recent_high = float(df['High'].iloc[i:].max())
                if recent_high > entry * 1.03:
                    target = recent_high
                    
                msg = [f"상승 FVG(공정가치갭) 되돌림 지지 포착 (갭구간: {int(fvg_low):,}원 ~ {int(fvg_high):,}원)"]
                return True, msg, {"entry": entry, "stop": stop, "target": target, "type": "FVG"}
                
    return False, [], None

def check_turtle_soup_long(df):
    """
    가짜 하방 돌파 후 급반등하는 터틀 수프(Turtle Soup) 매수 타점을 포착합니다.
    최근 20일 최저가를 일시 이탈했다가 다시 복귀한 경우입니다.
    """
    if len(df) < 22: return False, [], None
    
    # 20일 전부터 어제까지의 최저가 구하기
    prev_20_low = float(df['Low'].iloc[-21:-1].min())
    
    last = df.iloc[-1]
    
    # 조건: 오늘 최저가가 20일 최저가보다 낮았으나(하방 돌파 시도), 
    # 종가는 20일 최저가 위로 복귀하여 마감
    if float(last['Low']) < prev_20_low and float(last['Close']) > prev_20_low:
        entry = float(last['Close'])
        stop = float(last['Low']) * 0.98 # 꼬리 끝 이탈 시 손절
        
        # 목표가는 최근 20일 고점 혹은 피보나치 되돌림 중간 지점
        prev_20_high = float(df['High'].iloc[-21:-1].max())
        target = (entry + prev_20_high) / 2.0
        
        msg = ["SMC-Turtle Soup: 20일 최저가 가짜 하방 돌파(유동성 휩쓸기) 후 복귀 매수 시그널"]
        return True, msg, {"entry": entry, "stop": stop, "target": target, "type": "Turtle Soup"}
        
    return False, [], None

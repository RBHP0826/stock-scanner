import FinanceDataReader as fdr
import yfinance as yf
import pyupbit
import pandas as pd
import datetime
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator
from ta.volatility import BollingerBands

class StockScanner:
    def __init__(self):
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        # 분석을 위해 1년 정도의 데이터가 필요함
        self.start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')

    def get_krx_symbols(self):
        """코스피, 코스닥 종목 리스트를 가져옵니다. (클라우드 환경 호환성 강화)"""
        try:
            # Streamlit Cloud 등에서는 KOSPI(Marcap Github) 차단 이슈가 잦으므로 KRX로 통합 조회
            df_krx = fdr.StockListing('KRX')
            
            # Code 컬럼이 없는 경우 대비 (버전 호환)
            if 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
                df_krx['Code'] = df_krx['Symbol']
                
            return df_krx
        except Exception as e:
            # 실패 시 예비 수단 (KIND 직접 조회)
            print(f"KRX 조회 실패, 예비 수단 가동: {e}")
            df_krx_desc = fdr.StockListing('KRX-DESC')
            if 'Code' not in df_krx_desc.columns and 'Symbol' in df_krx_desc.columns:
                df_krx_desc['Code'] = df_krx_desc['Symbol']
            return df_krx_desc

    def get_us_symbols(self):
        """S&P 500 주요 종목 리스트를 가져옵니다."""
        try:
            df_sp500 = fdr.StockListing('S&P500')
            return df_sp500
        except:
            return pd.DataFrame({'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK-B', 'UNH', 'JNJ'],
                                 'Name': ['Apple', 'Microsoft', 'Alphabet', 'Amazon', 'Tesla', 'NVIDIA', 'Meta', 'Berkshire', 'UnitedHealth', 'J&J']})

    def get_coin_symbols(self):
        """업비트 원화 마켓의 주요 코인 리스트를 가져옵니다."""
        try:
            tickers = pyupbit.get_tickers(fiat="KRW")
            # 단순히 티커 리스트를 데이터프레임으로 변환
            return pd.DataFrame({'Symbol': tickers, 'Name': [t.split("-")[1] for t in tickers]})
        except:
            return pd.DataFrame({'Symbol': ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-ADA'], 
                                 'Name': ['BTC', 'ETH', 'XRP', 'SOL', 'ADA']})

    def get_symbol_name(self, symbol, market='KR'):
        """종목 코드를 기반으로 종목명을 찾아 반환합니다."""
        try:
            if market == 'KR':
                # 캐싱된 리스트에서 찾기 (효율성)
                if not hasattr(self, '_krx_list'):
                    self._krx_list = self.get_krx_symbols()
                
                # 'Symbol' 또는 'Code' 컬럼 대응
                code_col = 'Code' if 'Code' in self._krx_list.columns else 'Symbol'
                match = self._krx_list[self._krx_list[code_col] == symbol]
                if not match.empty:
                    return match.iloc[0]['Name']
                    
            elif market == 'US':
                if not hasattr(self, '_us_list'):
                    self._us_list = self.get_us_symbols()
                match = self._us_list[self._us_list['Symbol'] == symbol]
                if not match.empty:
                    return match.iloc[0]['Name']
                # 보조 검색 (yfinance)
                ticker = yf.Ticker(symbol)
                return ticker.info.get('longName', symbol)
                
            elif market == 'COIN':
                if not hasattr(self, '_coin_list'):
                    self._coin_list = self.get_coin_symbols()
                match = self._coin_list[self._coin_list['Symbol'] == symbol]
                if not match.empty:
                    return match.iloc[0]['Name']
        except:
            pass
        return symbol

    def find_symbol_by_name(self, name):
        """종목명을 기반으로 심볼과 시장 코드를 찾아 반환합니다."""
        if not name: return None, None
        name_upper = name.upper()
        
        # 1. 한국 시장 검색
        if not hasattr(self, '_krx_list'):
            self._krx_list = self.get_krx_symbols()
        kr_match = self._krx_list[self._krx_list['Name'].str.upper().str.contains(name_upper, na=False)]
        if not kr_match.empty:
            code_col = 'Code' if 'Code' in kr_match.columns else 'Symbol'
            return kr_match.iloc[0][code_col], 'KR'
            
        # 2. 미국 시장 검색
        if not hasattr(self, '_us_list'):
            self._us_list = self.get_us_symbols()
        us_match = self._us_list[self._us_list['Name'].str.upper().str.contains(name_upper, na=False)]
        if not us_match.empty:
            return us_match.iloc[0]['Symbol'], 'US'
            
        # 3. 코인 시장 검색
        if not hasattr(self, '_coin_list'):
            self._coin_list = self.get_coin_symbols()
        coin_match = self._coin_list[self._coin_list['Name'].str.upper().str.contains(name_upper, na=False)]
        if not coin_match.empty:
            return coin_match.iloc[0]['Symbol'], 'COIN'
            
        return None, None

    def analyze_stock(self, symbol, market='KR'):
        """개별 종목/코인의 기술적 지표를 분석하여 점수를 매깁니다."""
        try:
            if market == 'KR':
                df = fdr.DataReader(symbol, self.start_date)
            elif market == 'US':
                df = fdr.DataReader(symbol, self.start_date)
            elif market == 'COIN':
                # pyupbit는 count로 데이터를 가져옴 (1년치 대략 365개)
                df = pyupbit.get_ohlcv(symbol, interval="day", count=365)
                if df is not None:
                    # 컬럼명 통일 (upbit는 close, open 등 소문자)
                    df.columns = [c.capitalize() for c in df.columns]

            if df is None or len(df) < 200:
                return None

            # 지표 계산 로직 분리 (재사용 가능하도록)
            df = self.add_indicators(df)
            
            last_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            change_rate = ((last_price - prev_price) / prev_price) * 100
            
            last_rsi = df['RSI'].iloc[-1]
            last_ma50 = df['MA50'].iloc[-1]
            last_ma200 = df['MA200'].iloc[-1]
            
            # --- 점수 산출 로직 ---
            score = 0
            signals = []
            
            # A. 정배열 확인 (추세)
            if last_price > last_ma50 > last_ma200:
                score += 40
                signals.append("정배열 완만 상승 중")
            elif last_price > last_ma50:
                score += 20
                signals.append("단기 이평선 상단 위치")
                
            # B. RSI 모멘텀 (과매수 방지 및 상승력 확인)
            if 45 <= last_rsi <= 65:
                score += 30
                signals.append("안정적 상승 모멘텀 (RSI)")
            elif last_rsi < 45:
                score += 10
                signals.append("저점 매수 유효 구간")
                
            # C. 거래량 지표 (최근 5일 평균 vs 20일 평균)
            avg_vol_20 = df['Volume'].rolling(window=20).mean()
            current_vol = df['Volume'].rolling(window=5).mean()
            last_vol = df['Volume'].iloc[-1]
            prev_vol = df['Volume'].iloc[-2]
            
            if current_vol.iloc[-1] > avg_vol_20.iloc[-1] * 1.5:
                score += 30
                signals.append("수급 증가 (거래량 폭발)")

            # F. 급등 임박 (Surge Alarm) - 유튜브 전략 반영
            surge_signal = False
            surge_reasons = []
            
            # 1. 에너지 분출 (거래량 300% 이상 폭증)
            if last_vol > avg_vol_20.iloc[-1] * 2.5: # 대략 250%~300% 이상
                surge_signal = True
                surge_reasons.append("거래량 에너지 분출 (폭증)")
                score += 20
                
            # 2. 볼린저 밴드 수축 (Squeeze)
            # 최근 10일 중 최저 밴드폭이 현재와 비슷할 때 (응축 구간)
            min_width = df['BB_Width'].rolling(window=30).min().iloc[-1]
            if df['BB_Width'].iloc[-1] <= min_width * 1.1:
                surge_reasons.append("변동성 응축 (볼린저 밴드 수축)")
                score += 10
            
            # 3. 연속 양봉 (3일 연속 상승 캔들)
            if (df['Close'].iloc[-1] > df['Open'].iloc[-1] and 
                df['Close'].iloc[-2] > df['Open'].iloc[-2] and 
                df['Close'].iloc[-3] > df['Open'].iloc[-3]):
                surge_signal = True
                surge_reasons.append("3일 연속 상승 캔들 발현")
                score += 15

            if surge_signal:
                signals.append(f"🚀 급등 전조 신호: {' / '.join(surge_reasons)}")

            # D. 눌림목(Pullback) 포착 (매수 급소)
            is_pullback = False
            if last_price > last_ma200: # 우상향 종목 중
                # 최근에 MA20에 근접했거나 닿은 경우 (눌림목)
                if last_price <= df['MA20'].iloc[-1] * 1.02: # MA20 근처 (2% 이내)
                    score += 20
                    is_pullback = True
                    signals.append("추세 내 눌림목(Pullback) 포착")

            # E. 세력 수급 (Whale Money Flow) 분석
            whale_score = 0
            last_obv = df['OBV'].iloc[-1]
            prev_obv = df['OBV'].iloc[-5] # 5일 전과 비교
            last_mfi = df['MFI'].iloc[-1]
            
            # 1. OBV 우상향 (매집 확인)
            if last_obv > prev_obv:
                whale_score += 15
                signals.append("세력 매집 흔적 포착 (OBV 우상향)")
            
            # 2. MFI 자금 유입 (돈이 들어오는가)
            if last_mfi > 55:
                whale_score += 15
                signals.append("자금 유입 강세 (MFI)")
            elif last_mfi < 30:
                signals.append("바닥권 자금 유입 준비 중")
                
            score += whale_score

            # --- 액션(Action) 결정 ---
            action = "HOLD"
            action_desc = "관망"
            
            if score >= 70:
                action = "BUY"
                action_desc = "강력 매수" if is_pullback else "추격 매수 가능"
            elif score >= 50:
                action = "BUY"
                action_desc = "분할 매수 유효"
                
            if last_rsi >= 75:
                action = "SELL"
                action_desc = "과매수 익절 권장"
            elif last_price < df['MA20'].iloc[-1] and score < 40:
                action = "SELL"
                action_desc = "추세 이탈 우려 (매도/손절)"

            # G. 전문가 기법 통합 분석 (주식단테, 고쨱짹)
            dante_bowl, dante_bowl_msg = self.check_dante_bowl(df)
            if dante_bowl:
                score += 25
                signals.extend(dante_bowl_msg)
            
            dante_256, dante_256_msg = self.check_dante_256(df)
            if dante_256:
                score += 15
                signals.extend(dante_256_msg)
                
            gozack, gozack_msg = self.check_gozack_box(df)
            if gozack:
                score += 30
                signals.extend(gozack_msg)
                
            # H. 세력(Smart Money) 수급 분석
            acc_bar, acc_msg = self.check_accumulation_bar(df)
            if acc_bar:
                score += 20
                signals.extend(acc_msg)
                
            money_flow, flow_msg = self.check_smart_money_flow(df)
            if money_flow:
                score += 20
                signals.extend(flow_msg)

            # I. 대왕개미 홍인기 매매법 (대장주/장대양봉/끼)
            hongingi, hongingi_msg = self.check_hongingi(df)
            if hongingi:
                score += 35
                signals.extend(hongingi_msg)

            # J. AP투자연구소 김용재 소장 매매법 (시가돌파/수급/이평수렴)
            ap_inv, ap_msg = self.check_ap_investment(df)
            if ap_inv:
                score += 30
                signals.extend(ap_msg)

            # K. ✨ 오로라 검색기 (낙폭과대 변곡점 돌파)
            aurora_signal, aurora_reasons = self.check_aurora_signal(df)
            if aurora_signal:
                score += 40
                signals.extend(aurora_reasons)

            # L. 🏆 퓨처온(Future On) 멘토 군단 매매법
            isle, isle_msg = self.check_futureon_isle(df)
            shintae, shintae_msg = self.check_futureon_shintae(df)
            juns, juns_msg = self.check_futureon_juns(df)

            if isle: 
                score += 25
                signals.extend(isle_msg)
            if shintae: 
                score += 25
                signals.extend(shintae_msg)
            if juns: 
                score += 25
                signals.extend(juns_msg)

            return {
                'symbol': symbol,
                'current_price': last_price,
                'change_rate': change_rate,
                'rsi': last_rsi,
                'score': min(100, score), # 최대 100점 제한
                'signals': ", ".join(signals),
                'action': action,
                'action_desc': action_desc,
                'experts': {
                    'dante': dante_bowl or dante_256,
                    'gozack': gozack,
                    'hongingi': hongingi,
                    'ap_inv': ap_inv
                },
                'smart_money': {
                    'accumulation': acc_bar,
                    'money_flow': money_flow
                },
                'aurora': {
                    'signal': aurora_signal,
                    'reasons': aurora_reasons
                },
                'futureon': {
                    'isle': isle,
                    'shintae': shintae,
                    'juns': juns,
                    'reasons': isle_msg + shintae_msg + juns_msg
                }
            }
        except Exception as e:
            return None

    def add_indicators(self, df):
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
        self.horizontal_levels = self.find_horizontal_levels(df)
        
        # 퓨처온 신태 멘토 - NS밴드 (볼린저 상/하단 20, 2)
        # 이미 BB_High, BB_Low가 add_indicators에 있으므로 그대로 활용 가능
        
        return df

    def check_accumulation_bar(self, df):
        """대량 거래를 동반한 매집봉(윗꼬리 캔들)을 분석합니다."""
        if len(df) < 20: return False, []
        
        last = df.iloc[-1]
        avg_vol = df['Volume'].iloc[-21:-1].mean()
        
        # 1. 거래량이 평균 대비 3배 이상 터졌는가? (자금 유입)
        is_big_vol = last['Volume'] > avg_vol * 3.0
        
        # 2. 윗꼬리가 몸통보다 길고 종가가 고점 대비 밀렸는가?
        body = abs(last['Close'] - last['Open'])
        upper_shadow = last['High'] - max(last['Close'], last['Open'])
        
        if is_big_vol and upper_shadow > body * 1.5:
            return True, ["세력 매집봉 포착 (대량거래 윗꼬리)"]
        return False, []

    def check_smart_money_flow(self, df):
        """OBV 및 MFI를 활용한 자금 유입 흐름을 분석합니다."""
        if len(df) < 20: return False, []
        
        reasons = []
        # 1. OBV 상승 다이버전스 (주가는 횡보/하락인데 OBV는 상승)
        obv_trend = df['OBV'].iloc[-1] > df['OBV'].iloc[-10]
        price_trend = df['Close'].iloc[-1] <= df['Close'].iloc[-10] * 1.02 # 주가는 거의 그대로거나 하락
        
        if obv_trend and price_trend:
            reasons.append("세력 매집 신호 (OBV 상승 다이버전스)")
            
        # 2. MFI 자금 유입 (과매도 탈출 또는 급증)
        if df['MFI'].iloc[-1] > 60 and df['MFI'].iloc[-5] < 40:
            reasons.append("자금 유입 급증 (MFI 돌파)")
            
        return len(reasons) > 0, reasons

    def check_dante_bowl(self, df):
        """주식단테의 '밥그릇 패턴'을 분석합니다. (급락-횡보-추세전환)"""
        if len(df) < 224: return False, []
        
        close = df['Close']
        high_1y = close.iloc[-224:-112].max() if len(df) >= 224 else close.iloc[0:-112].max()
        low_recent = close.iloc[-112:].min()
        current_price = close.iloc[-1]
        
        reasons = []
        # 1. 밥그릇 1번(급락) & 2번(횡보) 확인
        # 고점 대비 충분히 하락했는가?
        if low_recent < high_1y * 0.7:
            # 최근 횡보 중인가? (저점 부근에서 노는 중)
            avg_recent = close.iloc[-60:].mean()
            if abs(current_price - avg_recent) / avg_recent < 0.1: # 10% 내외 횡보
                # 3. 밥그릇 3번(추세 전환) 확인 - 장기이평 돌파 시도
                if current_price > df['MA112'].iloc[-1] and close.iloc[-5] <= df['MA112'].iloc[-5]:
                    reasons.append("밥그릇 3번 자리 (112선 돌파)")
                    return True, reasons
                elif current_price > df['MA112'].iloc[-1]:
                    reasons.append("밥그릇 바닥 다지기 후 상단 안착")
                    return True, reasons
        return False, []

    def check_dante_256(self, df):
        """주식단테의 '256 기법'을 분석합니다. (5, 20, 60일선 배열)"""
        ma5 = df['MA20'].rolling(window=5).mean() # 대용치
        # 실제 5일선 계산
        ma5 = SMAIndicator(df['Close'], window=5).sma_indicator()
        ma20 = df['MA20']
        ma60 = SMAIndicator(df['Close'], window=60).sma_indicator()
        
        current_price = df['Close'].iloc[-1]
        
        # 2: 20일선 우상향 또는 5일선이 20일선 돌파
        cond2 = (ma20.iloc[-1] > ma20.iloc[-5])
        # 5: 5일선이 20일선 위에 위치
        cond5 = (ma5.iloc[-1] > ma20.iloc[-1])
        # 6: 60일선 돌파 중이거나 위에 있음
        cond6 = (current_price > ma60.iloc[-1])
        
        if cond2 and cond5 and cond6:
            return True, ["256 기법 (5/20/60 추세 정배열 초입)"]
        return False, []

    def check_gozack_box(self, df):
        """고쨱짹의 '박스권 돌파 & 거봉' 분석"""
        close = df['Close']
        vol = df['Volume']
        
        # 최근 20일간의 고점 (박스 상단)
        box_top = close.iloc[-21:-1].max()
        current_price = close.iloc[-1]
        
        # 거봉(거래량 폭발) 확인
        avg_vol = vol.iloc[-20:-1].mean()
        is_big_vol = vol.iloc[-1] > avg_vol * 2.5
        
        if current_price > box_top and is_big_vol:
            return True, ["고쨱짹 박스권 돌파 + 거봉(수급폭발)"]
        return False, []

    def check_hongingi(self, df):
        """대왕개미 홍인기의 '대장주 첫 장대양봉 & 끼' 분석"""
        if len(df) < 120: return False, []
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        vol = df['Volume']
        close = df['Close']
        
        reasons = []
        
        # 1. 첫 장대양봉 (D+0) 감지
        # 종가 상승률 7% 이상
        change_rate = (last['Close'] - prev['Close']) / prev['Close'] * 100
        # 거래량 폭증 (20일 평균 대비 300% 이상)
        avg_vol_20 = vol.iloc[-21:-1].mean()
        is_vol_surge = last['Volume'] > avg_vol_20 * 3.0
        # 60일 신고가 돌파 (몸통 기준)
        high_60 = close.iloc[-61:-1].max()
        is_new_high = last['Close'] > high_60
        
        if change_rate >= 7.0 and is_vol_surge and is_new_high:
            reasons.append("홍인기 D+0: 첫 장대양봉 + 거래량 폭발 + 60일 신고가 돌파")
            
        # 2. 종목의 '끼' 분석 (최근 3개월 내 급등 이력)
        # 3개월(약 60거래일) 내 20% 이상 급등한 적이 있는가?
        has_talent = False
        for i in range(-60, -1):
            if i < -len(df): continue
            day_change = (df['High'].iloc[i] - df['Low'].iloc[i]) / df['Low'].iloc[i] * 100
            if day_change > 20.0 or (df['Close'].iloc[i] / df['Close'].iloc[i-1] > 1.25): # 상한가 근처
                has_talent = True
                break
        
        if has_talent:
            reasons.append("종목의 '끼' 확인 (과거 급등 이력 보유)")
            
        # 3. 정배열 초입 확인
        ma5 = df['MA5'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        ma60 = df['MA60'].iloc[-1]
        ma120 = df['MA120'].iloc[-1]
        
        if ma5 > ma20 > ma60:
            reasons.append("정배열 추세 (5 > 20 > 60)")

        # 최종 판정: 장대양봉이거나(D+0) 끼가 있으면서 정배열인 경우
        if (change_rate >= 7.0 and is_vol_surge) or (has_talent and ma5 > ma20):
            return True, reasons
            
        return False, []

    def check_ap_investment(self, df):
        """AP투자연구소 김용재 소장의 '시가/고가 돌파 & 수급' 분석"""
        if len(df) < 20: return False, []
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        vol = df['Volume']
        
        reasons = []
        
        # 1. 시가 및 전일 고가 돌파 (Breakout)
        is_break_open = last['Close'] > last['Open']
        is_break_prev_high = last['Close'] > prev['High']
        # 최근 5일 최고가 돌파 확인
        high_5pd = df['High'].iloc[-6:-1].max()
        is_break_5pd = last['Close'] > high_5pd
        
        # 2. 거래량 폭증 (전일 대비 300% 이상 또는 20일 평균 대비 200% 이상)
        avg_vol_20 = vol.iloc[-21:-1].mean()
        is_vol_surge = (last['Volume'] > prev['Volume'] * 3.0) or (last['Volume'] > avg_vol_20 * 2.0)
        
        # 3. 이평선 조건 (5일선 >= 20일선) 및 이평선 밀집 확인
        ma5 = df['MA5'].iloc[-1]
        ma20 = df['MA20'].iloc[-1]
        ma60 = df['MA60'].iloc[-1]
        
        # 이평선 역배열 탈출 또는 정배열 초입
        is_ma_ok = ma5 >= ma20
        # 이평선 밀집도 (5일선과 20일선 차이가 3% 이내)
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

    def check_aurora_signal(self, df):
        """오로라 검색기: 엔벨로프 하단 낙폭과대 후 변곡점(반등) 포착"""
        if len(df) < 20: return False, []
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        rsi = last['RSI']
        
        reasons = []
        is_aurora = False
        
        # 1. 낙폭과대 조건 (가격이 엔벨로프 하한선 부근이거나 하회)
        # 하한선 3% 이내 접근 시 '준비', 하회 시 '포착'
        is_near_lower = last['Close'] <= last['Env_Lower'] * 1.03
        is_below_lower = last['Close'] <= last['Env_Lower']
        
        # 2. 반등 변곡점 조건 (양봉 + 거래량 증가 또는 RSI 과매도 탈출)
        is_reversal = last['Close'] > last['Open'] # 양봉
        is_rsi_oversold = rsi < 35 # 과매도권
        is_vol_bump = last['Volume'] > prev['Volume'] * 1.2 # 전일비 거래량 증가
        
        # 핵심 로직: 하단선 근처에서 양봉이 뜨고 RSI가 낮을 때
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

    def check_futureon_isle(self, df):
        """퓨처온 이슬 멘토: 골드라인(EMA 33) 매매법"""
        if len(df) < 33: return False, []
        
        last = df.iloc[-1]
        prev = df.iloc[-5] # 5일 전과 비교
        
        # 골드라인 돌파 및 유지
        is_above = last['Close'] > last['GoldLine']
        is_sloping_up = last['GoldLine'] > prev['GoldLine']
        
        if is_above and is_sloping_up:
            return True, ["🏆 이슬 멘토: 골드라인(EMA 33) 지지 및 추세 안착"]
        return False, []

    def check_futureon_shintae(self, df):
        """퓨처온 신태 멘토: NS밴드(볼린저 하단) 지지 및 수급 분석"""
        if len(df) < 20: return False, []
        
        last = df.iloc[-1]
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
        
        # NS밴드(여기서는 볼린저 하단) 부근 지지
        is_supported = last['Low'] <= last['BB_Low'] * 1.02 # 하단 2% 이내
        is_rebound = last['Close'] > last['Open'] # 양봉
        is_vol_ok = last['Volume'] > avg_vol * 1.2 # 수급 확인
        
        if is_supported and is_rebound and is_vol_ok:
            return True, ["🏆 신태 멘토: NS밴드 하단 지지 및 수급 유입 확인"]
        return False, []

    def check_futureon_juns(self, df):
        """퓨처온 준S 멘토: 20일 기준선 지지 및 3파동(저점 상승) 확인"""
        if len(df) < 60: return False, []
        
        # 최근 60일간의 저점 확인
        lows = []
        for i in range(3): # 최근 3개의 주요 저점 (약식 구현)
            idx = - (i * 20) - 1
            if idx < -len(df): break
            lows.append(df['Low'].iloc[max(-len(df), idx-10) : idx].min())
        
        # 저점이 점점 높아지는가? (우상향 파동)
        is_wave_up = len(lows) >= 2 and lows[0] > lows[1]
        
        last = df.iloc[-1]
        is_above_base = last['Close'] > last['MA20'] # 기준선 위
        
        if is_above_base and is_wave_up:
            return True, ["🏆 준S 멘토: 20일 기준선 상단 및 우상향 파동 확인"]
        return False, []

    def find_horizontal_levels(self, df, window=120):
        """최근 데이터에서 주요 수평 지지/저항 가격대를 추출합니다."""
        if len(df) < window: return []
        
        recent_df = df.iloc[-window:]
        # 소수점 반올림하여 가격대 그룹화 (가독성 및 밀집도 확인용)
        # 가격대에 따라 rounding 정밀도 조절
        first_price = recent_df['Close'].iloc[0]
        if first_price > 100000: round_val = -3 # 1000원 단위
        elif first_price > 10000: round_val = -2 # 100원 단위
        elif first_price > 1000: round_val = -1 # 10원 단위
        else: round_val = 0 # 1원 단위
        
        # 고점과 저점들을 모아서 빈도수 체크
        levels = []
        # Local Max/Min 찾기 (간단한 방식)
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
        
        # 빈도수가 높은 상위 3~5개 레벨 추출
        from collections import Counter
        counts = Counter(levels)
        # 현재가와 너무 먼 레벨은 제외하고 상위 N개 선택
        current_price = df['Close'].iloc[-1]
        valid_ranges = [l for l, c in counts.most_common(10) if 0.7 * current_price < l < 1.3 * current_price]
        
        return sorted(valid_ranges[:5])

    def get_historical_data(self, symbol, market='KR', days=365):
        """차트용 역사적 데이터를 가져와 지표를 포함하여 반환합니다."""
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        df = None
        if market in ['KR', '한국 (KRX)']:
            df = fdr.DataReader(symbol, start_date)
        elif market in ['US', '미국 (US)']:
            df = fdr.DataReader(symbol, start_date)
        elif market in ['COIN', '암호화폐 (Upbit)']:
            df = pyupbit.get_ohlcv(symbol, interval="day", count=days)
            if df is not None:
                df.columns = [c.capitalize() for c in df.columns]
        
        if df is not None:
            df = self.add_indicators(df)
        return df

if __name__ == "__main__":
    scanner = StockScanner()
    # 테스트 실행
    print("삼성전자 분석 중...")
    print(scanner.analyze_stock('005930', 'KR'))
    print("애플 분석 중...")
    print(scanner.analyze_stock('AAPL', 'US'))

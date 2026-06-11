import FinanceDataReader as fdr
import yfinance as yf
import pyupbit
import pandas as pd
import datetime
import concurrent.futures
import time

from utils.indicators import add_indicators
from strategies.experts import (
    check_accumulation_bar, check_smart_money_flow, check_dante_bowl, 
    check_dante_256, check_gozack_box, check_hongingi, check_ap_investment, 
    check_aurora_signal, check_futureon_isle, check_futureon_shintae, 
    check_futureon_juns, check_day_trading_signal, check_katch_signal,
    check_fvg_mitigation, check_turtle_soup_long
)
from utils.logger import logger

# --- 한글 초성 검색용 데이터 ---
CHOSEONG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

def get_choseong(text):
    if not isinstance(text, str): return ""
    result = ""
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            result += CHOSEONG[(code - 0xAC00) // 588]
        else:
            result += char
    return result

def is_consonant_only(text):
    if not text: return False
    return all('ㄱ' <= char <= 'ㅎ' for char in text)

class StockScanner:
    def __init__(self):
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
        self.horizontal_levels = []

    def get_krx_symbols(self):
        try:
            df_krx = fdr.StockListing('KRX')
            if 'Code' not in df_krx.columns and 'Symbol' in df_krx.columns:
                df_krx['Code'] = df_krx['Symbol']
            return df_krx
        except Exception as e:
            logger.error(f"FinanceDataReader 조회 실패. pykrx 예비 수단 가동: {e}", exc_info=True)
            print(f"FinanceDataReader 조회 실패. pykrx 예비 수단 가동: {e}")
            try:
                from pykrx import stock
                today_dt = datetime.datetime.today()
                if today_dt.weekday() == 5: today_dt -= datetime.timedelta(days=1)
                elif today_dt.weekday() == 6: today_dt -= datetime.timedelta(days=2)
                
                today = today_dt.strftime("%Y%m%d")
                kospi = []
                for i in range(7):
                    check_date = (today_dt - datetime.timedelta(days=i)).strftime("%Y%m%d")
                    try:
                        kospi = stock.get_market_ticker_list(check_date, market="KOSPI")
                        if kospi:
                            today = check_date
                            break
                    except Exception:
                        continue
                
                kosdaq = stock.get_market_ticker_list(today, market="KOSDAQ")
                symbols = kospi + kosdaq
                if not symbols:
                    raise ValueError("pykrx에서 반환된 티커 리스트가 비어있습니다.")
                
                names = [stock.get_market_ticker_name(s) for s in symbols]
                return pd.DataFrame({'Code': symbols, 'Symbol': symbols, 'Name': names})
            except Exception as ex:
                logger.error(f"pykrx마저 실패: {ex}", exc_info=True)
                print(f"pykrx마저 실패: {ex}")
                return pd.DataFrame({
                    'Code': ['005930', '000660', '035420', '035720', '005380'], 
                    'Symbol': ['005930', '000660', '035420', '035720', '005380'], 
                    'Name': ['삼성전자', 'SK하이닉스', 'NAVER', '카카오', '현대차']
                })

    def get_us_symbols(self):
        try:
            return fdr.StockListing('S&P500')
        except:
            return pd.DataFrame({'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK-B', 'UNH', 'JNJ'],
                                 'Name': ['Apple', 'Microsoft', 'Alphabet', 'Amazon', 'Tesla', 'NVIDIA', 'Meta', 'Berkshire', 'UnitedHealth', 'J&J']})

    def get_coin_symbols(self):
        try:
            tickers = pyupbit.get_tickers(fiat="KRW")
            return pd.DataFrame({'Symbol': tickers, 'Name': [t.split("-")[1] for t in tickers]})
        except:
            return pd.DataFrame({'Symbol': ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-ADA'], 
                                 'Name': ['BTC', 'ETH', 'XRP', 'SOL', 'ADA']})

    def get_symbol_name(self, symbol, market='KR'):
        try:
            if market == 'KR':
                if not hasattr(self, '_krx_list'): self._krx_list = self.get_krx_symbols()
                code_col = 'Code' if 'Code' in self._krx_list.columns else 'Symbol'
                match = self._krx_list[self._krx_list[code_col] == symbol]
                if not match.empty: return match.iloc[0]['Name']
            elif market == 'US':
                if not hasattr(self, '_us_list'): self._us_list = self.get_us_symbols()
                match = self._us_list[self._us_list['Symbol'] == symbol]
                if not match.empty: return match.iloc[0]['Name']
                return yf.Ticker(symbol).info.get('longName', symbol)
            elif market == 'COIN':
                if not hasattr(self, '_coin_list'): self._coin_list = self.get_coin_symbols()
                match = self._coin_list[self._coin_list['Symbol'] == symbol]
                if not match.empty: return match.iloc[0]['Name']
        except: pass
        return symbol

    def find_symbol_by_name(self, name):
        if not name: return None, None
        results = self.search_symbols(name)
        if results: return results[0]['Symbol'], results[0]['Market']
        return None, None

    def search_symbols(self, query, limit=10):
        if not query: return []
        query_upper = query.upper()
        is_cons = is_consonant_only(query)
        matches = []
        
        # KRX
        if not hasattr(self, '_krx_list'): self._krx_list = self.get_krx_symbols()
        if 'Initials' not in self._krx_list.columns:
            self._krx_list['Initials'] = self._krx_list['Name'].apply(get_choseong)
        
        kr_df = self._krx_list
        code_col = 'Code' if 'Code' in kr_df.columns else 'Symbol'
        kr_match = kr_df[kr_df['Initials'].str.contains(query, na=False)] if is_cons else kr_df[
            kr_df['Name'].str.upper().str.contains(query_upper, na=False) | kr_df[code_col].str.upper().str.contains(query_upper, na=False)
        ]
        for _, row in kr_match.head(limit).iterrows():
            matches.append({'Symbol': row[code_col], 'Name': row['Name'], 'Market': 'KR', 'Display': f"🇰🇷 {row['Name']} ({row[code_col]})"})
            
        # COIN
        if not hasattr(self, '_coin_list'): self._coin_list = self.get_coin_symbols()
        if 'Initials' not in self._coin_list.columns:
            self._coin_list['Initials'] = self._coin_list['Name'].apply(get_choseong)
            
        coin_match = self._coin_list[self._coin_list['Initials'].str.contains(query, na=False)] if is_cons else self._coin_list[
            self._coin_list['Name'].str.upper().str.contains(query_upper, na=False) | self._coin_list['Symbol'].str.upper().str.contains(query_upper, na=False)
        ]
        for _, row in coin_match.head(limit).iterrows():
            matches.append({'Symbol': row['Symbol'], 'Name': row['Name'], 'Market': 'COIN', 'Display': f"🪙 {row['Name']} ({row['Symbol']})"})

        # US
        if not is_cons:
            if not hasattr(self, '_us_list'): self._us_list = self.get_us_symbols()
            us_match = self._us_list[
                self._us_list['Name'].str.upper().str.contains(query_upper, na=False) | self._us_list['Symbol'].str.upper().str.contains(query_upper, na=False)
            ]
            for _, row in us_match.head(limit).iterrows():
                matches.append({'Symbol': row['Symbol'], 'Name': row['Name'], 'Market': 'US', 'Display': f"🇺🇸 {row['Name']} ({row['Symbol']})"})
                
        return matches[:limit]

    def get_historical_data(self, symbol, market='KR', days=365):
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        df = None
        if market in ['KR', '한국 (KRX)']: df = fdr.DataReader(symbol, start_date)
        elif market in ['US', '미국 (US)']: df = fdr.DataReader(symbol, start_date)
        elif market in ['COIN', '암호화폐 (Upbit)']:
            df = pyupbit.get_ohlcv(symbol, interval="day", count=days)
            if df is not None: df.columns = [c.capitalize() for c in df.columns]
        
        if df is not None and len(df) >= 20:
            df = df.ffill().bfill()
            df, self.horizontal_levels = add_indicators(df)
        return df

    def analyze_stock(self, symbol, market='KR'):
        try:
            df = self.get_historical_data(symbol, market, 365)
            if df is None or len(df) < 200: return None

            last_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            change_rate = ((last_price - prev_price) / prev_price) * 100
            
            last_rsi = df['RSI'].iloc[-1]
            last_ma50 = df['MA50'].iloc[-1]
            last_ma200 = df['MA200'].iloc[-1]
            
            score = 0
            signals = []
            
            # A. 정배열
            if last_price > last_ma50 > last_ma200:
                score += 40; signals.append("정배열 완만 상승 중")
            elif last_price > last_ma50:
                score += 20; signals.append("단기 이평선 상단 위치")
                
            # B. RSI
            if 45 <= last_rsi <= 65:
                score += 30; signals.append("안정적 상승 모멘텀 (RSI)")
            elif last_rsi < 45:
                score += 10; signals.append("저점 매수 유효 구간")
                
            # C. 거래량 지표
            avg_vol_20 = df['Volume'].rolling(window=20).mean()
            current_vol = df['Volume'].rolling(window=5).mean()
            last_vol = df['Volume'].iloc[-1]
            
            if current_vol.iloc[-1] > avg_vol_20.iloc[-1] * 1.5:
                score += 30; signals.append("수급 증가 (거래량 폭발)")

            # F. 급등 임박
            surge_signal = False
            surge_reasons = []
            if last_vol > avg_vol_20.iloc[-1] * 2.5:
                surge_signal = True; surge_reasons.append("거래량 에너지 분출 (폭증)"); score += 20
            min_width = df['BB_Width'].rolling(window=30).min().iloc[-1]
            if df['BB_Width'].iloc[-1] <= min_width * 1.1:
                surge_reasons.append("변동성 응축 (볼린저 밴드 수축)"); score += 10
            if (df['Close'].iloc[-1] > df['Open'].iloc[-1] and df['Close'].iloc[-2] > df['Open'].iloc[-2] and df['Close'].iloc[-3] > df['Open'].iloc[-3]):
                surge_signal = True; surge_reasons.append("3일 연속 상승 캔들 발현"); score += 15

            if surge_signal: signals.append(f"🚀 급등 전조 신호: {' / '.join(surge_reasons)}")

            # D. 눌림목
            is_pullback = False
            if last_price > last_ma200 and last_price <= df['MA20'].iloc[-1] * 1.02:
                score += 20; is_pullback = True; signals.append("추세 내 눌림목(Pullback) 포착")

            # E. 세력 수급
            whale_score = 0
            if df['OBV'].iloc[-1] > df['OBV'].iloc[-5]:
                whale_score += 15; signals.append("세력 매집 흔적 포착 (OBV 우상향)")
            if df['MFI'].iloc[-1] > 55:
                whale_score += 15; signals.append("자금 유입 강세 (MFI)")
            elif df['MFI'].iloc[-1] < 30:
                signals.append("바닥권 자금 유입 준비 중")
            score += whale_score

            action = "HOLD"; action_desc = "관망"
            if score >= 70:
                action = "BUY"; action_desc = "강력 매수" if is_pullback else "추격 매수 가능"
            elif score >= 50:
                action = "BUY"; action_desc = "분할 매수 유효"
                
            if last_rsi >= 75:
                action = "SELL"; action_desc = "과매수 익절 권장"
            elif last_price < df['MA20'].iloc[-1] and score < 40:
                action = "SELL"; action_desc = "추세 이탈 우려 (매도/손절)"

            # 전문가 매매법
            dante_bowl, msg = check_dante_bowl(df)
            if dante_bowl: score += 25; signals.extend(msg)
            
            dante_256, msg = check_dante_256(df)
            if dante_256: score += 15; signals.extend(msg)
                
            gozack, msg = check_gozack_box(df)
            if gozack: score += 30; signals.extend(msg)
                
            acc_bar, msg = check_accumulation_bar(df)
            if acc_bar: score += 20; signals.extend(msg)
                
            money_flow, msg = check_smart_money_flow(df)
            if money_flow: score += 20; signals.extend(msg)

            hongingi, msg = check_hongingi(df)
            if hongingi: score += 35; signals.extend(msg)

            ap_inv, msg = check_ap_investment(df)
            if ap_inv: score += 30; signals.extend(msg)

            aurora_signal, msg = check_aurora_signal(df)
            if aurora_signal: score += 40; signals.extend(msg)

            isle, msg_isle = check_futureon_isle(df)
            shintae, msg_shintae = check_futureon_shintae(df)
            juns, msg_juns = check_futureon_juns(df)

            if isle: score += 25; signals.extend(msg_isle)
            if shintae: score += 25; signals.extend(msg_shintae)
            if juns: score += 25; signals.extend(msg_juns)

            day_trade, msg = check_day_trading_signal(df)
            if day_trade: score += 45; signals.extend(msg)

            katch_signal, msg = check_katch_signal(df)
            if katch_signal: score += 50; signals.extend(msg)

            # --- SMC / ICT 기법 연동 ---
            fvg_signal, fvg_msg, fvg_data = check_fvg_mitigation(df)
            turtle_signal, turtle_msg, turtle_data = check_turtle_soup_long(df)
            
            smc_data = None
            if fvg_signal:
                score += 30
                signals.extend(fvg_msg)
                smc_data = fvg_data
            elif turtle_signal:
                score += 40
                signals.extend(turtle_msg)
                smc_data = turtle_data

            # --- 돈깡 데이매매법 시나리오 타점 계산 ---
            try:
                # 돌파 타점: 당일 고가
                dk_breakout_buy = float(df['High'].iloc[-1])
                dk_breakout_stop = dk_breakout_buy * 0.97
                dk_breakout_target = dk_breakout_buy * 1.05
                
                # 눌림목 타점: 당일 (고가+저가+종가) / 3 (단기 평균단가)
                dk_support_buy = (float(df['High'].iloc[-1]) + float(df['Low'].iloc[-1]) + float(df['Close'].iloc[-1])) / 3.0
                dk_support_stop = dk_support_buy * 0.97
                dk_support_target = dk_support_buy * 1.05
                
                # 데이매매 적합도 평가 (거래량 급증 및 상승 추세)
                is_dk_suitable = (change_rate >= 1.5) and (last_vol > avg_vol_20.iloc[-1] * 1.2)
                
                donkkang_data = {
                    'suitable': bool(is_dk_suitable),
                    'breakout': {'buy': dk_breakout_buy, 'stop': dk_breakout_stop, 'target': dk_breakout_target},
                    'support': {'buy': dk_support_buy, 'stop': dk_support_stop, 'target': dk_support_target}
                }
            except Exception as e:
                logger.error(f"Donkkang calc error: {e}")
                donkkang_data = None

            # --- 일반 스윙 매매 시나리오 타점 계산 ---
            try:
                # 목표가 (익절): 최근 20일 기준 최고가 돌파 수치, 또는 보수적인 수익률(+10%) 중 더 높은 가격
                recent_20_high = float(df['High'].rolling(window=20).max().iloc[-1])
                target_price = max(last_price * 1.10, recent_20_high)
                
                # 손절선: 최근 10일 기준 최저가 이탈 수치, 또는 심리적 마지노선(-5%) 중 더 낮은 가격
                recent_10_low = float(df['Low'].rolling(window=10).min().iloc[-1])
                stop_price = min(last_price * 0.95, recent_10_low)
                
                general_scenario = {
                    'buy': last_price,
                    'stop': stop_price,
                    'target': target_price
                }
            except Exception as e:
                logger.error(f"General scenario calc error: {e}")
                general_scenario = None

            return {
                'symbol': symbol,
                'current_price': last_price,
                'change_rate': change_rate,
                'rsi': last_rsi,
                'score': min(100, score),
                'signals': ", ".join(signals),
                'action': action,
                'action_desc': action_desc,
                'experts': {'dante': dante_bowl or dante_256, 'gozack': gozack, 'hongingi': hongingi, 'ap_inv': ap_inv, 'katch': katch_signal, 'fvg': fvg_signal, 'turtle': turtle_signal},
                'smart_money': {'accumulation': acc_bar, 'money_flow': money_flow},
                'aurora': {'signal': aurora_signal, 'reasons': msg if aurora_signal else []},
                'futureon': {'isle': isle, 'shintae': shintae, 'juns': juns, 'reasons': msg_isle + msg_shintae + msg_juns},
                'donkkang': donkkang_data,
                'general_scenario': general_scenario,
                'smc': smc_data
            }
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            return None

    def calculate_whale_analysis(self, symbol, market='KR'):
        import numpy as np
        df = self.get_historical_data(symbol, market, 365)
        if df is None or len(df) < 20: return None
            
        period = min(120, len(df))
        recent_df = df.iloc[-period:].copy()
        
        window_size = min(20, len(recent_df))
        recent_df['MA20_Vol'] = recent_df['Volume'].rolling(window=window_size).mean().bfill()
        recent_df['Typical_Price'] = (recent_df['High'] + recent_df['Low'] + recent_df['Close']) / 3
        
        whale_days = recent_df[recent_df['Volume'] > recent_df['MA20_Vol'] * 1.8]
        if len(whale_days) < 3:
            top_vol_threshold = recent_df['Volume'].quantile(0.85)
            whale_days = recent_df[recent_df['Volume'] >= top_vol_threshold]
            
        def calc_vwap(sub_df):
            if sub_df.empty: return recent_df['Close'].iloc[-1]
            try:
                val = (sub_df['Typical_Price'] * sub_df['Volume']).sum() / sub_df['Volume'].sum()
                if np.isnan(val) or np.isinf(val): return recent_df['Close'].iloc[-1]
                return val
            except:
                return recent_df['Close'].iloc[-1]
                
        sub_short = whale_days[whale_days.index >= recent_df.index[-min(20, len(recent_df))]]
        price_whale_short = calc_vwap(sub_short)
        sub_mid = whale_days[whale_days.index >= recent_df.index[-min(60, len(recent_df))]]
        price_whale_mid = calc_vwap(sub_mid)
        price_whale_long = calc_vwap(whale_days)
        
        current_price = recent_df['Close'].iloc[-1]
        
        buy_zone_lower = price_whale_mid * 0.98
        buy_zone_upper = price_whale_mid * 1.03
        breakout_point = recent_df['High'].iloc[-min(20, len(recent_df)):].max()
        
        target_price_1 = price_whale_mid * 1.15
        target_price_2 = price_whale_mid * 1.30
        stop_loss = price_whale_long * 0.93
        
        near_resistances = [l for l in self.horizontal_levels if l > current_price]
        if near_resistances:
            target_price_1 = min(near_resistances[0], target_price_1)
            if target_price_1 <= current_price * 1.02: target_price_1 = price_whale_mid * 1.15
            if len(near_resistances) > 1:
                target_price_2 = min(near_resistances[1], target_price_2)
                if target_price_2 <= target_price_1: target_price_2 = target_price_1 * 1.15
        
        risk = max(1, current_price - stop_loss)
        reward = max(1, target_price_1 - current_price)
        rr_ratio = reward / risk if risk > 0 else 0.0
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'short_term_basis': price_whale_short,
            'mid_term_basis': price_whale_mid,
            'long_term_basis': price_whale_long,
            'buy_zone': (buy_zone_lower, buy_zone_upper),
            'breakout_point': breakout_point,
            'target_price_1': target_price_1,
            'target_price_2': target_price_2,
            'stop_loss': stop_loss,
            'rr_ratio': rr_ratio,
            'whale_activity_count': len(whale_days),
            'df': df
        }

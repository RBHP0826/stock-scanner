import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import datetime

# 테스트 날짜
target_date_str = "2026-06-17"
target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
start_date = (target_date - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
end_date = (target_date + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

print(f"Target: {target_date_str}, Range: {start_date} ~ {end_date}")

# 종목 리스트 10개만
tickers = ["005930.KS", "000660.KS", "035420.KS", "005380.KS", "068270.KS"]

df_chunk = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', threads=True, progress=False)

for ticker in tickers:
    if ticker not in df_chunk.columns.levels[0]:
        continue
    df_sym = df_chunk[ticker].dropna(subset=['Close'])
    if df_sym.empty:
        continue
    
    # target_date가 인덱스에 있는지 확인
    # yfinance 인덱스는 datetime 객체이므로 날짜 문자열 비교를 위해 format 변환 또는 date 비교
    df_sym.index = pd.to_datetime(df_sym.index)
    
    # target_date_str에 해당하는 행 찾기
    target_rows = df_sym[df_sym.index.strftime("%Y-%m-%d") == target_date_str]
    if target_rows.empty:
        print(f"{ticker}: {target_date_str} 데이터 없음 (공휴일 등)")
        continue
        
    # target_date의 위치 인덱스 구하기
    idx = df_sym.index.get_loc(target_rows.index[0])
    
    if idx > 0:
        prev_close = df_sym['Close'].iloc[idx-1]
        curr_close = df_sym['Close'].iloc[idx]
        curr_vol = df_sym['Volume'].iloc[idx]
        curr_amount = curr_close * curr_vol
        
        change_ratio = ((curr_close - prev_close) / prev_close) * 100.0
        print(f"{ticker} -> 종가: {curr_close}, 전일종가: {prev_close}, 등락률: {change_ratio:.2f}%, 거래대금: {curr_amount/100000000.0:.2f}억")
    else:
        print(f"{ticker}: 직전 영업일 데이터 없음")
